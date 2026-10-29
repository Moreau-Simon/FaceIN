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
    monkeypatch.setenv("TLS_ENABLED", "false")
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
    monkeypatch.setenv("TLS_ENABLED", "false")
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


def test_demander_vote_utilise_tls_mutuel_quand_active(monkeypatch, tmp_path):
    ca = tmp_path / "ca.crt"
    cert = tmp_path / "node.crt"
    key = tmp_path / "node.key"
    ca.write_bytes(b"ca")
    cert.write_bytes(b"certificate")
    key.write_bytes(b"private-key")
    monkeypatch.setenv("TLS_ENABLED", "true")
    monkeypatch.setenv("TLS_CA_CERT", str(ca))
    monkeypatch.setenv("TLS_CERT", str(cert))
    monkeypatch.setenv("TLS_KEY", str(key))

    demande = SimpleNamespace(id_demande="requete-123")
    reponse = SimpleNamespace(
        id_demande="requete-123",
        noeud_id="node-b",
        vote=consensus_pb2.VOTE_POUR,
    )
    canal = CanalFactice()
    credentials = object()
    appels_credentials = {}
    appels_canal = {}

    class StubFactice:
        def __init__(self, channel):
            assert channel is canal

        def DemanderVote(self, demande_recue, timeout):
            return reponse

    def ssl_channel_credentials(**kwargs):
        appels_credentials.update(kwargs)
        return credentials

    def secure_channel(address, actual_credentials):
        appels_canal.update(address=address, credentials=actual_credentials)
        return canal

    monkeypatch.setattr(
        peer_client.grpc, "ssl_channel_credentials", ssl_channel_credentials
    )
    monkeypatch.setattr(peer_client.grpc, "secure_channel", secure_channel)
    monkeypatch.setattr(
        peer_client.consensus_pb2_grpc,
        "ConsensusServiceStub",
        StubFactice,
    )

    assert peer_client.demander_vote("node-b", 50052, demande, 1.5) == (
        "node-b",
        True,
    )
    assert appels_credentials == {
        "root_certificates": b"ca",
        "private_key": b"private-key",
        "certificate_chain": b"certificate",
    }
    assert appels_canal == {
        "address": "node-b:50052",
        "credentials": credentials,
    }
