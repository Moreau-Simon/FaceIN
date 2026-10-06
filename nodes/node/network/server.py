"""
Serveur gRPC du noeud pour les échanges de synchronisation entre pairs.

Le service SyncService répond actuellement aux heartbeats.
"""
import logging
from concurrent import futures

import grpc

import sync_pb2
import sync_pb2_grpc


logger = logging.getLogger(__name__)


class SyncService(sync_pb2_grpc.SyncServiceServicer):
    """Implémente le service de synchronisation exposé par le noeud."""

    def __init__(self, node_id):
        self.node_id = node_id

    def Heartbeat(self, request, context):
        """Confirme que le noeud répond aux appels gRPC."""
        logger.info(
            "[%s] Heartbeat reçu de %s",
            self.node_id,
            request.noeud_id,
        )

        return sync_pb2.PongNoeud(
            noeud_id=self.node_id,
            en_sante=True,
        )


def start_grpc_server(node_id, port):
    """Démarre le service gRPC et retourne son serveur actif."""
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10)
    )

    sync_pb2_grpc.add_SyncServiceServicer_to_server(
        SyncService(node_id),
        server,
    )

    bound_port = server.add_insecure_port(f"0.0.0.0:{port}")
    if bound_port == 0:
        raise RuntimeError(
            f"[{node_id}] Impossible d'ouvrir le port gRPC {port}"
        )

    server.start()

    logger.info(
        "[%s] Serveur gRPC démarré sur 0.0.0.0:%s",
        node_id,
        bound_port,
    )

    return server