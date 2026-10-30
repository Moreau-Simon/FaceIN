import client_verification
import pytest


def test_creer_canal_utilise_le_mtls(monkeypatch, tmp_path):
    ca = tmp_path / "ca.crt"
    cert = tmp_path / "node-a.crt"
    key = tmp_path / "node-a.key"
    ca.write_bytes(b"ca")
    cert.write_bytes(b"certificate")
    key.write_bytes(b"private-key")

    monkeypatch.setenv("TLS_ENABLED", "true")
    monkeypatch.setenv("TLS_CA_CERT", str(ca))
    monkeypatch.setenv("TLS_CERT", str(cert))
    monkeypatch.setenv("TLS_KEY", str(key))

    credentials = object()
    canal = object()
    appels = {}

    def ssl_channel_credentials(**kwargs):
        appels["credentials"] = kwargs
        return credentials

    def secure_channel(address, actual_credentials):
        appels["channel"] = (address, actual_credentials)
        return canal

    monkeypatch.setattr(
        client_verification.grpc,
        "ssl_channel_credentials",
        ssl_channel_credentials,
    )
    monkeypatch.setattr(
        client_verification.grpc,
        "secure_channel",
        secure_channel,
    )

    assert client_verification.creer_canal("node-a:50051") is canal
    assert appels == {
        "credentials": {
            "root_certificates": b"ca",
            "private_key": b"private-key",
            "certificate_chain": b"certificate",
        },
        "channel": ("node-a:50051", credentials),
    }


def test_creer_canal_exige_tls_sauf_option_insecure(monkeypatch):
    monkeypatch.delenv("TLS_ENABLED", raising=False)
    canal = object()
    appels = []
    monkeypatch.setattr(
        client_verification.grpc,
        "insecure_channel",
        lambda address: appels.append(address) or canal,
    )

    with pytest.raises(RuntimeError, match="TLS_ENABLED"):
        client_verification.creer_canal("node-a:50051")

    assert client_verification.creer_canal(
        "node-a:50051", insecure=True
    ) is canal
    assert appels == ["node-a:50051"]
