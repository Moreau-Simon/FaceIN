"""Chargement et validation de la configuration du nœud.

Deux sources de configuration :
- le fichier YAML partagé (paramètres communs à tous les nœuds) ;
- les variables d'environnement (identité propre à chaque nœud).

Variables d'environnement :
    NODE_ID     : identifiant unique du nœud (obligatoire)
    NODE_PORT   : port gRPC du nœud (défaut : 50051)
    PEERS       : pairs au format hostname:port, séparés par des virgules
    CONFIG_PATH : chemin explicite du YAML (optionnel, utile pour les tests)
"""

import os

import yaml

CHEMIN_DOCKER = "/app/shared/config/noeuds.yaml"
CHEMIN_RELATIF = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "shared",
        "config",
        "noeuds.yaml",
    )
)
HOTES_LOCAUX = {"localhost", "127.0.0.1"}


# ---------------------------------------------------------------------------
# Fichier YAML partagé
# ---------------------------------------------------------------------------

def _lire_yaml(chemin: str) -> dict:
    """Lit un fichier YAML. Lève FileNotFoundError s'il n'existe pas."""
    try:
        with open(chemin, "r", encoding="utf-8") as fichier:
            return yaml.safe_load(fichier)
    except PermissionError as exc:
        raise RuntimeError(f"Accès refusé au fichier : {chemin}") from exc
    except yaml.YAMLError as exc:
        raise RuntimeError(f"Fichier YAML invalide : {chemin}") from exc


def _entier_positif(nom: str, valeur: object) -> int:
    """Vérifie qu'une valeur est un entier strictement positif.

    `type(...) is int` rejette aussi les booléens (True est un int en Python).
    """
    if type(valeur) is not int or valeur <= 0:
        raise RuntimeError(
            f"Paramètre '{nom}' invalide : {valeur!r}. "
            "Un entier strictement positif est attendu"
        )
    return valeur


def _charger_yaml(chemin: str | None = None) -> dict:
    """Charge et valide le YAML partagé.

    Si `chemin` est fourni (CONFIG_PATH), seul ce fichier est essayé : une
    faute de frappe ne doit pas charger silencieusement un autre fichier.
    Sinon, on essaie le chemin Docker puis le chemin relatif au dépôt.

    `seuil_majorite` est optionnel : s'il est absent, il vaut None et sera
    calculé à partir du nombre de nœuds.
    """
    candidats = [chemin] if chemin else [CHEMIN_DOCKER, CHEMIN_RELATIF]

    config = None
    for candidat in dict.fromkeys(candidats):
        try:
            config = _lire_yaml(candidat)
            break
        except FileNotFoundError:
            continue
    else:
        raise RuntimeError(
            "Fichier de configuration introuvable. Chemins essayés : "
            + ", ".join(candidats)
        )

    if not isinstance(config, dict):
        raise RuntimeError("Configuration YAML vide ou invalide")

    consensus = config.get("consensus")
    sync_merkle = config.get("sync_merkle")

    if not isinstance(consensus, dict):
        raise RuntimeError("Section 'consensus' absente ou invalide")

    if not isinstance(sync_merkle, dict):
        raise RuntimeError("Section 'sync_merkle' absente ou invalide")

    seuil = consensus.get("seuil_majorite")
    if seuil is not None:
        _entier_positif("seuil_majorite", seuil)

    return {
        "seuil_majorite": seuil,
        "timeout_ms": _entier_positif(
            "timeout_ms", consensus.get("timeout_ms")
        ),
        "intervalle_secondes": _entier_positif(
            "intervalle_secondes", sync_merkle.get("intervalle_secondes")
        ),
    }


# ---------------------------------------------------------------------------
# Variables d'environnement
# ---------------------------------------------------------------------------

def _valider_port(port: int, contexte: str) -> None:
    """Vérifie qu'un port est dans la plage valide."""
    if not 1 <= port <= 65535:
        raise RuntimeError(
            f"Port hors limites (1-65535) pour {contexte} : {port}"
        )


def _lire_env() -> tuple[str, int, str]:
    """Lit et valide les variables d'environnement du nœud."""
    node_id = os.environ.get("NODE_ID", "").strip()
    node_port_raw = os.environ.get("NODE_PORT", "50051")
    peers_raw = os.environ.get("PEERS", "")

    if not node_id:
        raise RuntimeError(
            "NODE_ID manquant : chaque nœud doit avoir une identité"
        )

    try:
        node_port = int(node_port_raw)
    except ValueError as exc:
        raise RuntimeError(
            f"NODE_PORT invalide : {node_port_raw!r}"
        ) from exc

    _valider_port(node_port, "NODE_PORT")

    return node_id, node_port, peers_raw


def _parser_peers(peers_raw: str) -> list[dict[str, object]]:
    """Convertit la chaîne PEERS en liste de pairs validés."""
    peers = []
    adresses_vues = set()

    for element in peers_raw.split(","):
        peer = element.strip()

        if not peer:
            continue

        if peer.count(":") != 1:
            raise RuntimeError(
                f"Format de pair invalide : {peer!r}. "
                "Format attendu : hostname:port"
            )

        host, port_raw = peer.split(":")
        host = host.strip()

        if not host:
            raise RuntimeError(f"Nom d'hôte vide dans le pair : {peer!r}")

        try:
            port = int(port_raw)
        except ValueError as exc:
            raise RuntimeError(
                f"Port invalide pour le pair : {peer!r}"
            ) from exc

        _valider_port(port, f"le pair {peer!r}")

        adresse = (host.lower(), port)

        if adresse in adresses_vues:
            raise RuntimeError(f"Pair dupliqué dans PEERS : {peer!r}")

        adresses_vues.add(adresse)
        peers.append({"host": host, "port": port})

    return peers


def _verifier_pas_auto_reference(
    node_id: str, node_port: int, peers: list[dict[str, object]]
) -> None:
    """Refuse qu'un nœud se déclare lui-même comme pair.

    Dans Docker, le nom d'hôte d'un pair est le nom de son conteneur, donc
    le NODE_ID. En local, on détecte aussi localhost sur son propre port.
    """
    for peer in peers:
        host = str(peer["host"]).lower()
        est_soi_par_nom = host == node_id.lower()
        est_soi_en_local = host in HOTES_LOCAUX and peer["port"] == node_port

        if est_soi_par_nom or est_soi_en_local:
            raise RuntimeError(
                f"Le nœud {node_id!r} est listé parmi ses propres pairs "
                f"({host}:{peer['port']}) : corrigez PEERS"
            )


# ---------------------------------------------------------------------------
# Point d'entrée du module
# ---------------------------------------------------------------------------

def _determiner_seuil(seuil_yaml: int | None, nb_noeuds: int) -> int:
    """Détermine le seuil de majorité.

    Une majorité stricte exige au moins nb_noeuds // 2 + 1 nœuds.
    Sans valeur dans le YAML, ce minimum est utilisé : ajouter un nœud ne
    demande alors aucune modification du fichier partagé.
    """
    minimum = nb_noeuds // 2 + 1

    if seuil_yaml is None:
        return minimum

    if not minimum <= seuil_yaml <= nb_noeuds:
        raise RuntimeError(
            f"seuil_majorite={seuil_yaml} incohérent pour {nb_noeuds} nœuds "
            f"(valeur attendue entre {minimum} et {nb_noeuds})"
        )

    return seuil_yaml


def charger_configuration() -> dict:
    """Charge et valide la configuration complète du nœud."""
    chemin = os.environ.get("CONFIG_PATH", "").strip() or None

    config_yaml = _charger_yaml(chemin)
    node_id, node_port, peers_raw = _lire_env()
    peers = _parser_peers(peers_raw)
    _verifier_pas_auto_reference(node_id, node_port, peers)

    nb_noeuds = len(peers) + 1
    seuil = _determiner_seuil(config_yaml["seuil_majorite"], nb_noeuds)

    return {
        "node_id": node_id,
        "port": node_port,
        "peers": peers,
        "seuil_majorite": seuil,
        "timeout_ms_consensus": config_yaml["timeout_ms"],
        "intervalle_sec_merkle": config_yaml["intervalle_secondes"],
    }