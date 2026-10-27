"""
Logique de validation et de consensus léger entre noeuds.

Principe : une authentification est validée par la vérification cryptographique
d'une preuve à divulgation nulle de connaissance (ZKP Groth16) via snarkjs.
"""

import json
import logging
import os
import subprocess
import tempfile
import warnings
from typing import List, Union

logger = logging.getLogger(__name__)


def valider_avec_mock(preuve_recue: str) -> bool:
    """
    Mock temporaire - Déprécié.

    .. deprecated::
        Utiliser :func:`verifier_preuve` pour la véritable vérification ZKP avec snarkjs.
    """
    warnings.warn(
        "valider_avec_mock est déprécié, utilisez verifier_preuve à la place.",
        DeprecationWarning,
        stacklevel=2,
    )
    return bool(preuve_recue)


def verifier_preuve(
    preuve_zkp_json: Union[str, dict],
    public_signals: Union[List[str], str],
    verification_key_path: str = "/app/shared/verification_key.json",
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
