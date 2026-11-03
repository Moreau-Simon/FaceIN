"""Tests de l'intégration du registre avec les heartbeats de main.py."""

import logging
from threading import Barrier
from types import SimpleNamespace

import grpc
import pytest

import main as main_module
from network.peers import PeerRegistry


class ErreurHeartbeat(grpc.RpcError):
    pass


class ErreurHeartbeatDetaillee(grpc.RpcError):
    def code(self):
        return grpc.StatusCode.UNAVAILABLE

    def details(self):
        return "Connexion refusée"

    def __str__(self):
        return "détails techniques complets de l'erreur"


class ServeurFactice:
    def __init__(self):
        self.arret_demande = False
        self.delai_arret = None

    def stop(self, grace):
        self.arret_demande = True
        self.delai_arret = grace
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
        "seuil_majorite": 2,
        "timeout_ms_consensus": 1500,
    }
    registre = PeerRegistry()
    serveur = ServeurFactice()
    dependances_serveur = {}

    def demarrer_serveur(
        node_id, port, verifier, nonces, decider_fn, fabriquer_token
    ):
        decision = decider_fn(
            SimpleNamespace(
                id_demande="requete-123",
                utilisateur_id="user-1",
                preuve_zkp=b"preuve",
                nonce="nonce-123",
                service_cible="service-1",
            )
        )
        dependances_serveur.update(
            verifier=verifier,
            nonces=nonces,
            decider_fn=decider_fn,
            fabriquer_token=fabriquer_token,
            decision=decision,
        )
        return serveur

    def interrompre_cycle(_):
        raise KeyboardInterrupt

    monkeypatch.setattr(main_module, "charger_configuration", lambda: config)
    monkeypatch.setattr(main_module, "PeerRegistry", lambda: registre)
    monkeypatch.setattr(
        main_module, "Event", lambda: EvenementFactice(interrompre_cycle)
    )
    monkeypatch.setattr(main_module, "start_grpc_server", demarrer_serveur)

    verificateur_factice = lambda *args: True
    monkeypatch.setattr(
        main_module, "VerificateurZKP", lambda store: verificateur_factice
    )

    appels_vote = []

    def demander_vote(host, port, demande, timeout_sec):
        appels_vote.append((host, port, demande.id_demande, timeout_sec))
        return "node-b", True

    monkeypatch.setattr(main_module, "demander_vote", demander_vote)

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
    assert dependances_serveur["verifier"] is verificateur_factice
    assert isinstance(dependances_serveur["nonces"], main_module.NonceStore)
    assert callable(dependances_serveur["decider_fn"])
    assert callable(dependances_serveur["fabriquer_token"])

    assert dependances_serveur["decision"] is True
    assert len(appels_vote) == 1
    host, port, id_demande, timeout_s = appels_vote[0]
    assert (host, port, id_demande) == ("node-b", 50052, "requete-123")
    assert 0 < timeout_s <= 1.5
    assert serveur.arret_demande


def test_main_garde_une_raison_courte_et_journalise_les_details_grpc(
    monkeypatch, caplog
):
    caplog.set_level(logging.DEBUG)
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

    def envoyer(*args):
        raise ErreurHeartbeatDetaillee()

    monkeypatch.setattr(main_module, "charger_configuration", lambda: config)
    monkeypatch.setattr(main_module, "PeerRegistry", lambda: registre)
    monkeypatch.setattr(
        main_module, "Event", lambda: EvenementFactice(interrompre_cycle)
    )
    monkeypatch.setattr(
        main_module,
        "start_grpc_server",
        lambda node_id, port, verifier, nonces, decider_fn, fabriquer_token:
            serveur,
    )
    monkeypatch.setattr(main_module, "envoyer_heartbeat", envoyer)

    main_module.main()

    pair = registre.get_peer("node-b", 50052)
    assert pair.last_error == "UNAVAILABLE: Connexion refusée"
    assert any(
        "code=UNAVAILABLE" in record.getMessage()
        and "détails=Connexion refusée" in record.getMessage()
        and "détails techniques complets de l'erreur"
        in record.getMessage()
        and record.exc_info is not None
        for record in caplog.records
    )
    assert serveur.arret_demande


def test_main_signale_une_erreur_de_configuration(monkeypatch, caplog):
    def charger_configuration_invalide():
        raise main_module.ErreurConfiguration("NODE_ID manquant")

    monkeypatch.setattr(
        main_module, "charger_configuration", charger_configuration_invalide
    )

    with pytest.raises(SystemExit) as erreur:
        main_module.main()

    assert erreur.value.code == 1
    assert "Configuration invalide : NODE_ID manquant" in caplog.text


def test_main_signale_distinctement_un_echec_de_demarrage_serveur(
    monkeypatch, caplog
):
    config = {
        "node_id": "node-a",
        "port": 50051,
        "peers": [],
        "timeout_sec_heartbeat": 15,
        "intervalle_sec_heartbeat": 5,
    }

    def demarrer_serveur_en_echec(*args):
        raise main_module.ErreurDemarrageServeur(
            "[node-a] Impossible d'ouvrir le port gRPC 50051"
        )

    monkeypatch.setattr(main_module, "charger_configuration", lambda: config)
    monkeypatch.setattr(
        main_module, "start_grpc_server", demarrer_serveur_en_echec
    )

    with pytest.raises(SystemExit) as erreur:
        main_module.main()

    assert erreur.value.code == 1
    assert "Échec du démarrage du serveur gRPC" in caplog.text
    assert "Configuration invalide" not in caplog.text


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
        main_module,
        "start_grpc_server",
        lambda node_id, port, verifier, nonces, decider_fn, fabriquer_token:
            serveur,
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
        main_module,
        "start_grpc_server",
        lambda node_id, port, verifier, nonces, decider_fn, fabriquer_token:
            serveur,
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

    cycles = 0

    def interrompre_apres_trois_cycles(_):
        nonlocal cycles
        cycles += 1
        if cycles == 3:
            raise KeyboardInterrupt

    def envoyer(node_id, host, port, timeout):
        if host == "node-b":
            raise RuntimeError("erreur inattendue")
        return "node-c", True

    monkeypatch.setattr(main_module, "charger_configuration", lambda: config)
    monkeypatch.setattr(main_module, "PeerRegistry", lambda: registre)
    monkeypatch.setattr(
        main_module,
        "Event",
        lambda: EvenementFactice(interrompre_apres_trois_cycles),
    )
    monkeypatch.setattr(
        main_module,
        "start_grpc_server",
        lambda node_id, port, verifier, nonces, decider_fn, fabriquer_token:
            serveur,
    )
    monkeypatch.setattr(main_module, "envoyer_heartbeat", envoyer)

    main_module.main()

    pair_en_erreur = registre.get_peer("node-b", 50052)
    assert pair_en_erreur.status == "unknown"
    assert pair_en_erreur.consecutive_failures == 0
    assert pair_en_erreur.last_error is None
    assert registre.get_peer("node-c", 50053).status == "online"
    erreurs = [
        record
        for record in caplog.records
        if "Erreur inattendue pendant l'appel battement de"
        in record.getMessage()
    ]
    assert len(erreurs) == 3
    assert all(record.exc_info is not None for record in erreurs)
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
        main_module,
        "start_grpc_server",
        lambda node_id, port, verifier, nonces, decider_fn, fabriquer_token:
            serveur,
    )
    monkeypatch.setattr(main_module.signal, "signal", installer_signal)

    main_module.main()

    assert evenement.arret_demande
    assert serveur.arret_demande
    assert serveur.delai_arret == main_module.GRACEFUL_SHUTDOWN_SECONDS
