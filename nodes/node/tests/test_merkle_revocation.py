"""
Tests unitaires et d'intégration pour l'arbre de Merkle, la synchronisation
ciblée entre nœuds et la révocation persistante anti-résurrection.
"""

import os
import sys
import tempfile
import time
import unittest
from types import SimpleNamespace

NODE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if NODE_DIR not in sys.path:
    sys.path.insert(0, NODE_DIR)

from merkle.sync import synchroniser_avec_pair
from merkle.tree import EMPTY_ROOT_HASH, MerkleTree
from network.server import RevocationService, SyncService
from store.engagements import EngagementsStore


class TestMerkleTreeAndSync(unittest.TestCase):
    """Couvre la construction Merkle, la divergence ciblée et le rattrapage."""

    def setUp(self):
        self.tmp_files = []

    def tearDown(self):
        for path in self.tmp_files:
            if os.path.exists(path):
                try:
                    os.unlink(path)
                except OSError:
                    pass

    def _new_store(self) -> EngagementsStore:
        fd, path = tempfile.mkstemp(prefix="merkle_store_", suffix=".json")
        os.close(fd)
        os.unlink(path)
        self.tmp_files.append(path)
        return EngagementsStore(persistence_file=path)

    def test_construction_arbre_vide_et_peuple(self):
        arbre_vide = MerkleTree({})
        self.assertEqual(arbre_vide.root_hash, EMPTY_ROOT_HASH)
        self.assertEqual(arbre_vide.nb_feuilles, 0)

        entries = {
            "alice": {"commitment": "111", "statut": "actif", "version": 1, "updated_at": 100.0},
            "bob": {"commitment": "222", "statut": "actif", "version": 1, "updated_at": 101.0},
        }
        arbre = MerkleTree(entries)
        self.assertNotEqual(arbre.root_hash, EMPTY_ROOT_HASH)
        self.assertEqual(arbre.nb_feuilles, 2)
        self.assertEqual([f.utilisateur_id for f in arbre.all_leaves()], ["alice", "bob"])

    def test_racine_identique_sur_trois_noeuds(self):
        stores = [self._new_store() for _ in range(3)]
        # Insertion dans des ordres différents sur les 3 nœuds
        for uid, comm, ts in [("alice", "1001", 10.0), ("bob", "1002", 20.0), ("charlie", "1003", 30.0)]:
            stores[0].save(uid, comm, timestamp=ts, version=1)
        for uid, comm, ts in [("charlie", "1003", 30.0), ("alice", "1001", 10.0), ("bob", "1002", 20.0)]:
            stores[1].save(uid, comm, timestamp=ts, version=1)
        for uid, comm, ts in [("bob", "1002", 20.0), ("charlie", "1003", 30.0), ("alice", "1001", 10.0)]:
            stores[2].save(uid, comm, timestamp=ts, version=1)

        racines = [MerkleTree(s.all_entries()).root_hash for s in stores]
        self.assertEqual(racines[0], racines[1])
        self.assertEqual(racines[1], racines[2])

    def test_une_feuille_modifiee_change_la_racine(self):
        s1 = self._new_store()
        s2 = self._new_store()
        for uid, comm in [("alice", "111"), ("bob", "222"), ("charlie", "333"), ("david", "444")]:
            s1.save(uid, comm, timestamp=100.0, version=1)
            s2.save(uid, comm, timestamp=100.0, version=1)

        s2.save("david", "999", timestamp=200.0, version=2)
        r1 = MerkleTree(s1.all_entries()).root_hash
        r2 = MerkleTree(s2.all_entries()).root_hash
        self.assertFalse(MerkleTree.racines_identiques(r1, r2))

    def test_detection_branche_divergente_et_sync_partielle(self):
        local_store = self._new_store()
        remote_store = self._new_store()

        # 4 utilisateurs : alice, bob (branche gauche "0") et charlie, david (branche droite "1")
        for uid, comm in [("alice", "111"), ("bob", "222"), ("charlie", "333"), ("david", "444")]:
            local_store.save(uid, comm, timestamp=100.0, version=1)
            remote_store.save(uid, comm, timestamp=100.0, version=1)

        # Modification uniquement sur "david" (branche droite "1")
        remote_store.save("david", "9999", timestamp=200.0, version=2)

        remote_sync = SyncService("node-b", store=remote_store)
        chemins_appeles = []

        def fake_echanger_racine(host, port, nid, timeout):
            rep = remote_sync.EchangerRacine(SimpleNamespace(noeud_id=nid), None)
            return rep.racine_hash, rep.derniere_maj

        def fake_recuperer_branche(host, port, chemin, timeout):
            chemins_appeles.append(chemin)
            rep = remote_sync.RecupererBranche(SimpleNamespace(chemin_branche=chemin), None)
            return rep.noeuds

        bilan = synchroniser_avec_pair(
            "node-a", "node-b", 50052, local_store,
            echanger_racine_fn=fake_echanger_racine,
            recuperer_branche_fn=fake_recuperer_branche,
        )

        self.assertEqual(bilan["statut"], "synchronise")
        self.assertEqual(bilan["nb_sync"], 1)
        self.assertEqual(local_store.get("david"), "9999")
        # La branche gauche "0" (alice/bob) étant identique, on ne doit pas y descendre
        self.assertIn("", chemins_appeles)
        self.assertIn("1", chemins_appeles)
        self.assertNotIn("0", chemins_appeles)

    def test_synchronisation_complete_noeud_vide(self):
        local_store = self._new_store()  # Vide
        remote_store = self._new_store()
        for uid, comm in [("alice", "111"), ("bob", "222"), ("charlie", "333")]:
            remote_store.save(uid, comm, timestamp=100.0, version=1)

        remote_sync = SyncService("node-b", store=remote_store)
        bilan = synchroniser_avec_pair(
            "node-a", "node-b", 50052, local_store,
            echanger_racine_fn=lambda h, p, n, t: (
                remote_sync.EchangerRacine(SimpleNamespace(noeud_id=n), None).racine_hash, 0
            ),
            recuperer_branche_fn=lambda h, p, c, t: (
                remote_sync.RecupererBranche(SimpleNamespace(chemin_branche=c), None).noeuds
            ),
        )

        self.assertEqual(bilan["statut"], "synchronise")
        self.assertEqual(bilan["nb_sync"], 3)
        self.assertEqual(
            MerkleTree(local_store.all_entries()).root_hash,
            MerkleTree(remote_store.all_entries()).root_hash,
        )

    def test_noeud_absent_puis_reconnecte(self):
        local_store = self._new_store()
        remote_store = self._new_store()
        remote_store.save("alice", "111", timestamp=100.0, version=1)

        # 1. Pair indisponible -> erreur gérée sans exception fatale
        def unreachable(h, p, n, t):
            raise ConnectionError("Pair hors ligne")

        bilan_ko = synchroniser_avec_pair(
            "node-a", "node-b", 50052, local_store,
            echanger_racine_fn=unreachable,
        )
        self.assertEqual(bilan_ko["statut"], "erreur")
        self.assertIsNone(local_store.get("alice"))

        # 2. Pair reconnecté -> rattrapage automatique
        remote_sync = SyncService("node-b", store=remote_store)
        bilan_ok = synchroniser_avec_pair(
            "node-a", "node-b", 50052, local_store,
            echanger_racine_fn=lambda h, p, n, t: (
                remote_sync.EchangerRacine(SimpleNamespace(noeud_id=n), None).racine_hash, 0
            ),
            recuperer_branche_fn=lambda h, p, c, t: (
                remote_sync.RecupererBranche(SimpleNamespace(chemin_branche=c), None).noeuds
            ),
        )
        self.assertEqual(bilan_ok["statut"], "synchronise")
        self.assertEqual(local_store.get("alice"), "111")


class TestRevocationServiceAndPersistence(unittest.TestCase):
    """Couvre la révocation normale, idempotente, anti-résurrection et persistance."""

    def setUp(self):
        self.tmp_files = []

    def tearDown(self):
        for path in self.tmp_files:
            if os.path.exists(path):
                try:
                    os.unlink(path)
                except OSError:
                    pass

    def _new_store_with_path(self):
        fd, path = tempfile.mkstemp(prefix="revocation_store_", suffix=".json")
        os.close(fd)
        os.unlink(path)
        self.tmp_files.append(path)
        return EngagementsStore(persistence_file=path), path

    def test_revocation_normale_et_repetee_idempotente(self):
        store, _ = self._new_store_with_path()
        store.save("alice", "12345", timestamp=100.0, version=1)
        self.assertEqual(store.get("alice"), "12345")

        self.assertTrue(store.revoke("alice", raison="perte appareil", timestamp=200.0))
        self.assertIsNone(store.get("alice"))

        # Révocation répétée : idempotente, ne réactive rien et ne plante pas
        self.assertTrue(store.revoke("alice", raison="perte appareil", timestamp=200.0))
        self.assertIsNone(store.get("alice"))

    def test_revocation_recue_en_double_via_grpc(self):
        store, _ = self._new_store_with_path()
        store.save("bob", "67890", timestamp=100.0, version=1)
        svc = RevocationService("node-b", store=store)

        req = SimpleNamespace(
            utilisateur_id="bob",
            engagement_id="67890",
            raison="compromission",
            timestamp_revocation=200000,
            noeud_origine="node-a",
        )
        ack1 = svc.PropagerRevocation(req, None)
        ack2 = svc.PropagerRevocation(req, None)

        self.assertTrue(ack1.recu)
        self.assertTrue(ack2.recu)
        self.assertEqual(ack1.noeud_id, "node-b")
        self.assertIsNone(store.get("bob"))

        fraicheur = svc.VerifierFraicheur(SimpleNamespace(noeud_id="node-a"), None)
        self.assertTrue(fraicheur.a_jour)
        self.assertGreater(fraicheur.derniere_revocation_connue, 0)

    def test_engagement_revoque_ne_reapparait_pas_avec_ancienne_copie(self):
        store, _ = self._new_store_with_path()
        store.save("charlie", "99999", timestamp=100.0, version=1)
        store.revoke("charlie", raison="revoque", timestamp=150.0)
        self.assertIsNone(store.get("charlie"))

        # Tentative de réinjection d'une ancienne copie active (même avec timestamp plus élevé)
        nb = store.sync_batch([
            {
                "utilisateur_id": "charlie",
                "commitment": "99999",
                "statut": "actif",
                "updated_at": 9999.0,
                "version": 1,
            }
        ])
        self.assertEqual(nb, 0)
        self.assertIsNone(store.get("charlie"))

    def test_redemarrage_apres_revocation_conserve_etat(self):
        store1, path = self._new_store_with_path()
        store1.save("alice", "11111", timestamp=100.0, version=1)
        store1.save("bob", "22222", timestamp=100.0, version=1)
        store1.revoke("alice", raison="demande utilisateur", timestamp=200.0)

        # Redémarrage simulé : nouvelle instance lisant le même fichier
        store2 = EngagementsStore(persistence_file=path)
        self.assertIsNone(store2.get("alice"))
        self.assertEqual(store2.get("bob"), "22222")
        self.assertEqual(store2.all_entries()["alice"]["statut"], "revoque")


if __name__ == "__main__":
    unittest.main()
