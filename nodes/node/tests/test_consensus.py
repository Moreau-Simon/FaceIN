"""Tests de la décision de consensus et du RPC de vote gRPC."""

from concurrent.futures import ThreadPoolExecutor
from threading import Event
from types import SimpleNamespace

import grpc
import pytest
from grpc_health.v1 import health_pb2, health_pb2_grpc

import consensus_pb2
import consensus_pb2_grpc
import verification_pb2
from consensus.validation import decider
from network.peer_client import demander_vote
import network.server as server_module
from network.server import ConsensusService, VerificationService
from verification.nonces import NonceStore


def _interroger_vote(votes):
    def interroger(pair, demande, timeout_s):
        vote = votes[pair]
        if isinstance(vote, Exception):
            raise vote
        return f"node-{pair}", vote

    return interroger


def _creer_demande(**overrides):
    valeurs = {
        "id_demande": "requete-test",
        "utilisateur_id": "user-1",
        "preuve_zkp": b"preuve",
        "nonce": "nonce-test",
        "service_cible": "service-1",
    }
    valeurs.update(overrides)
    return SimpleNamespace(**valeurs)


def test_decider_compte_le_vote_local_et_les_votes_pour_des_pairs():
    demande = _creer_demande()
    votes = {"b": True, "c": False, "d": True}

    resultat = decider(
        demande,
        ["b", "c", "d"],
        verifier_local=lambda *args: False,
        interroger_pair=_interroger_vote(votes),
        seuil=2,
        timeout_s=1,
    )

    assert resultat is True


def test_decider_refuse_si_le_seuil_n_est_pas_atteint():
    demande = _creer_demande()
    votes = {"b": False, "c": True}

    resultat = decider(
        demande,
        ["b", "c"],
        verifier_local=lambda *args: True,
        interroger_pair=_interroger_vote(votes),
        seuil=3,
        timeout_s=1,
    )

    assert resultat is False


def test_decider_exclut_les_pairs_en_erreur():
    demande = _creer_demande()
    votes = {
        "b": RuntimeError("pair indisponible"),
        "c": False,
    }

    resultat = decider(
        demande,
        ["b", "c"],
        verifier_local=lambda *args: True,
        interroger_pair=_interroger_vote(votes),
        seuil=2,
        timeout_s=1,
    )

    assert resultat is False


def test_decider_ne_bloque_pas_sur_un_pair_qui_depasse_le_delai():
    demande = _creer_demande()
    liberation_pair = Event()

    def interroger(pair, demande, timeout_s):
        liberation_pair.wait()
        return "node-b", True

    try:
        resultat = decider(
            demande,
            ["b"],
            verifier_local=lambda *args: False,
            interroger_pair=interroger,
            seuil=1,
            timeout_s=0.01,
        )
    finally:
        liberation_pair.set()

    assert resultat is False


@pytest.mark.parametrize(
    "accepte",
    [
        True,
        False,
    ],
)
def test_rpc_demander_vote_transmet_le_vote_et_l_identifiant(
    accepte
):
    preuve_verifiee = []
    executor = ThreadPoolExecutor(max_workers=2)
    serveur = grpc.server(executor)
    consensus_pb2_grpc.add_ConsensusServiceServicer_to_server(
        ConsensusService(
            "node-b",
            lambda utilisateur_id, preuve, nonce, service_cible:
                preuve_verifiee.append(
                    (utilisateur_id, preuve, nonce, service_cible)
                ) or accepte,
        ),
        serveur,
    )
    port = serveur.add_insecure_port("127.0.0.1:0")
    assert port != 0

    demande = consensus_pb2.DemandeVote(
        id_demande="requete-123",
        noeud_initiateur="node-a",
        utilisateur_id="user-1",
        preuve_zkp=b"preuve",
        nonce="nonce-123",
        service_cible="service-1",
        timestamp=123,
    )

    serveur.start()
    try:
        resultat = demander_vote("127.0.0.1", port, demande, 1)
    finally:
        serveur.stop(0).wait()
        executor.shutdown(wait=True)

    assert resultat == ("node-b", accepte)
    assert preuve_verifiee == [
        ("user-1", b"preuve", "nonce-123", "service-1")
    ]


def test_rpc_demander_vote_retourne_contre_si_le_verificateur_echoue():
    executor = ThreadPoolExecutor(max_workers=2)
    serveur = grpc.server(executor)

    def verifier_en_echec(utilisateur_id, preuve, nonce, service_cible):
        raise RuntimeError("erreur interne")

    consensus_pb2_grpc.add_ConsensusServiceServicer_to_server(
        ConsensusService("node-b", verifier_en_echec),
        serveur,
    )
    port = serveur.add_insecure_port("127.0.0.1:0")
    assert port != 0
    demande = consensus_pb2.DemandeVote(
        id_demande="requete-456",
        utilisateur_id="user-1",
        preuve_zkp=b"preuve",
        nonce="nonce-456",
        service_cible="service-1",
    )

    serveur.start()
    try:
        resultat = demander_vote("127.0.0.1", port, demande, 1)
    finally:
        serveur.stop(0).wait()
        executor.shutdown(wait=True)

    assert resultat == ("node-b", False)


def test_service_verification_transmet_preuve_et_nonce_au_consensus():
    nonces = NonceStore()
    nonce, _ = nonces.emettre("user-1")
    demande_consensus = []
    service = VerificationService(
        "node-a",
        nonces,
        lambda demande: demande_consensus.append(demande) or True,
        lambda utilisateur_id: "token-test",
    )
    demande = verification_pb2.DemandeVerification(
        utilisateur_id="user-1",
        preuve_zkp=b"preuve-binaire",
        nonce=nonce,
        timestamp=123,
        service_cible="service-1",
    )

    reponse = service.VerifierPreuve(demande, context=None)

    assert reponse.accepte is True
    assert reponse.token == "token-test"
    assert len(demande_consensus) == 1
    assert demande_consensus[0].preuve_zkp == b"preuve-binaire"
    assert demande_consensus[0].nonce == nonce


def test_demarrage_enregistre_le_service_de_verification(monkeypatch):
    class ServeurFactice:
        def add_insecure_port(self, adresse):
            return 50051

        def start(self):
            return None

    serveur = ServeurFactice()
    services_enregistres = {}
    nonces = NonceStore()
    decider_fn = lambda demande: True
    fabriquer_token = lambda utilisateur_id: "token-test"

    monkeypatch.setattr(server_module.grpc, "server", lambda executor: serveur)
    monkeypatch.setattr(
        server_module.sync_pb2_grpc,
        "add_SyncServiceServicer_to_server",
        lambda service, serveur: services_enregistres.update(sync=service),
    )
    monkeypatch.setattr(
        server_module.consensus_pb2_grpc,
        "add_ConsensusServiceServicer_to_server",
        lambda service, serveur: services_enregistres.update(
            consensus=service
        ),
    )
    monkeypatch.setattr(
        server_module.verification_pb2_grpc,
        "add_VerificationServiceServicer_to_server",
        lambda service, serveur: services_enregistres.update(
            verification=service
        ),
    )
    monkeypatch.setattr(
        health_pb2_grpc,
        "add_HealthServicer_to_server",
        lambda service, serveur: services_enregistres.update(health=service),
    )

    resultat = server_module.start_grpc_server(
        "node-a",
        50051,
        lambda *args: True,
        nonces,
        decider_fn,
        fabriquer_token,
    )

    assert resultat is serveur
    assert isinstance(
        services_enregistres["verification"], VerificationService
    )
    assert services_enregistres["verification"]._nonces is nonces
    assert services_enregistres["verification"]._decider is decider_fn
    assert (
        services_enregistres["verification"]._fabriquer_token
        is fabriquer_token
    )
    assert services_enregistres["health"].Check(
        health_pb2.HealthCheckRequest(), None
    ).status == health_pb2.HealthCheckResponse.SERVING
