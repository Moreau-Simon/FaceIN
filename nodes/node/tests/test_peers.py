"""Tests de network/peers.py : registre et transitions d'état des pairs."""

import os
import sys
from concurrent.futures import ThreadPoolExecutor

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import network.peers as peers_module  # noqa: E402
from network.peers import PeerInfo, PeerRegistry  # noqa: E402


@pytest.fixture
def registre():
    return PeerRegistry()


@pytest.fixture
def pair_enregistre(registre):
    registre.register_peer("node-a", "localhost", 50051)
    return registre


# ---------------------------------------------------------------------------
# Enregistrement des pairs
# ---------------------------------------------------------------------------


def test_registre_vide(registre):
    assert registre.get_all_peers() == []
    assert registre.get_peer("inconnu") is None


def test_enregistrer_pair_initialise_son_etat(registre):
    registre.register_peer("node-a", "localhost", 50051)

    assert registre.get_peer("node-a") == PeerInfo(
        node_id="node-a",
        host="localhost",
        port=50051,
    )


@pytest.mark.parametrize(
    "node_id, host, port",
    [
        ("", "localhost", 50051),
        ("   ", "localhost", 50051),
        ("node-a", "", 50051),
        ("node-a", "   ", 50051),
        ("node-a", "localhost", 0),
        ("node-a", "localhost", -1),
        ("node-a", "localhost", 65536),
    ],
)
def test_enregistrement_refuse_les_valeurs_invalides(
    registre, node_id, host, port
):
    with pytest.raises(ValueError):
        registre.register_peer(node_id, host, port)


@pytest.mark.parametrize("port", [1, 65535])
def test_enregistrement_accepte_les_ports_aux_limites(registre, port):
    registre.register_peer("node-a", "localhost", port)

    assert registre.get_peer("node-a").port == port


def test_reenregistrer_le_meme_pair_est_idempotent(pair_enregistre):
    pair_enregistre.record_failure("node-a", "timeout")

    pair_enregistre.register_peer("node-a", "localhost", 50051)

    pair = pair_enregistre.get_peer("node-a")
    assert pair.status == "suspect"
    assert pair.consecutive_failures == 1
    assert pair.last_error == "timeout"


def test_reenregistrer_id_avec_une_autre_adresse_est_refuse(pair_enregistre):
    with pytest.raises(ValueError, match="autre adresse"):
        pair_enregistre.register_peer("node-a", "127.0.0.1", 50051)

    with pytest.raises(ValueError, match="autre adresse"):
        pair_enregistre.register_peer("node-a", "localhost", 50052)


# ---------------------------------------------------------------------------
# Heartbeat et échecs
# ---------------------------------------------------------------------------


def test_heartbeat_met_le_pair_en_ligne_et_enregistre_l_heure(
    pair_enregistre, monkeypatch
):
    pair_enregistre.record_failure("node-a", "timeout")
    monkeypatch.setattr(peers_module, "time", lambda: 1234.5)

    pair_enregistre.record_heartbeat("node-a")

    pair = pair_enregistre.get_peer("node-a")
    assert pair.status == "online"
    assert pair.last_heartbeat == 1234.5
    assert pair.consecutive_failures == 0
    assert pair.last_error is None


def test_un_echec_isole_rend_le_pair_suspect(pair_enregistre):
    pair_enregistre.record_failure("node-a", "timeout")

    pair = pair_enregistre.get_peer("node-a")
    assert pair.status == "suspect"
    assert pair.consecutive_failures == 1
    assert pair.last_error == "timeout"
    assert pair.last_heartbeat is None


def test_seuil_par_defaut_met_le_pair_hors_ligne(pair_enregistre):
    for _ in range(3):
        pair_enregistre.record_failure("node-a", "timeout")

    pair = pair_enregistre.get_peer("node-a")
    assert pair.status == "offline"
    assert pair.consecutive_failures == 3
    assert pair.last_error == "timeout"


def test_seuil_personnalise_est_applique(pair_enregistre):
    pair_enregistre.record_failure(
        "node-a", "connexion refusée", failures_before_offline=2
    )
    assert pair_enregistre.get_peer("node-a").status == "suspect"

    pair_enregistre.record_failure(
        "node-a", "connexion refusée", failures_before_offline=2
    )
    assert pair_enregistre.get_peer("node-a").status == "offline"


def test_seuil_d_echec_invalide_est_refuse(pair_enregistre):
    for seuil in (0, -1):
        with pytest.raises(ValueError, match="doit être positif"):
            pair_enregistre.record_failure(
                "node-a", "erreur", failures_before_offline=seuil
            )


def test_heartbeat_retablit_un_pair_hors_ligne(pair_enregistre):
    for _ in range(3):
        pair_enregistre.record_failure("node-a", "timeout")

    pair_enregistre.record_heartbeat("node-a")

    pair = pair_enregistre.get_peer("node-a")
    assert pair.status == "online"
    assert pair.consecutive_failures == 0
    assert pair.last_error is None
    assert pair.last_heartbeat is not None


# ---------------------------------------------------------------------------
# Lecture, copies et erreurs pour les pairs inconnus
# ---------------------------------------------------------------------------


def test_get_peer_retourne_une_copie(pair_enregistre):
    copie = pair_enregistre.get_peer("node-a")
    copie.status = "offline"
    copie.host = "autre-hote"

    pair = pair_enregistre.get_peer("node-a")
    assert pair.status == "unknown"
    assert pair.host == "localhost"


def test_get_all_peers_retourne_des_copies(pair_enregistre):
    pair_enregistre.register_peer("node-b", "localhost", 50052)

    copies = pair_enregistre.get_all_peers()
    copies[0].status = "offline"
    copies.clear()

    assert len(pair_enregistre.get_all_peers()) == 2
    assert pair_enregistre.get_peer("node-a").status == "unknown"


def test_operations_sur_un_pair_inconnu_levent_key_error(registre):
    with pytest.raises(KeyError, match="Pair inconnu"):
        registre.record_heartbeat("inconnu")

    with pytest.raises(KeyError, match="Pair inconnu"):
        registre.record_failure("inconnu", "timeout")


def test_echecs_concurrents_sont_comptabilises(pair_enregistre):
    nombre_echecs = 100
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(
            pool.map(
                lambda _: pair_enregistre.record_failure("node-a", "timeout"),
                range(nombre_echecs),
            )
        )

    pair = pair_enregistre.get_peer("node-a")
    assert pair.consecutive_failures == nombre_echecs
    assert pair.status == "offline"