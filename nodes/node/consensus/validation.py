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
from concurrent.futures import (
    ThreadPoolExecutor,
    TimeoutError,
    as_completed,
)
from typing import List, Union

logger = logging.getLogger(__name__)

CLE_VERIFICATION_PAR_DEFAUT = "/app/shared/verification_key.json"


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


def decider(demande, pairs, verifier_local, interroger_pair, seuil, timeout_s):
    """Retourne True si le seuil de votes POUR (initiateur inclus) est atteint.

    ``interroger_pair`` peut retourner un booléen ou le tuple
    ``(node_id, vote)`` renvoyé par le client gRPC.
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

    pool = ThreadPoolExecutor(max_workers=max(1, len(pairs)))
    futures = [pool.submit(interroger_pair, p, demande, timeout_s) for p in pairs]
    try:
        for futur in as_completed(futures, timeout=timeout_s):
            try:
                resultat = futur.result()
                vote = resultat[1] if isinstance(resultat, tuple) else resultat
                if vote is True:
                    pour += 1
            except Exception:
                continue
            if pour >= seuil:
                return True
    except TimeoutError:
        pass
    finally:
        pool.shutdown(wait=False, cancel_futures=True)
    return False