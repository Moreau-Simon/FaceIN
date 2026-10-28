"""Tests du client gRPC pour les heartbeats et les votes de consensus."""

from types import SimpleNamespace

import pytest

import consensus_pb2
import network.peer_client as peer_client


class CanalFactice:
    def __init__(self):
        self.adresse = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


@pytest.mark.parametrize(
    "vote, vote_attendu",
    [
        (consensus_pb2.VOTE_POUR, True),
        (consensus_pb2.VOTE_CONTRE, False),
    ],
)
def test_demander_vote_retourne_identite_et_vote(
    monkeypatch, vote, vote_attendu
):
    demande = SimpleNamespace(id_demande="requete-123")
    reponse = SimpleNamespace(
        id_demande="requete-123",
        noeud_id="node-b",
        vote=vote,
    )
    canal = CanalFactice()
    appel = {}

    class StubFactice:
        def __init__(self, channel):
            appel["channel"] = channel

        def DemanderVote(self, demande_recue, timeout):
            appel["demande"] = demande_recue
            appel["timeout"] = timeout
            return reponse

    monkeypatch.setattr(
        peer_client.grpc, "insecure_channel", lambda address: canal
    )
    monkeypatch.setattr(
        peer_client.consensus_pb2_grpc,
        "ConsensusServiceStub",
        StubFactice,
    )

    resultat = peer_client.demander_vote("node-b", 50052, demande, 1.5)

    assert resultat == ("node-b", vote_attendu)
    assert appel == {
        "channel": canal,
        "demande": demande,
        "timeout": 1.5,
    }


def test_demander_vote_refuse_une_reponse_pour_un_autre_id(monkeypatch):
    demande = SimpleNamespace(id_demande="requete-attendue")
    reponse = SimpleNamespace(
        id_demande="autre-requete",
        noeud_id="node-b",
        vote=consensus_pb2.VOTE_POUR,
    )
    canal = CanalFactice()

    class StubFactice:
        def __init__(self, channel):
            pass

        def DemanderVote(self, demande_recue, timeout):
            return reponse

    monkeypatch.setattr(
        peer_client.grpc, "insecure_channel", lambda address: canal
    )
    monkeypatch.setattr(
        peer_client.consensus_pb2_grpc,
        "ConsensusServiceStub",
        StubFactice,
    )

    with pytest.raises(ValueError, match="id_demande inattendu"):
        peer_client.demander_vote("node-b", 50052, demande, 1.5)
