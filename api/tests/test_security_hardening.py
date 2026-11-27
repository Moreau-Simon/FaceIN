"""
Tests de durcissement sécurité (anti-mock en production) et tests de concurrence
(inscriptions simultanées, consommation atomique de nonces, votes et sync Merkle).
"""

from concurrent.futures import ThreadPoolExecutor
import os
import sys
import tempfile
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("STORE_BACKEND", "memory")

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
API_DIR = os.path.dirname(CURRENT_DIR)
ROOT_DIR = os.path.dirname(API_DIR)
NODES_DIR = os.path.join(ROOT_DIR, "nodes", "node")

for p in (API_DIR, NODES_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from models import RegisterRequest  # noqa: E402
from services import grpc_bridge, jwt_manager, store, zkp_verifier  # noqa: E402
from verification.nonces import NonceStore  # noqa: E402
from network.server import ConsensusService  # noqa: E402
from store.engagements import EngagementsStore  # noqa: E402
from merkle.tree import MerkleTree  # noqa: E402


import consensus.validation as node_validation  # noqa: E402

PREUVE_SYNTAXIQUE = {"pi_a": ["1", "2"], "pi_b": [["1", "2"], ["3", "4"]], "pi_c": ["1", "2"]}
SIGNAUX_SYNTAXIQUES = ["123", "16000000", "1", "2"]


class TestProductionAntiMockGuards(unittest.TestCase):
    """Garantit qu'aucun mode mock ne peut être activé accidentellement en production."""

    def test_consensus_jamais_simule_meme_avec_anciennes_variables(self):
        """Sans réseau, le consensus est refusé et aucun vote n'est fabriqué,
        même si ALLOW_MOCK_CONSENSUS et MOCK_ZKP_VERIFICATION valent true."""
        env = {
            "STORE_BACKEND": "memory",
            "ALLOW_MOCK_CONSENSUS": "true",
            "MOCK_ZKP_VERIFICATION": "true",
        }
        with patch.dict(os.environ, env, clear=True):
            with patch.object(grpc_bridge, "grpc", None):
                res = grpc_bridge.verify_on_nodes(
                    user_id="alice",
                    proof_json_str="{}",
                    nonce="a" * 64,
                )
        self.assertFalse(res["consensus"])
        self.assertIn("injoignables", res["reason"].lower())
        self.assertEqual(res["votes"], {})
        self.assertEqual(res["nb_votes_pour"], 0)
        self.assertIsNone(res["token"])

    def test_grpc_bridge_ne_contient_aucun_chemin_de_simulation(self):
        """Le pont gRPC ne doit plus contenir de votes ou de jetons simulés."""
        source_path = os.path.join(API_DIR, "services", "grpc_bridge.py")
        with open(source_path, "r", encoding="utf-8") as f:
            source = f.read()
        self.assertNotIn("token-simule", source)
        self.assertNotIn("ALLOW_MOCK_CONSENSUS", source)
        self.assertNotIn("MOCK_ZKP_VERIFICATION", source)

    def test_api_refuse_demarrage_mock_en_production(self):
        with patch.dict(os.environ, {"FACEIN_ENV": "production", "MOCK_ZKP_VERIFICATION": "true"}):
            with self.assertRaises(RuntimeError):
                zkp_verifier.verifier_absence_mock_en_production()

    def test_api_demarrage_autorise_sans_mock_en_production(self):
        with patch.dict(os.environ, {"FACEIN_ENV": "production", "MOCK_ZKP_VERIFICATION": "false"}):
            zkp_verifier.verifier_absence_mock_en_production()

    def test_api_mock_refuse_la_preuve_en_production(self):
        """Même si le démarrage était contourné, la simulation n'accepte rien en production."""
        with patch.dict(os.environ, {"FACEIN_ENV": "production", "MOCK_ZKP_VERIFICATION": "true"}):
            with patch("services.zkp_verifier.subprocess.run") as run:
                ok = zkp_verifier.verify_proof(PREUVE_SYNTAXIQUE, SIGNAUX_SYNTAXIQUES)
        self.assertFalse(ok)
        run.assert_not_called()

    def test_api_lifespan_refuse_demarrage_mock_en_production(self):
        import main as api_main

        async def demarrer():
            async with api_main.lifespan(api_main.app):
                pass

        import asyncio
        with patch.dict(os.environ, {"FACEIN_ENV": "production", "MOCK_ZKP_VERIFICATION": "true"}):
            with self.assertRaises(RuntimeError):
                asyncio.run(demarrer())

    def test_noeud_refuse_demarrage_mock_en_production(self):
        with patch.dict(os.environ, {"FACEIN_ENV": "production", "MOCK_ZKP_VERIFICATION": "1"}):
            with self.assertRaises(RuntimeError):
                node_validation.verifier_absence_mock_en_production()

    def test_noeud_mock_refuse_la_preuve_en_production(self):
        fd, vk = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        try:
            with patch.dict(os.environ, {"FACEIN_ENV": "production", "MOCK_ZKP_VERIFICATION": "true"}):
                with patch("consensus.validation.subprocess.run") as run:
                    ok = node_validation.verifier_preuve(
                        PREUVE_SYNTAXIQUE, SIGNAUX_SYNTAXIQUES, verification_key_path=vk
                    )
            self.assertFalse(ok)
            run.assert_not_called()
        finally:
            os.unlink(vk)

    def test_noeud_main_refuse_demarrage_mock_en_production(self):
        import main as node_main  # noqa: F401  (nodes/node/main.py masqué par api/main.py)
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "facein_node_main", os.path.join(NODES_DIR, "main.py")
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with patch.dict(os.environ, {"FACEIN_ENV": "production", "MOCK_ZKP_VERIFICATION": "true"}):
            with patch.object(module, "charger_configuration") as charger:
                with self.assertRaises(SystemExit):
                    module.main()
        charger.assert_not_called()

    def test_zkp_verifier_rejects_without_mock_flag(self):
        with patch.dict(os.environ, {"MOCK_ZKP_VERIFICATION": "false"}):
            with patch("services.zkp_verifier.subprocess.run", side_effect=FileNotFoundError("snarkjs")):
                ok = zkp_verifier.verify_proof(
                    proof={"pi_a": ["1", "2"], "pi_b": [["1", "2"], ["3", "4"]], "pi_c": ["1", "2"]},
                    public_signals=["123", "16000000", "1", "2"],
                )
            self.assertFalse(ok)

    def test_jwt_production_requires_secret_key(self):
        with patch.dict(os.environ, {"JWT_ENV": "production", "JWT_SECRET_KEY": ""}):
            with self.assertRaises(RuntimeError):
                jwt_manager._charger_cle_secrete()

    def test_docker_compose_prod_disables_all_mocks_and_closes_db_port(self):
        prod_path = os.path.join(ROOT_DIR, "docker-compose.prod.yml")
        self.assertTrue(os.path.isfile(prod_path), "docker-compose.prod.yml doit exister")
        with open(prod_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("JWT_ENV=production", content)
        self.assertIn("MOCK_ZKP_VERIFICATION=false", content)
        self.assertNotIn("MOCK_ZKP_VERIFICATION=true", content)
        # API + 3 nœuds en mode production (refus de toute simulation)
        self.assertEqual(content.count("- FACEIN_ENV=production"), 4)
        self.assertIn("ports: !reset []", content)
        self.assertIn("no-new-privileges:true", content)


class TestBackendConcurrency(unittest.TestCase):
    """Tests de concurrence multi-thread sur les points critiques du backend."""

    def setUp(self):
        store.reset_store()

    def tearDown(self):
        store.reset_store()

    def test_concurrent_user_registrations(self):
        from routes.register import register

        nb_users = 20
        results = []
        lock = threading.Lock()

        def do_register(idx: int):
            req = RegisterRequest(user_id=f"conc_user_{idx}", commitment=str(100000 + idx))
            with patch("routes.register.propagate_commitment_to_nodes", return_value={"propagated": 3, "total": 3}):
                res = register(req)
            with lock:
                results.append(res.success)

        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(do_register, range(nb_users)))

        self.assertEqual(len(results), nb_users)
        self.assertTrue(all(results))
        for idx in range(nb_users):
            self.assertEqual(store.get_commitment(f"conc_user_{idx}"), str(100000 + idx))

    def test_concurrent_registrations_same_user_only_one_wins(self):
        """Deux inscriptions simultanées du même identifiant : une seule réussit,
        l'autre reçoit 409 et l'engagement du gagnant n'est jamais écrasé."""
        from fastapi import HTTPException
        from routes import register as register_module

        nb = 6
        barriere = threading.Barrier(nb)
        user_exists_original = register_module.user_exists

        def user_exists_synchronise(user_id):
            # Toutes les requêtes passent le pré-contrôle avant qu'aucune n'écrive
            resultat = user_exists_original(user_id)
            barriere.wait(timeout=5)
            return resultat

        def do_register(idx: int):
            req = RegisterRequest(user_id="same_user", commitment=str(700000 + idx))
            try:
                register_module.register(req)
                return ("ok", str(700000 + idx))
            except HTTPException as exc:
                return (exc.status_code, None)

        with patch.object(register_module, "user_exists", side_effect=user_exists_synchronise), \
                patch.object(register_module, "propagate_commitment_to_nodes", return_value={"quorum": True}):
            with ThreadPoolExecutor(max_workers=nb) as pool:
                resultats = list(pool.map(do_register, range(nb)))

        gagnants = [c for statut, c in resultats if statut == "ok"]
        self.assertEqual(len(gagnants), 1, resultats)
        self.assertEqual([s for s, _ in resultats].count(409), nb - 1)
        self.assertEqual(store.get_commitment("same_user"), gagnants[0])

    def test_concurrent_nonce_consumption_allows_exactly_one(self):
        nonce_store = NonceStore(duree_s=60)
        nonce, _ = nonce_store.emettre("alice", "facein-web")

        def try_consume(_):
            return nonce_store.consommer("alice", nonce, "facein-web")

        with ThreadPoolExecutor(max_workers=12) as pool:
            outcomes = list(pool.map(try_consume, range(12)))

        self.assertEqual(outcomes.count(True), 1)
        self.assertEqual(outcomes.count(False), 11)

    def test_concurrent_vote_requests_use_idempotency_cache(self):
        call_count = 0
        lock = threading.Lock()

        def verifier(uid, preuve, nonce, service):
            nonlocal call_count
            with lock:
                call_count += 1
            return True

        svc = ConsensusService("node-a", verifier)
        req = SimpleNamespace(
            id_demande="req-concurrent-1",
            utilisateur_id="alice",
            preuve_zkp=b"{}",
            nonce="a" * 64,
            service_cible="facein-web",
        )

        with ThreadPoolExecutor(max_workers=8) as pool:
            resps = list(pool.map(lambda _: svc.DemanderVote(req, None), range(8)))

        self.assertEqual(len(resps), 8)
        self.assertTrue(all(r.vote == 1 for r in resps))
        # Idempotence : une même demande de vote ne doit être vérifiée qu'une seule fois
        self.assertEqual(call_count, 1)

    def test_concurrent_merkle_sync_batches_thread_safe(self):
        fd, path = tempfile.mkstemp(prefix="conc_merkle_", suffix=".json")
        os.close(fd)
        os.unlink(path)
        try:
            eng_store = EngagementsStore(persistence_file=path)

            def push_batch(idx: int):
                eng_store.sync_batch([
                    {
                        "utilisateur_id": f"u_{idx}",
                        "commitment": str(5000 + idx),
                        "statut": "actif",
                        "updated_at": 100.0 + idx,
                        "version": 1,
                    }
                ])
                return MerkleTree(eng_store.all_entries()).root_hash

            with ThreadPoolExecutor(max_workers=8) as pool:
                roots = list(pool.map(push_batch, range(16)))

            self.assertEqual(len(roots), 16)
            self.assertEqual(eng_store.count(), 16)
        finally:
            if os.path.exists(path):
                os.unlink(path)


if __name__ == "__main__":
    unittest.main()
