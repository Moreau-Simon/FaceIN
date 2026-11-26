"""
Tests unitaires pour la validation des preuves ZKP (consensus/validation.py).
"""

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from consensus.validation import (
    BN254_PRIME,
    DEFAULT_SEUIL_MAX,
    EXPECTED_PUBLIC_SIGNALS_COUNT,
    VerificateurZKP,
    empaqueter_preuve,
    valider_avec_mock,
    verifier_preuve,
)
from store.engagements import EngagementsStore


class TestValidationZKP(unittest.TestCase):
    """Vérifie le comportement de la vérification Groth16 bas-niveau."""

    def test_valider_avec_mock_accepte_une_preuve_non_vide(self):
        self.assertTrue(valider_avec_mock("user-1", b"preuve", "nonce", "service"))
        self.assertFalse(valider_avec_mock("user-1", b"", "nonce", "service"))

    def test_verifier_preuve_fichier_cle_manquant(self):
        # Chemin inexistant
        res = verifier_preuve(
            preuve_zkp_json='{"pi_a": []}',
            public_signals=["123", "100000", "0", "0"],
            verification_key_path="/fichier/inexistant/verification_key.json",
        )
        self.assertFalse(res)

    @patch("subprocess.run")
    def test_verifier_preuve_succes_snarkjs(self, mock_subproc):
        mock_subproc.return_value = MagicMock(
            returncode=0,
            stdout="[INFO]  snarkJS: OK!\n",
            stderr="",
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write('{"protocol": "groth16"}')
            temp_vkey = f.name

        try:
            res = verifier_preuve(
                preuve_zkp_json={"pi_a": ["1", "2"], "pi_b": [["3", "4"]], "pi_c": ["5", "6"]},
                public_signals=["12345", "16000000", "1", "2"],
                verification_key_path=temp_vkey,
            )
            self.assertTrue(res)
            self.assertTrue(mock_subproc.called)
        finally:
            if os.path.exists(temp_vkey):
                os.unlink(temp_vkey)

    @patch("subprocess.run")
    def test_verifier_preuve_echec_snarkjs(self, mock_subproc):
        mock_subproc.return_value = MagicMock(
            returncode=1,
            stdout="[ERROR] snarkJS: Invalid proof",
            stderr="",
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write('{"protocol": "groth16"}')
            temp_vkey = f.name

        try:
            res = verifier_preuve(
                preuve_zkp_json='{"pi_a": []}',
                public_signals=["12345", "16000000", "1", "2"],
                verification_key_path=temp_vkey,
            )
            self.assertFalse(res)
        finally:
            if os.path.exists(temp_vkey):
                os.unlink(temp_vkey)


class TestEmpaquetage(unittest.TestCase):
    """Format d'échange {"proof", "publicSignals"} entre noeuds."""

    def test_empaqueter_preuve_depuis_bytes(self):
        octets = empaqueter_preuve(b'{"pi_a": ["1"]}', ["123", 50000])

        self.assertEqual(
            json.loads(octets),
            {"proof": {"pi_a": ["1"]}, "publicSignals": ["123", "50000"]},
        )

    def test_empaqueter_preuve_depuis_str_et_dict(self):
        attendu = {"proof": {"pi_a": ["1"]}, "publicSignals": ["123"]}

        self.assertEqual(json.loads(empaqueter_preuve('{"pi_a": ["1"]}', ["123"])), attendu)

    def test_empaqueter_preuve_refuse_un_json_invalide(self):
        with self.assertRaises(ValueError):
            empaqueter_preuve(b"pas du json", ["123"])
        with self.assertRaises(ValueError):
            empaqueter_preuve(b"\xff\xfe", ["123"])


class TestVerificateurZKP(unittest.TestCase):
    """Vérificateur local branché sur l'EngagementsStore avec contrôles stricts."""

    VALID_NONCE = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
    VAL_INT = int(VALID_NONCE, 16)
    NONCE_HI = str(VAL_INT >> 128)
    NONCE_LO = str(VAL_INT & ((1 << 128) - 1))
    DEFAULT_SEUIL = str(DEFAULT_SEUIL_MAX)
    VALID_COMMITMENT = "12345678901234567890"

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        storage_file = os.path.join(self.tmp_dir.name, "engagements.json")
        self.store = EngagementsStore(persistence_file=storage_file)
        self.verificateur = VerificateurZKP(self.store)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def _preuve(self, signaux):
        return empaqueter_preuve({"pi_a": ["1", "2"], "pi_b": [["3", "4"]], "pi_c": ["5", "6"]}, signaux)

    def _valid_signals(self, commitment=None, seuil=None, hi=None, lo=None):
        return [
            commitment or self.VALID_COMMITMENT,
            seuil or self.DEFAULT_SEUIL,
            hi or self.NONCE_HI,
            lo or self.NONCE_LO,
        ]

    @patch("consensus.validation.verifier_preuve", return_value=True)
    def test_accepte_une_preuve_valide_pour_un_engagement_connu(self, mock_verifier):
        self.store.save("user_123", self.VALID_COMMITMENT)
        signaux = self._valid_signals()

        res = self.verificateur(
            "user_123", self._preuve(signaux), self.VALID_NONCE, "demo"
        )

        self.assertTrue(res)
        mock_verifier.assert_called_once()
        preuve, sig_recus, _ = mock_verifier.call_args.args
        self.assertEqual(sig_recus, signaux)

    @patch("consensus.validation.verifier_preuve", return_value=True)
    def test_refuse_si_l_engagement_public_ne_correspond_pas(self, mock_verifier):
        self.store.save("user_123", self.VALID_COMMITMENT)
        signaux = self._valid_signals(commitment="99999999999999999999")

        res = self.verificateur(
            "user_123", self._preuve(signaux), self.VALID_NONCE, "demo"
        )

        self.assertFalse(res)
        mock_verifier.assert_not_called()

    @patch("consensus.validation.verifier_preuve", return_value=True)
    def test_refuse_utilisateur_inconnu(self, mock_verifier):
        signaux = self._valid_signals()
        res = self.verificateur("user_inconnu", self._preuve(signaux), self.VALID_NONCE, "demo")

        self.assertFalse(res)
        mock_verifier.assert_not_called()

    @patch("consensus.validation.verifier_preuve", return_value=True)
    def test_refuse_signaux_publics_insuffisants(self, mock_verifier):
        self.store.save("user_123", self.VALID_COMMITMENT)
        signaux_incomplets = [self.VALID_COMMITMENT, self.DEFAULT_SEUIL]

        res = self.verificateur(
            "user_123", self._preuve(signaux_incomplets), self.VALID_NONCE, "demo"
        )
        self.assertFalse(res)
        mock_verifier.assert_not_called()

    @patch("consensus.validation.verifier_preuve", return_value=True)
    def test_refuse_signaux_publics_surnumeraires(self, mock_verifier):
        self.store.save("user_123", self.VALID_COMMITMENT)
        signaux_trop = self._valid_signals() + ["extra_signal"]

        res = self.verificateur(
            "user_123", self._preuve(signaux_trop), self.VALID_NONCE, "demo"
        )
        self.assertFalse(res)
        mock_verifier.assert_not_called()

    @patch("consensus.validation.verifier_preuve", return_value=True)
    def test_refuse_seuil_maximal_altere_par_le_client(self, mock_verifier):
        self.store.save("user_123", self.VALID_COMMITMENT)
        signaux = self._valid_signals(seuil="99999999")  # Seuil permissif forgé

        res = self.verificateur(
            "user_123", self._preuve(signaux), self.VALID_NONCE, "demo"
        )
        self.assertFalse(res)
        mock_verifier.assert_not_called()

    @patch("consensus.validation.verifier_preuve", return_value=True)
    def test_refuse_nonce_non_conforme_anti_rejeu(self, mock_verifier):
        self.store.save("user_123", self.VALID_COMMITMENT)
        signaux = self._valid_signals(hi="42")  # Mauvais nonceHi

        res = self.verificateur(
            "user_123", self._preuve(signaux), self.VALID_NONCE, "demo"
        )
        self.assertFalse(res)
        mock_verifier.assert_not_called()

    @patch("consensus.validation.verifier_preuve", return_value=True)
    def test_refuse_signal_public_non_canonique(self, mock_verifier):
        self.store.save("user_123", self.VALID_COMMITMENT)
        # Zéro superflus en tête
        signaux = [self.VALID_COMMITMENT, "016000000", self.NONCE_HI, self.NONCE_LO]

        res = self.verificateur(
            "user_123", self._preuve(signaux), self.VALID_NONCE, "demo"
        )
        self.assertFalse(res)
        mock_verifier.assert_not_called()

    @patch("consensus.validation.verifier_preuve", return_value=True)
    def test_refuse_signal_public_hors_corps_bn254(self, mock_verifier):
        self.store.save("user_123", self.VALID_COMMITMENT)
        # Valeur >= ordre du corps BN254
        signaux = [str(BN254_PRIME + 1), self.DEFAULT_SEUIL, self.NONCE_HI, self.NONCE_LO]

        res = self.verificateur(
            "user_123", self._preuve(signaux), self.VALID_NONCE, "demo"
        )
        self.assertFalse(res)
        mock_verifier.assert_not_called()

    def test_refuse_une_preuve_illisible(self):
        self.assertFalse(self.verificateur("user_123", b"pas du json", self.VALID_NONCE, "demo"))
        self.assertFalse(self.verificateur("user_123", b"\xff\xfe", self.VALID_NONCE, "demo"))
        self.assertFalse(self.verificateur("user_123", None, self.VALID_NONCE, "demo"))

    def test_refuse_des_signaux_publics_mal_formes(self):
        contenu = json.dumps({"proof": {}, "publicSignals": "abc"}).encode()
        self.assertFalse(self.verificateur("user_123", contenu, self.VALID_NONCE, "demo"))

    def test_expose_le_store(self):
        self.assertIs(self.verificateur.store, self.store)


if __name__ == "__main__":
    unittest.main()
