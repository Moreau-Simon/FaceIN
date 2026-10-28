"""Parcours gRPC de bout en bout avec trois nœuds locaux."""

from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import grpc

import consensus_pb2_grpc
import verification_pb2
import verification_pb2_grpc
from consensus.validation import decider, valider_avec_mock
from network.peer_client import demander_vote
from network.server import ConsensusService, VerificationService
from verification.nonces import NonceStore


class NoeudLocal:
    def __init__(self, node_id, pairs):
        self.node_id = node_id
        self.executor = ThreadPoolExecutor(max_workers=8)
        self.server = grpc.server(self.executor)
        self.nonces = NonceStore()
        self.port = self.server.add_insecure_port("127.0.0.1:0")
        assert self.port != 0

        def interroger_pair(pair, demande, timeout_s):
            return demander_vote(
                pair.host,
                pair.port,
                demande,
                timeout_s,
            )

        def decider_fn(demande):
            return decider(
                demande,
                pairs,
                valider_avec_mock,
                interroger_pair,
                seuil=2,
                timeout_s=0.5,
            )

        consensus_pb2_grpc.add_ConsensusServiceServicer_to_server(
            ConsensusService(node_id, valider_avec_mock),
            self.server,
        )
        verification_pb2_grpc.add_VerificationServiceServicer_to_server(
            VerificationService(
                node_id,
                self.nonces,
                decider_fn,
                lambda utilisateur_id: f"token-{utilisateur_id}",
            ),
            self.server,
        )
        self.server.start()

    def arreter(self):
        self.server.stop(0).wait()
        self.executor.shutdown(wait=True)


def _demander_nonce_puis_verifier(host, port, utilisateur_id):
    with grpc.insecure_channel(f"{host}:{port}") as channel:
        stub = verification_pb2_grpc.VerificationServiceStub(channel)
        reponse_nonce = stub.DemanderNonce(
            verification_pb2.DemandeNonce(utilisateur_id=utilisateur_id),
            timeout=1,
        )
        return stub.VerifierPreuve(
            verification_pb2.DemandeVerification(
                utilisateur_id=utilisateur_id,
                preuve_zkp=b"preuve-de-test",
                nonce=reponse_nonce.nonce,
                timestamp=123,
                service_cible="service-1",
            ),
            timeout=2,
        )


def test_parcours_complet_reussit_avec_un_pair_arrete():
    node_b = NoeudLocal("node-b", [])
    node_c = NoeudLocal("node-c", [])
    pairs_a = [
        SimpleNamespace(host="127.0.0.1", port=node_b.port),
        SimpleNamespace(host="127.0.0.1", port=node_c.port),
    ]
    node_a = NoeudLocal("node-a", pairs_a)
    noeuds = [node_a, node_b, node_c]

    try:
        reponse_trois_noeuds = _demander_nonce_puis_verifier(
            "127.0.0.1",
            node_a.port,
            "user-1",
        )
        assert reponse_trois_noeuds.accepte is True
        assert reponse_trois_noeuds.token == "token-user-1"

        node_c.arreter()
        noeuds.remove(node_c)

        reponse_deux_sur_trois = _demander_nonce_puis_verifier(
            "127.0.0.1",
            node_a.port,
            "user-1",
        )
    finally:
        for noeud in noeuds:
            noeud.arreter()

    assert reponse_deux_sur_trois.accepte is True
    assert reponse_deux_sur_trois.token == "token-user-1"
