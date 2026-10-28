"""
Route d'authentification biométrique ZKP avec consensus décentralisé.

Valide la preuve mathématique Groth16 sans révéler le vecteur facial,
vérifie l'engagement Poseidon enregistré et consulte le réseau de pairs gRPC.
"""

import json
import logging
from typing import Any, Optional
from fastapi import APIRouter
from pydantic import BaseModel, Field

try:
    from services.grpc_bridge import verify_on_nodes
    from services.jwt_manager import generate_token
    from services.store import get_commitment, verify_nonce
    from services.zkp_verifier import verify_proof
except ImportError:
    from api.services.grpc_bridge import verify_on_nodes
    from api.services.jwt_manager import generate_token
    from api.services.store import get_commitment, verify_nonce
    from api.services.zkp_verifier import verify_proof

logger = logging.getLogger("facein.routes.authenticate")

router = APIRouter()


class AuthenticateRequest(BaseModel):
    user_id: str = Field(..., description="Identifiant unique de l'utilisateur")
    proof: dict[str, Any] = Field(..., description="Preuve Groth16 générée côté client (pi_a, pi_b, pi_c)")
    public_signals: list[str] = Field(
        ...,
        description="Signaux publics du circuit : [0]=engagementAttendu, [1]=seuilMax",
    )
    nonce: str = Field(..., description="Nonce cryptographique reçu lors de l'étape de défi")


class AuthenticateResponse(BaseModel):
    authenticated: bool = Field(..., description="Indique si l'authentification a réussi")
    token: Optional[str] = Field(None, description="Jeton JWT d'accès en cas de succès")
    reason: Optional[str] = Field(None, description="Raison du refus en cas d'échec")


@router.post(
    "/authenticate",
    response_model=AuthenticateResponse,
    summary="Authentification par preuve ZKP",
    description=(
        "Authentifie un utilisateur en 6 étapes : vérification du nonce, recherche de l'engagement, "
        "contrôle de cohérence de l'engagement public, vérification locale ZKP Groth16, "
        "consensus distribué gRPC (2/3 des noeuds) et émission d'un jeton JWT."
    ),
)
def authenticate(payload: AuthenticateRequest) -> AuthenticateResponse:
    user_id = payload.user_id.strip()
    nonce = payload.nonce.strip()

    # Étape 1 : Vérifier la validité et la non-expiration du nonce
    if not verify_nonce(nonce=nonce, user_id=user_id):
        logger.warning("[%s] Échec auth - Étape 1 : Nonce invalide ou expiré.", user_id)
        return AuthenticateResponse(
            authenticated=False,
            reason="Nonce invalide ou expiré",
        )

    # Étape 2 : Récupérer l'engagement enregistré pour cet utilisateur
    stored_commitment = get_commitment(user_id=user_id)
    if stored_commitment is None:
        logger.warning("[%s] Échec auth - Étape 2 : Utilisateur non trouvé ou sans engagement.", user_id)
        return AuthenticateResponse(
            authenticated=False,
            reason="Utilisateur non trouvé ou engagement absent",
        )

    # Étape 3 : Vérifier que public_signals[0] correspond à l'engagement enregistré
    # Le circuit circom sort l'engagement calculé sur vecteurOriginal en premier signal public
    if not payload.public_signals or str(payload.public_signals[0]).strip() != str(stored_commitment).strip():
        logger.warning(
            "[%s] Échec auth - Étape 3 : Incohérence d'engagement (attendu=%s, reçu=%s).",
            user_id,
            stored_commitment,
            payload.public_signals[0] if payload.public_signals else None,
        )
        return AuthenticateResponse(
            authenticated=False,
            reason="L'engagement public ne correspond pas à l'engagement enregistré",
        )

    # Étape 4 : Appel local du vérificateur ZKP snarkjs
    is_zkp_valid = verify_proof(
        proof=payload.proof,
        public_signals=payload.public_signals,
    )
    if not is_zkp_valid:
        logger.warning("[%s] Échec auth - Étape 4 : Preuve ZKP invalide.", user_id)
        return AuthenticateResponse(
            authenticated=False,
            reason="Échec de la vérification locale de la preuve ZKP",
        )

    # Étape 5 : Appel des noeuds gRPC pour consensus (majorité 2/3 requise)
    proof_json_str = json.dumps(payload.proof)
    consensus_result = verify_on_nodes(
        user_id=user_id,
        proof_json_str=proof_json_str,
        nonce=nonce,
        public_signals=payload.public_signals,
    )

    if not consensus_result.get("consensus", False):
        logger.warning(
            "[%s] Échec auth - Étape 5 : Consensus non atteint (%s).",
            user_id,
            consensus_result.get("majority"),
        )
        return AuthenticateResponse(
            authenticated=False,
            reason="Consensus non atteint par le réseau de pairs",
        )

    # Étape 6 : Génération et émission du jeton d'accès JWT
    token = generate_token(user_id=user_id)
    logger.info("[%s] Authentification réussie avec succès. Jeton émis.", user_id)

    return AuthenticateResponse(
        authenticated=True,
        token=token,
    )
