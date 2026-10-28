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


def envoyer_heartbeat(node_id, host, port):
    """Appelle le service Heartbeat d'un pair avec un délai maximal de 3 s."""
    address = f"{host}:{port}"

    logger.info(
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
            timeout=3,
        )

        if response.en_sante:
            logger.info(
                "[%s] Heartbeat confirmé par %s",
                node_id,
                response.noeud_id,
            )
        else:
            logger.warning(
                "[%s] Le pair %s a répondu mais se déclare indisponible",
                node_id,
                response.noeud_id,
            )