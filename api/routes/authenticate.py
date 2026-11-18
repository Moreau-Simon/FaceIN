"""
Route d'authentification biométrique ZKP avec consensus décentralisé.

Valide la preuve mathématique Groth16 sans révéler le vecteur facial,
et consulte le réseau de pairs gRPC pour le consensus distribué.

Architecture nonce (PROMPT 2) :
- Le nonce est géré UNIQUEMENT par les nœuds gRPC (autorité unique).
- L'API ne stocke PAS le nonce et ne l'appelle PAS verify_nonce() localement.
- La consommation du nonce est ATOMIQUE dans VerifierPreuve() côté nœud :
  vérification propriétaire + service_cible + expiry AVANT suppression.
- L'API valide uniquement le FORMAT du nonce (64 hex chars) avant l'envoi gRPC.
"""

import json
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Request, status

try:
    from models import AuthenticateRequest, AuthenticateResponse
    from services.grpc_bridge import verify_on_nodes
    from services.jwt_manager import generate_token
    from services.rate_limiter import enforce_rate_limit
    from services.zkp_verifier import verify_proof
except ImportError:
    from api.models import AuthenticateRequest, AuthenticateResponse
    from api.services.grpc_bridge import verify_on_nodes
    from api.services.jwt_manager import generate_token
    from api.services.rate_limiter import enforce_rate_limit
    from api.services.zkp_verifier import verify_proof

logger = logging.getLogger("facein.routes.authenticate")

router = APIRouter()

# Longueur attendue d'un nonce 256 bits encodé en hexadécimal
NONCE_HEX_LENGTH = 64


def _mask_commitment(comm: Optional[str]) -> str:
    """Masque un commitment pour protéger la vie privée dans les logs."""
    if not comm or len(comm) < 16:
        return "<masque>"
    return f"{comm[:8]}...{comm[-6:]}"


@router.post(
    "/authenticate",
    response_model=AuthenticateResponse,
    summary="Authentification par preuve ZKP",
    description=(
        "Authentifie un utilisateur en 4 étapes : validation du format du nonce, "
        "vérification locale ZKP Groth16, consensus distribué gRPC (2/3 des nœuds — "
        "inclut la consommation atomique du nonce et la vérification de l'engagement), "
        "et émission d'un jeton JWT."
    ),
)
def authenticate(payload: AuthenticateRequest, request: Request = None) -> AuthenticateResponse:
    user_id = payload.user_id.strip()
    nonce = payload.nonce.strip()

    if request is not None:
        enforce_rate_limit(
            request,
            endpoint_name="auth",
            default_max_requests=15,
            identifier=user_id,
        )

    # Étape 1 : Validation du format du nonce (64 caractères hexadécimaux — nonce 256 bits)
    # La consommation réelle et la vérification de propriété/expiry se font côté nœud gRPC.
    # Rejeter ici les nonces malformés évite un appel réseau inutile.
    if len(nonce) != NONCE_HEX_LENGTH or not all(c in "0123456789abcdefABCDEF" for c in nonce):
        logger.warning("[%s] Échec auth - Étape 1 : Nonce malformé (%d chars).", user_id, len(nonce))
        return AuthenticateResponse(
            success=False,
            authenticated=False,
            reason="Nonce malformé (attendu : 64 caractères hexadécimaux)",
            raison_refus="Nonce malformé",
            message="Échec de l'authentification : le défi cryptographique est malformé.",
        )

    # Étape 2 : Vérification locale de la preuve ZKP (pré-filtre rapide)
    # Les signaux publics doivent contenir 4 valeurs : [engagementAttendu, seuilMax, nonceHi, nonceLo]
    try:
        is_zkp_valid = verify_proof(
            proof=payload.proof,
            public_signals=payload.public_signals,
        )
    except Exception as exc:
        logger.error("[%s] Erreur interne lors de la vérification ZKP : %s", user_id, type(exc).__name__)
        is_zkp_valid = False

    if not is_zkp_valid:
        logger.warning("[%s] Échec auth - Étape 2 : Preuve ZKP invalide.", user_id)
        return AuthenticateResponse(
            success=False,
            authenticated=False,
            reason="Échec de la vérification locale de la preuve ZKP",
            raison_refus="Échec de la vérification locale de la preuve ZKP",
            message="Échec de l'authentification : preuve mathématique ZKP invalide.",
        )

    # Étape 3 : Consensus distribué gRPC (2/3 des nœuds requis).
    # C'est ici que le nœud :
    #   - consomme le nonce de façon atomique (check propriétaire + service + expiry AVANT pop)
    #   - vérifie l'engagement enregistré vs public_signals[0]
    #   - revérifie la preuve ZKP via snarkjs
    # Les signaux publics transmis : [engagementAttendu, seuilMax, nonceHi, nonceLo]
    proof_json_str = json.dumps(payload.proof)
    try:
        consensus_result = verify_on_nodes(
            user_id=user_id,
            proof_json_str=proof_json_str,
            nonce=nonce,
            public_signals=payload.public_signals,
        )
    except Exception as exc:
        logger.error("[%s] Erreur de communication avec le réseau gRPC : %s", user_id, type(exc).__name__)
        consensus_result = {"consensus": False, "majority": "0/3", "reason": "Erreur réseau gRPC"}

    if not consensus_result.get("consensus", False):
        logger.warning(
            "[%s] Échec auth - Étape 3 : Consensus non atteint (%s).",
            user_id,
            consensus_result.get("majority"),
        )
        return AuthenticateResponse(
            success=False,
            authenticated=False,
            reason="Consensus non atteint par le réseau de pairs",
            raison_refus=consensus_result.get("reason") or "Consensus non atteint par le réseau de pairs",
            message="Échec de l'authentification : le quorum de vérification n'a pas été atteint.",
        )

    # Étape 4 : Génération et émission du jeton d'accès JWT
    try:
        token = generate_token(user_id=user_id)
    except Exception as exc:
        logger.error("[%s] Erreur lors de la génération du JWT : %s", user_id, type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur interne lors de la finalisation de la session.",
        )

    logger.info("[%s] Authentification réussie avec succès. Jeton émis.", user_id)

    return AuthenticateResponse(
        success=True,
        authenticated=True,
        token=token,
        message="Authentification réussie",
    )
