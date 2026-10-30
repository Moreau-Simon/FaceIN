"""Tests du store. Backend mémoire : aucune base PostgreSQL nécessaire (CI incluse).

Pour tester contre un vrai PostgreSQL (docker compose up db) :
    STORE_BACKEND=postgres DATABASE_URL=postgresql://... pytest api/tests/test_store.py
"""
import os
import unittest

os.environ.setdefault("STORE_BACKEND", "memory")

from api.services import store as store_module  # noqa: E402


class TestStore(unittest.TestCase):
    def setUp(self):
        store_module.reset_store()
        self.store = store_module.get_store()

    def tearDown(self):
        store_module.reset_store()

    # --- engagements ---
    def test_save_et_get_engagement(self):
        self.store.save_engagement("alice", "0xabc")
        e = self.store.get_engagement("alice")
        self.assertEqual(e["commitment"], "0xabc")
        self.assertEqual(e["user_id"], "alice")

    def test_engagement_inconnu(self):
        self.assertIsNone(self.store.get_engagement("personne"))

    def test_un_seul_engagement_actif(self):
        self.store.save_engagement("alice", "v1")
        self.store.save_engagement("alice", "v2")
        self.assertEqual(self.store.get_engagement("alice")["commitment"], "v2")

    def test_revocation(self):
        self.store.save_engagement("alice", "v1")
        self.assertTrue(self.store.revoke_engagement("alice", "perte appareil"))
        self.assertIsNone(self.store.get_engagement("alice"))
        self.assertFalse(self.store.revoke_engagement("alice"))

    # --- nonces ---
    def test_nonce_usage_unique(self):
        self.store.save_nonce("n1", "alice", 2000.0)
        self.assertTrue(self.store.consume_nonce("n1", "alice", now=1000.0))
        self.assertFalse(self.store.consume_nonce("n1", "alice", now=1000.0))  # rejeu refusé

    def test_nonce_expire(self):
        self.store.save_nonce("n2", "alice", 1000.0)
        self.assertFalse(self.store.consume_nonce("n2", "alice", now=1500.0))

    def test_nonce_autre_utilisateur(self):
        self.store.save_nonce("n3", "alice", 2000.0)
        self.assertFalse(self.store.consume_nonce("n3", "bob", now=1000.0))
        # le nonce de alice reste utilisable par alice
        self.assertTrue(self.store.consume_nonce("n3", "alice", now=1000.0))

    def test_nonce_inconnu(self):
        self.assertFalse(self.store.consume_nonce("zzz", now=1000.0))

    def test_purge(self):
        self.store.save_nonce("vieux", "alice", 100.0)
        self.store.save_nonce("frais", "alice", 5000.0)
        self.assertEqual(self.store.purge_expired_nonces(now=1000.0), 1)
        self.assertTrue(self.store.consume_nonce("frais", now=1000.0))

    def test_backend_inconnu_refuse(self):
        store_module.reset_store()
        old = os.environ["STORE_BACKEND"]
        os.environ["STORE_BACKEND"] = "sqlite"
        try:
            with self.assertRaises(ValueError):
                store_module.get_store()
        finally:
            os.environ["STORE_BACKEND"] = old


if __name__ == "__main__":
    unittest.main()
