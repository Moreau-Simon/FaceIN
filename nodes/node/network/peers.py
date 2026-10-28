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
    if not isinstance(host, str) or not host.strip():
        raise ValueError("host ne peut pas être vide")
    if type(port) is not int:
        raise TypeError("port doit être un entier")
    if not 1 <= port <= 65535:
        raise ValueError("port doit être compris entre 1 et 65535")
    return f"{host.strip().lower()}:{port}"


@dataclass
class PeerInfo:
    """État observé d'un pair du réseau."""

    node_id: str | None
    host: str
    port: int
    status: PeerStatus = "unknown"
    last_heartbeat: float | None = None
    consecutive_failures: int = 0
    last_error: str | None = None


class PeerRegistry:
    """Stocke et protège l'état des pairs contre les accès concurrents.

    Le verrou protège uniquement CE registre contre les accès simultanés de
    plusieurs threads. Chaque nœud a sa propre vue de ses pairs : deux nœuds
    peuvent temporairement en avoir une différente. L'accord entre nœuds est
    le rôle du consensus (quorum), pas de ce registre.

    Les pairs sont indexés par leur adresse normalisée « hote:port ».
    Leur node_id reste inconnu jusqu'à la première réponse heartbeat valide.
    """

    def __init__(
        self,
        failures_before_offline: int = ECHECS_AVANT_HORS_LIGNE_DEFAUT,
    ) -> None:
        self._verifier_seuil(failures_before_offline)
        self._failures_before_offline = failures_before_offline
        self._peers: dict[str, PeerInfo] = {}
        self._node_ids: dict[str, str] = {}
        self._lock = Lock()

    def register_peer(
        self,
        host: str,
        port: int,
    ) -> None:
        """Ajoute un pair configuré par adresse, sans identité présumée."""
        cle = cle_pair(host, port)
        host_normalise = host.strip()
        with self._lock:
            if cle in self._peers:
                return

            self._peers[cle] = PeerInfo(
                node_id=None,
                host=host_normalise,
                port=port,
            )

    def record_heartbeat(
        self, host: str, port: int, node_id: str
    ) -> tuple[PeerStatus, PeerStatus]:
        """Enregistre une réponse réussie à un heartbeat.

        Associe l'identité annoncée à l'adresse interrogée et refuse toute
        identité vide, changeante ou déjà associée à une autre adresse.
        Retourne (ancien_statut, nouveau_statut) pour permettre de
        journaliser uniquement les changements d'état.
        """
        if not isinstance(node_id, str):
            raise TypeError("node_id doit être une chaîne de caractères")
        node_id = node_id.strip()
        if not node_id:
            raise ValueError("node_id ne peut pas être vide")

        with self._lock:
            cle = cle_pair(host, port)
            peer = self._require_peer(cle)
            if (
                peer.node_id is not None
                and peer.node_id.casefold() != node_id.casefold()
            ):
                raise ValueError(
                    f"L'adresse {cle!r} a déjà annoncé le node_id "
                    f"{peer.node_id!r}, pas {node_id!r}"
                )
            cle_identite = node_id.casefold()
            autre_cle = self._node_ids.get(cle_identite)
            if autre_cle is not None and autre_cle != cle:
                raise ValueError(
                    f"Le node_id {node_id!r} est déjà associé à "
                    f"l'adresse {autre_cle!r}, pas {cle!r}"
                )

            if peer.node_id is None:
                peer.node_id = node_id
            self._node_ids[cle_identite] = cle
            ancien = peer.status
            peer.status = "online"
            peer.last_heartbeat = time()
            peer.consecutive_failures = 0
            peer.last_error = None
            return ancien, peer.status

    def record_failure(
        self,
        host: str,
        port: int,
        error: str,
    ) -> tuple[PeerStatus, PeerStatus]:
        """Enregistre un échec sans confondre une panne et un échec isolé.

        Le seuil d'échecs consécutifs avant « offline » est celui fixé à la
        création du registre : il ne dépend pas de l'appelant.
        Retourne (ancien_statut, nouveau_statut).
        """
        seuil = self._failures_before_offline

        with self._lock:
            peer = self._require_peer(cle_pair(host, port))
            ancien = peer.status
            peer.consecutive_failures += 1
            peer.last_error = error

            if peer.consecutive_failures >= seuil:
                peer.status = "offline"
            else:
                peer.status = "suspect"

            return ancien, peer.status

    def get_peer(self, host: str, port: int) -> PeerInfo | None:
        """Retourne une copie des informations du pair."""
        with self._lock:
            peer = self._peers.get(cle_pair(host, port))
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

    def _require_peer(self, cle: str) -> PeerInfo:
        """Récupère un pair ou signale explicitement son absence."""
        peer = self._peers.get(cle)
        if peer is None:
            raise KeyError(f"Pair inconnu : {cle!r}")
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