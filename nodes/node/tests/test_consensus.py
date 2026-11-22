"""
Tests unitaires pour la décision de consensus distribué, le RPC de vote et le basculement.

Valide l'ensemble des scénarios de consensus :
- Consensus 3/3, 2/3, 1/3, 0/3
- Gestion des pannes de pairs et timeouts
- Seuil de majorité dynamique (1, 2, 5 nœuds)
- Idempotence des demandes de vote
- Failover sélectif (basculement sur panne réseau, pas sur refus calculé)
- Absence complète de réseau (refus sécurisé)
- Services gRPC de vérification et de consensus
"""

import json
import logging
import os
import sys
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from types import SimpleNamespace
from unittest.mock import Mock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from consensus.validation import DetailVote, ResultatConsensus, VoteExecutor, decider
from network.peer_client import demander_vote
import network.server as server_module
from network.server import ConsensusService, VerificationService
from verification.nonces import NonceStore

try:
    import grpc
    from grpc_health.v1 import health_pb2, health_pb2_grpc
    import consensus_pb2
    import consensus_pb2_grpc
    import verification_pb2
except ImportError:
    grpc = None
    health_pb2 = health_pb2_grpc = None
    consensus_pb2 = consensus_pb2_grpc = verification_pb2 = None


def _interroger_vote(votes):
    def interroger(pair, demande, timeout_s):
        vote = votes[pair]
        if isinstance(vote, Exception):
            raise vote
        if isinstance(vote, tuple):
            return vote
        return f"node-{pair}", vote

    return interroger


def _creer_demande(**overrides):
    valeurs = {
        "id_demande": "req-test-uuid",
        "utilisateur_id": "user-1",
        "preuve_zkp": b'{"pi_a":[],"pi_b":[],"pi_c":[]}',
        "nonce": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
        "service_cible": "facein-web",
    }
    valeurs.update(overrides)
    return SimpleNamespace(**valeurs)


class TestConsensusScenarios(unittest.TestCase):
    """Vérifie la robustesse du consensus décentralisé sous différentes conditions."""

    def setUp(self):
        self.executor = VoteExecutor(max_workers=3, max_pending=5)

    def tearDown(self):
        self.executor.close()

    def test_decider_compte_le_vote_local_et_les_votes_pour_des_pairs(self):
        demande = _creer_demande()
        votes = {"b": True, "c": False, "d": True}

        resultat = decider(
            demande,
            ["b", "c", "d"],
            verifier_local=lambda *args: False,
            interroger_pair=_interroger_vote(votes),
            seuil=2,
            timeout_s=1.0,
            vote_executor=self.executor,
        )
        self.assertTrue(resultat)

    def test_decider_refuse_si_le_seuil_n_est_pas_atteint(self):
        demande = _creer_demande()
        votes = {"b": False, "c": True}

        resultat = decider(
            demande,
            ["b", "c"],
            verifier_local=lambda *args: True,
            interroger_pair=_interroger_vote(votes),
            seuil=3,
            timeout_s=1.0,
            vote_executor=self.executor,
        )
        self.assertFalse(resultat)

    def test_decider_ne_bloque_pas_sur_un_pair_qui_depasse_le_delai(self):
        demande = _creer_demande()
        liberation_pair = Event()

        def interroger(pair, d, timeout_s):
            liberation_pair.wait(timeout=0.2)
            return "node-b", True

        try:
            resultat = decider(
                demande,
                ["b"],
                verifier_local=lambda *args: False,
                interroger_pair=interroger,
                seuil=1,
                timeout_s=0.01,
                vote_executor=self.executor,
            )
        finally:
            liberation_pair.set()

        self.assertFalse(resultat)

    def test_consensus_3_sur_3(self):
        demande = _creer_demande()
        votes = {"node-b": ("node-b", True, ""), "node-c": ("node-c", True, "")}

        res = decider(
            demande=demande,
            pairs=["node-b", "node-c"],
            verifier_local=lambda *args: True,
            interroger_pair=lambda pair, d, to: votes[pair],
            seuil=2,
            timeout_s=1.0,
            vote_executor=self.executor,
            node_id="node-a",
            return_details=True,
        )

        self.assertTrue(res.accepte)
        self.assertEqual(res.coordinateur_id, "node-a")
        self.assertGreaterEqual(res.nb_votes_pour, 2)
        self.assertEqual(res.nb_votes_contre, 0)
        self.assertEqual(len(res.noeuds_indisponibles), 0)

    def test_consensus_2_sur_3(self):
        demande = _creer_demande()
        votes = {"node-b": ("node-b", True, ""), "node-c": ("node-c", False, "preuve invalide")}

        res = decider(
            demande=demande,
            pairs=["node-b", "node-c"],
            verifier_local=lambda *args: True,
            interroger_pair=lambda pair, d, to: votes[pair],
            seuil=2,
            timeout_s=1.0,
            vote_executor=self.executor,
            node_id="node-a",
            return_details=True,
        )

        self.assertTrue(res.accepte)
        self.assertGreaterEqual(res.nb_votes_pour, 2)
        self.assertEqual(res.seuil_requis, 2)

    def test_consensus_1_sur_3(self):
        demande = _creer_demande()
        votes = {
            "node-b": ("node-b", False, "seuil depasse"),
            "node-c": ("node-c", False, "engagement mismatch"),
        }

        res = decider(
            demande=demande,
            pairs=["node-b", "node-c"],
            verifier_local=lambda *args: True,
            interroger_pair=lambda pair, d, to: votes[pair],
            seuil=2,
            timeout_s=1.0,
            vote_executor=self.executor,
            node_id="node-a",
            return_details=True,
        )

        self.assertFalse(res.accepte)
        self.assertEqual(res.nb_votes_pour, 1)
        self.assertEqual(res.nb_votes_contre, 2)

    def test_consensus_0_sur_3(self):
        demande = _creer_demande()
        votes = {
            "node-b": ("node-b", False, "rejet"),
            "node-c": ("node-c", False, "rejet"),
        }

        res = decider(
            demande=demande,
            pairs=["node-b", "node-c"],
            verifier_local=lambda *args: False,
            interroger_pair=lambda pair, d, to: votes[pair],
            seuil=2,
            timeout_s=1.0,
            vote_executor=self.executor,
            node_id="node-a",
            return_details=True,
        )

        self.assertFalse(res.accepte)
        self.assertEqual(res.nb_votes_pour, 0)
        self.assertGreaterEqual(res.nb_votes_contre, 1)

    def test_pair_indisponible_mais_quorum_atteint(self):
        demande = _creer_demande()

        def interroger(pair, d, to):
            if pair == "node-c":
                raise ConnectionError("node-c hors ligne")
            return "node-b", True, ""

        res = decider(
            demande=demande,
            pairs=["node-b", "node-c"],
            verifier_local=lambda *args: True,
            interroger_pair=interroger,
            seuil=2,
            timeout_s=1.0,
            vote_executor=self.executor,
            node_id="node-a",
            return_details=True,
        )

        self.assertTrue(res.accepte)
        self.assertIn("node-c", res.noeuds_indisponibles)
        self.assertEqual(res.nb_votes_pour, 2)

    def test_timeout_empechant_seuil(self):
        demande = _creer_demande()

        def interroger_timeout(pair, d, to):
            time.sleep(0.3)
            return pair, True

        res = decider(
            demande=demande,
            pairs=["node-b", "node-c"],
            verifier_local=lambda *args: False,
            interroger_pair=interroger_timeout,
            seuil=2,
            timeout_s=0.05,
            vote_executor=self.executor,
            node_id="node-a",
            return_details=True,
        )

        self.assertFalse(res.accepte)
        self.assertGreaterEqual(len(res.noeuds_indisponibles), 1)

    def test_nombre_noeuds_dynamique(self):
        demande = _creer_demande()

        # Réseau à 5 nœuds : majorité qualifiée = 3
        votes_5 = {
            "node-b": ("node-b", True, ""),
            "node-c": ("node-c", True, ""),
            "node-d": ("node-d", False, ""),
            "node-e": ("node-e", False, ""),
        }
        res_5 = decider(
            demande=demande,
            pairs=["node-b", "node-c", "node-d", "node-e"],
            verifier_local=lambda *args: True,
            interroger_pair=lambda p, d, to: votes_5[p],
            seuil=None,
            timeout_s=1.0,
            vote_executor=self.executor,
            node_id="node-a",
            return_details=True,
        )
        self.assertTrue(res_5.accepte)
        self.assertEqual(res_5.seuil_requis, 3)

        # Réseau à 1 nœud (initiateur seul) : seuil = 1
        res_1 = decider(
            demande=demande,
            pairs=[],
            verifier_local=lambda *args: True,
            interroger_pair=lambda p, d, to: None,
            seuil=None,
            timeout_s=1.0,
            vote_executor=self.executor,
            node_id="node-a",
            return_details=True,
        )
        self.assertTrue(res_1.accepte)
        self.assertEqual(res_1.seuil_requis, 1)


class TestIdempotenceAndFailover(unittest.TestCase):
    """Tests d'idempotence des votes et de basculement API Gateway."""

    def test_double_demande_vote_idempotente(self):
        mock_verifier = Mock(return_value=True)
        service = ConsensusService(node_id="node-b", verifier=mock_verifier)

        demande = SimpleNamespace(
            id_demande="unique-request-999",
            utilisateur_id="bob",
            preuve_zkp=b"preuve",
            nonce="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            service_cible="facein-web",
        )

        rep1 = service.DemanderVote(demande, None)
        self.assertEqual(rep1.id_demande, "unique-request-999")
        self.assertEqual(mock_verifier.call_count, 1)

        # Deuxième appel avec le même id_demande : réponse immédiate depuis le cache
        rep2 = service.DemanderVote(demande, None)
        self.assertEqual(rep2.id_demande, "unique-request-999")
        self.assertEqual(mock_verifier.call_count, 1)

    def test_failover_si_coordinateur_indisponible(self):
        from api.services import grpc_bridge

        nodes = [
            {"id": "node-a", "host": "127.0.0.1", "port": 50051},
            {"id": "node-b", "host": "127.0.0.1", "port": 50052},
        ]

        def faux_verifier_unitaire(node, user_id, proof_json_str, nonce, public_signals=None):
            if node["id"] == "node-a":
                return None  # node-a injoignable
            return {
                "node_id": "node-b",
                "accepte": True,
                "token": "token-node-b",
                "raison_refus": "",
                "coordinateur_id": "node-b",
                "votes": {"node-b": True, "node-c": True},
                "votes_recus": [],
                "nb_votes_pour": 2,
                "nb_votes_contre": 0,
                "noeuds_indisponibles": ["node-a"],
                "seuil_requis": 2,
            }

        with patch("api.services.grpc_bridge._verifier_noeud_unitaire", side_effect=faux_verifier_unitaire):
            res = grpc_bridge.verify_on_nodes(
                user_id="alice",
                proof_json_str='{"proof": true}',
                nonce="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
                nodes=nodes,
            )

            self.assertTrue(res["consensus"])
            self.assertEqual(res["initiator"], "node-b")
            self.assertIn("node-a", res["noeuds_indisponibles"])

    def test_decision_negative_ne_declenche_pas_de_failover(self):
        from api.services import grpc_bridge

        nodes = [
            {"id": "node-a", "host": "127.0.0.1", "port": 50051},
            {"id": "node-b", "host": "127.0.0.1", "port": 50052},
        ]

        appels = []

        def faux_verifier_unitaire(node, user_id, proof_json_str, nonce, public_signals=None):
            appels.append(node["id"])
            return {
                "node_id": "node-a",
                "accepte": False,
                "token": "",
                "raison_refus": "Consensus non atteint (1/3)",
                "coordinateur_id": "node-a",
                "votes": {"node-a": True, "node-b": False, "node-c": False},
                "votes_recus": [],
                "nb_votes_pour": 1,
                "nb_votes_contre": 2,
                "noeuds_indisponibles": [],
                "seuil_requis": 2,
            }

        with patch("api.services.grpc_bridge._verifier_noeud_unitaire", side_effect=faux_verifier_unitaire):
            res = grpc_bridge.verify_on_nodes(
                user_id="alice",
                proof_json_str='{"proof": true}',
                nonce="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
                nodes=nodes,
            )

            self.assertFalse(res["consensus"])
            self.assertEqual(res["initiator"], "node-a")
            self.assertEqual(appels, ["node-a"])

    def test_absence_complete_de_reseau_refuse_authentification(self):
        from api.services import grpc_bridge

        nodes = [{"id": "node-a", "host": "127.0.0.1", "port": 50051}]

        os.environ.pop("MOCK_ZKP_VERIFICATION", None)
        os.environ.pop("ALLOW_MOCK_CONSENSUS", None)

        with patch("api.services.grpc_bridge._verifier_noeud_unitaire", return_value=None):
            res = grpc_bridge.verify_on_nodes(
                user_id="alice",
                proof_json_str='{"proof": true}',
                nonce="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
                nodes=nodes,
            )

            self.assertFalse(res["consensus"])
            self.assertEqual(res["majority"], "0/1")
            self.assertIn("node-a", res["noeuds_indisponibles"])


class TestServicesVerificationEtVote(unittest.TestCase):
    """Tests unitaires des services gRPC de vérification et de consensus."""

    def test_service_verification_refuse_sans_nonce_valide(self):
        nonces = NonceStore()
        service = VerificationService(
            node_id="node-a",
            nonces=nonces,
            decider_fn=lambda d: True,
            fabriquer_token=lambda uid: "tok",
        )
        demande = SimpleNamespace(
            utilisateur_id="alice",
            preuve_zkp=b"preuve",
            nonce="court",
            service_cible="facein-web",
            public_signals=[],
            timestamp=int(time.time()),
        )
        reponse = service.VerifierPreuve(demande, None)
        self.assertFalse(reponse.accepte)
        self.assertIn("nonce", reponse.raison_refus)

    def test_service_verification_accepte_si_consensus_valide(self):
        nonces = NonceStore()
        nonce, _ = nonces.emettre("alice", "facein-web")
        decision_mock = ResultatConsensus(
            accepte=True,
            coordinateur_id="node-a",
            votes={"node-a": True, "node-b": True},
            votes_recus=[
                DetailVote("node-a", True, ""),
                DetailVote("node-b", True, ""),
            ],
            nb_votes_pour=2,
            nb_votes_contre=0,
            noeuds_indisponibles=[],
            seuil_requis=2,
            raison="",
        )
        service = VerificationService(
            node_id="node-a",
            nonces=nonces,
            decider_fn=lambda d: decision_mock,
            fabriquer_token=lambda uid: "jwt-token-123",
        )
        demande = SimpleNamespace(
            utilisateur_id="alice",
            preuve_zkp=b"preuve",
            nonce=nonce,
            service_cible="facein-web",
            public_signals=[],
            timestamp=int(time.time()),
        )
        reponse = service.VerifierPreuve(demande, None)
        self.assertTrue(reponse.accepte)
        self.assertEqual(reponse.token, "jwt-token-123")
        self.assertEqual(reponse.coordinateur_id, "node-a")
        self.assertEqual(reponse.nb_votes_pour, 2)

    def test_service_verification_refuse_si_consensus_rejette(self):
        nonces = NonceStore()
        nonce, _ = nonces.emettre("alice", "facein-web")
        decision_mock = ResultatConsensus(
            accepte=False,
            coordinateur_id="node-a",
            votes={"node-a": False},
            votes_recus=[DetailVote("node-a", False, "Preuve rejetée")],
            nb_votes_pour=0,
            nb_votes_contre=1,
            noeuds_indisponibles=["node-b"],
            seuil_requis=2,
            raison="Consensus non atteint (0/2)",
        )
        service = VerificationService(
            node_id="node-a",
            nonces=nonces,
            decider_fn=lambda d: decision_mock,
            fabriquer_token=lambda uid: "tok",
        )
        demande = SimpleNamespace(
            utilisateur_id="alice",
            preuve_zkp=b"preuve",
            nonce=nonce,
            service_cible="facein-web",
            public_signals=[],
            timestamp=int(time.time()),
        )
        reponse = service.VerifierPreuve(demande, None)
        self.assertFalse(reponse.accepte)
        self.assertIn("Consensus non atteint", reponse.raison_refus)


if __name__ == "__main__":
    unittest.main()
