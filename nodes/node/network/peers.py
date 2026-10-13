"""Registre des pairs connus par un nœud FaceIN."""

from dataclasses import dataclass
from threading import Lock
from time import time
from typing import Literal


PeerStatus = Literal["unknown", "online", "suspect", "offline"]


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

    def __init__(self) -> None:
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
        if not 1 <= port <= 65535:
            raise ValueError("port doit être compris entre 1 et 65535")

        with self._lock:
            if node_id in self._peers:
                existing = self._peers[node_id]
                if (existing.host, existing.port) != (host, port):
                    raise ValueError(
                        f"Le pair {node_id!r} existe déjà avec une autre adresse"
                    )
                return

            self._peers[node_id] = PeerInfo(
                node_id=node_id,
                host=host,
                port=port,
            )

    def record_heartbeat(self, node_id: str) -> None:
        """Enregistre une réponse réussie à un heartbeat."""
        with self._lock:
            peer = self._require_peer(node_id)
            peer.status = "online"
            peer.last_heartbeat = time()
            peer.consecutive_failures = 0
            peer.last_error = None

    def record_failure(
        self,
        node_id: str,
        error: str,
        failures_before_offline: int = 3,
    ) -> None:
        """Enregistre un échec sans confondre une panne et un échec isolé."""
        if failures_before_offline < 1:
            raise ValueError("failures_before_offline doit être positif")

        with self._lock:
            peer = self._require_peer(node_id)
            peer.consecutive_failures += 1
            peer.last_error = error

            if peer.consecutive_failures >= failures_before_offline:
                peer.status = "offline"
            else:
                peer.status = "suspect"

    def get_peer(self, node_id: str) -> PeerInfo | None:
        """Retourne une copie des informations du pair."""
        with self._lock:
            peer = self._peers.get(node_id)
            if peer is None:
                return None

            return PeerInfo(**vars(peer))

    def get_all_peers(self) -> list[PeerInfo]:
        """Retourne une copie des informations de tous les pairs."""
        with self._lock:
            return [
                PeerInfo(**vars(peer))
                for peer in self._peers.values()
            ]

    def _require_peer(self, node_id: str) -> PeerInfo:
        """Récupère un pair ou signale explicitement son absence."""
        peer = self._peers.get(node_id)
        if peer is None:
            raise KeyError(f"Pair inconnu : {node_id!r}")
        return peer
