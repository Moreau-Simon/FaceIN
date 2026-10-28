"""
Tests unitaires pour la validation des preuves ZKP (consensus/validation.py).
"""

import json
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from consensus.validation import (
    VerificateurZKP,
    empaqueter_preuve,
    valider_avec_mock,
    verifier_preuve,
)
from store.engagements import EngagementsStore


class TestValidationZKP(unittest.TestCase):
    """Vérifie le comportement de la validation de preuve ZKP."""

    def test_valider_avec_mock_accepte_une_preuve_non_vide(self):
        self.assertTrue(valider_avec_mock("user-1", b"preuve", "nonce", "service"))
        self.assertFalse(valider_avec_mock("user-1", b"", "nonce", "service"))

    def test_verifier_preuve_fichier_cle_manquant(self):
        # Chemin inexistant
        res = verifier_preuve(
            preuve_zkp_json='{"pi_a": []}',
            public_signals=["0x123", "100000"],
            verification_key_path="/fichier/inexistant/verification_key.json",
        )
        self.assertFalse(res)

    @patch("subprocess.run")
    def test_verifier_preuve_succes_snarkjs(self, mock_subproc):
        # Simule un retour positif de snarkjs
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
                public_signals=["0x12345", "50000"],
                verification_key_path=temp_vkey,
            )
            self.assertTrue(res)
            self.assertTrue(mock_subproc.called)
        finally:
            if os.path.exists(temp_vkey):
                os.unlink(temp_vkey)

    @patch("subprocess.run")
    def test_verifier_preuve_echec_snarkjs(self, mock_subproc):
        # Simule un retour d'erreur de snarkjs
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
                public_signals=["0x12345", "50000"],
                verification_key_path=temp_vkey,
            )
            self.assertFalse(res)
        finally:
            if os.path.exists(temp_vkey):
                os.unlink(temp_vkey)


class TestEmpaquetage(unittest.TestCase):
    """Format d'échange {"proof", "publicSignals"} entre noeuds."""

    def test_empaqueter_preuve_depuis_bytes(self):
        octets = empaqueter_preuve(b'{"pi_a": ["1"]}', ["0xabc", 50000])

        self.assertEqual(
            json.loads(octets),
            {"proof": {"pi_a": ["1"]}, "publicSignals": ["0xabc", "50000"]},
        )

    def test_empaqueter_preuve_depuis_str_et_dict(self):
        attendu = {"proof": {"pi_a": ["1"]}, "publicSignals": ["0xabc"]}

        self.assertEqual(json.loads(empaqueter_preuve('{"pi_a": ["1"]}', ["0xabc"])), attendu)
        self.assertEqual(json.loads(empaqueter_preuve({"pi_a": ["1"]}, ["0xabc"])), attendu)

    def test_empaqueter_preuve_refuse_un_json_invalide(self):
        with self.assertRaises(ValueError):
            empaqueter_preuve(b"pas du json", ["0xabc"])
        with self.assertRaises(ValueError):
            empaqueter_preuve(b"\xff\xfe", ["0xabc"])


class TestVerificateurZKP(unittest.TestCase):
    """Vérificateur local branché sur l'EngagementsStore."""

    def setUp(self):
        self.store = EngagementsStore()
        self.verificateur = VerificateurZKP(self.store)

    @staticmethod
    def _preuve(signaux):
        return empaqueter_preuve({"pi_a": ["1"]}, signaux)

    @patch("consensus.validation.verifier_preuve", return_value=True)
    def test_accepte_une_preuve_valide_pour_un_engagement_connu(self, mock_verifier):
        self.store.save("user_123", "engagement_ok")

        res = self.verificateur(
            "user_123", self._preuve(["engagement_ok", "50000"]), "nonce", "demo"
        )

        self.assertTrue(res)
        preuve, signaux, _ = mock_verifier.call_args.args
        self.assertEqual(preuve, {"pi_a": ["1"]})
        self.assertEqual(signaux, ["engagement_ok", "50000"])

    @patch("consensus.validation.verifier_preuve", return_value=True)
    def test_refuse_si_l_engagement_public_ne_correspond_pas(self, mock_verifier):
        self.store.save("user_123", "engagement_stocke")

        res = self.verificateur(
            "user_123", self._preuve(["mauvais_engagement", "1000"]), "nonce", "demo"
        )

        self.assertFalse(res)
        mock_verifier.assert_not_called()

    @patch("consensus.validation.verifier_preuve", return_value=True)
    def test_refuse_un_utilisateur_inconnu_sans_signaux_publics(self, mock_verifier):
        res = self.verificateur("user_inconnu", b'{"pi_a": []}', "nonce", "demo")

        self.assertFalse(res)
        mock_verifier.assert_not_called()

    @patch("consensus.validation.verifier_preuve", return_value=True)
    def test_preuve_seule_utilise_l_engagement_enregistre(self, mock_verifier):
        self.store.save("user_123", "engagement_ok")

        res = self.verificateur("user_123", b'{"pi_a": []}', "nonce", "demo")

        self.assertTrue(res)
        self.assertEqual(mock_verifier.call_args.args[1], ["engagement_ok"])

    @patch("consensus.validation.verifier_preuve", return_value=True)
    def test_synchronise_l_engagement_apres_une_preuve_valide(self, mock_verifier):
        res = self.verificateur(
            "user_nouveau", self._preuve(["engagement_nouveau", "50000"]), "nonce", "demo"
        )

        self.assertTrue(res)
        self.assertEqual(self.store.get("user_nouveau"), "engagement_nouveau")

    @patch("consensus.validation.verifier_preuve", return_value=False)
    def test_ne_memorise_pas_l_engagement_d_une_preuve_invalide(self, mock_verifier):
        res = self.verificateur(
            "user_nouveau", self._preuve(["engagement_nouveau", "50000"]), "nonce", "demo"
        )

        self.assertFalse(res)
        self.assertIsNone(self.store.get("user_nouveau"))

    def test_refuse_une_preuve_illisible(self):
        self.assertFalse(self.verificateur("user_123", b"pas du json", "nonce", "demo"))
        self.assertFalse(self.verificateur("user_123", b"\xff\xfe", "nonce", "demo"))
        self.assertFalse(self.verificateur("user_123", None, "nonce", "demo"))

    def test_refuse_des_signaux_publics_mal_formes(self):
        contenu = json.dumps({"proof": {}, "publicSignals": "abc"}).encode()

        self.assertFalse(self.verificateur("user_123", contenu, "nonce", "demo"))

    def test_expose_le_store(self):
        self.assertIs(self.verificateur.store, self.store)


if __name__ == "__main__":
    unittest.main()
