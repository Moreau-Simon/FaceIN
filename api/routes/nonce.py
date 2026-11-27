"""
Route de génération de nonce anti-rejeu éphémère.

Le nonce est UNIQUEMENT généré par le réseau de nœuds gRPC (autorité unique).
L'API ne stocke PAS le nonce localement : seul le nœud gère son cycle de vie
(émission, durée 60 s, consommation atomique lors de VerifierPreuve).

Fournit au client un défi cryptographique aléatoire de 32 octets (64 caractères
hexadécimaux) valide pendant 60 secondes pour la construction de la preuve ZKP,
accompagné :
- des défis de vie DÉRIVÉS de ce nonce (services/liveness.py) et de leur jeton HMAC ;
- des paramètres d'assertion WebAuthn dont le challenge est dérivé du nonce
  (services/webauthn_service.py). Ils sont renvoyés pour tous les comptes afin de ne
  pas révéler si un compte possède une passkey.
"""

import logging
from fastapi import APIRouter, HTTPException, Request, status

try:
    from models import NonceResponse, validate_user_id_format
    from services.grpc_bridge import request_nonce_from_node
    from services.liveness import SERVICE_CIBLE, preparer_defis
    from services.rate_limiter import enforce_rate_limit
    from services.webauthn_service import challenge_authentification_b64, rp_id
except ImportError:
    from api.models import NonceResponse, validate_user_id_format
    from api.services.grpc_bridge import request_nonce_from_node
    from api.services.liveness import SERVICE_CIBLE, preparer_defis
    from api.services.rate_limiter import enforce_rate_limit
    from api.services.webauthn_service import challenge_authentification_b64, rp_id

logger = logging.getLogger("facein.routes.nonce")

router = APIRouter()

# Délai laissé au navigateur pour l'assertion WebAuthn (ms)
WEBAUTHN_TIMEOUT_MS = 60_000


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

    # --- Défis de vie dérivés du nonce (HMAC) et liés à la session ---
    defis, defis_jeton = preparer_defis(user_id_clean, nonce, int(expires_at))
    logger.info("Défis de vie imposés à '%s' : %s", user_id_clean, ", ".join(defis))

    return NonceResponse(
        success=True,
        nonce=nonce,
        expires_at=int(expires_at),
        defis=defis,
        defis_jeton=defis_jeton,
        webauthn={
            "challenge": challenge_authentification_b64(user_id_clean, nonce, SERVICE_CIBLE),
            "rpId": rp_id(),
            "timeout": WEBAUTHN_TIMEOUT_MS,
            "userVerification": "required",
        },
    )
