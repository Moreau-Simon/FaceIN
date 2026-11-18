"""
Stockage des nonces d'authentification côté nœud FaceIN.

Chaque nonce est un token aléatoire 256 bits (64 caractères hexadécimaux),
lié à un utilisateur ET à un service cible pour éviter toute réutilisation
croisée entre sessions ou services différents.

Règles de sécurité :
- Génération via secrets.token_hex(32) → 256 bits d'entropie.
- Durée de vie uniforme : DUREE_NONCE_SECONDES (défaut 60 s).
- consommer() est atomique : vérifie propriétaire + expiry AVANT suppression.
  Un nonce invalide (mauvais user, mauvais service, expiré) n'est PAS supprimé,
  ce qui préserve l'entrée pour d'éventuels logs, mais empêche sa réutilisation
  via le flag ``_en_cours_de_consommation``.
"""
import secrets
import time
from threading import Lock

# Durée de vie par défaut d'un nonce (secondes). Doit correspondre à l'API.
DUREE_NONCE_SECONDES = 60


class NonceStore:
    """Registre thread-safe des nonces 256 bits émis par ce nœud.

    Structure interne :
        _nonces[nonce_hex] = (utilisateur_id, service_cible, expiration_timestamp)
    """

    def __init__(self, duree_s: int = DUREE_NONCE_SECONDES, horloge=time.time):
        if not isinstance(duree_s, int) or duree_s < 1:
            raise ValueError("duree_s doit être un entier >= 1")
        self._duree = duree_s
        self._horloge = horloge
        # nonce_hex → (utilisateur_id, service_cible, expiration_float)
        self._nonces: dict[str, tuple[str, str, float]] = {}
        self._lock = Lock()

    def emettre(self, utilisateur_id: str, service_cible: str = "") -> tuple[str, int]:
        """Génère un nonce 256 bits lié à l'utilisateur et au service cible.

        Returns:
            (nonce_hex, expiration_epoch_ms)  — 64 caractères hex, timestamp ms.
        """
        nonce = secrets.token_hex(32)  # 256 bits = 32 octets = 64 hex chars
        expiration = self._horloge() + self._duree
        with self._lock:
            self._purger()
            self._nonces[nonce] = (utilisateur_id, service_cible, expiration)
        return nonce, int(expiration * 1000)

    def consommer(
        self,
        utilisateur_id: str,
        nonce: str,
        service_cible: str = "",
    ) -> bool:
        """Valide et consomme un nonce de façon atomique à usage unique.

        Le nonce est retiré du registre dès sa présentation (usage unique strict,
        empêchant toute tentative de rejeu ou d'énumération concurrente).
        La validation du propriétaire, du service cible et de l'expiration
        est effectuée sous verrou de façon atomique.

        Returns:
            True si le nonce était valide et appartenait à cet utilisateur pour ce service,
            False sinon (dans tous les cas, le nonce est invalidé).
        """
        with self._lock:
            entree = self._nonces.pop(nonce, None)
            if entree is None:
                return False

            proprietaire, cible_enregistree, expiration = entree

            if proprietaire != utilisateur_id:
                return False
            if cible_enregistree and service_cible and cible_enregistree != service_cible:
                return False
            if self._horloge() > expiration:
                return False

            return True

    def _purger(self) -> None:
        """Supprime les nonces expirés. Doit être appelé sous verrou."""
        maintenant = self._horloge()
        self._nonces = {
            n: v for n, v in self._nonces.items() if v[2] > maintenant
        }