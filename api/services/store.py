"""
Service de stockage SQLite pour FaceIn.

Gère la persistance des engagements biométriques (commitments Poseidon)
et des nonces anti-rejeu éphémères.
"""

from contextlib import contextmanager
from datetime import datetime, timezone
import logging
import os
import sqlite3
import time
from typing import Generator, Optional

logger = logging.getLogger("facein.store")

# Emplacement de la base de données SQLite
DEFAULT_DB_PATH = os.path.normpath(
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "facein.db")
)
DB_PATH = os.getenv("FACEIN_DB_PATH", DEFAULT_DB_PATH)


@contextmanager
def get_db_cursor(db_path: Optional[str] = None) -> Generator[sqlite3.Cursor, None, None]:
    """Gestionnaire de contexte ouvrant, committant et fermant proprement la connexion SQLite."""
    path = db_path or DB_PATH
    conn = sqlite3.connect(path)
    try:
        with conn:
            yield conn.cursor()
    finally:
        conn.close()


def init_db(db_path: Optional[str] = None) -> None:
    """
    Initialise les tables de la base de données SQLite :
    - engagements : stockage des engagements Poseidon associés à chaque utilisateur
    - nonces : stockage des défis d'authentification temporaires
    """
    path = db_path or DB_PATH
    with get_db_cursor(path) as cursor:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS engagements (
                user_id TEXT PRIMARY KEY,
                commitment TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS nonces (
                nonce TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                expires_at REAL NOT NULL
            )
            """
        )
    logger.info("Base de données initialisée sur : %s", path)


def save_commitment(user_id: str, commitment: str, db_path: Optional[str] = None) -> None:
    """
    Enregistre l'engagement biométrique initial pour un utilisateur.

    Lève sqlite3.IntegrityError si l'utilisateur existe déjà.
    """
    path = db_path or DB_PATH
    created_at = datetime.now(timezone.utc).isoformat()
    with get_db_cursor(path) as cursor:
        cursor.execute(
            """
            INSERT INTO engagements (user_id, commitment, created_at)
            VALUES (?, ?, ?)
            """,
            (user_id, commitment, created_at),
        )
    logger.info("Engagement enregistré pour l'utilisateur '%s'", user_id)


def get_commitment(user_id: str, db_path: Optional[str] = None) -> Optional[str]:
    """
    Récupère l'engagement d'un utilisateur donné.
    Retourne None si l'utilisateur n'est pas trouvé.
    """
    path = db_path or DB_PATH
    with get_db_cursor(path) as cursor:
        cursor.execute(
            "SELECT commitment FROM engagements WHERE user_id = ?",
            (user_id,),
        )
        row = cursor.fetchone()
        return row[0] if row else None


def user_exists(user_id: str, db_path: Optional[str] = None) -> bool:
    """Vérifie si un utilisateur possède déjà un engagement enregistré."""
    path = db_path or DB_PATH
    with get_db_cursor(path) as cursor:
        cursor.execute(
            "SELECT 1 FROM engagements WHERE user_id = ?",
            (user_id,),
        )
        return cursor.fetchone() is not None


def save_nonce(nonce: str, user_id: str, expires_at: float, db_path: Optional[str] = None) -> None:
    """Enregistre un nonce avec une date d'expiration en secondes (timestamp Unix)."""
    path = db_path or DB_PATH
    with get_db_cursor(path) as cursor:
        cursor.execute(
            """
            INSERT OR REPLACE INTO nonces (nonce, user_id, expires_at)
            VALUES (?, ?, ?)
            """,
            (nonce, user_id, float(expires_at)),
        )


def verify_nonce(nonce: str, user_id: str, db_path: Optional[str] = None) -> bool:
    """
    Vérifie qu'un nonce est valide, correspond à l'utilisateur et n'est pas expiré.
    Le nonce est systématiquement supprimé après lecture (usage unique / anti-rejeu).
    """
    path = db_path or DB_PATH
    now = time.time()
    with get_db_cursor(path) as cursor:
        cursor.execute(
            "SELECT expires_at FROM nonces WHERE nonce = ? AND user_id = ?",
            (nonce, user_id),
        )
        row = cursor.fetchone()
        if not row:
            logger.warning("Nonce inconnu ou ne correspondant pas à l'utilisateur '%s'", user_id)
            return False

        expires_at = row[0]
        # Suppression immédiate pour empêcher toute réutilisation
        cursor.execute("DELETE FROM nonces WHERE nonce = ?", (nonce,))

        if expires_at < now:
            logger.warning("Nonce expiré pour l'utilisateur '%s'", user_id)
            return False

        return True


# Initialisation automatique des tables au chargement du module
init_db()
