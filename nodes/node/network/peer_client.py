"""
Client gRPC utilisé par CE noeud pour appeler ses pairs
(échange de racines Merkle, propagation de révocation, heartbeat).
"""
import logging
import time
import os
from pathlib import Path

import grpc

import consensus_pb2
import consensus_pb2_grpc
import sync_pb2
import sync_pb2_grpc

logger = logging.getLogger(__name__)

def _tls_enabled() -> bool:
    return os.getenv("TLS_ENABLED", "false").strip().lower() in {
        "1", "true", "yes", "on"
    }


def creer_canal_securise(address: str):
    """Crée un canal gRPC avec authentification mutuelle TLS."""
    if not _tls_enabled():
        return grpc.insecure_channel(address)

    ca_path = os.getenv("TLS_CA_CERT", "/app/certs/ca.crt")
    cert_path = os.getenv("TLS_CERT")
    key_path = os.getenv("TLS_KEY")

    if not cert_path or not key_path:
        raise RuntimeError(
            "TLS_CERT et TLS_KEY doivent être configurés"
        )

    ca = Path(ca_path).read_bytes()
    cert = Path(cert_path).read_bytes()
    key = Path(key_path).read_bytes()

    credentials = grpc.ssl_channel_credentials(
        root_certificates=ca,
        private_key=key,
        certificate_chain=cert,
    )

    return grpc.secure_channel(address, credentials)

def envoyer_heartbeat(node_id, host, port, timeout_sec) -> tuple[str, bool]:
    """Appelle le heartbeat d'un pair avec un délai maximal configuré.

    Retourne un tuple ``(node_id_pair, en_sante)`` avec l'identité annoncée
    par le pair et son indicateur de santé.
    """
    address = f"{host}:{port}"

    logger.debug(
        "[%s] Tentative d'envoi du heartbeat vers %s",
        node_id,
        address,
    )

    with creer_canal_securise(address) as channel:
        stub = sync_pb2_grpc.SyncServiceStub(channel)

        response = stub.Heartbeat(
            sync_pb2.PingNoeud(
                noeud_id=node_id,
                timestamp=int(time.time() * 1000),
            ),
            timeout=timeout_sec,
        )

        if response.en_sante:
            logger.debug(
                "[%s] Heartbeat confirmé par %s",
                node_id,
                response.noeud_id,
            )
        else:
            logger.debug(
                "[%s] Le pair %s a répondu mais se déclare indisponible",
                node_id,
                response.noeud_id,
            )

        return response.noeud_id, response.en_sante

def demander_vote(
    host: str,
    port: int,
    demande: consensus_pb2.DemandeVote,
    timeout_sec: float,
) -> tuple[str, bool]:
    """Demande le vote d'un pair et refuse une réponse à une autre demande."""
    address = f"{host}:{port}"
    with creer_canal_securise(address) as channel:
        stub = consensus_pb2_grpc.ConsensusServiceStub(channel)
        reponse = stub.DemanderVote(demande, timeout=timeout_sec)

    if reponse.id_demande != demande.id_demande:
        raise ValueError(
            f"Réponse de vote avec id_demande inattendu : "
            f"{reponse.id_demande!r} (attendu {demande.id_demande!r})"
        )

    return (
        reponse.noeud_id,
        reponse.vote == consensus_pb2.VOTE_POUR,
    )