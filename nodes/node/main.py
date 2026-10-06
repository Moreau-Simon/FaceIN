"""
Point d'entrée d'un noeud de vérification.

Important : ce fichier est UNIQUE pour tous les noeuds. Ce qui différencie
node-a, node-b, node-c n'est jamais le code, mais la configuration lue
au démarrage via les variables d'environnement (voir docker-compose.yml).
"""

import os
import time
import logging

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def charger_configuration() -> dict:
    """Lit l'identité et la configuration de CE noeud depuis l'environnement."""
    node_id = os.environ.get("NODE_ID")
    node_port = os.environ.get("NODE_PORT", "50051")
    peers_raw = os.environ.get("PEERS", "")

    if not node_id:
        raise RuntimeError("NODE_ID manquant : chaque instance doit connaître son identité")

    peers = []
    if peers_raw:
        for peer in peers_raw.split(","):
            host, port = peer.split(":")
            peers.append({"host": host, "port": int(port)})

    return {
        "node_id": node_id,
        "port": int(node_port),
        "peers": peers,
    }


def main():
    config = charger_configuration()
    logger.info("Démarrage du noeud '%s' sur le port %s", config["node_id"], config["port"])
    logger.info("Pairs connus : %s", config["peers"])

    # TODO (étapes suivantes) :
    # - démarrer le serveur gRPC (voir grpc/server.py)
    # - lancer la boucle de heartbeat/sync Merkle vers les pairs (voir merkle/sync.py)
    # - exposer le service de vérification (voir consensus/validation.py)

    # Pour l'instant : squelette vivant, utile pour valider que l'architecture
    # "un seul code, plusieurs instances" fonctionne via Docker Compose.
    while True:
        logger.info("Noeud '%s' actif - en attente d'implémentation gRPC", config["node_id"])
        time.sleep(5)


if __name__ == "__main__":
    main()
