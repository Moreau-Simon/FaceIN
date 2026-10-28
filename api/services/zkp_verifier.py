"""
Service de vérification locale de preuves ZKP (Zero-Knowledge Proof) Groth16.

Utilise le binaire `snarkjs` via un sous-processus sécurisé pour vérifier
la validité mathématique de la preuve soumise par le client.
"""

import json
import logging
import os
import subprocess
import tempfile
from typing import Any, Optional

logger = logging.getLogger("facein.zkp_verifier")

# Chemin par défaut de la clé de vérification relatif au dossier api/ : ../circuits/build/verification_key.json
API_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_VK_PATH = os.path.normpath(
    os.path.join(API_DIR, "..", "circuits", "build", "verification_key.json")
)


def resolve_verification_key_path(path: Optional[str] = None) -> str:
    """Résout le chemin absolu vers verification_key.json avec fallbacks."""
    if path and os.path.isfile(path):
        return os.path.abspath(path)

    env_path = os.getenv("VERIFICATION_KEY_PATH")
    if env_path and os.path.isfile(env_path):
        return os.path.abspath(env_path)

    # 1. Vérification au chemin par défaut : ../circuits/build/verification_key.json
    if os.path.isfile(DEFAULT_VK_PATH):
        return DEFAULT_VK_PATH

    # 2. Vérification dans l'arborescence Docker éventuelle (/app/circuits/build/...)
    docker_path = os.path.join(API_DIR, "circuits", "build", "verification_key.json")
    if os.path.isfile(docker_path):
        return docker_path

    # 3. Vérification dans le dossier partagé des noeuds (nodes/shared/verification_key.json)
    shared_path = os.path.normpath(
        os.path.join(API_DIR, "..", "nodes", "shared", "verification_key.json")
    )
    if os.path.isfile(shared_path):
        return shared_path

    # Retourne le chemin par défaut même s'il n'existe pas encore pour message explicite
    return DEFAULT_VK_PATH


def verify_proof(
    proof: dict[str, Any],
    public_signals: list[str],
    verification_key_path: Optional[str] = None,
) -> bool:
    """
    Vérifie une preuve ZKP Groth16 avec snarkjs.

    Paramètres :
        proof : Dictionnaire représentant la preuve Groth16 (pi_a, pi_b, pi_c, protocol)
        public_signals : Liste ordonnée des signaux publics [engagementAttendu, seuilMax]
        verification_key_path : Chemin vers le fichier verification_key.json

    Retourne :
        bool : True si la preuve est valide, False sinon.
    """
    # Option de simulation pour les environnements de test / CI sans snarkjs installé
    if os.getenv("MOCK_ZKP_VERIFICATION", "").lower() in ("true", "1", "yes"):
        logger.warning(
            "Vérification ZKP en mode simulation (MOCK_ZKP_VERIFICATION=true). "
            "Preuve acceptée d'office."
        )
        return True

    vk_path = resolve_verification_key_path(verification_key_path)

    if not os.path.isfile(vk_path):
        logger.error(
            "Clé de vérification introuvable à l'emplacement : '%s'. "
            "Assurez-vous que le circuit ZKP a bien été compilé.",
            vk_path,
        )
        return False

    with tempfile.TemporaryDirectory() as tmpdir:
        proof_file = os.path.join(tmpdir, "proof.json")
        public_file = os.path.join(tmpdir, "public.json")

        try:
            with open(proof_file, "w", encoding="utf-8") as pf:
                json.dump(proof, pf)

            with open(public_file, "w", encoding="utf-8") as sf:
                json.dump(public_signals, sf)

            # Commande snarkjs standard : snarkjs groth16 verify <vk> <public> <proof>
            cmd = ["snarkjs", "groth16", "verify", vk_path, public_file, proof_file]
            logger.info("Exécution de snarkjs : %s", " ".join(cmd))

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
            )

            stdout = result.stdout or ""
            stderr = result.stderr or ""

            if result.returncode == 0 and ("OK" in stdout or "OK" in stderr):
                logger.info("Vérification locale ZKP Groth16 réussie avec succès.")
                return True

            logger.warning(
                "Échec de la vérification ZKP (code=%d). Sortie: %s %s",
                result.returncode,
                stdout.strip(),
                stderr.strip(),
            )
            return False

        except FileNotFoundError:
            logger.error(
                "La commande 'snarkjs' est introuvable. "
                "Vérifiez que Node.js et snarkjs sont installés (npm install -g snarkjs)."
            )
            return False
        except subprocess.TimeoutExpired:
            logger.error("Délai d'attente dépassé (timeout 10s) lors de la vérification snarkjs.")
            return False
        except Exception as exc:
            logger.error("Erreur inattendue lors de la vérification de la preuve ZKP : %s", exc)
            return False
