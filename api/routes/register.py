"""
Route d'enregistrement de l'engagement biométrique initial.

Permet à un nouvel utilisateur d'enregistrer son commitment Poseidon
calculé côté client sur son vecteur de référence (128 dimensions).
"""

import logging
from fastapi import APIRouter, HTTPException, Request, status

try:
    from models import RegisterRequest, RegisterResponse
    from services.grpc_bridge import propagate_commitment_to_nodes
    from services.rate_limiter import enforce_rate_limit
    from services.store import save_commitment, user_exists
except ImportError:
    from api.models import RegisterRequest, RegisterResponse
    from api.services.grpc_bridge import propagate_commitment_to_nodes
    from api.services.rate_limiter import enforce_rate_limit
    from api.services.store import save_commitment, user_exists

logger = logging.getLogger("facein.routes.register")

router = APIRouter()


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_200_OK,
    summary="Enregistrement d'un utilisateur",
    description="Enregistre l'engagement biométrique de référence. Échoue avec 409 si l'identifiant existe déjà.",
)
def register(payload: RegisterRequest, request: Request = None) -> RegisterResponse:
    if request is not None:
        enforce_rate_limit(request, endpoint_name="register", default_max_requests=10)

    user_id = payload.user_id.strip()
    commitment = payload.commitment.strip()

    if user_exists(user_id):
        logger.warning("Tentative d'enregistrement d'un utilisateur déjà existant : '%s'", user_id)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"L'utilisateur '{user_id}' est déjà enregistré.",
        )

    try:
        save_commitment(user_id, commitment)
    except Exception as exc:
        logger.error("Erreur lors de la sauvegarde de l'engagement pour '%s' : %s", user_id, type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur interne lors de l'enregistrement.",
        )

    # Propagation explicite et sécurisée vers le réseau de nœuds de vérification
    try:
        prop_res = propagate_commitment_to_nodes(user_id, commitment)
        if prop_res.get("quorum"):
            logger.info(
                "[%s] Engagement propagé avec succès aux nœuds (%s)",
                user_id,
                prop_res.get("majority"),
            )
        else:
            logger.warning(
                "[%s] Quorum de propagation non atteint aux nœuds (%s) - sera synchronisé au rattrapage",
                user_id,
                prop_res.get("majority"),
            )
    except Exception as exc:
        logger.warning(
            "[%s] Erreur non bloquante lors de la propagation gRPC aux nœuds : %s",
            user_id,
            exc,
        )

    logger.info("Nouvel utilisateur enregistré avec succès : '%s'", user_id)
    return RegisterResponse(
        success=True,
        message="Engagement enregistré",
    )
