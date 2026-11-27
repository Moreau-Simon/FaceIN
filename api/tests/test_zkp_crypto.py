"""
Tests cryptographiques Groth16 RÉELS pour la vérification ZKP côté API et nœuds.

Aucune preuve n'est acceptée par simulation : les preuves sont produites par
snarkjs à partir du circuit circuits/distance.circom et d'une cérémonie de TEST
jetable générée par scripts/generate_test_zkp_artifacts.sh (clés du dépôt
jamais modifiées).

Couvre :
- Preuve correcte acceptée par l'API et par un nœud (mêmes règles)
- Preuve altérée (pi_a modifié)
- Mauvais commitment
- Mauvais nonce / ancienne preuve rejouée avec un nouveau nonce
- Seuil excessif ou abaissé
- Signaux publics manquants ou supplémentaires
- Mauvaise version de circuit (ancien circuit à 2 signaux publics)
- Mauvaise clé de vérification (autre cérémonie)
- Imposteur : impossible de calculer un témoin pour l'engagement d'autrui
- Cohérence des clés du dépôt (frontend/circuit vs nodes/shared)

Les cas d'erreur d'exécution (timeout, snarkjs absent) restent testés par
simulation de sous-processus, uniquement dans le sens du REFUS.

Sans artefacts, les tests réels sont ignorés en local ; avec
FACEIN_REQUIRE_REAL_ZKP=1 (CI), leur absence est une erreur.
"""

import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault("STORE_BACKEND", "memory")

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
API_DIR = os.path.dirname(CURRENT_DIR)
ROOT_DIR = os.path.dirname(API_DIR)
NODES_DIR = os.path.join(ROOT_DIR, "nodes", "node")

for p in (API_DIR, NODES_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from services import zkp_verifier  # noqa: E402
from consensus.validation import VerificateurZKP, empaqueter_preuve  # noqa: E402
from store.engagements import EngagementsStore  # noqa: E402

ARTEFACTS_DIR = os.getenv(
    "FACEIN_TEST_ZKP_DIR",
    os.path.join(ROOT_DIR, "circuits", "build", "test-zkp"),
)
SNARKJS_LOCAL = os.path.join(ROOT_DIR, "circuits", "node_modules", ".bin")
if os.path.isdir(SNARKJS_LOCAL) and SNARKJS_LOCAL not in os.environ.get("PATH", ""):
    os.environ["PATH"] = SNARKJS_LOCAL + os.pathsep + os.environ.get("PATH", "")

EXIGER_ZKP_REEL = os.getenv("FACEIN_REQUIRE_REAL_ZKP", "").strip().lower() in {"1", "true", "yes"}
FICHIERS_REQUIS = [
    "vk_a.json",
    "vk_b.json",
    "commitment.txt",
    os.path.join("session1", "proof.json"),
    os.path.join("session1", "public.json"),
    os.path.join("session1", "nonce.txt"),
    os.path.join("session2", "proof.json"),
    os.path.join("session2", "public.json"),
    os.path.join("session2", "nonce.txt"),
]


def _artefacts_disponibles() -> tuple[bool, str]:
    if shutil.which("snarkjs") is None:
        return False, "snarkjs introuvable (cd circuits && npm ci)"
    manquants = [f for f in FICHIERS_REQUIS if not os.path.isfile(os.path.join(ARTEFACTS_DIR, f))]
    if manquants:
        return False, (
            "Artefacts Groth16 de test absents (%s). "
            "Lancez : bash scripts/generate_test_zkp_artifacts.sh" % ", ".join(manquants)
        )
    return True, ""


DISPONIBLES, RAISON_ABSENCE = _artefacts_disponibles()


def _lire_json(*chemin):
    with open(os.path.join(ARTEFACTS_DIR, *chemin), "r", encoding="utf-8") as f:
        return json.load(f)


def _lire_texte(*chemin):
    with open(os.path.join(ARTEFACTS_DIR, *chemin), "r", encoding="utf-8") as f:
        return f.read().strip()


class TestPresenceArtefactsZkp(unittest.TestCase):
    """En CI (FACEIN_REQUIRE_REAL_ZKP=1), l'absence d'artefacts réels est une erreur."""

    @unittest.skipUnless(EXIGER_ZKP_REEL, "FACEIN_REQUIRE_REAL_ZKP non activé")
    def test_artefacts_reels_obligatoires(self):
        self.assertTrue(DISPONIBLES, RAISON_ABSENCE)


@unittest.skipUnless(DISPONIBLES, RAISON_ABSENCE)
class TestZkpGroth16Reel(unittest.TestCase):
    """Vérifications Groth16 réelles (snarkjs) côté API et côté nœud."""

    @classmethod
    def setUpClass(cls):
        cls.vk_a = os.path.join(ARTEFACTS_DIR, "vk_a.json")
        cls.vk_b = os.path.join(ARTEFACTS_DIR, "vk_b.json")
        cls.commitment = _lire_texte("commitment.txt")
        cls.nonce1 = _lire_texte("session1", "nonce.txt")
        cls.nonce2 = _lire_texte("session2", "nonce.txt")
        cls.proof1 = _lire_json("session1", "proof.json")
        cls.public1 = _lire_json("session1", "public.json")
        cls.proof2 = _lire_json("session2", "proof.json")
        cls.public2 = _lire_json("session2", "public.json")

    def setUp(self):
        self._env = patch.dict(
            os.environ, {"MOCK_ZKP_VERIFICATION": "false", "FACEIN_ENV": "test"}
        )
        self._env.start()
        fd, self.store_path = tempfile.mkstemp(prefix="zkp_reel_", suffix=".json")
        os.close(fd)
        os.unlink(self.store_path)
        self.eng_store = EngagementsStore(persistence_file=self.store_path)
        self.eng_store.save("alice", self.commitment)
        self.noeud = VerificateurZKP(self.eng_store, verification_key_path=self.vk_a)

    def tearDown(self):
        self._env.stop()
        if os.path.exists(self.store_path):
            os.unlink(self.store_path)

    # --- Aides -----------------------------------------------------------------
    def _api_accepte(self, proof, public, nonce, vk=None):
        """Chaîne complète côté API : contrôle des signaux puis vérification Groth16."""
        ok, _ = zkp_verifier.validate_public_signals_integrity(public, self.commitment, nonce)
        if not ok:
            return False
        return zkp_verifier.verify_proof(proof, public, verification_key_path=vk or self.vk_a)

    def _noeud_accepte(self, proof, public, nonce):
        paquet = empaqueter_preuve(json.dumps(proof).encode(), public)
        return self.noeud("alice", paquet, nonce, "facein-web")

    # --- Cas nominal ------------------------------------------------------------
    def test_signaux_publics_conformes_au_contrat(self):
        hi, lo = zkp_verifier.decompose_nonce_to_signals(self.nonce1)
        self.assertEqual(
            self.public1,
            [self.commitment, str(zkp_verifier.DEFAULT_SEUIL_MAX), hi, lo],
        )

    def test_preuve_correcte_acceptee_api_et_noeud(self):
        self.assertTrue(self._api_accepte(self.proof1, self.public1, self.nonce1))
        self.assertTrue(self._noeud_accepte(self.proof1, self.public1, self.nonce1))

    def test_deuxieme_session_acceptee_avec_son_propre_nonce(self):
        self.assertTrue(self._api_accepte(self.proof2, self.public2, self.nonce2))
        self.assertTrue(self._noeud_accepte(self.proof2, self.public2, self.nonce2))

    # --- Altérations ------------------------------------------------------------
    def test_preuve_alteree_rejetee(self):
        alteree = copy.deepcopy(self.proof1)
        alteree["pi_a"][0] = str((int(alteree["pi_a"][0]) + 1) % zkp_verifier.BN254_PRIME)
        self.assertFalse(zkp_verifier.verify_proof(alteree, self.public1, verification_key_path=self.vk_a))
        self.assertFalse(self._noeud_accepte(alteree, self.public1, self.nonce1))

    def test_composantes_de_preuves_melangees_rejetees(self):
        melangee = copy.deepcopy(self.proof1)
        melangee["pi_c"] = self.proof2["pi_c"]
        self.assertFalse(zkp_verifier.verify_proof(melangee, self.public1, verification_key_path=self.vk_a))

    def test_mauvais_commitment_rejete_cryptographiquement(self):
        """Même en contournant le contrôle applicatif, Groth16 refuse un autre engagement."""
        signaux = list(self.public1)
        signaux[0] = str(int(signaux[0]) ^ 1)
        self.assertFalse(zkp_verifier.verify_proof(self.proof1, signaux, verification_key_path=self.vk_a))

    def test_mauvais_commitment_rejete_par_le_noeud(self):
        self.eng_store.save("alice", str(int(self.commitment) ^ 1))
        self.assertFalse(self._noeud_accepte(self.proof1, self.public1, self.nonce1))

    def test_seuil_excessif_rejete(self):
        signaux = list(self.public1)
        signaux[1] = str(zkp_verifier.DEFAULT_SEUIL_MAX * 10)
        self.assertFalse(zkp_verifier.verify_proof(self.proof1, signaux, verification_key_path=self.vk_a))
        self.assertFalse(self._api_accepte(self.proof1, signaux, self.nonce1))
        self.assertFalse(self._noeud_accepte(self.proof1, signaux, self.nonce1))

    # --- Rejeu et liaison au nonce ----------------------------------------------
    def test_ancienne_preuve_rejouee_sur_nouvelle_session_rejetee(self):
        """Preuve valide de la session 1 présentée pendant la session 2."""
        self.assertFalse(self._api_accepte(self.proof1, self.public1, self.nonce2))
        self.assertFalse(self._noeud_accepte(self.proof1, self.public1, self.nonce2))

    def test_ancienne_preuve_avec_nonce_reecrit_rejetee(self):
        """L'attaquant réécrit nonceHi/nonceLo d'une ancienne preuve avec le nouveau nonce."""
        hi2, lo2 = zkp_verifier.decompose_nonce_to_signals(self.nonce2)
        signaux = [self.public1[0], self.public1[1], hi2, lo2]
        self.assertFalse(zkp_verifier.verify_proof(self.proof1, signaux, verification_key_path=self.vk_a))
        self.assertFalse(self._api_accepte(self.proof1, signaux, self.nonce2))
        self.assertFalse(self._noeud_accepte(self.proof1, signaux, self.nonce2))

    def test_une_seule_moitie_du_nonce_modifiee_rejetee(self):
        hi2, lo2 = zkp_verifier.decompose_nonce_to_signals(self.nonce2)
        for signaux in (
            [self.public1[0], self.public1[1], hi2, self.public1[3]],
            [self.public1[0], self.public1[1], self.public1[2], lo2],
        ):
            self.assertFalse(zkp_verifier.verify_proof(self.proof1, signaux, verification_key_path=self.vk_a))

    # --- Format des signaux publics ---------------------------------------------
    def test_signaux_publics_manquants_rejetes(self):
        self.assertFalse(zkp_verifier.verify_proof(self.proof1, self.public1[:3], verification_key_path=self.vk_a))
        self.assertFalse(self._noeud_accepte(self.proof1, self.public1[:3], self.nonce1))

    def test_signaux_publics_supplementaires_rejetes(self):
        signaux = self.public1 + ["0"]
        self.assertFalse(zkp_verifier.verify_proof(self.proof1, signaux, verification_key_path=self.vk_a))
        self.assertFalse(self._noeud_accepte(self.proof1, signaux, self.nonce1))

    # --- Version de circuit et clé ----------------------------------------------
    def test_mauvaise_cle_de_verification_rejetee(self):
        """Preuve produite avec la cérémonie A, vérifiée avec la clé de la cérémonie B."""
        self.assertFalse(self._api_accepte(self.proof1, self.public1, self.nonce1, vk=self.vk_b))
        noeud_b = VerificateurZKP(self.eng_store, verification_key_path=self.vk_b)
        paquet = empaqueter_preuve(json.dumps(self.proof1).encode(), self.public1)
        self.assertFalse(noeud_b("alice", paquet, self.nonce1, "facein-web"))

    @unittest.skipUnless(
        os.path.isfile(os.path.join(ARTEFACTS_DIR, "legacy", "proof.json")),
        "Aucune preuve de l'ancien circuit à 2 signaux n'a été générée",
    )
    def test_preuve_ancienne_version_du_circuit_rejetee(self):
        proof = _lire_json("legacy", "proof.json")
        public = _lire_json("legacy", "public.json")
        self.assertEqual(len(public), 2)
        self.assertFalse(zkp_verifier.verify_proof(proof, public, verification_key_path=self.vk_a))
        self.assertFalse(self._noeud_accepte(proof, public, self.nonce1))
        # Compléter artificiellement les signaux ne rend pas l'ancienne preuve valide
        hi, lo = zkp_verifier.decompose_nonce_to_signals(self.nonce1)
        self.assertFalse(self._api_accepte(proof, public + [hi, lo], self.nonce1))

    # --- Imposteur --------------------------------------------------------------
    @unittest.skipUnless(
        os.path.isfile(os.path.join(ARTEFACTS_DIR, "distance_js", "distance.wasm")),
        "WASM de test absent",
    )
    def test_imposteur_ne_peut_pas_calculer_de_temoin(self):
        with tempfile.TemporaryDirectory() as tmp:
            res = subprocess.run(
                [
                    "snarkjs", "wtns", "calculate",
                    os.path.join(ARTEFACTS_DIR, "distance_js", "distance.wasm"),
                    os.path.join(ARTEFACTS_DIR, "session1", "input_impostor.json"),
                    os.path.join(tmp, "w.wtns"),
                ],
                capture_output=True, text=True, timeout=60, check=False,
            )
            self.assertFalse(
                res.returncode == 0 and os.path.isfile(os.path.join(tmp, "w.wtns")),
                "Le circuit a accepté le vecteur d'un imposteur",
            )


@unittest.skipUnless(shutil.which("snarkjs"), "snarkjs introuvable (cd circuits && npm ci)")
class TestCoherenceClesDuDepot(unittest.TestCase):
    """
    Les clés livrées doivent provenir d'une même cérémonie et du circuit courant :
    frontend/circuit/distance.zkey (prouveur) et nodes/shared/verification_key.json
    (vérificateur API + nœuds).
    """

    ZKEY = os.path.join(ROOT_DIR, "frontend", "circuit", "distance.zkey")
    VK_PARTAGEE = os.path.join(ROOT_DIR, "nodes", "shared", "verification_key.json")

    def setUp(self):
        if not (os.path.isfile(self.ZKEY) and os.path.isfile(self.VK_PARTAGEE)):
            self.skipTest("Clés du dépôt absentes")
        self.tmp = tempfile.mkdtemp(prefix="vk_front_")
        self.vk_front = os.path.join(self.tmp, "vk.json")
        subprocess.run(
            ["snarkjs", "zkey", "export", "verificationkey", self.ZKEY, self.vk_front],
            capture_output=True, text=True, timeout=120, check=True,
        )
        with open(self.vk_front, "r", encoding="utf-8") as f:
            self.vk_frontend = json.load(f)
        with open(self.VK_PARTAGEE, "r", encoding="utf-8") as f:
            self.vk_partagee = json.load(f)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_zkey_frontend_correspond_au_circuit_courant(self):
        self.assertEqual(
            self.vk_frontend["nPublic"],
            zkp_verifier.EXPECTED_PUBLIC_SIGNALS_COUNT,
            "frontend/circuit/distance.zkey ne correspond pas au circuit courant "
            "(nombre de signaux publics différent) : régénérer les clés via circuits/build.sh",
        )

    def test_cle_partagee_identique_a_celle_du_prouveur_frontend(self):
        self.assertEqual(
            self.vk_frontend,
            self.vk_partagee,
            "nodes/shared/verification_key.json n'est pas issue de frontend/circuit/distance.zkey",
        )


class TestZkpErreursExecution(unittest.TestCase):
    """Erreurs d'exécution du vérificateur : toujours un refus, jamais une acceptation."""

    PREUVE = {"pi_a": ["1", "2", "1"], "pi_b": [["1", "2"], ["3", "4"], ["1", "0"]], "pi_c": ["1", "2", "1"]}
    SIGNAUX = ["123", str(zkp_verifier.DEFAULT_SEUIL_MAX), "1", "2"]

    def setUp(self):
        fd, self.vk = tempfile.mkstemp(suffix=".json")
        os.close(fd)

    def tearDown(self):
        os.unlink(self.vk)

    def test_timeout_snarkjs_refuse(self):
        with patch.dict(os.environ, {"MOCK_ZKP_VERIFICATION": "false"}), patch(
            "services.zkp_verifier.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="snarkjs", timeout=10),
        ):
            self.assertFalse(zkp_verifier.verify_proof(self.PREUVE, self.SIGNAUX, verification_key_path=self.vk))

    def test_snarkjs_absent_refuse(self):
        with patch.dict(os.environ, {"MOCK_ZKP_VERIFICATION": "false"}), patch(
            "services.zkp_verifier.subprocess.run", side_effect=FileNotFoundError("snarkjs")
        ):
            self.assertFalse(zkp_verifier.verify_proof(self.PREUVE, self.SIGNAUX, verification_key_path=self.vk))

    def test_sortie_snarkjs_sans_ok_refusee(self):
        """Un code retour 0 sans message OK n'est pas une validation."""
        with patch.dict(os.environ, {"MOCK_ZKP_VERIFICATION": "false"}), patch(
            "services.zkp_verifier.subprocess.run",
            return_value=subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
        ):
            self.assertFalse(zkp_verifier.verify_proof(self.PREUVE, self.SIGNAUX, verification_key_path=self.vk))

    def test_json_preuve_malforme_refuse_par_le_noeud(self):
        fd, store_path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        os.unlink(store_path)
        try:
            eng = EngagementsStore(persistence_file=store_path)
            eng.save("alice", "123")
            noeud = VerificateurZKP(eng, verification_key_path=self.vk)
            self.assertFalse(noeud("alice", b"{pas du json", "a" * 64, "facein-web"))
        finally:
            if os.path.exists(store_path):
                os.unlink(store_path)

    def test_preuve_trop_volumineuse_refusee(self):
        enorme = dict(self.PREUVE)
        enorme["pi_a"] = ["1" * 70000, "2", "1"]
        self.assertFalse(zkp_verifier.verify_proof(enorme, self.SIGNAUX, verification_key_path=self.vk))


if __name__ == "__main__":
    unittest.main()
