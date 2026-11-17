"""
Logique de validation et de consensus léger entre noeuds.

Principe : une authentification est validée par la vérification cryptographique
d'une preuve à divulgation nulle de connaissance (ZKP Groth16) via snarkjs.
Le consensus (fonction ``decider``) agrège ensuite les votes des pairs.
"""

import json
import logging
import os
import subprocess
import tempfile
import time
from concurrent.futures import (
    CancelledError,
    Future,
    FIRST_COMPLETED,
    ThreadPoolExecutor,
    TimeoutError,
    wait,
)
from threading import BoundedSemaphore
from typing import Any, Callable, List, Union

import grpc

logger = logging.getLogger(__name__)


class VoteExecutor:
    """Pool partagé pour les votes, avec une limite aux tâches en attente."""

    def __init__(self, max_workers: int, max_pending: int):
        if max_workers < 1 or max_pending < 0:
            raise ValueError(
                "max_workers doit être positif et max_pending positif ou nul"
            )
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="vote-pair",
        )
        self._capacity = BoundedSemaphore(max_workers + max_pending)

    def submit(
        self,
        function: Callable[..., Any],
        *args: Any,
        timeout_s: float,
    ) -> Future[Any] | None:
        """Soumet une tâche sans dépasser la capacité bornée du pool."""
        if not self._capacity.acquire(timeout=max(0.0, timeout_s)):
            return None

        try:
            future = self._executor.submit(function, *args)
        except RuntimeError:
            self._capacity.release()
            raise

        future.add_done_callback(lambda _: self._capacity.release())
        return future

    def close(self) -> None:
        """Ferme le pool et attend la fin des appels gRPC en cours."""
        self._executor.shutdown(wait=True, cancel_futures=True)


def _adresse_vote(pair: Any) -> str:
    host = getattr(pair, "host", None)
    port = getattr(pair, "port", None)
    if host is not None and port is not None:
        host = str(host)
        if ":" in host and not (host.startswith("[") and host.endswith("]")):
            host = f"[{host}]"
        return f"{host}:{port}"
    return str(pair)


def _extraire_vote(resultat: Any) -> bool:
    vote = resultat[1] if isinstance(resultat, tuple) else resultat
    if type(vote) is not bool:
        raise ValueError(f"Vote invalide : {vote!r}")
    return vote


def _interroger_avec_echeance(
    interroger_pair: Callable[..., Any],
    pair: Any,
    demande: Any,
    echeance: float,
) -> Any:
    timeout_s = echeance - time.monotonic()
    if timeout_s <= 0:
        raise TimeoutError("Délai du consensus dépassé avant l'appel gRPC")
    return interroger_pair(pair, demande, timeout_s)


def _journaliser_resultat_vote(pair: Any, future: Future[Any]) -> None:
    adresse = _adresse_vote(pair)
    if future.cancelled():
        logger.debug(
            "Appel de vote vers %s annulé avant son démarrage",
            adresse,
        )
        return

    try:
        vote = _extraire_vote(future.result())
    except grpc.RpcError as error:
        code = error.code()
        if code == grpc.StatusCode.DEADLINE_EXCEEDED:
            logger.warning(
                "Délai gRPC dépassé pour le vote demandé à %s",
                adresse,
            )
        else:
            logger.warning(
                "Échec gRPC du vote demandé à %s (code=%s, détails=%s)",
                adresse,
                code,
                error.details(),
            )
    except TimeoutError:
        logger.warning("Délai dépassé pour le vote demandé à %s", adresse)
    except Exception as error:
        logger.error(
            "Erreur inattendue pendant le vote demandé à %s : %s",
            adresse,
            error,
            exc_info=(type(error), error, error.__traceback__),
        )
    else:
        logger.debug(
            "Vote %s reçu de %s",
            "POUR" if vote else "CONTRE",
            adresse,
        )


def _localiser_verification_key() -> str:
    """Localise le fichier verification_key.json avec fallbacks (Docker, env, relatif)."""
    env_path = os.getenv("VERIFICATION_KEY_PATH")
    if env_path and os.path.exists(env_path):
        return env_path
    docker_path = "/app/shared/verification_key.json"
    if os.path.exists(docker_path):
        return docker_path
    repo_shared = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__), "..", "..", "shared", "verification_key.json"
        )
    )
    if os.path.exists(repo_shared):
        return repo_shared
    return docker_path


CLE_VERIFICATION_PAR_DEFAUT = _localiser_verification_key()


# ---------------------------------------------------------------------------
# Vérification ZKP (moyen actuel : CLI snarkjs)
# ---------------------------------------------------------------------------
def verifier_preuve(
    preuve_zkp_json: Union[str, dict],
    public_signals: Union[List[str], str],
    verification_key_path: str = CLE_VERIFICATION_PAR_DEFAUT,
) -> bool:
    """
    Vérifie une preuve Groth16 en appelant le CLI snarkjs.

    Écrit temporairement la preuve et les signaux publics sur disque,
    exécute 'snarkjs groth16 verify <vkey> <public> <proof>', analyse le résultat
    puis nettoie les fichiers temporaires.

    Args:
        preuve_zkp_json: JSON ou dictionnaire de la preuve Groth16 (pi_a, pi_b, pi_c).
        public_signals: Liste ou JSON des signaux publics [engagementAttendu, seuilMax].
        verification_key_path: Chemin vers le fichier verification_key.json.

    Returns:
        True si la preuve est valide, False en cas d'échec ou d'erreur.
    """
    if not os.path.exists(verification_key_path):
        logger.error(
            "Fichier de clé de vérification ZKP introuvable : %s",
            verification_key_path,
        )
        return False

    # Normalisation de la preuve en chaîne JSON
    if isinstance(preuve_zkp_json, (dict, list)):
        preuve_str = json.dumps(preuve_zkp_json)
    else:
        preuve_str = str(preuve_zkp_json)

    # Normalisation des signaux publics en chaîne JSON
    if isinstance(public_signals, list):
        public_str = json.dumps([str(sig) for sig in public_signals])
    else:
        public_str = str(public_signals)

    preuve_fd, preuve_path = tempfile.mkstemp(suffix=".json", prefix="facein_proof_")
    public_fd, public_path = tempfile.mkstemp(suffix=".json", prefix="facein_pub_")

    try:
        with os.fdopen(preuve_fd, "w", encoding="utf-8") as f:
            f.write(preuve_str)
        with os.fdopen(public_fd, "w", encoding="utf-8") as f:
            f.write(public_str)

        # Commande snarkjs standard : snarkjs groth16 verify <vkey.json> <public.json> <proof.json>
        cmd = [
            "snarkjs",
            "groth16",
            "verify",
            verification_key_path,
            public_path,
            preuve_path,
        ]

        logger.info(
            "Exécution de la vérification ZKP : snarkjs groth16 verify %s ...",
            verification_key_path,
        )

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

        output = f"{result.stdout}\n{result.stderr}".strip()

        if result.returncode == 0 and "OK" in output:
            logger.info("Preuve ZKP validée avec succès par snarkjs.")
            return True
        else:
            logger.warning(
                "Échec de validation de la preuve ZKP (code: %s). Sortie: %s",
                result.returncode,
                output,
            )
            return False

    except FileNotFoundError:
        logger.error(
            "L'exécutable 'snarkjs' est introuvable. Assurez-vous que Node.js et snarkjs sont installés."
        )
        return False
    except subprocess.TimeoutExpired:
        logger.error(
            "Délai d'attente dépassé (timeout) lors de l'exécution de snarkjs."
        )
        return False
    except Exception as e:
        logger.exception("Erreur lors de la vérification de la preuve ZKP : %s", e)
        return False
    finally:
        for path in (preuve_path, public_path):
            try:
                if os.path.exists(path):
                    os.unlink(path)
            except OSError as e:
                logger.warning(
                    "Impossible de supprimer le fichier temporaire %s : %s",
                    path,
                    e,
                )


# ---------------------------------------------------------------------------
# Format d'échange de la preuve entre noeuds
#
# Le champ protobuf ``preuve_zkp`` (bytes) et la signature de ``decider`` /
# ``verifier_local`` ne changent pas : la preuve et ses signaux publics
# voyagent ensemble, dans ce champ, sous la forme d'un JSON
#     {"proof": {...}, "publicSignals": ["...", "..."]}
# ---------------------------------------------------------------------------
def empaqueter_preuve(preuve_zkp: Union[bytes, str, dict], public_signals) -> bytes:
    """Regroupe la preuve Groth16 et les signaux publics dans un seul ``bytes``.

    Lève ``ValueError`` si la preuve n'est pas un JSON valide.
    """
    if isinstance(preuve_zkp, (bytes, bytearray)):
        preuve_zkp = bytes(preuve_zkp).decode("utf-8")
    if isinstance(preuve_zkp, str):
        preuve_zkp = json.loads(preuve_zkp)
    contenu = {
        "proof": preuve_zkp,
        "publicSignals": [str(signal) for signal in public_signals],
    }
    return json.dumps(contenu).encode("utf-8")


# ---------------------------------------------------------------------------
# Architecture du consensus (branche develop)
# ---------------------------------------------------------------------------
def valider_avec_mock(
    utilisateur_id: str,
    preuve_recue: bytes,
    nonce: str,
    service_cible: str,
) -> bool:
    """Mock temporaire, remplacé en production par :class:`VerificateurZKP`."""
    return bool(preuve_recue)


class VerificateurZKP:
    """Vérificateur local branché sur l'architecture de consensus.

    Même signature d'appel que ``valider_avec_mock`` : une instance se passe
    donc telle quelle comme ``verifier`` à ``start_grpc_server`` et comme
    ``verifier_local`` à ``decider``.

    Le magasin d'engagements est exposé via l'attribut ``store`` : le serveur
    s'en sert pour répondre à ``RecupererDonneeAide``.
    """

    def __init__(self, store, verification_key_path: str = CLE_VERIFICATION_PAR_DEFAUT):
        self.store = store
        self._verification_key_path = verification_key_path

    def __call__(
        self,
        utilisateur_id: str,
        preuve_recue: Union[bytes, str],
        nonce: str,
        service_cible: str,
    ) -> bool:
        # 1. Décodage : enveloppe {"proof", "publicSignals"} ou preuve seule
        try:
            if isinstance(preuve_recue, (bytes, bytearray)):
                preuve_recue = bytes(preuve_recue).decode("utf-8")
            contenu = json.loads(preuve_recue)
        except (ValueError, TypeError):
            logger.warning("Preuve ZKP illisible (JSON invalide) pour %s.", utilisateur_id)
            return False

        if isinstance(contenu, dict) and "proof" in contenu and "publicSignals" in contenu:
            preuve = contenu["proof"]
            signaux_bruts = contenu["publicSignals"]
            if not isinstance(signaux_bruts, list):
                logger.warning("publicSignals invalide pour %s.", utilisateur_id)
                return False
            public_signals = [str(signal) for signal in signaux_bruts]
        else:
            preuve = contenu
            public_signals = []

        # 2. Engagement de référence de l'utilisateur
        engagement = self.store.get(utilisateur_id)
        nouvel_engagement = False
        if engagement is None:
            if not public_signals:
                logger.warning(
                    "Vérification refusée : engagement introuvable pour %s.",
                    utilisateur_id,
                )
                return False
            # Synchronisation depuis les signaux publics (flux API)
            engagement = public_signals[0]
            nouvel_engagement = True

        if not public_signals:
            public_signals = [engagement]
        elif public_signals[0] != engagement:
            logger.warning(
                "Incohérence d'engagement pour %s : stocké '%s' vs public '%s'.",
                utilisateur_id,
                engagement,
                public_signals[0],
            )
            return False

        # 3. Vérification cryptographique (snarkjs)
        if not verifier_preuve(preuve, public_signals, self._verification_key_path):
            return False

        # L'engagement n'est mémorisé qu'une fois la preuve validée
        if nouvel_engagement:
            self.store.save(utilisateur_id, engagement)
            logger.info(
                "Engagement de %s synchronisé depuis les signaux publics.",
                utilisateur_id,
            )
        return True


def decider(
    demande,
    pairs,
    verifier_local,
    interroger_pair,
    seuil,
    timeout_s,
    vote_executor: VoteExecutor,
):
    """Retourne True si le seuil de votes POUR (initiateur inclus) est atteint.

    ``interroger_pair`` peut retourner un booléen ou le tuple
    ``(node_id, vote)`` renvoyé par le client gRPC.
    Les appels distants partagent ``vote_executor`` et sont bornés par
    ``timeout_s`` ainsi que par la capacité de ce pool.
    """
    pour = (
        1
        if verifier_local(
            demande.utilisateur_id,
            demande.preuve_zkp,
            demande.nonce,
            demande.service_cible,
        )
        else 0
    )
    if pour >= seuil:
        return True

    echeance = time.monotonic() + timeout_s
    futures: dict[Future[Any], Any] = {}
    for pair in pairs:
        restant = echeance - time.monotonic()
        if restant <= 0:
            logger.warning(
                "Délai global du consensus dépassé avant l'envoi du vote à %s",
                _adresse_vote(pair),
            )
            break
        try:
            futur = vote_executor.submit(
                _interroger_avec_echeance,
                interroger_pair,
                pair,
                demande,
                echeance,
                timeout_s=restant,
            )
        except RuntimeError:
            logger.exception(
                "Impossible de soumettre le vote demandé à %s",
                _adresse_vote(pair),
            )
            continue
        if futur is None:
            logger.warning(
                "Capacité du pool de votes saturée pour %s",
                _adresse_vote(pair),
            )
            continue
        futur.add_done_callback(
            lambda completed, pair=pair: _journaliser_resultat_vote(
                pair, completed
            )
        )
        futures[futur] = pair

    en_attente = set(futures)
    try:
        while en_attente:
            restant = echeance - time.monotonic()
            if restant <= 0:
                logger.warning("Délai global du consensus dépassé")
                break
            termines, en_attente = wait(
                en_attente,
                timeout=restant,
                return_when=FIRST_COMPLETED,
            )
            if not termines:
                logger.warning("Délai global du consensus dépassé")
                break
            for futur in termines:
                try:
                    vote = _extraire_vote(futur.result())
                except CancelledError:
                    continue
                except Exception:
                    continue
                if vote:
                    pour += 1
                if pour >= seuil:
                    for restant_futur in en_attente:
                        restant_futur.cancel()
                    return True
    finally:
        for futur in en_attente:
            futur.cancel()

    return False