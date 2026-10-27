"""
Client gRPC utilisé par CE noeud pour appeler ses pairs
(échange de racines Merkle, propagation de révocation, heartbeat).
"""
import logging
import time

import grpc

import sync_pb2
import sync_pb2_grpc

logger = logging.getLogger(__name__)


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

    with grpc.insecure_channel(address) as channel:
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