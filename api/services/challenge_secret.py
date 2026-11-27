"""
Secret serveur des challenges de session FaceIN (défis de vie et passkeys).

Le secret FACEIN_CHALLENGE_SECRET sert à :
- dériver de façon déterministe les défis de vie à partir du nonce de session ;
- signer (HMAC-SHA256) les jetons de défis et d'enregistrement de passkey,
  ce qui évite tout stockage côté API et reste compatible avec plusieurs
  instances de l'API (toutes partagent le même secret).

Règles :
- En production (FACEIN_ENV=production), le secret est OBLIGATOIRE (>= 32 caractères) ;
  son absence fait échouer le démarrage de l'API.
- Hors production, un secret aléatoire propre au processus est généré avec un
  avertissement : aucune valeur par défaut fixe n'est inscrite dans le code.
"""

import hashlib
import hmac
import logging
import os
import secrets
from threading import Lock
from typing import Optional

logger = logging.getLogger("facein.challenge_secret")

LONGUEUR_MIN_SECRET = 32
PRODUCTION_ENV_VALUES = {"production", "prod"}

_secret_processus: Optional[bytes] = None
_verrou = Lock()


def _est_production() -> bool:
    return os.getenv("FACEIN_ENV", "").strip().lower() in PRODUCTION_ENV_VALUES


def charger_secret() -> bytes:
    """Retourne le secret des challenges (lève RuntimeError si absent en production)."""
    global _secret_processus
    valeur = os.getenv("FACEIN_CHALLENGE_SECRET", "").strip()
    if valeur:
        if len(valeur) < LONGUEUR_MIN_SECRET:
            raise RuntimeError(
                f"FACEIN_CHALLENGE_SECRET doit contenir au moins {LONGUEUR_MIN_SECRET} caractères."
            )
        return valeur.encode("utf-8")

    if _est_production():
        raise RuntimeError(
            "FACEIN_CHALLENGE_SECRET est obligatoire lorsque FACEIN_ENV=production."
        )

    with _verrou:
        if _secret_processus is None:
            _secret_processus = secrets.token_bytes(32)
            logger.warning(
                "FACEIN_CHALLENGE_SECRET absent : secret aléatoire propre à ce processus "
                "(développement uniquement, incompatible avec plusieurs instances de l'API)."
            )
        return _secret_processus


def verifier_configuration_secret() -> None:
    """Contrôle de démarrage : lève RuntimeError si la configuration est invalide."""
    charger_secret()


def signer(domaine: str, *elements: str) -> str:
    """
    HMAC-SHA256 hexadécimal avec séparation de domaine.

    Chaque élément est préfixé par sa longueur, ce qui rend l'encodage injectif
    (aucune ambiguïté entre ("ab", "c") et ("a", "bc")).
    """
    mac = hmac.new(charger_secret(), digestmod=hashlib.sha256)
    for morceau in (domaine, *elements):
        donnees = str(morceau).encode("utf-8")
        mac.update(len(donnees).to_bytes(4, "big"))
        mac.update(donnees)
    return mac.hexdigest()


def comparer(signature_attendue: str, signature_recue: str) -> bool:
    """Comparaison en temps constant de deux signatures hexadécimales."""
    if not isinstance(signature_recue, str):
        return False
    return hmac.compare_digest(signature_attendue, signature_recue.strip().lower())
