import secrets
import time
from threading import Lock

class NonceStore:
    def __init__(self, duree_s=30, horloge=time.time):
        self._duree = duree_s
        self._horloge = horloge
        self._nonces: dict[str, tuple[str, float]] = {}
        self._lock = Lock()

    def emettre(self, utilisateur_id):
        nonce = secrets.token_hex(16)
        expiration = self._horloge() + self._duree
        with self._lock:
            self._purger()
            self._nonces[nonce] = (utilisateur_id, expiration)
        return nonce, int(expiration * 1000)

    def consommer(self, utilisateur_id, nonce):
        with self._lock:
            entree = self._nonces.pop(nonce, None)   # retiré dans tous les cas
        if entree is None:
            return False
        proprietaire, expiration = entree
        return proprietaire == utilisateur_id and self._horloge() <= expiration

    def _purger(self):  # appelé sous verrou
        maintenant = self._horloge()
        self._nonces = {n: v for n, v in self._nonces.items() if v[1] > maintenant}