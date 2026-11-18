"""
Route de génération de nonce anti-rejeu éphémère.

Le nonce est UNIQUEMENT généré par le réseau de nœuds gRPC (autorité unique).
L'API ne stocke PAS le nonce localement : seul le nœud gère son cycle de vie
(émission, durée 60 s, consommation atomique lors de VerifierPreuve).

Fournit au client un défi cryptographique aléatoire de 32 octets (64 caractères
hexadécimaux) valide pendant 60 secondes pour la construction de la preuve ZKP,
accompagné d'une liste aléatoire de défis de vie (liveness).
"""

import logging
import secrets
from fastapi import APIRouter, HTTPException, Request, status

try:
    from models import NonceResponse, validate_user_id_format
    from services.grpc_bridge import request_nonce_from_node
    from services.rate_limiter import enforce_rate_limit
except ImportError:
    from api.models import NonceResponse, validate_user_id_format
    from api.services.grpc_bridge import request_nonce_from_node
    from api.services.rate_limiter import enforce_rate_limit

logger = logging.getLogger("facein.routes.nonce")

router = APIRouter()

# --- Défis de vie supportés par le frontend (clés reconnues par liveness.js) ---
DEFIS_DISPONIBLES = ["blink", "turn_left", "turn_right", "smile"]
NOMBRE_DEFIS = 2


@router.get(
    "/nonce/{user_id}",
    response_model=NonceResponse,
    summary="Génération d'un nonce anti-rejeu + défis de vie",
    description=(
        "Génère un nonce 256 bits à usage unique valide 60 s, émis par le réseau "
        "de nœuds gRPC (autorité unique). Accompagné d'une liste aléatoire de défis "
        "de vie que le client doit exécuter devant la caméra."
    ),
)
def get_nonce(user_id: str, request: Request = None) -> NonceResponse:
    try:
        user_id_clean = validate_user_id_format(user_id)
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(val_err),
        )

    if request is not None:
        enforce_rate_limit(
            request,
            endpoint_name="nonce",
            default_max_requests=30,
            identifier=user_id_clean,
        )

    # Obtention du nonce auprès du réseau de nœuds gRPC (source unique d'autorité).
    # Le nonce est stocké et géré UNIQUEMENT par le nœud : l'API ne stocke rien.
    nonce, expires_at = request_nonce_from_node(user_id=user_id_clean)

    if not nonce or not expires_at:
        # Les nœuds gRPC sont indisponibles. On refuse explicitement :
        # un nonce généré localement serait inconnu des nœuds et ne pourrait
        # jamais être consommé lors de VerifierPreuve → authentification impossible.
        logger.error(
            "Nonce refusé pour '%s' : aucun nœud gRPC disponible.",
            user_id_clean,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Le réseau de vérification est temporairement indisponible. "
                "Veuillez réessayer dans quelques instants."
            ),
        )

    logger.info(
        "Nonce anti-rejeu 256 bits délivré par le réseau gRPC pour '%s' (expiration à %s)",
        user_id_clean,
        expires_at,
    )

    # --- Tirage aléatoire cryptographiquement sûr des défis de vie ---
    crypto_rng = secrets.SystemRandom()
    defis = crypto_rng.sample(DEFIS_DISPONIBLES, k=min(NOMBRE_DEFIS, len(DEFIS_DISPONIBLES)))
    logger.info("Défis de vie imposés à '%s' : %s", user_id_clean, ", ".join(defis))

    return NonceResponse(
        success=True,
        nonce=nonce,
        expires_at=int(expires_at),
        defis=defis,
    )
