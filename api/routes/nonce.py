"""
Route de génération de nonce anti-rejeu éphémère.

Fournit au client un défi cryptographique aléatoire de 32 octets (64 caractères hexadécimaux)
valide pendant 60 secondes pour la construction de la preuve ZKP, accompagné d'une liste
aléatoire de défis de vie (liveness) à exécuter devant la caméra avant la capture biométrique.
"""

import logging
import random
import secrets
import time
from fastapi import APIRouter
from pydantic import BaseModel, Field

try:
    from services.grpc_bridge import request_nonce_from_node
    from services.store import save_nonce
except ImportError:
    from api.services.grpc_bridge import request_nonce_from_node
    from api.services.store import save_nonce

logger = logging.getLogger("facein.routes.nonce")

router = APIRouter()

DUREE_NONCE_SECONDES = 60

# --- Défis de vie supportés par le frontend (clés reconnues par liveness.js) ---
DEFIS_DISPONIBLES = ["blink", "turn_left", "turn_right", "smile", "approche"]
NOMBRE_DEFIS = 2
# Le défi "approche" (parallaxe de profondeur) est TOUJOURS imposé : c'est le
# seul qu'un support plat (photo/écran) ne peut pas simuler en le manipulant.


class NonceResponse(BaseModel):
    nonce: str = Field(..., description="Valeur hexadécimale aléatoire anti-rejeu")
    expires_at: int = Field(..., description="Timestamp Unix d'expiration (en secondes)")
    defis: list = Field(
        default_factory=list,
        description="Défis de vie (liveness) aléatoires à exécuter avant la capture",
    )


@router.get(
    "/nonce/{user_id}",
    response_model=NonceResponse,
    summary="Génération d'un nonce anti-rejeu + défis de vie",
    description="Génère un nonce à usage unique valide 60 s, accompagné d'une liste "
    "aléatoire de défis de vie que le client doit exécuter devant la caméra.",
)
def get_nonce(user_id: str) -> NonceResponse:
    user_id_clean = user_id.strip()

    # 1. Tentative d'obtention d'un nonce officiel auprès du réseau de noeuds gRPC
    nonce, expires_at = request_nonce_from_node(user_id=user_id_clean)

    if not nonce or not expires_at:
        # Fallback local SQLite (mode test unitaire ou hors conteneur sans noeuds actifs)
        nonce = secrets.token_hex(32)
        expires_at = int(time.time() + DUREE_NONCE_SECONDES)
        logger.info(
            "Nonce généré localement (fallback SQLite) pour '%s' (expiration dans 60s)",
            user_id_clean,
        )
    else:
        logger.info(
            "Nonce anti-rejeu délivré par le réseau gRPC pour '%s' (expiration à %s)",
            user_id_clean,
            expires_at,
        )

    # 2. Enregistrement en SQLite pour double vérification par la passerelle API
    save_nonce(nonce=nonce, user_id=user_id_clean, expires_at=float(expires_at))

    # 3. --- Tirage des défis de vie : "approche" toujours imposé + 1 défi aléatoire ---
    autres = [d for d in DEFIS_DISPONIBLES if d != "approche"]
    defis = ["approche"] + random.sample(autres, k=min(NOMBRE_DEFIS - 1, len(autres)))
    logger.info("Défis de vie imposés à '%s' : %s", user_id_clean, ", ".join(defis))

    return NonceResponse(
        nonce=nonce,
        expires_at=int(expires_at),
        defis=defis,
    )