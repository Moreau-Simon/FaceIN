"""
Point d'entrée d'un noeud de vérification.

Important :
- Ce fichier est UNIQUE pour tous les noeuds.
- node-a, node-b et node-c utilisent exactement le même code.
- Leur identité et leur configuration viennent des variables
  d'environnement définies dans docker-compose.yml.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
import secrets
import signal
from threading import Event

import grpc

from store.engagements import EngagementsStore

from config import ErreurConfiguration, charger_configuration
from consensus.validation import VoteExecutor, decider, VerificateurZKP
from network.peer_client import demander_vote, envoyer_heartbeat
from network.peers import PeerRegistry, formater_adresse_pair
from network.server import ErreurDemarrageServeur, start_grpc_server
from verification.nonces import NonceStore

# ---------------------------------------------------------------------------
# Configuration des logs
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
)

logger = logging.getLogger(__name__)


def _journaliser_changement_etat(
    node_id: str,
    address: str,
    ancien: str,
    nouveau: str,
    raison: str | None = None,
    niveau: int = logging.INFO,
) -> None:
    """Journalise uniquement les transitions d'état d'un pair."""
    if ancien == nouveau:
        return

    suffixe = f" ({raison})" if raison else ""
    logger.log(
        niveau,
        "[%s] État de %s : %s -> %s%s",
        node_id,
        address,
        ancien,
        nouveau,
        suffixe,
    )


def _traiter_echec(
    registre: PeerRegistry,
    node_id: str,
    host: str,
    port: int,
    raison: str,
    niveau: int,
) -> None:
    """Enregistre un échec de battement de cœur et journalise la transition."""
    ancien, nouveau = registre.record_failure(host, port, raison)
    _journaliser_changement_etat(
        node_id,
        formater_adresse_pair(host, port),
        ancien,
        nouveau,
        raison,
        niveau,
    )


def _extraire_erreur_grpc(error: grpc.RpcError) -> tuple[str, str, str]:
    """Retourne une raison concise et les détails utiles au diagnostic."""
    code_method = getattr(error, "code", None)
    details_method = getattr(error, "details", None)
    if not callable(code_method) or not callable(details_method):
        return str(error), "", ""

    code = code_method()
    details = details_method()
    code_texte = getattr(code, "name", str(code)) if code is not None else ""
    details_texte = details.strip() if isinstance(details, str) else ""
    raison = ": ".join(part for part in (code_texte, details_texte) if part)
    return raison or str(error), code_texte, details_texte

# ---------------------------------------------------------------------------
# Programme principal
# ---------------------------------------------------------------------------

def main():
    """
    Démarre le noeud et vérifie périodiquement la disponibilité de ses pairs.

    Les battements de cœur sont envoyés en parallèle aux pairs. Une erreur de
    communication avec un pair n'empêche pas le traitement des autres.
    """

    try:
        config = charger_configuration()
    except ErreurConfiguration as exc:
        logger.error("Configuration invalide : %s", exc)
        raise SystemExit(1) from exc

    registre = PeerRegistry()
    for peer in config["peers"]:
        registre.register_peer(peer["host"], peer["port"])

    nonces = NonceStore()
    store = EngagementsStore()
    verifier = VerificateurZKP(store)
    vote_executor = VoteExecutor(
        max_workers=min(10, max(1, len(config["peers"]))),
        max_pending=10,
    )

    def interroger_pair(pair, demande, timeout_s):
        return demander_vote(
            pair.host,
            pair.port,
            demande,
            timeout_s,
        )

    def decider_fn(demande):
        return decider(
            demande,
            registre.get_non_offline_peers(),
            verifier,
            interroger_pair,
            config["seuil_majorite"],
            config["timeout_ms_consensus"] / 1000,
            vote_executor,
        )

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

    logger.info(
        "[%s] Nombre d'engagements chargés au démarrage : %d",
        config["node_id"],
        store.count(),
    )

    try:
        server = start_grpc_server(
            config["node_id"],
            config["port"],
            verifier,
            nonces,
            decider_fn,
            lambda utilisateur_id: secrets.token_urlsafe(32),
        )
    except ErreurDemarrageServeur as exc:
        vote_executor.close()
        logger.error("Échec du démarrage du serveur gRPC : %s", exc)
        raise SystemExit(1) from exc
        
    logger.info(
        "[%s] Nœud prêt ; %d pair(s) configuré(s)",
        config["node_id"],
        len(config["peers"]),
    )

    arret_demande = Event()
    signaux = (signal.SIGINT, signal.SIGTERM)
    gestionnaires_precedents = {}

    def demander_arret(_signum, _frame):
        arret_demande.set()

    try:
        for signe in signaux:
            gestionnaires_precedents[signe] = signal.getsignal(signe)
            signal.signal(signe, demander_arret)

        with ThreadPoolExecutor(
            max_workers=max(1, len(config["peers"]))
        ) as executor:
            while not arret_demande.is_set():
                futures = {
                    executor.submit(
                        envoyer_heartbeat,
                        config["node_id"],
                        peer["host"],
                        peer["port"],
                        config["timeout_sec_heartbeat"],
                    ): peer
                    for peer in config["peers"]
                }

                for future in as_completed(futures):
                    peer = futures[future]
                    address = formater_adresse_pair(
                        peer["host"], peer["port"]
                    )
                    try:
                        try:
                            resultat = future.result()
                        except grpc.RpcError as error:
                            raison, code, details = _extraire_erreur_grpc(
                                error
                            )
                            logger.debug(
                                "[%s] Détails de l'erreur gRPC vers %s : "
                                "code=%s, détails=%s, erreur=%s",
                                config["node_id"],
                                address,
                                code,
                                details,
                                error,
                                exc_info=True,
                            )
                            _traiter_echec(
                                registre,
                                config["node_id"],
                                peer["host"],
                                peer["port"],
                                raison,
                                logging.WARNING,
                            )
                            continue
                        except Exception:
                            logger.exception(
                                "[%s] Erreur inattendue pendant l'appel "
                                "battement de cœur vers %s ; le traitement des "
                                "autres pairs continue",
                                config["node_id"],
                                address,
                            )
                            continue

                        try:
                            node_id_pair, en_sante = resultat
                            if en_sante:
                                if (
                                    node_id_pair.strip().casefold()
                                    == config["node_id"].casefold()
                                ):
                                    raise ValueError(
                                        "Le pair annonce l'identité locale "
                                        f"{config['node_id']!r}"
                                    )
                                ancien, nouveau = registre.record_heartbeat(
                                    peer["host"],
                                    peer["port"],
                                    node_id_pair,
                                )
                                _journaliser_changement_etat(
                                    config["node_id"],
                                    address,
                                    ancien,
                                    nouveau,
                                )
                            else:
                                raison = "Le pair se déclare indisponible"
                                _traiter_echec(
                                    registre,
                                    config["node_id"],
                                    peer["host"],
                                    peer["port"],
                                    raison,
                                    logging.WARNING,
                                )
                        except ValueError as error:
                            _traiter_echec(
                                registre,
                                config["node_id"],
                                peer["host"],
                                peer["port"],
                                str(error),
                                logging.ERROR,
                            )
                    except Exception:
                        logger.exception(
                            "[%s] Erreur inattendue pendant le traitement "
                            "du battement de cœur vers %s ; le traitement des "
                            "autres pairs continue",
                            config["node_id"],
                            address,
                        )

                arret_demande.wait(config["intervalle_sec_heartbeat"])

    except KeyboardInterrupt:
        arret_demande.set()
    finally:
        server.stop(0).wait()
        vote_executor.close()
        for signe, gestionnaire in gestionnaires_precedents.items():
            signal.signal(signe, gestionnaire)
        logger.info(
            "[%s] Noeud arrêté",
            config["node_id"],
        )


# ---------------------------------------------------------------------------
# Lancement
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    main()