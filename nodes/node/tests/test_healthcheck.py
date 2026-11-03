from types import SimpleNamespace

from grpc_health.v1 import health_pb2

import healthcheck


class CanalFactice:
    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


def test_healthcheck_reussit_si_le_noeud_est_serving(monkeypatch):
    monkeypatch.setenv("NODE_ID", "node-a")
    monkeypatch.setenv("NODE_PORT", "50051")
    canal = CanalFactice()
    appels = {}

    class HealthStubFactice:
        def __init__(self, channel):
            appels["channel"] = channel

        def Check(self, request, timeout):
            appels["request"] = request
            appels["timeout"] = timeout
            return SimpleNamespace(
                status=health_pb2.HealthCheckResponse.SERVING
            )

    monkeypatch.setattr(
        healthcheck,
        "creer_canal_securise",
        lambda address: appels.update(address=address) or canal,
    )
    monkeypatch.setattr(
        healthcheck.health_pb2_grpc,
        "HealthStub",
        HealthStubFactice,
    )

    assert healthcheck.main() == 0
    assert appels["address"] == "node-a:50051"
    assert appels["channel"] is canal
    assert appels["timeout"] == 3


def test_healthcheck_echoue_si_le_noeud_ne_sert_pas(monkeypatch):
    monkeypatch.setenv("NODE_ID", "node-a")
    monkeypatch.setenv("NODE_PORT", "50051")

    class HealthStubFactice:
        def __init__(self, channel):
            pass

        def Check(self, request, timeout):
            return SimpleNamespace(
                status=health_pb2.HealthCheckResponse.NOT_SERVING
            )

    monkeypatch.setattr(
        healthcheck,
        "creer_canal_securise",
        lambda address: CanalFactice(),
    )
    monkeypatch.setattr(
        healthcheck.health_pb2_grpc,
        "HealthStub",
        HealthStubFactice,
    )

    assert healthcheck.main() == 1
