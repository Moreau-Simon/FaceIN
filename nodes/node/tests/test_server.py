"""
Tests unitaires du VerificationService fusionné (network/server.py) :
architecture develop (NonceStore + consensus) et magasin d'engagements.
"""

import json

import pytest

import network.server as server_module
from grpc_health.v1 import health_pb2, health_pb2_grpc
import verification_pb2
from consensus.validation import VerificateurZKP
from network.server import VerificationService
from store.engagements import EngagementsStore
from verification.nonces import NonceStore


@pytest.fixture
def store():
    return EngagementsStore()


def _service(store=None, decider_fn=lambda demande: True):
    nonces = NonceStore()
    service = VerificationService(
        "node-test",
        nonces,
        decider_fn,
        lambda utilisateur_id: f"token-{utilisateur_id}",
        store=store,
    )
    return service, nonces


def test_recuperer_donnee_aide_trouve(store):
    store.save("user_123", "poseidon_hash_abc")
    service, _ = _service(store)

    reponse = service.RecupererDonneeAide(
        verification_pb2.DemandeDonneeAide(utilisateur_id="user_123"), None
    )

    assert reponse.trouve is True
    assert reponse.donnee_aide == "poseidon_hash_abc"


def test_recuperer_donnee_aide_non_trouve(store):
    service, _ = _service(store)

    reponse = service.RecupererDonneeAide(
        verification_pb2.DemandeDonneeAide(utilisateur_id="user_inconnu"), None
    )

    assert reponse.trouve is False
    assert reponse.donnee_aide == ""


def test_recuperer_donnee_aide_sans_store():
    service, _ = _service(store=None)

    reponse = service.RecupererDonneeAide(
        verification_pb2.DemandeDonneeAide(utilisateur_id="user_123"), None
    )

    assert reponse.trouve is False


def test_demander_nonce_est_emis_par_le_nonce_store():
    service, nonces = _service()

    reponse = service.DemanderNonce(
        verification_pb2.DemandeNonce(utilisateur_id="user_123"), None
    )

    assert len(reponse.nonce) > 10
    assert reponse.expiration_timestamp > 0
    assert nonces.consommer("user_123", reponse.nonce) is True


def test_verifier_preuve_empaquette_les_signaux_publics_pour_le_consensus():
    demandes = []
    service, nonces = _service(decider_fn=lambda d: demandes.append(d) or True)
    nonce, _ = nonces.emettre("user_123")

    reponse = service.VerifierPreuve(
        verification_pb2.DemandeVerification(
            utilisateur_id="user_123",
            preuve_zkp=b'{"pi_a": ["1"]}',
            nonce=nonce,
            service_cible="demo",
            public_signals=["engagement_ok", "50000"],
        ),
        None,
    )

    assert reponse.accepte is True
    assert reponse.token == "token-user_123"
    assert json.loads(demandes[0].preuve_zkp) == {
        "proof": {"pi_a": ["1"]},
        "publicSignals": ["engagement_ok", "50000"],
    }


def test_verifier_preuve_refuse_une_preuve_illisible_sans_appeler_le_decideur():
    demandes = []
    service, nonces = _service(decider_fn=lambda d: demandes.append(d) or True)
    nonce, _ = nonces.emettre("user_123")

    reponse = service.VerifierPreuve(
        verification_pb2.DemandeVerification(
            utilisateur_id="user_123",
            preuve_zkp=b"pas du json",
            nonce=nonce,
            public_signals=["engagement_ok"],
        ),
        None,
    )

    assert reponse.accepte is False
    assert reponse.raison_refus == "preuve ZKP illisible"
    assert demandes == []


def test_demarrage_branche_le_store_du_verificateur(monkeypatch, store):
    class ServeurFactice:
        def add_insecure_port(self, adresse):
            return 50051

        def add_secure_port(self, adresse, credentials):
            return 50051

        def start(self):
            return None

    monkeypatch.setenv("TLS_ENABLED", "false")
    enregistres = {}
    monkeypatch.setattr(server_module.grpc, "server", lambda executor: ServeurFactice())
    monkeypatch.setattr(
        server_module.sync_pb2_grpc,
        "add_SyncServiceServicer_to_server",
        lambda service, serveur: None,
    )
    monkeypatch.setattr(
        server_module.consensus_pb2_grpc,
        "add_ConsensusServiceServicer_to_server",
        lambda service, serveur: None,
    )
    monkeypatch.setattr(
        server_module.verification_pb2_grpc,
        "add_VerificationServiceServicer_to_server",
        lambda service, serveur: enregistres.update(verification=service),
    )
    monkeypatch.setattr(
        health_pb2_grpc,
        "add_HealthServicer_to_server",
        lambda service, serveur: enregistres.update(health=service),
    )

    server_module.start_grpc_server(
        "node-a",
        50051,
        VerificateurZKP(store),
        NonceStore(),
        lambda demande: True,
        lambda utilisateur_id: "token",
    )

    assert enregistres["verification"]._store is store
    assert enregistres["health"].Check(
        health_pb2.HealthCheckRequest(), None
    ).status == health_pb2.HealthCheckResponse.SERVING


def test_demarrage_ouvre_un_port_tls_mutuel(monkeypatch, tmp_path):
    class ServeurFactice:
        def add_secure_port(self, adresse, credentials):
            self.adresse = adresse
            self.credentials = credentials
            return 50051

        def start(self):
            return None

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

    serveur = ServeurFactice()
    monkeypatch.setattr(server_module.grpc, "server", lambda executor: serveur)
    monkeypatch.setattr(
        server_module.sync_pb2_grpc,
        "add_SyncServiceServicer_to_server",
        lambda service, serveur: None,
    )
    monkeypatch.setattr(
        server_module.consensus_pb2_grpc,
        "add_ConsensusServiceServicer_to_server",
        lambda service, serveur: None,
    )
    monkeypatch.setattr(
        server_module.verification_pb2_grpc,
        "add_VerificationServiceServicer_to_server",
        lambda service, serveur: None,
    )
    monkeypatch.setattr(
        health_pb2_grpc,
        "add_HealthServicer_to_server",
        lambda service, serveur: None,
    )
    credentials = object()
    appels_credentials = {}

    def credentials_tls(pairs, root_certificates, require_client_auth):
        appels_credentials.update(
            pairs=pairs,
            root_certificates=root_certificates,
            require_client_auth=require_client_auth,
        )
        return credentials

    monkeypatch.setattr(
        server_module.grpc, "ssl_server_credentials", credentials_tls
    )

    server_module.start_grpc_server(
        "node-a",
        50051,
        lambda *args: True,
        NonceStore(),
        lambda demande: True,
        lambda utilisateur_id: "token",
    )

    assert serveur.adresse == "0.0.0.0:50051"
    assert serveur.credentials is credentials
    assert appels_credentials == {
        "pairs": [(b"private-key", b"certificate")],
        "root_certificates": b"ca",
        "require_client_auth": True,
    }
