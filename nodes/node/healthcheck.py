"""Vérifie la disponibilité gRPC locale avec l'identité mTLS du nœud."""

import logging
import os

import grpc
from grpc_health.v1 import health_pb2, health_pb2_grpc

from network.peer_client import creer_canal_securise, fermer_canaux
from network.peers import formater_adresse_pair

logger = logging.getLogger(__name__)


def main() -> int:
    node_id = os.getenv("NODE_ID", "").strip()
    port_raw = os.getenv("NODE_PORT", "").strip()
    if not node_id or not port_raw:
        logger.error("NODE_ID et NODE_PORT sont requis pour le contrôle de santé")
        return 1

    try:
        address = formater_adresse_pair(node_id, int(port_raw))
        channel = creer_canal_securise(address)
        response = health_pb2_grpc.HealthStub(channel).Check(
            health_pb2.HealthCheckRequest(),
            timeout=3,
        )
    except (ValueError, RuntimeError, OSError) as error:
        logger.error("Échec du contrôle de santé gRPC : %s", error)
        return 1
    except grpc.RpcError as error:
        logger.error(
            "Échec de l'appel gRPC de contrôle de santé (%s) : %s",
            error.code(),
            error.details(),
        )
        return 1
    finally:
        fermer_canaux()

    if response.status != health_pb2.HealthCheckResponse.SERVING:
        logger.error("Le nœud %s n'est pas prêt à servir les requêtes", node_id)
        return 1

    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.ERROR)
    raise SystemExit(main())
