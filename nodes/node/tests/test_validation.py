"""
Tests unitaires pour la validation des preuves ZKP (consensus/validation.py).
"""

import json
import os
import sys
import tempfile
import unittest
import warnings
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from consensus.validation import valider_avec_mock, verifier_preuve


class TestValidationZKP(unittest.TestCase):
    """Vérifie le comportement de la validation de preuve ZKP."""

    def test_valider_avec_mock_emits_deprecation(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            res_true = valider_avec_mock("preuve_valide")
            res_false = valider_avec_mock("")

            self.assertTrue(res_true)
            self.assertFalse(res_false)
            self.assertTrue(any(issubclass(item.category, DeprecationWarning) for item in w))

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


if __name__ == "__main__":
    unittest.main()
