"""
Point d'entrée d'un noeud de vérification.

Important :
- Ce fichier est UNIQUE pour tous les noeuds.
- node-a, node-b et node-c utilisent exactement le même code.
- Leur identité et leur configuration viennent des variables
  d'environnement définies dans docker-compose.yml.
"""

import logging
import os
import time

import grpc

from network.peer_client import envoyer_heartbeat
from network.server import start_grpc_server


# ---------------------------------------------------------------------------
# Configuration des logs
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Chargement de la configuration
# ---------------------------------------------------------------------------

def charger_configuration() -> dict:
    """
    Lit la configuration du noeud depuis les variables d'environnement.

    Variables utilisées :
        NODE_ID   : identité du noeud (ex: node-a)
        NODE_PORT : port gRPC du noeud (ex: 50051)
        PEERS     : liste des autres noeuds
                    (ex: node-b:50052,node-c:50053)
    """

    node_id = os.environ.get("NODE_ID")
    node_port = os.environ.get("NODE_PORT", "50051")
    peers_raw = os.environ.get("PEERS", "")

    # L'identité du noeud est obligatoire.
    if not node_id:
        raise RuntimeError(
            "NODE_ID manquant : chaque instance doit connaître son identité"
        )

    # Conversion de la liste des pairs.
    peers = []

    if peers_raw:
        for peer in peers_raw.split(","):
            peer = peer.strip()

            if not peer:
                continue

            try:
                host, port = peer.split(":")
            except ValueError:
                raise RuntimeError(
                    f"Format de pair invalide : '{peer}'. "
                    "Format attendu : hostname:port"
                )

            peers.append(
                {
                    "host": host,
                    "port": int(port),
                }
            )

    return {
        "node_id": node_id,
        "port": int(node_port),
        "peers": peers,
    }


# ---------------------------------------------------------------------------
# Programme principal
# ---------------------------------------------------------------------------

def main():
    """
    Démarre le noeud et vérifie périodiquement la disponibilité de ses pairs.

    Les heartbeats sont envoyés séquentiellement aux pairs. Une erreur de
    communication avec un pair n'empêche pas les tentatives vers les suivants.
    """

    config = charger_configuration()

    logger.info(
        "[%s] Initialisation du noeud sur le port %s",
        config["node_id"],
        config["port"],
    )

    logger.info(
        "[%s] Pairs configurés : %s",
        config["node_id"],
        config["peers"],
    )

    server = start_grpc_server(
        config["node_id"],
        config["port"],
    )
    logger.info(
        "[%s] Noeud prêt ; %d pair(s) configuré(s)",
        config["node_id"],
        len(config["peers"]),
    )

    try:
        while True:
            for peer in config["peers"]:
                address = f"{peer['host']}:{peer['port']}"
                try:
                    envoyer_heartbeat(
                        config["node_id"],
                        peer["host"],
                        peer["port"],
                    )
                except grpc.RpcError as error:
                    logger.warning(
                        "[%s] Échec du heartbeat vers %s : %s",
                        config["node_id"],
                        address,
                        error,
                    )

            time.sleep(5)

    except KeyboardInterrupt:
        # Attendre l'arrêt du serveur avant d'annoncer qu'il est arrêté.
        server.stop(0).wait()
        logger.info(
            "[%s] Noeud arrêté",
            config["node_id"],
        )


# ---------------------------------------------------------------------------
# Lancement
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    main()