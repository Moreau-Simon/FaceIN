"""
Route d'enregistrement de l'engagement biométrique initial.

Permet à un nouvel utilisateur d'enregistrer son commitment Poseidon
calculé côté client sur son vecteur de référence (128 dimensions).
"""

import logging
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

try:
    from services.store import save_commitment, user_exists
except ImportError:
    from api.services.store import save_commitment, user_exists

logger = logging.getLogger("facein.routes.register")

router = APIRouter()


class RegisterRequest(BaseModel):
    user_id: str = Field(..., description="Identifiant unique de l'utilisateur")
    commitment: str = Field(
        ...,
        description="Empreinte cryptographique Poseidon de référence calculée localement",
    )


class RegisterResponse(BaseModel):
    success: bool
    message: str


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_200_OK,
    summary="Enregistrement d'un utilisateur",
    description="Enregistre l'engagement biométrique de référence. Échoue avec 409 si l'identifiant existe déjà.",
)
def register(payload: RegisterRequest) -> RegisterResponse:
    user_id = payload.user_id.strip()
    commitment = payload.commitment.strip()

    if not user_id or not commitment:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Les champs 'user_id' et 'commitment' ne peuvent pas être vides.",
        )

    if user_exists(user_id):
        logger.warning("Tentative d'enregistrement d'un utilisateur déjà existant : '%s'", user_id)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"L'utilisateur '{user_id}' est déjà enregistré.",
        )

    try:
        save_commitment(user_id, commitment)
    except Exception as exc:
        logger.error("Erreur lors de la sauvegarde de l'engagement pour '%s' : %s", user_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur interne lors de l'enregistrement.",
        )

    logger.info("Nouvel utilisateur enregistré avec succès : '%s'", user_id)
    return RegisterResponse(
        success=True,
        message="Engagement enregistré",
    )
