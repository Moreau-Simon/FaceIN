"""
Service de stockage FaceIn.

Supporte deux backends configurables via la variable STORE_BACKEND :
- 'memory'   : stockage volatile en mémoire (CI et tests sans dépendance).
- 'postgres' : stockage persistant relationnel (PostgreSQL 16).
"""

from contextlib import contextmanager
import logging
import os
import time
from typing import Any, Dict, Generator, Optional

try:
    import psycopg2
    from psycopg2 import pool
except ImportError:
    psycopg2 = None
    pool = None

logger = logging.getLogger("facein.store")


# =====================================================================
# Backend 1 : Mémoire (In-Memory)
# =====================================================================
class MemoryStore:
    """Store volatile en mémoire pour la CI et les tests rapides."""

    def __init__(self):
        self.engagements: Dict[str, Dict[str, Any]] = {}
        self.nonces: Dict[str, Dict[str, Any]] = {}

    def clear(self) -> None:
        self.engagements.clear()
        self.nonces.clear()

    # --- Engagements ---
    def save_engagement(self, user_id: str, commitment: str) -> None:
        self.engagements[user_id] = {
            "user_id": user_id,
            "commitment": commitment,
            "statut": "actif",
        }

    def get_engagement(self, user_id: str) -> Optional[Dict[str, str]]:
        e = self.engagements.get(user_id)
        if e and e.get("statut") == "actif":
            return {"user_id": user_id, "commitment": e["commitment"]}
        return None

    def revoke_engagement(self, user_id: str, reason: Optional[str] = None) -> bool:
        e = self.engagements.get(user_id)
        if e and e.get("statut") == "actif":
            e["statut"] = "revoque"
            return True
        return False

    # --- Nonces ---
    def save_nonce(self, nonce: str, user_id: str, expires_at: float) -> None:
        self.nonces[nonce] = {
            "user_id": user_id,
            "expires_at": float(expires_at),
        }

    def consume_nonce(
        self, nonce: str, user_id: Optional[str] = None, now: Optional[float] = None
    ) -> bool:
        current_time = time.time() if now is None else float(now)
        item = self.nonces.get(nonce)
        if not item:
            return False
        if user_id is not None and item["user_id"] != user_id:
            return False
        if item["expires_at"] < current_time:
            return False

        del self.nonces[nonce]
        return True

    def purge_expired_nonces(self, now: Optional[float] = None) -> int:
        current_time = time.time() if now is None else float(now)
        expired = [n for n, item in self.nonces.items() if item["expires_at"] < current_time]
        for n in expired:
            del self.nonces[n]
        return len(expired)


# =====================================================================
# Backend 2 : PostgreSQL
# =====================================================================
class PostgresStore:
    """Store persistant branché sur le schéma PostgreSQL 16 de FaceIn."""

    def __init__(self):
        if psycopg2 is None:
            raise ImportError(
                "Le module 'psycopg2' est requis pour utiliser le backend 'postgres'."
            )
        self.database_url = os.getenv(
            "DATABASE_URL",
            "postgresql://facein_user:facein_password@localhost:5432/facein",
        )
        self._pool = pool.SimpleConnectionPool(minconn=1, maxconn=10, dsn=self.database_url)

    @contextmanager
    def get_cursor(self) -> Generator:
        conn = self._pool.getconn()
        try:
            with conn:
                with conn.cursor() as cursor:
                    yield cursor
        finally:
            self._pool.putconn(conn)

    def clear(self) -> None:
        with self.get_cursor() as cur:
            cur.execute(
                "TRUNCATE TABLE nonces, engagements_cryptographiques, utilisateurs CASCADE;"
            )

    # --- Engagements ---
    def save_engagement(self, user_id: str, commitment: str) -> None:
        with self.get_cursor() as cur:
            # Récupération ou création de l'utilisateur
            cur.execute("SELECT id FROM utilisateurs WHERE nom = %s LIMIT 1;", (user_id,))
            row = cur.fetchone()
            if row:
                user_uuid = row[0]
            else:
                cur.execute(
                    "INSERT INTO utilisateurs (nom) VALUES (%s) RETURNING id;",
                    (user_id,),
                )
                user_uuid = cur.fetchone()[0]

            # Révocation des anciens engagements actifs (maintient l'unicité actif)
            cur.execute(
                """
                UPDATE engagements_cryptographiques
                SET statut = 'revoque', date_revocation = now()
                WHERE utilisateur_id = %s AND statut = 'actif';
                """,
                (user_uuid,),
            )

            # Insertion du nouvel engagement actif
            cur.execute(
                """
                INSERT INTO engagements_cryptographiques (utilisateur_id, valeur, algorithme, statut)
                VALUES (%s, %s, 'poseidon', 'actif');
                """,
                (user_uuid, commitment),
            )

    def get_engagement(self, user_id: str) -> Optional[Dict[str, str]]:
        with self.get_cursor() as cur:
            cur.execute(
                """
                SELECT ec.valeur
                FROM engagements_cryptographiques ec
                JOIN utilisateurs u ON u.id = ec.utilisateur_id
                WHERE u.nom = %s AND ec.statut = 'actif'
                ORDER BY ec.date_creation DESC
                LIMIT 1;
                """,
                (user_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            return {"user_id": user_id, "commitment": row[0]}

    def revoke_engagement(self, user_id: str, reason: Optional[str] = None) -> bool:
        with self.get_cursor() as cur:
            cur.execute(
                """
                UPDATE engagements_cryptographiques ec
                SET statut = 'revoque', date_revocation = now()
                FROM utilisateurs u
                WHERE ec.utilisateur_id = u.id
                  AND u.nom = %s
                  AND ec.statut = 'actif';
                """,
                (user_id,),
            )
            return cur.rowcount > 0

    # --- Nonces ---
    def save_nonce(self, nonce: str, user_id: str, expires_at: float) -> None:
        with self.get_cursor() as cur:
            cur.execute(
                """
                INSERT INTO nonces (nonce, user_id, expires_at)
                VALUES (%s, %s, %s)
                ON CONFLICT (nonce) DO UPDATE
                SET user_id = EXCLUDED.user_id, expires_at = EXCLUDED.expires_at;
                """,
                (nonce, user_id, float(expires_at)),
            )

    def consume_nonce(
        self, nonce: str, user_id: Optional[str] = None, now: Optional[float] = None
    ) -> bool:
        current_time = time.time() if now is None else float(now)
        with self.get_cursor() as cur:
            cur.execute(
                "SELECT user_id, expires_at FROM nonces WHERE nonce = %s;",
                (nonce,),
            )
            row = cur.fetchone()
            if not row:
                return False

            stored_user_id, expires_at = row
            if user_id is not None and stored_user_id != user_id:
                return False
            if expires_at < current_time:
                return False

            cur.execute("DELETE FROM nonces WHERE nonce = %s;", (nonce,))
            return True

    def purge_expired_nonces(self, now: Optional[float] = None) -> int:
        current_time = time.time() if now is None else float(now)
        with self.get_cursor() as cur:
            cur.execute(
                "DELETE FROM nonces WHERE expires_at < %s;",
                (float(current_time),),
            )
            return cur.rowcount


# =====================================================================
# Factory et gestion du cycle de vie
# =====================================================================
_current_store = None


def get_store():
    """Initialise et retourne le singleton du store selon STORE_BACKEND."""
    global _current_store
    if _current_store is not None:
        return _current_store

    backend = os.getenv("STORE_BACKEND", "memory").lower()
    if backend == "memory":
        _current_store = MemoryStore()
    elif backend in ("postgres", "postgresql"):
        _current_store = PostgresStore()
    else:
        raise ValueError(f"Backend de stockage non supporté : '{backend}'")

    return _current_store


def reset_store() -> None:
    """Réinitialise les données du store et libère l'instance."""
    global _current_store
    backend = os.getenv("STORE_BACKEND", "memory").lower()
    if backend == "memory":
        if isinstance(_current_store, MemoryStore):
            _current_store.clear()
    elif backend in ("postgres", "postgresql"):
        db_url = os.getenv(
            "DATABASE_URL",
            "postgresql://facein_user:facein_password@localhost:5432/facein",
        )
        try:
            if psycopg2 is not None:
                conn = psycopg2.connect(db_url)
                with conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            "TRUNCATE TABLE nonces, engagements_cryptographiques, utilisateurs CASCADE;"
                        )
                conn.close()
        except Exception as e:
            logger.debug("Erreur lors de la purge PostgreSQL : %s", e)

    _current_store = None


# Fonctions de compatibilité pour d'éventuels anciens modules
def save_commitment(user_id: str, commitment: str) -> None:
    get_store().save_engagement(user_id, commitment)


def get_commitment(user_id: str) -> Optional[str]:
    e = get_store().get_engagement(user_id)
    return e["commitment"] if e else None


def user_exists(user_id: str) -> bool:
    return get_store().get_engagement(user_id) is not None


def save_nonce(nonce: str, user_id: str, expires_at: float) -> None:
    get_store().save_nonce(nonce, user_id, expires_at)


def verify_nonce(nonce: str, user_id: str) -> bool:
    return get_store().consume_nonce(nonce, user_id)