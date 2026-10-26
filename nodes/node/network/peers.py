"""Registre des pairs connus par un nœud FaceIN."""

from dataclasses import dataclass, replace
from threading import Lock
from time import time
from typing import Literal


PeerStatus = Literal["unknown", "online", "suspect", "offline"]

ECHECS_AVANT_HORS_LIGNE_DEFAUT = 3


def cle_pair(host: str, port: int) -> str:
    """Identifiant stable d'un pair dans le registre : « hote:port ».

    La configuration ne connaît que l'adresse d'un pair, pas son node_id
    (qu'il ne révèle qu'en répondant). L'adresse sert donc de clé.
    L'hôte est mis en minuscules, comme pour la détection de doublons
    dans config.py.
    """
    return f"{host.strip().lower()}:{port}"


@dataclass
class PeerInfo:
    """État observé d'un pair du réseau."""

    node_id: str
    host: str
    port: int
    status: PeerStatus = "unknown"
    last_heartbeat: float | None = None
    consecutive_failures: int = 0
    last_error: str | None = None


class PeerRegistry:
    """Stocke et protège l'état des pairs contre les accès concurrents."""

    def __init__(
        self,
        failures_before_offline: int = ECHECS_AVANT_HORS_LIGNE_DEFAUT,
    ) -> None:
        self._verifier_seuil(failures_before_offline)
        self._failures_before_offline = failures_before_offline
        self._peers: dict[str, PeerInfo] = {}
        self._lock = Lock()

    def register_peer(
        self,
        node_id: str,
        host: str,
        port: int,
    ) -> None:
        """Ajoute un pair sans écraser silencieusement un pair existant."""
        if not node_id.strip():
            raise ValueError("node_id ne peut pas être vide")
        if not host.strip():
            raise ValueError("host ne peut pas être vide")
        if type(port) is not int:
            raise TypeError("port doit être un entier")
        if not 1 <= port <= 65535:
            raise ValueError("port doit être compris entre 1 et 65535")

        with self._lock:
            if node_id in self._peers:
                existing = self._peers[node_id]
                if (existing.host, existing.port) != (host, port):
                    raise ValueError(
                        f"Le pair {node_id!r} existe déjà "
                        "avec une autre adresse"
                    )
                return

            self._peers[node_id] = PeerInfo(
                node_id=node_id,
                host=host,
                port=port,
            )

    def record_heartbeat(self, node_id: str) -> tuple[PeerStatus, PeerStatus]:
        """Enregistre une réponse réussie à un heartbeat.

        Retourne (ancien_statut, nouveau_statut) pour permettre de
        journaliser uniquement les changements d'état.
        """
        with self._lock:
            peer = self._require_peer(node_id)
            ancien = peer.status
            peer.status = "online"
            peer.last_heartbeat = time()
            peer.consecutive_failures = 0
            peer.last_error = None
            return ancien, peer.status

    def record_failure(
        self,
        node_id: str,
        error: str,
    ) -> tuple[PeerStatus, PeerStatus]:
        """Enregistre un échec sans confondre une panne et un échec isolé.

        Le seuil d'échecs consécutifs avant « offline » est celui fixé à la
        création du registre : il ne dépend pas de l'appelant.
        Retourne (ancien_statut, nouveau_statut).
        """
        seuil = self._failures_before_offline

        with self._lock:
            peer = self._require_peer(node_id)
            ancien = peer.status
            peer.consecutive_failures += 1
            peer.last_error = error

            if peer.consecutive_failures >= seuil:
                peer.status = "offline"
            else:
                peer.status = "suspect"

            return ancien, peer.status
        
    def get_peer(self, node_id: str) -> PeerInfo | None:
        """Retourne une copie des informations du pair."""
        with self._lock:
            peer = self._peers.get(node_id)
            if peer is None:
                return None

            return replace(peer)

    def get_all_peers(self) -> list[PeerInfo]:
        """Retourne une copie des informations de tous les pairs."""
        with self._lock:
            return [replace(peer) for peer in self._peers.values()]

    def get_non_offline_peers(self) -> list[PeerInfo]:
        """Retourne les pairs dont le statut n'est pas « offline ».

        Destinée au consensus : éviter d'attendre un timeout sur un pair déjà
        considéré en panne. Un pair « unknown » ou « suspect » est inclus.

        ATTENTION : ne pas l'utiliser pour choisir qui sonder par heartbeat.
        Un pair hors ligne doit continuer à être sondé, sinon son retour ne
        serait jamais détecté (utiliser get_all_peers).
        """
        with self._lock:
            return [
                replace(peer)
                for peer in self._peers.values()
                if peer.status != "offline"
            ]

    def _require_peer(self, node_id: str) -> PeerInfo:
        """Récupère un pair ou signale explicitement son absence."""
        peer = self._peers.get(node_id)
        if peer is None:
            raise KeyError(f"Pair inconnu : {node_id!r}")
        if type(peer.port) is not int:
            raise TypeError("port doit être un entier")
        if not 1 <= peer.port <= 65535:
            raise ValueError("port doit être compris entre 1 et 65535")
        return peer

    @staticmethod
    def _verifier_seuil(seuil: int) -> None:
        """Refuse un seuil qui n'est pas un entier supérieur ou égal à 1.

        `type(...) is int` rejette aussi les booléens (True est un int).
        """
        if type(seuil) is not int:
            raise TypeError("failures_before_offline doit être un entier")
        if seuil < 1:
            raise ValueError("failures_before_offline doit être positif")