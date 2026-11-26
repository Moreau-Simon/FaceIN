"""
Boucle de synchronisation Merkle entre nœuds de vérification.

Toutes les ``intervalle_sec_merkle`` secondes :
1. Compare la racine Merkle locale avec celle de chaque pair actif.
2. Si les racines diffèrent, descend de façon ciblée sur les seules
   branches divergentes via ``RecupererBranche``.
3. Applique les feuilles manquantes ou plus récentes dans ``EngagementsStore``
   via ``sync_batch()`` (idempotent et protégé contre la résurrection d'un
   engagement révoqué).
"""

import logging
from typing import Any, Callable, Dict, List, Optional

from merkle.tree import MerkleTree
from network.peer_client import echanger_racine, recuperer_branche

logger = logging.getLogger(__name__)


def synchroniser_avec_pair(
    node_id: str,
    host: str,
    port: int,
    store: Any,
    timeout_sec: float = 3.0,
    echanger_racine_fn: Callable = echanger_racine,
    recuperer_branche_fn: Callable = recuperer_branche,
) -> Dict[str, Any]:
    """
    Synchronise l'état local des engagements avec un pair donné.

    Retourne un dictionnaire de bilan :
    ``{"pair": ..., "statut": ..., "nb_sync": int, "racine_locale": ..., "racine_pair": ...}``.
    """
    adresse = f"{host}:{port}"
    arbre_local = MerkleTree(store.all_entries())
    racine_locale = arbre_local.root_hash

    try:
        racine_pair, _ = echanger_racine_fn(host, port, node_id, timeout_sec)
    except Exception as exc:
        logger.warning(
            "[%s] Échec d'échange de racine Merkle avec %s : %s",
            node_id,
            adresse,
            exc,
        )
        return {
            "pair": adresse,
            "statut": "erreur",
            "nb_sync": 0,
            "racine_locale": racine_locale,
            "racine_pair": "",
        }

    if MerkleTree.racines_identiques(racine_locale, racine_pair):
        logger.debug("[%s] Racine Merkle synchronisée avec %s", node_id, adresse)
        return {
            "pair": adresse,
            "statut": "identique",
            "nb_sync": 0,
            "racine_locale": racine_locale,
            "racine_pair": racine_pair,
        }

    logger.info(
        "[%s] Divergence Merkle détectée avec %s (local=%s..., pair=%s...)",
        node_id,
        adresse,
        racine_locale[:12],
        racine_pair[:12],
    )

    def _fetch(chemin: str):
        return recuperer_branche_fn(host, port, chemin, timeout_sec)

    try:
        feuilles_divergentes = arbre_local.trouver_feuilles_divergentes(_fetch, racine_pair)
    except Exception as exc:
        logger.warning(
            "[%s] Échec lors de la récupération des branches sur %s : %s",
            node_id,
            adresse,
            exc,
        )
        return {
            "pair": adresse,
            "statut": "erreur",
            "nb_sync": 0,
            "racine_locale": racine_locale,
            "racine_pair": racine_pair,
        }

    nb_sync = 0
    if feuilles_divergentes:
        nb_sync = store.sync_batch(feuilles_divergentes)
        logger.info(
            "[%s] Resynchronisation ciblée depuis %s : %d feuille(s) appliquée(s) sur %d reçue(s)",
            node_id,
            adresse,
            nb_sync,
            len(feuilles_divergentes),
        )

    nouvelle_racine = MerkleTree(store.all_entries()).root_hash
    return {
        "pair": adresse,
        "statut": "synchronise",
        "nb_sync": nb_sync,
        "racine_locale": nouvelle_racine,
        "racine_pair": racine_pair,
    }


def synchroniser_tous_les_pairs(
    node_id: str,
    peers: List[Any],
    store: Any,
    timeout_sec: float = 3.0,
    echanger_racine_fn: Callable = echanger_racine,
    recuperer_branche_fn: Callable = recuperer_branche,
) -> List[Dict[str, Any]]:
    """Exécute la synchronisation Merkle sur l'ensemble des pairs fournis."""
    rapports: List[Dict[str, Any]] = []
    for peer in peers:
        host = peer["host"] if isinstance(peer, dict) else peer.host
        port = peer["port"] if isinstance(peer, dict) else peer.port
        rapport = synchroniser_avec_pair(
            node_id=node_id,
            host=host,
            port=port,
            store=store,
            timeout_sec=timeout_sec,
            echanger_racine_fn=echanger_racine_fn,
            recuperer_branche_fn=recuperer_branche_fn,
        )
        rapports.append(rapport)
    return rapports
