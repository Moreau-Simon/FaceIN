"""
Route de génération de nonce anti-rejeu éphémère.

Fournit au client un défi cryptographique aléatoire de 32 octets (64 caractères hexadécimaux)
valide pendant 60 secondes pour la construction de la preuve ZKP.
"""

import logging
import secrets
import time
from fastapi import APIRouter
from pydantic import BaseModel, Field

try:
    from services.store import save_nonce
except ImportError:
    from api.services.store import save_nonce

logger = logging.getLogger("facein.routes.nonce")

router = APIRouter()

DUREE_NONCE_SECONDES = 60


class NonceResponse(BaseModel):
    nonce: str = Field(..., description="Valeur hexadécimale aléatoire de 32 octets (anti-rejeu)")
    expires_at: int = Field(..., description="Timestamp Unix d'expiration (en secondes)")


@router.get(
    "/nonce/{user_id}",
    response_model=NonceResponse,
    summary="Génération d'un nonce anti-rejeu",
    description="Génère un nonce unique à usage unique valide pendant 60 secondes pour un utilisateur donné.",
)
def get_nonce(user_id: str) -> NonceResponse:
    # 32 octets aléatoires sous forme hexadécimale
    nonce = secrets.token_hex(32)
    expires_at = int(time.time() + DUREE_NONCE_SECONDES)

    save_nonce(nonce=nonce, user_id=user_id, expires_at=expires_at)
    logger.info("Nonce généré pour l'utilisateur '%s' (expiration dans 60s)", user_id)

    return NonceResponse(
        nonce=nonce,
        expires_at=expires_at,
    )
