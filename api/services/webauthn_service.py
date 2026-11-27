"""
Attestation matérielle par passkey WebAuthn (architecture C du chantier 11).

Principe :
- Après une authentification FaceIN réussie (ZKP + quorum, JWT valide), l'utilisateur
  peut enregistrer une passkey (Windows Hello, Face ID, Touch ID, clé FIDO2…).
- Dès qu'un compte possède au moins une passkey active, chaque authentification doit
  présenter une assertion WebAuthn valide, avec vérification de l'utilisateur (UV)
  par l'appareil.
- Le challenge WebAuthn de l'authentification est dérivé du nonce de session :
  SHA-256(domaine, service, utilisateur, nonce). Il est donc à usage unique (le nonce
  est consommé atomiquement par les nœuds) et lié à l'utilisateur et au service,
  sans aucun stockage côté API.
- Aucune image ni aucun vecteur facial ne quitte l'appareil.

Garantie apportée : une signature produite par un authentificateur enregistré, après
vérification locale de l'utilisateur par un composant de confiance. Limite : elle
prouve la présence de l'utilisateur sur l'appareil enregistré, pas que le visage
capturé par FaceIN est celui de cette personne.

Les passkeys sont « découvrables » (resident key) : /api/nonce n'expose jamais la
liste des identifiants d'un compte, ce qui évite de révéler l'existence d'un compte
ou d'une passkey.
"""

import hashlib
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional, Tuple

try:
    from services.challenge_secret import comparer, signer
except ImportError:
    from api.services.challenge_secret import comparer, signer

try:
    from webauthn import (
        generate_registration_options,
        options_to_json,
        verify_authentication_response,
        verify_registration_response,
    )
    from webauthn.helpers import base64url_to_bytes, bytes_to_base64url
    from webauthn.helpers.structs import (
        AuthenticatorSelectionCriteria,
        PublicKeyCredentialDescriptor,
        ResidentKeyRequirement,
        UserVerificationRequirement,
    )
except ImportError:  # pragma: no cover - dépendance déclarée dans api/requirements.txt
    generate_registration_options = None

logger = logging.getLogger("facein.webauthn")

PRODUCTION_ENV_VALUES = {"production", "prod"}
DOMAINE_CHALLENGE_AUTH = "FaceIN-webauthn-authentification-v1"
DOMAINE_USER_HANDLE = "FaceIN-webauthn-user-handle-v1"
DOMAINE_JETON_ENREGISTREMENT = "FaceIN-webauthn-enregistrement-v1"
DUREE_ENREGISTREMENT_S = 300
TAILLE_MAX_CREDENTIAL_JSON = 16 * 1024


class ErreurWebAuthn(Exception):
    """Erreur de vérification WebAuthn (message exposable à l'utilisateur)."""


def disponible() -> bool:
    return generate_registration_options is not None


def _est_production() -> bool:
    return os.getenv("FACEIN_ENV", "").strip().lower() in PRODUCTION_ENV_VALUES


def rp_id() -> str:
    return os.getenv("WEBAUTHN_RP_ID", "localhost").strip()


def rp_name() -> str:
    return os.getenv("WEBAUTHN_RP_NAME", "FaceIN").strip() or "FaceIN"


def origines_autorisees() -> List[str]:
    brut = os.getenv("WEBAUTHN_ORIGINS", "http://localhost:3000")
    return [o.strip().rstrip("/") for o in brut.split(",") if o.strip()]


def verifier_configuration_webauthn() -> None:
    """Contrôle de démarrage (production : RP ID et origines HTTPS explicites)."""
    if not disponible():
        raise RuntimeError("Le module 'webauthn' est requis (voir api/requirements.txt).")
    if not _est_production():
        return
    if not os.getenv("WEBAUTHN_RP_ID", "").strip() or not os.getenv("WEBAUTHN_ORIGINS", "").strip():
        raise RuntimeError(
            "WEBAUTHN_RP_ID et WEBAUTHN_ORIGINS sont obligatoires lorsque FACEIN_ENV=production."
        )
    non_https = [o for o in origines_autorisees() if not o.startswith("https://")]
    if non_https:
        raise RuntimeError(
            "WEBAUTHN_ORIGINS doit contenir uniquement des origines HTTPS en production : "
            + ", ".join(non_https)
        )


def user_handle(user_id: str) -> bytes:
    """Identifiant opaque de l'utilisateur pour l'authentificateur (non réversible)."""
    return bytes.fromhex(signer(DOMAINE_USER_HANDLE, user_id))[:32]


def challenge_authentification(user_id: str, nonce: str, service: str) -> bytes:
    """Challenge WebAuthn dérivé du nonce de session (usage unique, lié au contexte)."""
    h = hashlib.sha256()
    for morceau in (DOMAINE_CHALLENGE_AUTH, service, user_id, nonce.lower()):
        donnees = morceau.encode("utf-8")
        h.update(len(donnees).to_bytes(4, "big"))
        h.update(donnees)
    return h.digest()


def challenge_authentification_b64(user_id: str, nonce: str, service: str) -> str:
    return bytes_to_base64url(challenge_authentification(user_id, nonce, service))


# ---------------------------------------------------------------------------
# Enregistrement d'une passkey
# ---------------------------------------------------------------------------
def _jeton_enregistrement(user_id: str, challenge_b64: str, expires_at: int) -> str:
    return signer(DOMAINE_JETON_ENREGISTREMENT, user_id, challenge_b64, str(int(expires_at)))


def options_enregistrement(
    user_id: str, credentials_existants: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Options de création de passkey + jeton signé (aucun stockage serveur)."""
    options = generate_registration_options(
        rp_id=rp_id(),
        rp_name=rp_name(),
        user_name=user_id,
        user_id=user_handle(user_id),
        user_display_name=user_id,
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.REQUIRED,
            user_verification=UserVerificationRequirement.REQUIRED,
        ),
        exclude_credentials=[
            PublicKeyCredentialDescriptor(id=base64url_to_bytes(c["credential_id"]))
            for c in credentials_existants
        ],
    )
    challenge_b64 = bytes_to_base64url(options.challenge)
    expires_at = int(time.time()) + DUREE_ENREGISTREMENT_S
    return {
        "options": json.loads(options_to_json(options)),
        "challenge": challenge_b64,
        "expires_at": expires_at,
        "jeton": _jeton_enregistrement(user_id, challenge_b64, expires_at),
    }


def verifier_enregistrement(
    user_id: str,
    credential: Dict[str, Any],
    challenge_b64: str,
    expires_at: int,
    jeton: str,
    maintenant: Optional[float] = None,
) -> Dict[str, Any]:
    """Vérifie la réponse de création et retourne la passkey à enregistrer."""
    instant = time.time() if maintenant is None else float(maintenant)
    if not comparer(_jeton_enregistrement(user_id, challenge_b64, expires_at), jeton):
        raise ErreurWebAuthn("Demande d'enregistrement de passkey non reconnue")
    if instant > int(expires_at):
        raise ErreurWebAuthn("Demande d'enregistrement de passkey expirée")
    _controler_taille(credential)
    try:
        verifie = verify_registration_response(
            credential=credential,
            expected_challenge=base64url_to_bytes(challenge_b64),
            expected_rp_id=rp_id(),
            expected_origin=origines_autorisees(),
            require_user_verification=True,
        )
    except Exception as exc:
        logger.warning("[%s] Enregistrement de passkey refusé : %s", user_id, type(exc).__name__)
        raise ErreurWebAuthn("Réponse d'enregistrement de passkey invalide") from exc

    transports = []
    reponse = credential.get("response") if isinstance(credential, dict) else None
    if isinstance(reponse, dict) and isinstance(reponse.get("transports"), list):
        transports = [str(t) for t in reponse["transports"]][:8]
    return {
        "credential_id": bytes_to_base64url(verifie.credential_id),
        "public_key": verifie.credential_public_key,
        "sign_count": int(verifie.sign_count),
        "transports": transports,
    }


# ---------------------------------------------------------------------------
# Vérification d'une assertion lors de l'authentification
# ---------------------------------------------------------------------------
def _controler_taille(credential: Any) -> None:
    if not isinstance(credential, dict):
        raise ErreurWebAuthn("Réponse WebAuthn mal formée")
    if len(json.dumps(credential)) > TAILLE_MAX_CREDENTIAL_JSON:
        raise ErreurWebAuthn("Réponse WebAuthn trop volumineuse")


def verifier_assertion(
    user_id: str,
    nonce: str,
    service: str,
    assertion: Optional[Dict[str, Any]],
    credentials: List[Dict[str, Any]],
) -> Tuple[str, int, int]:
    """
    Vérifie l'assertion WebAuthn d'une authentification.

    Retourne (credential_id, ancien compteur, nouveau compteur) ; la mise à jour
    atomique du compteur est faite par l'appelant via le store.
    Lève ErreurWebAuthn en cas de refus.
    """
    if assertion is None:
        raise ErreurWebAuthn("Vérification par passkey requise pour ce compte")
    _controler_taille(assertion)

    credential_id = str(assertion.get("rawId") or assertion.get("id") or "")
    connue = next((c for c in credentials if c["credential_id"] == credential_id), None)
    if connue is None:
        raise ErreurWebAuthn("Passkey non associée à ce compte")

    reponse = assertion.get("response")
    if isinstance(reponse, dict) and reponse.get("userHandle"):
        try:
            handle = base64url_to_bytes(str(reponse["userHandle"]))
        except Exception as exc:
            raise ErreurWebAuthn("Réponse WebAuthn mal formée") from exc
        if handle != user_handle(user_id):
            raise ErreurWebAuthn("Passkey non associée à ce compte")

    try:
        verifie = verify_authentication_response(
            credential=assertion,
            expected_challenge=challenge_authentification(user_id, nonce, service),
            expected_rp_id=rp_id(),
            expected_origin=origines_autorisees(),
            credential_public_key=connue["public_key"],
            credential_current_sign_count=int(connue["sign_count"]),
            require_user_verification=True,
        )
    except Exception as exc:
        logger.warning("[%s] Assertion WebAuthn refusée : %s", user_id, type(exc).__name__)
        raise ErreurWebAuthn("Vérification par passkey invalide") from exc

    return credential_id, int(connue["sign_count"]), int(verifie.new_sign_count)
