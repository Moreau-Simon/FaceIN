"""
Gestionnaire de jetons d'accès JWT (JSON Web Tokens) pour FaceIn.

Responsabilités :
- Émettre des tokens JWT signés après authentification ZKP validée par quorum.
- Valider l'intégrité, l'expiration, l'émetteur, l'audience et la liste noire des tokens.
- Gérer la rotation des clés (clé courante + clé précédente en transition).
- Rejeter tout démarrage en production si aucune clé n'est configurée.

Claims JWT émis :
  sub  : identifiant de l'utilisateur authentifié
  iss  : identifiant de l'émetteur ("facein-api")
  aud  : service cible du token (ex. "facein-web", "facein-mobile")
  iat  : timestamp d'émission (Unix)
  exp  : timestamp d'expiration (Unix)
  jti  : identifiant unique du token (UUID4, utilisé pour la révocation)
  ver  : version du schéma de claims ("1")
"""

import logging
import os
import time
import uuid
from typing import Any, Dict, List, Optional

try:
    import jwt
except ImportError:
    jwt = None  # type: ignore

logger = logging.getLogger("facein.jwt_manager")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

JWT_ISSUER = "facein-api"
JWT_ALGORITHM = "HS256"
JWT_CLAIMS_VERSION = "1"

# Durée de vie configurable via variable d'environnement (défaut : 1 heure)
JWT_EXPIRATION_SECONDS = int(os.getenv("JWT_EXPIRATION_SECONDS", "3600"))

# Service cible par défaut si non précisé à l'émission
JWT_DEFAULT_AUDIENCE = os.getenv("JWT_DEFAULT_AUDIENCE", "facein-web")

# ---------------------------------------------------------------------------
# Gestion de la clé secrète
# ---------------------------------------------------------------------------

_SENTINEL = object()


def _charger_cle_secrete() -> str:
    """
    Charge la clé secrète JWT depuis l'environnement.

    En mode production (JWT_ENV=production), l'absence de clé lève
    une erreur fatale : aucune clé par défaut ne peut signer un token valide.
    En mode non-production, une clé par défaut est utilisée avec un avertissement.
    """
    cle = os.getenv("JWT_SECRET_KEY", "").strip()
    env_mode = os.getenv("JWT_ENV", "development").strip().lower()

    if not cle:
        if env_mode == "production":
            raise RuntimeError(
                "JWT_SECRET_KEY est obligatoire en environnement de production. "
                "Configurez cette variable d'environnement avec une clé aléatoire "
                "d'au moins 256 bits."
            )
        # Développement/tests : clé fixe avec avertissement explicite
        logger.warning(
            "JWT_SECRET_KEY non configurée. Utilisation d'une clé de développement. "
            "NE PAS utiliser en production."
        )
        return "__FACEIN_DEV_KEY_NOT_FOR_PRODUCTION__"

    return cle


def _charger_cle_precedente() -> Optional[str]:
    """
    Charge l'ancienne clé secrète JWT (rotation en cours).

    Pendant une rotation de clé, les tokens émis avec l'ancienne clé
    restent valides jusqu'à leur expiration naturelle.
    """
    cle = os.getenv("JWT_SECRET_KEY_PREVIOUS", "").strip()
    return cle if cle else None


# ---------------------------------------------------------------------------
# Liste noire des tokens révoqués (jti)
# ---------------------------------------------------------------------------

# Stockage en mémoire pour les environnements sans PostgreSQL.
# En production, la révocation persistante utilise le store PostgreSQL via
# les fonctions save_revoked_jti() / is_jti_revoked() du module store.
_jti_blacklist: Dict[str, float] = {}  # jti -> timestamp d'expiration


try:
    from services import store as _store
except ImportError:
    try:
        from api.services import store as _store
    except ImportError:
        _store = None  # type: ignore


def revoquer_token_jti(jti: str, exp: float) -> None:
    """Ajoute un JTI à la liste noire locale et persistante jusqu'à son expiration."""
    _purger_jti_expires()
    _jti_blacklist[jti] = exp
    if _store is not None:
        try:
            _store.save_revoked_jti(jti, exp)
        except Exception as exc:
            logger.warning("Impossible de persister la révocation du JTI %s : %s", jti, exc)
    logger.info("Token révoqué (jti=%s, expire=%s)", jti, exp)


def est_jti_revoque(jti: str) -> bool:
    """Vérifie si un JTI est dans la liste noire locale ou persistante."""
    if jti in _jti_blacklist:
        if _jti_blacklist[jti] < time.time():
            del _jti_blacklist[jti]
        else:
            return True
    if _store is not None:
        try:
            if _store.is_jti_revoked(jti):
                return True
        except Exception as exc:
            logger.warning("Erreur lors du contrôle de révocation persistant pour %s : %s", jti, exc)
    return False


def _purger_jti_expires() -> None:
    """Supprime les JTIs expirés de la liste noire pour limiter la consommation mémoire."""
    now = time.time()
    expires = [jti for jti, exp in _jti_blacklist.items() if exp < now]
    for jti in expires:
        del _jti_blacklist[jti]


def reset_blacklist() -> None:
    """Réinitialise la liste noire (usage tests uniquement)."""
    _jti_blacklist.clear()


# ---------------------------------------------------------------------------
# Émission
# ---------------------------------------------------------------------------


def generate_token(
    user_id: str,
    audience: Optional[str] = None,
    expiration_seconds: Optional[int] = None,
) -> str:
    """
    Génère un token JWT signé avec les claims complets.

    Args:
        user_id: identifiant de l'utilisateur authentifié (claim ``sub``).
        audience: service cible (claim ``aud``). Défaut : JWT_DEFAULT_AUDIENCE.
        expiration_seconds: durée de vie en secondes. Défaut : JWT_EXPIRATION_SECONDS.

    Returns:
        Token JWT encodé en chaîne.

    Raises:
        RuntimeError: si PyJWT n'est pas installé ou si la clé est absente en prod.
    """
    if jwt is None:
        raise RuntimeError("La bibliothèque 'PyJWT' est requise pour générer un jeton.")

    secret = _charger_cle_secrete()
    aud = audience or JWT_DEFAULT_AUDIENCE
    duree = expiration_seconds if expiration_seconds is not None else JWT_EXPIRATION_SECONDS
    now = int(time.time())

    payload = {
        "sub": user_id,
        "iss": JWT_ISSUER,
        "aud": aud,
        "iat": now,
        "exp": now + duree,
        "jti": str(uuid.uuid4()),
        "ver": JWT_CLAIMS_VERSION,
    }

    return jwt.encode(payload, secret, algorithm=JWT_ALGORITHM)


# ---------------------------------------------------------------------------
# Vérification
# ---------------------------------------------------------------------------


def verify_token(
    token: str,
    audience: Optional[str] = None,
    verify_revocation: bool = True,
) -> Optional[Dict[str, Any]]:
    """
    Décode et valide un token JWT.

    Vérifie :
    - Signature (clé courante, puis clé précédente si rotation en cours).
    - Expiration (``exp``).
    - Émetteur (``iss`` == "facein-api").
    - Audience (``aud``).
    - Liste noire de révocation (``jti``).

    Args:
        token: token JWT à valider.
        audience: audience attendue. Défaut : JWT_DEFAULT_AUDIENCE.
        verify_revocation: si True, consulte la liste noire des jti révoqués.

    Returns:
        Payload décodé si valide, None sinon.
    """
    if jwt is None:
        raise RuntimeError("La bibliothèque 'PyJWT' est requise pour vérifier un jeton.")

    aud = audience or JWT_DEFAULT_AUDIENCE
    cles_a_tester: List[str] = [_charger_cle_secrete()]
    cle_precedente = _charger_cle_precedente()
    if cle_precedente:
        cles_a_tester.append(cle_precedente)

    payload = None
    for cle in cles_a_tester:
        try:
            payload = jwt.decode(
                token,
                cle,
                algorithms=[JWT_ALGORITHM],
                issuer=JWT_ISSUER,
                audience=aud,
                options={"require": ["sub", "iss", "aud", "iat", "exp", "jti"]},
            )
            break  # Validation réussie avec cette clé
        except jwt.ExpiredSignatureError:
            logger.warning("Token JWT expiré.")
            return None
        except jwt.InvalidIssuerError:
            logger.warning("Token JWT : émetteur invalide.")
            return None
        except jwt.InvalidAudienceError:
            logger.warning("Token JWT : audience invalide.")
            return None
        except jwt.MissingRequiredClaimError as exc:
            logger.warning("Token JWT : claim obligatoire manquant : %s", exc)
            return None
        except jwt.InvalidTokenError:
            # Mauvaise signature avec cette clé → essayer la suivante
            continue

    if payload is None:
        logger.warning("Token JWT invalide : aucune clé valide.")
        return None

    # Vérification de la liste noire (révocation)
    if verify_revocation:
        jti = payload.get("jti", "")
        if jti and est_jti_revoque(jti):
            logger.warning("Token JWT révoqué (jti=%s).", jti)
            return None

    return payload


# ---------------------------------------------------------------------------
# Révocation d'un token actif
# ---------------------------------------------------------------------------


def revoquer_token(token: str, audience: Optional[str] = None) -> bool:
    """
    Révoque immédiatement un token valide en blacklistant son jti.

    Args:
        token: token JWT à révoquer.
        audience: audience pour la validation préalable.

    Returns:
        True si révoqué avec succès, False si le token est déjà invalide.
    """
    payload = verify_token(token, audience=audience, verify_revocation=False)
    if payload is None:
        return False

    jti = payload.get("jti")
    exp = float(payload.get("exp", time.time()))
    if jti:
        revoquer_token_jti(jti, exp)
        return True
    return False


def verify_service_access(token: str, required_service: str) -> Optional[Dict[str, Any]]:
    """
    Valide un token JWT et vérifie que l'utilisateur est autorisé sur ``required_service``.

    Contrôle :
    - Signature, expiration, émetteur et audience ``required_service``.
    - Non-révocation du ``jti``.
    - Autorisation active de l'utilisateur pour ce service dans le store.
    """
    payload = verify_token(token, audience=required_service, verify_revocation=True)
    if payload is None:
        return None

    user_id = payload.get("sub", "")
    if not user_id:
        return None

    if _store is not None:
        try:
            if not _store.is_service_authorized(user_id, required_service):
                logger.warning(
                    "Accès refusé pour '%s' sur le service '%s' (autorisation révoquée ou absente).",
                    user_id,
                    required_service,
                )
                return None
        except Exception as exc:
            logger.warning("Erreur de vérification d'autorisation par service : %s", exc)
            return None

    return payload
