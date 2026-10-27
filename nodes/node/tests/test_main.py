"""Tests de l'intégration du registre avec les heartbeats de main.py."""

import logging
import os
import sys
from threading import Barrier
from types import ModuleType

import grpc
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Les stubs gRPC sont générés par le Dockerfile, pas présents dans le dépôt
# source lors de l'exécution locale des tests.
sync_pb2 = ModuleType("sync_pb2")
sync_pb2_grpc = ModuleType("sync_pb2_grpc")
sync_pb2_grpc.SyncServiceServicer = object
sys.modules.setdefault("sync_pb2", sync_pb2)
sys.modules.setdefault("sync_pb2_grpc", sync_pb2_grpc)

import main as main_module  # noqa: E402
from network.peers import PeerRegistry  # noqa: E402


class ErreurHeartbeat(grpc.RpcError):
    pass


class ServeurFactice:
    def __init__(self):
        self.arret_demande = False

    def stop(self, grace):
        self.arret_demande = True
        return self

    def wait(self):
        return None


class EvenementFactice:
    def __init__(self, attendre):
        self._attendre = attendre
        self.arret_demande = False

    def set(self):
        self.arret_demande = True

    def is_set(self):
        return self.arret_demande

    def wait(self, timeout=None):
        self._attendre(timeout)


@pytest.mark.parametrize(
    "resultat, erreur, statut_attendu, node_id_attendu",
    [
        (("node-b", True), None, "online", "node-b"),
        (("node-b", False), None, "suspect", None),
        (None, ErreurHeartbeat("timeout"), "suspect", None),
        (("NODE-A", True), None, "suspect", None),
    ],
)
def test_main_met_a_jour_le_registre_pour_chaque_heartbeat(
    monkeypatch, resultat, erreur, statut_attendu, node_id_attendu
):
    config = {
        "node_id": "node-a",
        "port": 50051,
        "peers": [{"host": "node-b", "port": 50052}],
        "timeout_sec_heartbeat": 15,
        "intervalle_sec_heartbeat": 5,
    }
    registre = PeerRegistry()
    serveur = ServeurFactice()

    def interrompre_cycle(_):
        raise KeyboardInterrupt

    monkeypatch.setattr(main_module, "charger_configuration", lambda: config)
    monkeypatch.setattr(main_module, "PeerRegistry", lambda: registre)
    monkeypatch.setattr(
        main_module, "Event", lambda: EvenementFactice(interrompre_cycle)
    )
    monkeypatch.setattr(
        main_module, "start_grpc_server", lambda node_id, port: serveur
    )

    def envoyer(*args):
        if erreur is not None:
            raise erreur
        return resultat

    monkeypatch.setattr(main_module, "envoyer_heartbeat", envoyer)

    main_module.main()

    pair = registre.get_peer("node-b", 50052)
    assert pair.status == statut_attendu
    assert pair.node_id == node_id_attendu
    assert pair.consecutive_failures == (0 if statut_attendu == "online" else 1)
    assert serveur.arret_demande


@pytest.mark.parametrize(
    "reponses, transition_attendue, raison_attendue",
    [
        ([("node-b", True)] * 2, "unknown -> online", None),
        (
            [("node-b", False)] * 2,
            "unknown -> suspect",
            "Le pair se déclare indisponible",
        ),
        (
            [ErreurHeartbeat("timeout"), ErreurHeartbeat("timeout")],
            "unknown -> suspect",
            "timeout",
        ),
    ],
)
def test_main_journalise_une_seule_fois_une_transition_inchangee(
    monkeypatch, caplog, reponses, transition_attendue, raison_attendue
):
    caplog.set_level(logging.INFO)
    config = {
        "node_id": "node-a",
        "port": 50051,
        "peers": [{"host": "node-b", "port": 50052}],
        "timeout_sec_heartbeat": 15,
        "intervalle_sec_heartbeat": 5,
    }
    serveur = ServeurFactice()
    reponses = iter(reponses)
    cycles = 0

    def attendre(_):
        nonlocal cycles
        cycles += 1
        if cycles == 2:
            raise KeyboardInterrupt

    monkeypatch.setattr(main_module, "charger_configuration", lambda: config)
    monkeypatch.setattr(main_module, "PeerRegistry", PeerRegistry)
    monkeypatch.setattr(
        main_module, "Event", lambda: EvenementFactice(attendre)
    )
    monkeypatch.setattr(
        main_module, "start_grpc_server", lambda node_id, port: serveur
    )

    def envoyer(*args):
        reponse = next(reponses)
        if isinstance(reponse, grpc.RpcError):
            raise reponse
        return reponse

    monkeypatch.setattr(main_module, "envoyer_heartbeat", envoyer)

    main_module.main()

    transitions = [
        record.getMessage()
        for record in caplog.records
        if "État de node-b:50052" in record.getMessage()
    ]
    transition = (
        f"[node-a] État de node-b:50052 : {transition_attendue}"
    )
    if raison_attendue:
        transition += f" ({raison_attendue})"
    assert transitions == [
        transition
    ]
    assert serveur.arret_demande


def test_main_envoie_les_heartbeats_en_parallele(monkeypatch):
    pairs = [
        {"host": "node-b", "port": 50052},
        {"host": "node-c", "port": 50053},
    ]
    config = {
        "node_id": "node-a",
        "port": 50051,
        "peers": pairs,
        "timeout_sec_heartbeat": 15,
        "intervalle_sec_heartbeat": 5,
    }
    registre = PeerRegistry()
    serveur = ServeurFactice()
    barriere = Barrier(len(pairs))

    def interrompre_cycle(_):
        raise KeyboardInterrupt

    monkeypatch.setattr(main_module, "charger_configuration", lambda: config)
    monkeypatch.setattr(main_module, "PeerRegistry", lambda: registre)
    monkeypatch.setattr(
        main_module, "Event", lambda: EvenementFactice(interrompre_cycle)
    )
    monkeypatch.setattr(
        main_module, "start_grpc_server", lambda node_id, port: serveur
    )

    def envoyer(node_id, host, port, timeout):
        barriere.wait(timeout=2)
        return host, True

    monkeypatch.setattr(main_module, "envoyer_heartbeat", envoyer)

    main_module.main()

    assert {
        (peer.host, peer.port, peer.node_id, peer.status)
        for peer in registre.get_all_peers()
    } == {
        ("node-b", 50052, "node-b", "online"),
        ("node-c", 50053, "node-c", "online"),
    }
    assert serveur.arret_demande


def test_exception_inattendue_sur_un_pair_n_interrompt_pas_les_autres(
    monkeypatch, caplog
):
    caplog.set_level(logging.ERROR)
    pairs = [
        {"host": "node-b", "port": 50052},
        {"host": "node-c", "port": 50053},
    ]
    config = {
        "node_id": "node-a",
        "port": 50051,
        "peers": pairs,
        "timeout_sec_heartbeat": 3,
        "intervalle_sec_heartbeat": 5,
    }
    registre = PeerRegistry()
    serveur = ServeurFactice()

    def interrompre_cycle(_):
        raise KeyboardInterrupt

    monkeypatch.setattr(main_module, "charger_configuration", lambda: config)
    monkeypatch.setattr(main_module, "PeerRegistry", lambda: registre)
    monkeypatch.setattr(
        main_module, "Event", lambda: EvenementFactice(interrompre_cycle)
    )
    monkeypatch.setattr(
        main_module, "start_grpc_server", lambda node_id, port: serveur
    )

    def envoyer(node_id, host, port, timeout):
        if host == "node-b":
            raise RuntimeError("erreur inattendue")
        return "node-c", True

    monkeypatch.setattr(main_module, "envoyer_heartbeat", envoyer)

    main_module.main()

    assert registre.get_peer("node-b", 50052).status == "unknown"
    assert registre.get_peer("node-c", 50053).status == "online"
    assert any(
        "Erreur inattendue pendant le heartbeat vers node-b:50052"
        in record.getMessage()
        and record.exc_info is not None
        for record in caplog.records
    )
    assert serveur.arret_demande


def test_main_arrete_proprement_sur_sigterm(monkeypatch):
    config = {
        "node_id": "node-a",
        "port": 50051,
        "peers": [],
        "timeout_sec_heartbeat": 15,
        "intervalle_sec_heartbeat": 5,
    }
    serveur = ServeurFactice()
    gestionnaires_installes = {}

    def installer_signal(signe, gestionnaire):
        gestionnaires_installes[signe] = gestionnaire
        return None

    def attendre(_):
        gestionnaires_installes[main_module.signal.SIGTERM](
            main_module.signal.SIGTERM,
            None,
        )

    evenement = EvenementFactice(attendre)
    monkeypatch.setattr(main_module, "charger_configuration", lambda: config)
    monkeypatch.setattr(
        main_module, "Event", lambda: evenement
    )
    monkeypatch.setattr(
        main_module, "start_grpc_server", lambda node_id, port: serveur
    )
    monkeypatch.setattr(main_module.signal, "signal", installer_signal)

    main_module.main()

    assert evenement.arret_demande
    assert serveur.arret_demande
