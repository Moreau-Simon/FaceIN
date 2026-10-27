"""
Gestionnaire de jetons d'accès JWT (JSON Web Tokens).

Permet d'émettre un jeton signé après authentification réussie
et de valider son intégrité ainsi que sa durée de vie (1 heure).
"""

import logging
import os
import time
from typing import Any, Optional

try:
    import jwt
except ImportError:
    jwt = None  # type: ignore

logger = logging.getLogger("facein.jwt_manager")

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "facein-secret-key-super-securisee-but3-sae-2026")
ALGORITHM = "HS256"
EXPIRATION_SECONDS = 3600  # Validité de 1 heure


def generate_token(user_id: str) -> str:
    """
    Génère un jeton JWT contenant :
    - user_id : identifiant de l'utilisateur authentifié
    - iat : date d'émission (timestamp Unix)
    - exp : date d'expiration (iat + 1h)

    Signé avec la clé secrète en algorithme HS256.
    """
    if jwt is None:
        raise RuntimeError("La bibliothèque 'PyJWT' est requise pour générer un jeton.")

    now = int(time.time())
    payload = {
        "user_id": user_id,
        "iat": now,
        "exp": now + EXPIRATION_SECONDS,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> Optional[dict[str, Any]]:
    """
    Décode et valide un jeton JWT.

    Retourne le dictionnaire du payload si valide, None en cas d'expiration ou d'altération.
    """
    if jwt is None:
        raise RuntimeError("La bibliothèque 'PyJWT' est requise pour vérifier un jeton.")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Jeton JWT expiré.")
        return None
    except jwt.InvalidTokenError as exc:
        logger.warning("Jeton JWT invalide : %s", exc)
        return None
