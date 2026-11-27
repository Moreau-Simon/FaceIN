"""
Routes d'enregistrement d'une passkey WebAuthn (attestation matérielle).

L'ajout d'une passkey exige un JWT FaceIN valide (authentification ZKP + quorum
réussie) dont le sujet est l'utilisateur concerné : un tiers ne peut donc pas
associer sa propre passkey au compte d'autrui pour en bloquer l'accès.

- POST /api/webauthn/register/options : options de création + jeton signé
- POST /api/webauthn/register/verify  : vérification de l'attestation et enregistrement

Dès qu'une passkey est enregistrée, elle devient obligatoire pour ce compte
(voir routes/authenticate.py).
"""

import logging
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Request, status

try:
    from models import (
        PasskeyOptionsRequest,
        PasskeyOptionsResponse,
        PasskeyVerifyRequest,
        PasskeyVerifyResponse,
    )
    from services.jwt_manager import verify_token
    from services.rate_limiter import enforce_rate_limit
    from services.store import add_webauthn_credential, get_webauthn_credentials
    from services.webauthn_service import (
        ErreurWebAuthn,
        options_enregistrement,
        verifier_enregistrement,
    )
except ImportError:
    from api.models import (
        PasskeyOptionsRequest,
        PasskeyOptionsResponse,
        PasskeyVerifyRequest,
        PasskeyVerifyResponse,
    )
    from api.services.jwt_manager import verify_token
    from api.services.rate_limiter import enforce_rate_limit
    from api.services.store import add_webauthn_credential, get_webauthn_credentials
    from api.services.webauthn_service import (
        ErreurWebAuthn,
        options_enregistrement,
        verifier_enregistrement,
    )

logger = logging.getLogger("facein.routes.webauthn")

router = APIRouter()


def _exiger_session(authorization: Optional[str], user_id: str) -> None:
    """Exige un JWT FaceIN valide dont le sujet est user_id (401 sinon)."""
    refus = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentification FaceIN requise pour gérer les passkeys.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not authorization or not authorization.lower().startswith("bearer "):
        raise refus
    payload = verify_token(authorization[7:].strip())
    if not payload or payload.get("sub") != user_id:
        raise refus


@router.post(
    "/webauthn/register/options",
    response_model=PasskeyOptionsResponse,
    summary="Options de création d'une passkey (session FaceIN requise)",
)
def passkey_options(
    payload: PasskeyOptionsRequest,
    request: Request = None,
    authorization: Optional[str] = Header(None),
) -> PasskeyOptionsResponse:
    if request is not None:
        enforce_rate_limit(request, endpoint_name="passkey", default_max_requests=10, identifier=payload.user_id)
    _exiger_session(authorization, payload.user_id)
    try:
        existants = get_webauthn_credentials(payload.user_id)
    except Exception as exc:
        logger.error("[%s] Lecture des passkeys impossible : %s", payload.user_id, type(exc).__name__)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Stockage indisponible.")
    return PasskeyOptionsResponse(success=True, **options_enregistrement(payload.user_id, existants))


@router.post(
    "/webauthn/register/verify",
    response_model=PasskeyVerifyResponse,
    summary="Vérification et enregistrement d'une passkey (session FaceIN requise)",
)
def passkey_verify(
    payload: PasskeyVerifyRequest,
    request: Request = None,
    authorization: Optional[str] = Header(None),
) -> PasskeyVerifyResponse:
    if request is not None:
        enforce_rate_limit(request, endpoint_name="passkey", default_max_requests=10, identifier=payload.user_id)
    _exiger_session(authorization, payload.user_id)
    try:
        passkey = verifier_enregistrement(
            payload.user_id,
            payload.credential,
            payload.challenge,
            payload.expires_at,
            payload.jeton,
        )
    except ErreurWebAuthn as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    try:
        ajoutee = add_webauthn_credential(
            payload.user_id,
            passkey["credential_id"],
            passkey["public_key"],
            passkey["sign_count"],
            passkey["transports"],
        )
    except Exception as exc:
        logger.error("[%s] Enregistrement de passkey impossible : %s", payload.user_id, type(exc).__name__)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Stockage indisponible.")
    if not ajoutee:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cette passkey est déjà enregistrée.")

    logger.info("[%s] Passkey enregistrée : elle est désormais exigée à chaque connexion.", payload.user_id)
    return PasskeyVerifyResponse(
        success=True,
        message="Passkey enregistrée : elle sera demandée à chaque connexion.",
    )
