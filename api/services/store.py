"""
Service de stockage FaceIn.

Supporte deux backends configurables via la variable STORE_BACKEND :
- 'memory'   : stockage volatile en mémoire (CI et tests sans dépendance).
- 'postgres' : stockage persistant relationnel (PostgreSQL 16).
"""

from contextlib import contextmanager
import logging
import os
import threading
import time
from typing import Any, Dict, Generator, List, Optional

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
        self.users: set = set()
        self.revoked_jtis: Dict[str, float] = {}
        self.service_authorizations: Dict[tuple, str] = {}
        self.webauthn_credentials: Dict[str, Dict[str, Any]] = {}
        # Verrou garantissant l'atomicité de la création d'un nouvel utilisateur
        self._lock = threading.Lock()

    def ping(self) -> bool:
        return True

    def close(self) -> None:
        pass

    def clear(self) -> None:
        self.engagements.clear()
        self.nonces.clear()
        self.users.clear()
        self.revoked_jtis.clear()
        self.service_authorizations.clear()
        self.webauthn_credentials.clear()

    def user_exists(self, user_id: str) -> bool:
        return user_id in self.users or user_id in self.engagements

    # --- Engagements ---
    def save_engagement(self, user_id: str, commitment: str) -> None:
        self.users.add(user_id)
        self.engagements[user_id] = {
            "user_id": user_id,
            "commitment": commitment,
            "statut": "actif",
        }

    def create_user_with_engagement(self, user_id: str, commitment: str) -> bool:
        """
        Crée atomiquement un nouvel utilisateur et son engagement actif.

        Retourne False (sans rien modifier) si l'identifiant existe déjà.
        """
        with self._lock:
            if self.user_exists(user_id):
                return False
            self.save_engagement(user_id, commitment)
            return True

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

    # --- Révocation JWT & Autorisations par service ---
    def save_revoked_jti(self, jti: str, expires_at: float) -> None:
        self.revoked_jtis[jti] = float(expires_at)

    def is_jti_revoked(self, jti: str, now: Optional[float] = None) -> bool:
        exp = self.revoked_jtis.get(jti)
        if exp is None:
            return False
        current_time = time.time() if now is None else float(now)
        if exp < current_time:
            del self.revoked_jtis[jti]
            return False
        return True

    def set_service_authorization(
        self, user_id: str, service_name: str, statut: str = "actif"
    ) -> None:
        self.service_authorizations[(user_id, service_name)] = statut

    def is_service_authorized(self, user_id: str, service_name: str) -> bool:
        statut = self.service_authorizations.get((user_id, service_name))
        if statut == "revoque":
            return False
        strict = os.getenv("STRICT_SERVICE_AUTH", "false").strip().lower() in {
            "1", "true", "yes"
        }
        if strict:
            return statut == "actif"
        return True

    # --- Passkeys WebAuthn ---
    def add_webauthn_credential(
        self,
        user_id: str,
        credential_id: str,
        public_key: bytes,
        sign_count: int,
        transports: Optional[List[str]] = None,
    ) -> bool:
        """Enregistre une passkey ; False si l'identifiant existe déjà ou l'utilisateur est inconnu."""
        with self._lock:
            if not self.user_exists(user_id) or credential_id in self.webauthn_credentials:
                return False
            self.webauthn_credentials[credential_id] = {
                "user_id": user_id,
                "credential_id": credential_id,
                "public_key": bytes(public_key),
                "sign_count": int(sign_count),
                "transports": list(transports or []),
                "statut": "actif",
            }
            return True

    def get_webauthn_credentials(self, user_id: str) -> List[Dict[str, Any]]:
        return [
            dict(c)
            for c in self.webauthn_credentials.values()
            if c["user_id"] == user_id and c["statut"] == "actif"
        ]

    def update_webauthn_sign_count(self, credential_id: str, ancien: int, nouveau: int) -> bool:
        """Mise à jour conditionnelle : échoue si le compteur a changé entre-temps."""
        with self._lock:
            c = self.webauthn_credentials.get(credential_id)
            if not c or c["statut"] != "actif" or c["sign_count"] != int(ancien):
                return False
            c["sign_count"] = int(nouveau)
            return True


# =====================================================================
# Backend 2 : PostgreSQL
# =====================================================================
class PostgresStore:
    """Store persistant branché sur le schéma PostgreSQL 16 de FaceIn."""

    def __init__(self, database_url: Optional[str] = None):
        if psycopg2 is None or pool is None:
            raise ImportError(
                "Le module 'psycopg2' est requis pour utiliser le backend 'postgres'."
            )
        self.database_url = database_url or os.getenv(
            "DATABASE_URL",
            "postgresql://facein_user:facein_password@localhost:5432/facein",
        )
        # ThreadedConnectionPool pour accès multithread concurrent sécurisé
        self._pool = pool.ThreadedConnectionPool(minconn=2, maxconn=20, dsn=self.database_url)

    def ping(self) -> bool:
        """Contrôle de disponibilité de la base de données au démarrage."""
        try:
            with self.get_cursor() as cur:
                cur.execute("SELECT 1;")
                row = cur.fetchone()
                return bool(row and row[0] == 1)
        except Exception as exc:
            logger.warning("Échec du contrôle de disponibilité PostgreSQL : %s", exc)
            return False

    def close(self) -> None:
        """Ferme proprement toutes les connexions du pool au shutdown."""
        if self._pool is not None:
            try:
                self._pool.closeall()
                logger.info("Pool de connexions PostgreSQL fermé avec succès.")
            except Exception as exc:
                logger.warning("Erreur lors de la fermeture du pool PostgreSQL : %s", exc)
            finally:
                self._pool = None

    @contextmanager
    def get_cursor(self) -> Generator:
        if self._pool is None:
            raise RuntimeError("Le pool de connexions PostgreSQL est fermé.")
        conn = self._pool.getconn()
        try:
            with conn:
                with conn.cursor() as cursor:
                    yield cursor
        finally:
            if self._pool is not None:
                self._pool.putconn(conn)

    def user_exists(self, user_id: str) -> bool:
        """Vérifie l'existence de l'utilisateur indépendamment de l'état de son engagement."""
        with self.get_cursor() as cur:
            cur.execute("SELECT 1 FROM utilisateurs WHERE nom = %s LIMIT 1;", (user_id,))
            return cur.fetchone() is not None

    def clear(self) -> None:
        """TRUNCATE destructeur sécurisé (autorisé uniquement si explicitement configuré pour les tests)."""
        allow_reset = os.getenv("ALLOW_DESTRUCTIVE_STORE_RESET", "false").strip().lower() in {
            "1", "true", "yes"
        }
        if not allow_reset:
            logger.warning(
                "Tentative de clear() sur PostgreSQL ignorée : ALLOW_DESTRUCTIVE_STORE_RESET n'est pas activé."
            )
            return
        with self.get_cursor() as cur:
            cur.execute(
                "TRUNCATE TABLE nonces, engagements_cryptographiques, utilisateurs CASCADE;"
            )

    # --- Engagements atomiques ---
    def save_engagement(self, user_id: str, commitment: str) -> None:
        """Enregistre un engagement de façon atomique et sans race condition."""
        with self.get_cursor() as cur:
            # Upsert atomique de l'utilisateur (gère les accès concurrents sans doublons)
            cur.execute(
                """
                INSERT INTO utilisateurs (nom)
                VALUES (%s)
                ON CONFLICT (nom) DO UPDATE SET nom = EXCLUDED.nom
                RETURNING id;
                """,
                (user_id,),
            )
            user_uuid = cur.fetchone()[0]

            # Révocation des anciens engagements actifs dans la même transaction
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

    def create_user_with_engagement(self, user_id: str, commitment: str) -> bool:
        """
        Crée atomiquement un nouvel utilisateur et son engagement actif.

        L'INSERT ... ON CONFLICT DO NOTHING s'appuie sur la contrainte UNIQUE de
        utilisateurs.nom : en cas d'inscriptions concurrentes du même identifiant,
        une seule transaction crée la ligne, les autres ne modifient rien.
        Retourne False si l'identifiant existe déjà.
        """
        with self.get_cursor() as cur:
            cur.execute(
                """
                INSERT INTO utilisateurs (nom)
                VALUES (%s)
                ON CONFLICT (nom) DO NOTHING
                RETURNING id;
                """,
                (user_id,),
            )
            row = cur.fetchone()
            if row is None:
                return False
            cur.execute(
                """
                INSERT INTO engagements_cryptographiques (utilisateur_id, valeur, algorithme, statut)
                VALUES (%s, %s, 'poseidon', 'actif');
                """,
                (row[0], commitment),
            )
            return True

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

    # --- Nonces atomiques ---
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
        """Consommation atomique via DELETE ... RETURNING en une seule opération SQL."""
        current_time = time.time() if now is None else float(now)
        with self.get_cursor() as cur:
            if user_id is not None:
                cur.execute(
                    """
                    DELETE FROM nonces
                    WHERE nonce = %s AND user_id = %s AND expires_at >= %s
                    RETURNING nonce;
                    """,
                    (nonce, user_id, float(current_time)),
                )
            else:
                cur.execute(
                    """
                    DELETE FROM nonces
                    WHERE nonce = %s AND expires_at >= %s
                    RETURNING nonce;
                    """,
                    (nonce, float(current_time)),
                )
            return cur.fetchone() is not None

    def purge_expired_nonces(self, now: Optional[float] = None) -> int:
        current_time = time.time() if now is None else float(now)
        with self.get_cursor() as cur:
            cur.execute(
                "DELETE FROM nonces WHERE expires_at < %s;",
                (float(current_time),),
            )
            return cur.rowcount

    # --- Révocation JWT & Autorisations par service ---
    def save_revoked_jti(self, jti: str, expires_at: float) -> None:
        with self.get_cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS tokens_revoques (
                    jti VARCHAR(255) PRIMARY KEY,
                    expires_at DOUBLE PRECISION NOT NULL
                );
                """
            )
            cur.execute(
                """
                INSERT INTO tokens_revoques (jti, expires_at)
                VALUES (%s, %s)
                ON CONFLICT (jti) DO UPDATE SET expires_at = EXCLUDED.expires_at;
                """,
                (jti, float(expires_at)),
            )

    def is_jti_revoked(self, jti: str, now: Optional[float] = None) -> bool:
        current_time = time.time() if now is None else float(now)
        with self.get_cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS tokens_revoques (
                    jti VARCHAR(255) PRIMARY KEY,
                    expires_at DOUBLE PRECISION NOT NULL
                );
                """
            )
            cur.execute(
                "SELECT expires_at FROM tokens_revoques WHERE jti = %s;",
                (jti,),
            )
            row = cur.fetchone()
            if not row:
                return False
            if float(row[0]) < current_time:
                cur.execute("DELETE FROM tokens_revoques WHERE jti = %s;", (jti,))
                return False
            return True

    def set_service_authorization(
        self, user_id: str, service_name: str, statut: str = "actif"
    ) -> None:
        if statut not in ("actif", "revoque"):
            raise ValueError(f"Statut d'autorisation invalide : '{statut}'")
        with self.get_cursor() as cur:
            cur.execute(
                """
                INSERT INTO utilisateurs (nom)
                VALUES (%s)
                ON CONFLICT (nom) DO UPDATE SET nom = EXCLUDED.nom
                RETURNING id;
                """,
                (user_id,),
            )
            user_uuid = cur.fetchone()[0]
            cur.execute(
                """
                INSERT INTO services (nom, cle_publique)
                VALUES (%s, '')
                ON CONFLICT (nom) DO UPDATE SET nom = EXCLUDED.nom
                RETURNING id;
                """,
                (service_name,),
            )
            service_uuid = cur.fetchone()[0]
            cur.execute(
                """
                INSERT INTO autorisations_service (utilisateur_id, service_id, statut)
                VALUES (%s, %s, %s)
                ON CONFLICT (utilisateur_id, service_id) DO UPDATE
                SET statut = EXCLUDED.statut;
                """,
                (user_uuid, service_uuid, statut),
            )

    def is_service_authorized(self, user_id: str, service_name: str) -> bool:
        with self.get_cursor() as cur:
            cur.execute(
                """
                SELECT a.statut
                FROM autorisations_service a
                JOIN utilisateurs u ON u.id = a.utilisateur_id
                JOIN services s ON s.id = a.service_id
                WHERE u.nom = %s AND s.nom = %s
                LIMIT 1;
                """,
                (user_id, service_name),
            )
            row = cur.fetchone()
            if row and row[0] == "revoque":
                return False
            strict = os.getenv("STRICT_SERVICE_AUTH", "false").strip().lower() in {
                "1", "true", "yes"
            }
            if strict:
                return bool(row and row[0] == "actif")
            return True

    # --- Passkeys WebAuthn ---
    def add_webauthn_credential(
        self,
        user_id: str,
        credential_id: str,
        public_key: bytes,
        sign_count: int,
        transports: Optional[List[str]] = None,
    ) -> bool:
        """Enregistre une passkey ; False si l'identifiant existe déjà ou l'utilisateur est inconnu."""
        with self.get_cursor() as cur:
            cur.execute(
                """
                INSERT INTO cles_webauthn
                    (utilisateur_id, credential_id, cle_publique, compteur, transports)
                SELECT u.id, %s, %s, %s, %s
                FROM utilisateurs u WHERE u.nom = %s
                ON CONFLICT (credential_id) DO NOTHING
                RETURNING id;
                """,
                (
                    credential_id,
                    psycopg2.Binary(bytes(public_key)),
                    int(sign_count),
                    ",".join(transports or []),
                    user_id,
                ),
            )
            return cur.fetchone() is not None

    def get_webauthn_credentials(self, user_id: str) -> List[Dict[str, Any]]:
        with self.get_cursor() as cur:
            cur.execute(
                """
                SELECT k.credential_id, k.cle_publique, k.compteur, k.transports
                FROM cles_webauthn k
                JOIN utilisateurs u ON u.id = k.utilisateur_id
                WHERE u.nom = %s AND k.statut = 'actif';
                """,
                (user_id,),
            )
            return [
                {
                    "user_id": user_id,
                    "credential_id": row[0],
                    "public_key": bytes(row[1]),
                    "sign_count": int(row[2]),
                    "transports": [t for t in (row[3] or "").split(",") if t],
                }
                for row in cur.fetchall()
            ]

    def update_webauthn_sign_count(self, credential_id: str, ancien: int, nouveau: int) -> bool:
        """Mise à jour atomique conditionnelle du compteur (détection d'usage concurrent)."""
        with self.get_cursor() as cur:
            cur.execute(
                """
                UPDATE cles_webauthn
                SET compteur = %s, derniere_utilisation = now()
                WHERE credential_id = %s AND compteur = %s AND statut = 'actif'
                RETURNING id;
                """,
                (int(nouveau), credential_id, int(ancien)),
            )
            return cur.fetchone() is not None


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


def close_store() -> None:
    """Ferme proprement le store actif et ses connexions."""
    global _current_store
    if _current_store is not None:
        if hasattr(_current_store, "close"):
            _current_store.close()
        _current_store = None


def reset_store() -> None:
    """Réinitialise les données du store et libère l'instance."""
    backend = os.getenv("STORE_BACKEND", "memory").lower()
    if backend == "memory":
        if isinstance(_current_store, MemoryStore):
            _current_store.clear()
    elif backend in ("postgres", "postgresql"):
        allow_reset = os.getenv("ALLOW_DESTRUCTIVE_STORE_RESET", "false").strip().lower() in {
            "1", "true", "yes"
        }
        if allow_reset:
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
        else:
            logger.info("reset_store() ignoré sur PostgreSQL (protection contre le TRUNCATE intempestif).")

    close_store()


# Fonctions de compatibilité pour les routes
def save_commitment(user_id: str, commitment: str) -> None:
    get_store().save_engagement(user_id, commitment)


def register_new_commitment(user_id: str, commitment: str) -> bool:
    """Inscription atomique : False si l'identifiant est déjà enregistré."""
    return get_store().create_user_with_engagement(user_id, commitment)


def get_commitment(user_id: str) -> Optional[str]:
    e = get_store().get_engagement(user_id)
    return e["commitment"] if e else None


def user_exists(user_id: str) -> bool:
    return get_store().user_exists(user_id)


def save_nonce(nonce: str, user_id: str, expires_at: float) -> None:
    get_store().save_nonce(nonce, user_id, expires_at)


def verify_nonce(nonce: str, user_id: str) -> bool:
    return get_store().consume_nonce(nonce, user_id)


def save_revoked_jti(jti: str, expires_at: float) -> None:
    get_store().save_revoked_jti(jti, expires_at)


def is_jti_revoked(jti: str) -> bool:
    return get_store().is_jti_revoked(jti)


def set_service_authorization(
    user_id: str, service_name: str, statut: str = "actif"
) -> None:
    get_store().set_service_authorization(user_id, service_name, statut)


def is_service_authorized(user_id: str, service_name: str) -> bool:
    return get_store().is_service_authorized(user_id, service_name)


def add_webauthn_credential(
    user_id: str,
    credential_id: str,
    public_key: bytes,
    sign_count: int,
    transports: Optional[List[str]] = None,
) -> bool:
    return get_store().add_webauthn_credential(
        user_id, credential_id, public_key, sign_count, transports
    )


def get_webauthn_credentials(user_id: str) -> List[Dict[str, Any]]:
    return get_store().get_webauthn_credentials(user_id)


def update_webauthn_sign_count(credential_id: str, ancien: int, nouveau: int) -> bool:
    return get_store().update_webauthn_sign_count(credential_id, ancien, nouveau)
