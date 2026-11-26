"""
Service de vérification locale de preuves ZKP (Zero-Knowledge Proof) Groth16.

Utilise le binaire `snarkjs` via un sous-processus sécurisé pour vérifier
la validité mathématique de la preuve soumise par le client et applique
des contrôles stricts sur les signaux publics et les composantes de la preuve.
"""

import hashlib
import json
import logging
import os
import subprocess
import tempfile
from typing import Any, List, Optional, Tuple

logger = logging.getLogger("facein.zkp_verifier")

# Ordre du corps fini BN254 (alt_bn128)
BN254_PRIME = 21888242871839275222246405745257275088548364400416034343698204186575808495617

# Version du circuit et paramètres attendus
CIRCUIT_VERSION = "1.0.0"
EXPECTED_PUBLIC_SIGNALS_COUNT = 4
DEFAULT_SEUIL_MAX = int(os.getenv("DISTANCE_THRESHOLD", "16000000"))
MAX_PROOF_PAYLOAD_BYTES = 64 * 1024  # 64 Ko max pour prévenir les attaques DoS
SNARKJS_TIMEOUT_SECONDS = 10

API_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_VK_PATH = os.path.normpath(
    os.path.join(API_DIR, "..", "circuits", "build", "verification_key.json")
)


def decompose_nonce_to_signals(nonce_hex: str) -> Tuple[str, str]:
    """Décompose un nonce hexadécimal 256 bits en (nonceHi, nonceLo) canoniques BN254."""
    nonce_clean = str(nonce_hex).strip().lower()
    val = int(nonce_clean, 16)
    hi = val >> 128
    lo = val & ((1 << 128) - 1)
    return str(hi), str(lo)


def validate_public_signal_value(value: Any) -> Tuple[bool, str, Optional[int]]:
    """Vérifie qu'une valeur est un entier décimal positif canonique dans BN254."""
    if not isinstance(value, str):
        return False, "Le signal public doit être une chaîne de caractères", None

    s = value.strip()
    if not s or not s.isdigit():
        return False, "Le signal public doit être un entier décimal non signé", None

    # Représentation canonique : pas de zéros non significatifs en tête (sauf "0")
    if len(s) > 1 and s.startswith("0"):
        return False, "Le signal public n'est pas sous forme canonique (zéros superflus)", None

    val = int(s)
    if val >= BN254_PRIME:
        return False, "Le signal public dépasse le corps premier BN254", None

    return True, "", val


def validate_public_signals_structure(public_signals: Any) -> Tuple[bool, str]:
    """
    Vérifie la présence exacte des 4 signaux publics et leur validité BN254 canonique.
    Ordre strict attendu :
      [0] engagementAttendu
      [1] seuilMax
      [2] nonceHi
      [3] nonceLo
    """
    if not isinstance(public_signals, (list, tuple)):
        return False, "public_signals doit être une liste"

    count = len(public_signals)
    if count != EXPECTED_PUBLIC_SIGNALS_COUNT:
        return (
            False,
            f"Nombre de signaux publics invalide : {count} reçus "
            f"({EXPECTED_PUBLIC_SIGNALS_COUNT} attendus exactement)",
        )

    for i, sig in enumerate(public_signals):
        ok, err, _ = validate_public_signal_value(sig)
        if not ok:
            return False, f"Signal public [{i}] invalide : {err}"

    return True, ""


def validate_public_signals_integrity(
    public_signals: List[str],
    expected_commitment: str,
    nonce_hex: str,
    max_threshold: Optional[int] = None,
) -> Tuple[bool, str]:
    """
    Vérifie l'intégrité métier stricte des signaux publics :
    - Format et cardinalité (4 signaux canoniques BN254)
    - [0] correspond exactement à l'engagement enregistré de l'utilisateur
    - [1] correspond au seuil maximal autorisé par le serveur
    - [2] et [3] correspondent à la décomposition 128 bits du nonce
    """
    ok_struct, err_struct = validate_public_signals_structure(public_signals)
    if not ok_struct:
        return False, err_struct

    # 1. Vérification de l'engagement utilisateur
    if str(public_signals[0]).strip() != str(expected_commitment).strip():
        logger.warning(
            "Incohérence d'engagement ZKP : signal[0]=%s vs enregistré=%s",
            public_signals[0],
            expected_commitment,
        )
        return False, "L'engagement biométrique de référence ne correspond pas à l'utilisateur"

    # 2. Vérification du seuil maximal imposé par le serveur
    seuil_requis = max_threshold if max_threshold is not None else DEFAULT_SEUIL_MAX
    if int(public_signals[1]) != seuil_requis:
        logger.warning(
            "Tentative de manipulation du seuil ZKP : client=%s vs serveur=%s",
            public_signals[1],
            seuil_requis,
        )
        return False, f"Seuil biométrique non conforme (imposé par le serveur : {seuil_requis})"

    # 3. Vérification de la liaison cryptographique au nonce de session
    hi_attendu, lo_attendu = decompose_nonce_to_signals(nonce_hex)
    if public_signals[2] != hi_attendu or public_signals[3] != lo_attendu:
        logger.warning(
            "Liaison nonce ZKP invalide : reçus=(%s, %s) vs attendus=(%s, %s)",
            public_signals[2],
            public_signals[3],
            hi_attendu,
            lo_attendu,
        )
        return False, "La preuve ZKP n'est pas liée au défi nonce de cette session"

    return True, ""


def validate_proof_structure(proof: Any) -> Tuple[bool, str]:
    """Valide la taille et la structure d'une preuve Groth16 (pi_a, pi_b, pi_c)."""
    if not isinstance(proof, dict):
        return False, "La preuve Groth16 doit être un objet JSON valide"

    # Protection contre les payloads anormalement volumineux (anti-DoS)
    try:
        raw_size = len(json.dumps(proof))
        if raw_size > MAX_PROOF_PAYLOAD_BYTES:
            return False, f"Payload de preuve trop volumineux ({raw_size} octets > {MAX_PROOF_PAYLOAD_BYTES})"
    except Exception:
        return False, "Erreur de sérialisation de la preuve"

    for composante in ("pi_a", "pi_b", "pi_c"):
        if composante not in proof:
            return False, f"Composante '{composante}' manquante dans la preuve Groth16"
        val = proof[composante]
        if not isinstance(val, list) or len(val) < 2:
            return False, f"Composante '{composante}' invalide dans la preuve Groth16"

    return True, ""


def resolve_verification_key_path(path: Optional[str] = None) -> str:
    """Résout le chemin absolu vers verification_key.json avec fallbacks."""
    if path and os.path.isfile(path):
        return os.path.abspath(path)

    env_path = os.getenv("VERIFICATION_KEY_PATH")
    if env_path and os.path.isfile(env_path):
        return os.path.abspath(env_path)

    # 1. Vérification dans le dossier partagé des noeuds (nodes/shared/verification_key.json)
    shared_path = os.path.normpath(
        os.path.join(API_DIR, "..", "nodes", "shared", "verification_key.json")
    )
    if os.path.isfile(shared_path):
        return shared_path

    # 2. Vérification au chemin par défaut : ../circuits/build/verification_key.json
    if os.path.isfile(DEFAULT_VK_PATH):
        return DEFAULT_VK_PATH

    # 3. Vérification dans l'arborescence Docker éventuelle (/app/circuits/build/...)
    docker_path = os.path.join(API_DIR, "circuits", "build", "verification_key.json")
    if os.path.isfile(docker_path):
        return docker_path

    return shared_path


def get_verification_key_fingerprint(vk_path: Optional[str] = None) -> str:
    """Calcule l'empreinte SHA-256 de la clé de vérification pour contrôle d'intégrité."""
    resolved = resolve_verification_key_path(vk_path)
    if not os.path.isfile(resolved):
        return ""
    h = hashlib.sha256()
    with open(resolved, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


def verify_proof(
    proof: dict[str, Any],
    public_signals: list[str],
    verification_key_path: Optional[str] = None,
) -> bool:
    """
    Vérifie une preuve ZKP Groth16 avec snarkjs après validation stricte des entrées.

    Paramètres :
        proof : Dictionnaire représentant la preuve Groth16 (pi_a, pi_b, pi_c)
        public_signals : Liste ordonnée exacte [engagementAttendu, seuilMax, nonceHi, nonceLo]
        verification_key_path : Chemin optionnel vers verification_key.json

    Retourne :
        bool : True si la preuve est valide mathématiquement, False sinon.
    """
    # Validation structurelle obligatoire (même en mode mock de test)
    ok_proof, err_proof = validate_proof_structure(proof)
    if not ok_proof:
        logger.warning("Structure de preuve ZKP invalide : %s", err_proof)
        return False

    ok_sig, err_sig = validate_public_signals_structure(public_signals)
    if not ok_sig:
        logger.warning("Signaux publics ZKP invalides : %s", err_sig)
        return False

    # Mode simulation (pour environnements de test / CI sans Node.js ou snarkjs)
    if os.getenv("MOCK_ZKP_VERIFICATION", "").lower() in ("true", "1", "yes"):
        logger.warning(
            "Vérification ZKP en mode simulation (MOCK_ZKP_VERIFICATION=true). "
            "Preuve acceptée après validation syntaxique."
        )
        return True

    vk_path = resolve_verification_key_path(verification_key_path)
    if not os.path.isfile(vk_path):
        logger.error(
            "Clé de vérification introuvable à l'emplacement : '%s'.",
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

            cmd = ["snarkjs", "groth16", "verify", vk_path, public_file, proof_file]
            logger.info("Exécution de snarkjs : %s", " ".join(cmd))

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                timeout=SNARKJS_TIMEOUT_SECONDS,
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
                "Vérifiez que Node.js et snarkjs sont installés."
            )
            return False
        except subprocess.TimeoutExpired:
            logger.error(
                "Délai d'attente dépassé (%ds) lors de la vérification snarkjs.",
                SNARKJS_TIMEOUT_SECONDS,
            )
            return False
        except Exception as exc:
            logger.error("Erreur inattendue lors de la vérification ZKP : %s", exc)
            return False
