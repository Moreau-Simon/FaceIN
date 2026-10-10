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
import yaml

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
    Charge les paramètres communs depuis le YAML et les paramètres
    propres au nœud depuis les variables d'environnement.

    Variables :
        NODE_ID   : identifiant unique du nœud (obligatoire)
        NODE_PORT : port gRPC (défaut : 50051)
        PEERS     : liste des pairs au format hostname:port,
                    séparés par des virgules
    """
    chemin = "/app/shared/config/noeuds.yaml"

    # 1. Charger le fichier YAML
    try:
        with open(chemin, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

    except FileNotFoundError as e:
        raise RuntimeError(
            f"Fichier de configuration introuvable : {chemin}"
        ) from e

    except PermissionError as e:
        raise RuntimeError(
            f"Accès refusé au fichier : {chemin}"
        ) from e

    except yaml.YAMLError as e:
        raise RuntimeError(
            f"Fichier YAML invalide : {chemin}"
        ) from e

    # 2. Vérifier la structure du YAML
    if not isinstance(config, dict):
        raise RuntimeError("Configuration YAML vide ou invalide")

    consensus = config.get("consensus")
    sync_merkle = config.get("sync_merkle")

    if not isinstance(consensus, dict):
        raise RuntimeError(
            "Section 'consensus' absente ou invalide"
        )

    if not isinstance(sync_merkle, dict):
        raise RuntimeError(
            "Section 'sync_merkle' absente ou invalide"
        )

    # 3. Récupérer et valider les paramètres YAML
    seuil_majorite = consensus.get("seuil_majorite")
    timeout_ms_consensus = consensus.get("timeout_ms")
    intervalle_sec_merkle = sync_merkle.get(
        "intervalle_secondes"
    )

    parametres = {
        "seuil_majorite": seuil_majorite,
        "timeout_ms": timeout_ms_consensus,
        "intervalle_secondes": intervalle_sec_merkle,
    }

    for nom, valeur in parametres.items():
        if type(valeur) is not int or valeur <= 0:
            raise RuntimeError(
                f"Paramètre '{nom}' invalide : "
                "un entier strictement positif est attendu"
            )

    # 4. Charger les variables d'environnement
    node_id = os.environ.get("NODE_ID", "").strip()
    node_port_raw = os.environ.get("NODE_PORT", "50051")
    peers_raw = os.environ.get("PEERS", "")

    if not node_id:
        raise RuntimeError(
            "NODE_ID manquant : chaque nœud doit avoir une identité"
        )

    # 5. Valider le port local
    try:
        node_port = int(node_port_raw)
    except ValueError as e:
        raise RuntimeError(
            f"NODE_PORT invalide : {node_port_raw!r}"
        ) from e

    if not 1 <= node_port <= 65535:
        raise RuntimeError(
            "NODE_PORT doit être compris entre 1 et 65535"
        )

    # 6. Analyser les pairs
    peers = []
    adresses_vues = set()

    for element in peers_raw.split(","):
        peer = element.strip()

        if not peer:
            continue

        # Format pris en charge : hostname:port ou IPv4:port.
        if peer.count(":") != 1:
            raise RuntimeError(
                f"Format de pair invalide : {peer!r}. "
                "Format attendu : hostname:port"
            )

        host, port_raw = peer.rsplit(":", 1)
        host = host.strip()

        if not host:
            raise RuntimeError(
                f"Nom d'hôte vide dans le pair : {peer!r}"
            )

        try:
            port = int(port_raw)
        except ValueError as e:
            raise RuntimeError(
                f"Port invalide pour le pair : {peer!r}"
            ) from e

        if not 1 <= port <= 65535:
            raise RuntimeError(
                f"Port hors limites pour le pair : {peer!r}"
            )

        adresse = (host.lower(), port)

        if adresse in adresses_vues:
            raise RuntimeError(
                f"Pair dupliqué dans PEERS : {peer!r}"
            )

        adresses_vues.add(adresse)

        peers.append({
            "host": host,
            "port": port,
        })

    # 7. Retourner la configuration validée
    return {
        "node_id": node_id,
        "port": node_port,
        "peers": peers,
        "seuil_majorite": seuil_majorite,
        "timeout_ms_consensus": timeout_ms_consensus,
        "intervalle_sec_merkle": intervalle_sec_merkle,
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