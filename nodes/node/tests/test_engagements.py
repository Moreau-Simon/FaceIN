"""
Tests unitaires pour le magasin d'engagements cryptographiques (EngagementsStore).

Couvre (PROMPT 4) :
- Persistance atomique sur disque
- Format enrichi (statut, updated_at, version)
- Révocation et idempotence
- sync_batch idempotent
- Rétrocompatibilité ancien format chaîne
- Thread-safety
"""

import json
import os
import sys
import tempfile
import threading
import time
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from store.engagements import EngagementsStore


class TestEngagementsStore(unittest.TestCase):
    """Vérifie le bon fonctionnement du magasin d'engagements."""

    def setUp(self):
        # Chaque test utilise un fichier temporaire isolé (pas /app/data inaccessible)
        self._tmp = tempfile.NamedTemporaryFile(
            suffix=".json", delete=False, mode="w", encoding="utf-8"
        )
        self._tmp.close()
        os.unlink(self._tmp.name)  # On supprime le fichier vide : le store le créera
        self.store = EngagementsStore(persistence_file=self._tmp.name)

    def tearDown(self):
        if os.path.exists(self._tmp.name):
            os.unlink(self._tmp.name)

    # ------------------------------------------------------------------
    # 1. Initialisation vide
    # ------------------------------------------------------------------
    def test_initialisation_vide(self):
        self.assertEqual(self.store.count(), 0)
        self.assertEqual(self.store.all(), {})
        self.assertFalse(self.store.exists("alice"))
        self.assertIsNone(self.store.get("alice"))

    # ------------------------------------------------------------------
    # 2. Sauvegarde et récupération d'un engagement actif
    # ------------------------------------------------------------------
    def test_sauvegarde_et_recuperation(self):
        engagement = "0x123456789abcdef"
        self.store.save("alice", engagement)

        self.assertEqual(self.store.count(), 1)
        self.assertTrue(self.store.exists("alice"))
        self.assertEqual(self.store.get("alice"), engagement)
        self.assertFalse(self.store.exists("bob"))
        self.assertIsNone(self.store.get("bob"))

    # ------------------------------------------------------------------
    # 3. Mise à jour — idempotence temporelle
    # ------------------------------------------------------------------
    def test_mise_a_jour_plus_recente_ecrase(self):
        t0 = time.time() - 10
        t1 = time.time()
        self.store.save("alice", "engagement_v1", timestamp=t0)
        self.store.save("alice", "engagement_v2", timestamp=t1)
        self.assertEqual(self.store.get("alice"), "engagement_v2")
        self.assertEqual(self.store.count(), 1)

    def test_mise_a_jour_plus_ancienne_ignoree(self):
        t0 = time.time()
        t_vieux = t0 - 100
        self.store.save("alice", "engagement_recent", timestamp=t0)
        self.store.save("alice", "engagement_vieux", timestamp=t_vieux)
        # La version récente doit être conservée
        self.assertEqual(self.store.get("alice"), "engagement_recent")

    # ------------------------------------------------------------------
    # 4. Révocation
    # ------------------------------------------------------------------
    def test_revocation(self):
        self.store.save("alice", "0xabc")
        result = self.store.revoke("alice", raison="fraude détectée")
        self.assertTrue(result)
        # Après révocation : get() et exists() retournent None / False
        self.assertIsNone(self.store.get("alice"))
        self.assertFalse(self.store.exists("alice"))
        # count() n'inclut pas les révoqués
        self.assertEqual(self.store.count(), 0)

    def test_revocation_utilisateur_inexistant(self):
        # Ne doit pas lever d'exception
        result = self.store.revoke("inconnu", raison="test")
        self.assertFalse(result)

    def test_revocation_idempotente(self):
        self.store.save("bob", "0xdef")
        self.assertTrue(self.store.revoke("bob"))
        # Deuxième appel : idempotent, retourne True
        self.assertTrue(self.store.revoke("bob"))

    # ------------------------------------------------------------------
    # 5. all() ne retourne que les actifs
    # ------------------------------------------------------------------
    def test_all_ne_retourne_que_actifs(self):
        self.store.save("alice", "hash_alice")
        self.store.save("bob", "hash_bob")
        self.store.revoke("bob")

        tous = self.store.all()
        self.assertIn("alice", tous)
        self.assertNotIn("bob", tous)
        self.assertEqual(len(tous), 1)

    # ------------------------------------------------------------------
    # 6. count() ne compte que les actifs
    # ------------------------------------------------------------------
    def test_count_actifs_seulement(self):
        self.store.save("alice", "hash_alice")
        self.store.save("bob", "hash_bob")
        self.store.save("charlie", "hash_charlie")
        self.store.revoke("alice")
        self.assertEqual(self.store.count(), 2)

    # ------------------------------------------------------------------
    # 7. all_entries() retourne actifs ET révoqués
    # ------------------------------------------------------------------
    def test_all_entries_inclut_revoques(self):
        self.store.save("alice", "hash_alice")
        self.store.save("bob", "hash_bob")
        self.store.revoke("alice")

        entries = self.store.all_entries()
        self.assertIn("alice", entries)
        self.assertIn("bob", entries)
        self.assertEqual(entries["alice"]["statut"], "revoque")
        self.assertEqual(entries["bob"]["statut"], "actif")

    # ------------------------------------------------------------------
    # 8. sync_batch — idempotent (doublon ignoré)
    # ------------------------------------------------------------------
    def test_sync_batch_idempotent(self):
        ts = time.time()
        entry = {"utilisateur_id": "alice", "commitment": "0xabc", "updated_at": ts, "version": 1, "statut": "actif"}
        nb = self.store.sync_batch([entry, entry])
        # Le deuxième est ignoré (même timestamp)
        self.assertEqual(nb, 1)
        self.assertEqual(self.store.count(), 1)

    # ------------------------------------------------------------------
    # 9. sync_batch — mise à jour si plus récent
    # ------------------------------------------------------------------
    def test_sync_batch_met_a_jour_si_plus_recent(self):
        t0 = time.time() - 5
        t1 = time.time()
        self.store.sync_batch([{"utilisateur_id": "alice", "commitment": "v1", "updated_at": t0, "version": 1, "statut": "actif"}])
        nb = self.store.sync_batch([{"utilisateur_id": "alice", "commitment": "v2", "updated_at": t1, "version": 2, "statut": "actif"}])
        self.assertEqual(nb, 1)
        self.assertEqual(self.store.get("alice"), "v2")

    # ------------------------------------------------------------------
    # 10. Persistance atomique — rechargement depuis fichier
    # ------------------------------------------------------------------
    def test_persistance_atomique(self):
        self.store.save("alice", "0xabc")
        self.store.save("bob", "0xdef")
        self.store.revoke("bob")

        # Vérifier que le fichier a bien été créé
        self.assertTrue(os.path.exists(self._tmp.name))

        # Recharger depuis le fichier dans un nouveau store
        store2 = EngagementsStore(persistence_file=self._tmp.name)
        self.assertEqual(store2.get("alice"), "0xabc")
        self.assertIsNone(store2.get("bob"))  # révoqué → non retourné
        self.assertEqual(store2.count(), 1)

    # ------------------------------------------------------------------
    # 11. Rétrocompatibilité — ancien format chaîne JSON
    # ------------------------------------------------------------------
    def test_retro_compatibilite_format_chaine(self):
        # Simuler un fichier JSON au format v1 (clé → chaîne)
        old_data = {"alice": "0xancien_commitment", "bob": "0xbob_commitment"}
        with open(self._tmp.name, "w", encoding="utf-8") as f:
            json.dump(old_data, f)

        store = EngagementsStore(persistence_file=self._tmp.name)
        self.assertEqual(store.get("alice"), "0xancien_commitment")
        self.assertEqual(store.get("bob"), "0xbob_commitment")
        self.assertEqual(store.count(), 2)
        self.assertTrue(store.exists("alice"))

    # ------------------------------------------------------------------
    # 12. Thread-safety (concurrence)
    # ------------------------------------------------------------------
    def test_concurrence_thread_safe(self):
        def travailleur(debut, fin):
            for i in range(debut, fin):
                self.store.save(f"user_{i}", f"hash_{i}")
                _ = self.store.get(f"user_{i}")
                _ = self.store.exists(f"user_{i}")

        threads = []
        for t in range(5):
            th = threading.Thread(target=travailleur, args=(t * 20, (t + 1) * 20))
            threads.append(th)
            th.start()

        for th in threads:
            th.join()

        self.assertEqual(self.store.count(), 100)


if __name__ == "__main__":
    unittest.main()
