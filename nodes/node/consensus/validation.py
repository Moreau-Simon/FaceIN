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
from dataclasses import dataclass, field
from threading import BoundedSemaphore
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

try:
    import grpc
    _RpcError = grpc.RpcError
except ImportError:
    grpc = None

    class _RpcError(Exception):
        pass

logger = logging.getLogger(__name__)

# Constantes BN254 et paramètres du circuit ZKP
BN254_PRIME = 21888242871839275222246405745257275088548364400416034343698204186575808495617
EXPECTED_PUBLIC_SIGNALS_COUNT = 4
DEFAULT_SEUIL_MAX = int(os.getenv("DISTANCE_THRESHOLD", "16000000"))

# Environnements dans lesquels toute simulation est interdite (FACEIN_ENV),
# règle identique à celle de l'API Gateway (api/services/zkp_verifier.py).
PRODUCTION_ENV_VALUES = {"production", "prod"}


def est_environnement_production() -> bool:
    """Indique si le nœud s'exécute en production (FACEIN_ENV=production)."""
    return os.getenv("FACEIN_ENV", "").strip().lower() in PRODUCTION_ENV_VALUES


def mock_zkp_demande() -> bool:
    """Indique si la simulation ZKP est demandée via MOCK_ZKP_VERIFICATION."""
    return os.getenv("MOCK_ZKP_VERIFICATION", "").strip().lower() in ("true", "1", "yes")


def verifier_absence_mock_en_production() -> None:
    """
    Refuse le démarrage du nœud si une simulation est active en production.

    Lève RuntimeError lorsque FACEIN_ENV=production et MOCK_ZKP_VERIFICATION est actif.
    """
    if est_environnement_production() and mock_zkp_demande():
        raise RuntimeError(
            "MOCK_ZKP_VERIFICATION est interdit lorsque FACEIN_ENV=production. "
            "Désactivez la simulation ZKP avant de démarrer le nœud."
        )


@dataclass
class DetailVote:
    """Représente un vote individuel d'un nœud du réseau."""
    noeud_id: str
    vote_pour: bool
    raison: str = ""


@dataclass
class ResultatConsensus:
    """Rapport détaillé et infalsifiable du consensus décentralisé."""
    accepte: bool
    coordinateur_id: str
    votes: Dict[str, bool] = field(default_factory=dict)
    votes_recus: List[DetailVote] = field(default_factory=list)
    nb_votes_pour: int = 0
    nb_votes_contre: int = 0
    noeuds_indisponibles: List[str] = field(default_factory=list)
    seuil_requis: int = 2
    raison: str = ""

    def __bool__(self) -> bool:
        return self.accepte


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
    if isinstance(resultat, tuple):
        vote = resultat[1] if len(resultat) >= 2 else resultat[0]
    else:
        vote = resultat
    if type(vote) is not bool:
        raise ValueError(f"Vote invalide : {vote!r}")
    return vote


def _extraire_info_vote(resultat: Any, default_node_id: str = "") -> Tuple[str, bool, str]:
    """Extrait (node_id, vote_bool, raison) depuis la réponse d'un pair."""
    if isinstance(resultat, tuple):
        if len(resultat) >= 3:
            nid, vote, raison = resultat[0], resultat[1], resultat[2]
        elif len(resultat) == 2:
            nid, vote, raison = resultat[0], resultat[1], ""
        else:
            nid, vote, raison = default_node_id, resultat[0], ""
    else:
        nid, vote, raison = default_node_id, resultat, ""

    if type(vote) is not bool:
        raise ValueError(f"Vote invalide : {vote!r}")
    return str(nid or default_node_id), bool(vote), str(raison or "")


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
    except _RpcError as error:
        code = getattr(error, "code", lambda: None)()
        if grpc and hasattr(grpc, "StatusCode") and code == grpc.StatusCode.DEADLINE_EXCEEDED:
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
        public_signals: Liste ou JSON des 4 signaux publics :
            [engagementAttendu, seuilMax, nonceHi, nonceLo].
            nonceHi et nonceLo sont les moitiés haute/basse du nonce 256 bits,
            ce qui lie cryptographiquement la preuve à cette session d'authentification.
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

    if mock_zkp_demande():
        if est_environnement_production():
            logger.error(
                "MOCK_ZKP_VERIFICATION ignoré : simulation interdite en production. "
                "Preuve refusée."
            )
            return False
        logger.warning("Vérification ZKP en mode simulation (MOCK_ZKP_VERIFICATION=true).")
        return True

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
        # 1. Décodage : enveloppe {"proof", "publicSignals"}
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
            logger.warning("Structure d'enveloppe preuve/signaux invalide pour %s.", utilisateur_id)
            return False

        # 2. Vérification stricte de la cardinalité des signaux publics (4 attendus)
        if len(public_signals) != EXPECTED_PUBLIC_SIGNALS_COUNT:
            logger.warning(
                "Nombre de signaux publics invalide pour %s : %d (attendu : %d).",
                utilisateur_id,
                len(public_signals),
                EXPECTED_PUBLIC_SIGNALS_COUNT,
            )
            return False

        # 3. Vérification canonique BN254 de chaque signal public
        for i, sig in enumerate(public_signals):
            s = str(sig).strip()
            if not s or not s.isdigit():
                logger.warning("Signal public [%d] non numérique pour %s : %s", i, utilisateur_id, s)
                return False
            if len(s) > 1 and s.startswith("0"):
                logger.warning("Signal public [%d] non canonique (zéros superflus) pour %s : %s", i, utilisateur_id, s)
                return False
            val = int(s)
            if val >= BN254_PRIME:
                logger.warning("Signal public [%d] hors corps BN254 pour %s : %d", i, utilisateur_id, val)
                return False

        # 4. Engagement de référence de l'utilisateur
        engagement = self.store.get(utilisateur_id)
        if engagement is None:
            # L'engagement doit être enregistré lors du processus d'inscription
            # (register). Il ne peut PAS être appris depuis les signaux publics
            # d'une preuve d'authentification : cela permettrait à n'importe qui
            # de forger un engagement valide au moment de la vérification.
            logger.warning(
                "Vérification refusée : engagement introuvable pour %s. "
                "L'utilisateur doit s'inscrire (register) avant de s'authentifier.",
                utilisateur_id,
            )
            return False

        if public_signals[0] != str(engagement).strip():
            logger.warning(
                "Incohérence d'engagement pour %s : stocké '%s' vs public '%s'.",
                utilisateur_id,
                engagement,
                public_signals[0],
            )
            return False

        # 5. Vérification du seuil maximal imposé par le serveur
        if int(public_signals[1]) != DEFAULT_SEUIL_MAX:
            logger.warning(
                "Tentative d'altération du seuil ZKP pour %s : reçu=%s vs attendu=%s",
                utilisateur_id,
                public_signals[1],
                DEFAULT_SEUIL_MAX,
            )
            return False

        # 6. Vérification de la liaison cryptographique au nonce de session
        try:
            nonce_clean = str(nonce).strip().lower()
            nonce_val = int(nonce_clean, 16)
            hi_attendu = str(nonce_val >> 128)
            lo_attendu = str(nonce_val & ((1 << 128) - 1))
            if public_signals[2] != hi_attendu or public_signals[3] != lo_attendu:
                logger.warning(
                    "Liaison nonce ZKP invalide pour %s : (%s, %s) vs attendu (%s, %s)",
                    utilisateur_id,
                    public_signals[2],
                    public_signals[3],
                    hi_attendu,
                    lo_attendu,
                )
                return False
        except Exception as exc:
            logger.warning("Erreur lors de la validation du nonce ZKP pour %s : %s", utilisateur_id, exc)
            return False

        # 7. Vérification cryptographique (snarkjs)
        # Les 4 signaux publics vérifiés :
        #   [0] engagementAttendu   — Poseidon hash du vecteur de référence
        #   [1] seuilMax            — Distance maximale tolérée
        #   [2] nonceHi             — 128 bits de poids fort du nonce (nonce >> 128)
        #   [3] nonceLo             — 128 bits de poids faible du nonce (nonce & mask)
        if not verifier_preuve(preuve, public_signals, self._verification_key_path):
            return False

        return True


def decider(
    demande,
    pairs,
    verifier_local,
    interroger_pair,
    seuil,
    timeout_s,
    vote_executor: VoteExecutor,
    node_id: str = "initiateur",
    return_details: bool = False,
):
    """Retourne la décision de consensus ou un objet ResultatConsensus si return_details=True.

    ``interroger_pair`` peut retourner un booléen ou un tuple
    ``(node_id, vote)`` ou ``(node_id, vote, raison)`` renvoyé par le client gRPC.
    Les appels distants partagent ``vote_executor`` et sont bornés par
    ``timeout_s`` ainsi que par la capacité de ce pool.
    """
    total_noeuds = len(pairs) + 1
    if seuil is None or seuil <= 0:
        seuil = (total_noeuds // 2) + 1
    elif seuil > total_noeuds:
        seuil = total_noeuds

    votes_recus: List[DetailVote] = []
    votes_map: Dict[str, bool] = {}
    noeuds_indisponibles: List[str] = []

    try:
        vote_local = bool(
            verifier_local(
                demande.utilisateur_id,
                demande.preuve_zkp,
                demande.nonce,
                demande.service_cible,
            )
        )
        raison_locale = "" if vote_local else "Vérification locale invalide"
    except Exception as exc:
        logger.exception(
            "Erreur inattendue pendant la vérification locale pour %s",
            getattr(demande, "utilisateur_id", ""),
        )
        vote_local = False
        raison_locale = f"Erreur locale: {exc}"

    votes_recus.append(
        DetailVote(noeud_id=node_id, vote_pour=vote_local, raison=raison_locale)
    )
    votes_map[node_id] = vote_local
    pour = 1 if vote_local else 0
    contre = 0 if vote_local else 1

    if pour >= seuil and not pairs:
        # Seul nœud du réseau ou seuil déjà atteint sans pairs
        if return_details:
            return ResultatConsensus(
                accepte=True,
                coordinateur_id=node_id,
                votes=votes_map,
                votes_recus=votes_recus,
                nb_votes_pour=pour,
                nb_votes_contre=contre,
                noeuds_indisponibles=noeuds_indisponibles,
                seuil_requis=seuil,
                raison="",
            )
        return True

    echeance = time.monotonic() + timeout_s
    futures: dict[Future[Any], Any] = {}
    for pair in pairs:
        restant = echeance - time.monotonic()
        pair_ident = getattr(pair, "node_id", None) or _adresse_vote(pair)
        if restant <= 0:
            logger.warning(
                "Délai global du consensus dépassé avant l'envoi du vote à %s",
                pair_ident,
            )
            noeuds_indisponibles.append(pair_ident)
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
                pair_ident,
            )
            noeuds_indisponibles.append(pair_ident)
            continue
        if futur is None:
            logger.warning(
                "Capacité du pool de votes saturée pour %s",
                pair_ident,
            )
            noeuds_indisponibles.append(pair_ident)
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
                for f in en_attente:
                    f.cancel()
                    pair = futures[f]
                    p_id = getattr(pair, "node_id", None) or _adresse_vote(pair)
                    noeuds_indisponibles.append(p_id)
                break

            termines, en_attente = wait(
                en_attente,
                timeout=restant,
                return_when=FIRST_COMPLETED,
            )
            if not termines:
                logger.warning("Délai global du consensus dépassé")
                for f in en_attente:
                    f.cancel()
                    pair = futures[f]
                    p_id = getattr(pair, "node_id", None) or _adresse_vote(pair)
                    noeuds_indisponibles.append(p_id)
                break

            for futur in termines:
                pair = futures[futur]
                pair_ident = getattr(pair, "node_id", None) or _adresse_vote(pair)
                if futur.cancelled():
                    continue
                try:
                    res = futur.result()
                    nid, vote, raison = _extraire_info_vote(
                        res, default_node_id=pair_ident
                    )
                    votes_map[nid] = vote
                    votes_recus.append(
                        DetailVote(noeud_id=nid, vote_pour=vote, raison=raison)
                    )
                    if vote:
                        pour += 1
                    else:
                        contre += 1
                except CancelledError:
                    continue
                except Exception:
                    noeuds_indisponibles.append(pair_ident)
    finally:
        for futur in en_attente:
            futur.cancel()

    accepte = pour >= seuil
    if return_details:
        raison_finale = (
            ""
            if accepte
            else f"Consensus non atteint ({pour}/{total_noeuds} votes positifs, {seuil} requis)"
        )
        return ResultatConsensus(
            accepte=accepte,
            coordinateur_id=node_id,
            votes=votes_map,
            votes_recus=votes_recus,
            nb_votes_pour=pour,
            nb_votes_contre=contre,
            noeuds_indisponibles=noeuds_indisponibles,
            seuil_requis=seuil,
            raison=raison_finale,
        )

    return accepte