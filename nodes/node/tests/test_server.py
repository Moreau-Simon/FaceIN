"""
Tests unitaires pour VerificationServiceImpl (network/server.py).
"""

import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from network.server import VerificationServiceImpl
from store.engagements import EngagementsStore


class TestVerificationService(unittest.TestCase):
    """Vérifie le bon fonctionnement du service de vérification du noeud."""

    def setUp(self):
        self.store = EngagementsStore()
        self.service = VerificationServiceImpl(node_id="node-test", store=self.store)

    def test_recuperer_donnee_aide_trouve(self):
        self.store.save("user_123", "poseidon_hash_abc")

        request = SimpleNamespace(utilisateur_id="user_123")
        response = self.service.RecupererDonneeAide(request, None)

        self.assertTrue(response.trouve)
        self.assertEqual(response.donnee_aide, "poseidon_hash_abc")

    def test_recuperer_donnee_aide_non_trouve(self):
        request = SimpleNamespace(utilisateur_id="user_inconnu")
        response = self.service.RecupererDonneeAide(request, None)

        self.assertFalse(response.trouve)
        self.assertEqual(response.donnee_aide, "")

    def test_demander_nonce(self):
        request = SimpleNamespace(utilisateur_id="user_123")
        response = self.service.DemanderNonce(request, None)

        self.assertTrue(len(response.nonce) > 10)
        self.assertTrue(response.expiration_timestamp > 0)

    def test_verifier_preuve_utilisateur_inconnu(self):
        request = SimpleNamespace(
            utilisateur_id="user_inconnu",
            preuve_zkp="{}",
            nonce="nonce_test",
            service_cible="demo",
            public_signals=[],
        )
        response = self.service.VerifierPreuve(request, None)

        self.assertFalse(response.accepte)
        self.assertIn("introuvable", response.raison_refus)

    def test_verifier_preuve_incoherence_engagement(self):
        self.store.save("user_123", "engagement_stocke")

        request = SimpleNamespace(
            utilisateur_id="user_123",
            preuve_zkp="{}",
            nonce="nonce_test",
            service_cible="demo",
            public_signals=["mauvais_engagement", "1000"],
        )
        response = self.service.VerifierPreuve(request, None)

        self.assertFalse(response.accepte)
        self.assertIn("ne correspond pas", response.raison_refus)

    @patch("consensus.validation.verifier_preuve")
    def test_verifier_preuve_succes(self, mock_verifier):
        mock_verifier.return_value = True
        self.store.save("user_123", "engagement_ok")

        request = SimpleNamespace(
            utilisateur_id="user_123",
            preuve_zkp='{"pi_a": []}',
            nonce="nonce_test",
            service_cible="demo",
            public_signals=["engagement_ok", "50000"],
        )
        response = self.service.VerifierPreuve(request, None)

        self.assertTrue(response.accepte)
        self.assertEqual(response.raison_refus, "")
        self.assertTrue(len(response.token) > 0)


if __name__ == "__main__":
    unittest.main()
