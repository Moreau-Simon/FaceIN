"""
Tests unitaires pour le magasin d'engagements cryptographiques (EngagementsStore).
"""

import os
import sys
import threading
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from store.engagements import EngagementsStore


class TestEngagementsStore(unittest.TestCase):
    """Vérifie le bon fonctionnement du magasin d'engagements en mémoire."""

    def setUp(self):
        self.store = EngagementsStore()

    def test_initialisation_vide(self):
        self.assertEqual(self.store.count(), 0)
        self.assertEqual(self.store.all(), {})
        self.assertFalse(self.store.exists("alice"))
        self.assertIsNone(self.store.get("alice"))

    def test_sauvegarde_et_recuperation(self):
        engagement_poseidon = "0x123456789abcdef"
        self.store.save("alice", engagement_poseidon)

        self.assertEqual(self.store.count(), 1)
        self.assertTrue(self.store.exists("alice"))
        self.assertEqual(self.store.get("alice"), engagement_poseidon)
        self.assertFalse(self.store.exists("bob"))
        self.assertIsNone(self.store.get("bob"))

    def test_mise_a_jour_engagement(self):
        self.store.save("alice", "engagement_v1")
        self.assertEqual(self.store.get("alice"), "engagement_v1")

        self.store.save("alice", "engagement_v2")
        self.assertEqual(self.store.get("alice"), "engagement_v2")
        self.assertEqual(self.store.count(), 1)

    def test_all_retourne_copie(self):
        self.store.save("alice", "hash_alice")
        self.store.save("bob", "hash_bob")

        tous = self.store.all()
        self.assertEqual(len(tous), 2)
        self.assertEqual(tous["alice"], "hash_alice")
        self.assertEqual(tous["bob"], "hash_bob")

        # Vérifier que modifier la copie ne modifie pas le store interne
        tous["charlie"] = "hash_charlie"
        self.assertFalse(self.store.exists("charlie"))
        self.assertEqual(self.store.count(), 2)

    def test_concurrence_thread_safe(self):
        def travailleur(debut, fin):
            for i in range(debut, fin):
                self.store.save(f"user_{i}", f"hash_{i}")
                _ = self.store.get(f"user_{i}")
                _ = self.store.exists(f"user_{i}")

        threads = []
        for t in range(5):
            th = threading.Thread(target=travailleur, args=(t * 50, (t + 1) * 50))
            threads.append(th)
            th.start()

        for th in threads:
            th.join()

        self.assertEqual(self.store.count(), 250)


if __name__ == "__main__":
    unittest.main()
