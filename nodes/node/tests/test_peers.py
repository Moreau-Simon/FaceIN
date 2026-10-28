"""Tests de network/peers.py : registre et transitions d'état des pairs."""

from concurrent.futures import ThreadPoolExecutor

import pytest

import network.peers as peers_module
from network.peers import PeerInfo, PeerRegistry


@pytest.fixture
def registre():
    return PeerRegistry()


@pytest.fixture
def pair_enregistre(registre):
    registre.register_peer("localhost", 50051)
    return registre


# ---------------------------------------------------------------------------
# Enregistrement des pairs
# ---------------------------------------------------------------------------


def test_registre_vide(registre):
    assert registre.get_all_peers() == []
    assert registre.get_peer("localhost", 50051) is None


def test_enregistrer_pair_initialise_son_etat(registre):
    registre.register_peer("localhost", 50051)

    assert registre.get_peer("localhost", 50051) == PeerInfo(
        node_id=None,
        host="localhost",
        port=50051,
    )


@pytest.mark.parametrize(
    "host, port",
    [
        ("", 50051),
        ("   ", 50051),
        ("localhost", 0),
        ("localhost", -1),
        ("localhost", 65536),
    ],
)
def test_enregistrement_refuse_les_valeurs_invalides(
    registre, host, port
):
    with pytest.raises(ValueError):
        registre.register_peer(host, port)


@pytest.mark.parametrize("port", [1, 65535])
def test_enregistrement_accepte_les_ports_aux_limites(registre, port):
    registre.register_peer("localhost", port)

    assert registre.get_peer("localhost", port).port == port


def test_reenregistrer_le_meme_pair_est_idempotent(pair_enregistre):
    pair_enregistre.record_failure("localhost", 50051, "timeout")

    pair_enregistre.register_peer("LOCALHOST", 50051)

    pair = pair_enregistre.get_peer("localhost", 50051)
    assert pair.status == "suspect"
    assert pair.consecutive_failures == 1
    assert pair.last_error == "timeout"


def test_un_pair_peut_avoir_un_node_id_inconnu_a_l_enregistrement(
    pair_enregistre,
):
    pair = pair_enregistre.get_peer("localhost", 50051)
    assert pair.node_id is None


# ---------------------------------------------------------------------------
# Heartbeat et échecs
# ---------------------------------------------------------------------------


def test_heartbeat_met_le_pair_en_ligne_et_enregistre_l_heure(
    pair_enregistre, monkeypatch
):
    pair_enregistre.record_failure("localhost", 50051, "timeout")
    monkeypatch.setattr(peers_module, "time", lambda: 1234.5)

    pair_enregistre.record_heartbeat("localhost", 50051, "node-a")

    pair = pair_enregistre.get_peer("localhost", 50051)
    assert pair.status == "online"
    assert pair.last_heartbeat == 1234.5
    assert pair.consecutive_failures == 0
    assert pair.last_error is None


def test_un_echec_isole_rend_le_pair_suspect(pair_enregistre):
    pair_enregistre.record_failure("localhost", 50051, "timeout")

    pair = pair_enregistre.get_peer("localhost", 50051)
    assert pair.status == "suspect"
    assert pair.consecutive_failures == 1
    assert pair.last_error == "timeout"
    assert pair.last_heartbeat is None


def test_seuil_par_defaut_met_le_pair_hors_ligne(pair_enregistre):
    for _ in range(3):
        pair_enregistre.record_failure("localhost", 50051, "timeout")

    pair = pair_enregistre.get_peer("localhost", 50051)
    assert pair.status == "offline"
    assert pair.consecutive_failures == 3
    assert pair.last_error == "timeout"


def test_seuil_personnalise_est_applique():
    registre = PeerRegistry(failures_before_offline=2)
    registre.register_peer("localhost", 50051)

    registre.record_failure("localhost", 50051, "connexion refusée")
    assert registre.get_peer("localhost", 50051).status == "suspect"

    registre.record_failure("localhost", 50051, "connexion refusée")
    assert registre.get_peer("localhost", 50051).status == "offline"


@pytest.mark.parametrize("seuil", [0, -1])
def test_seuil_invalide_est_refuse_a_la_creation(seuil):
    with pytest.raises(ValueError, match="doit être positif"):
        PeerRegistry(failures_before_offline=seuil)

def test_heartbeat_retablit_un_pair_hors_ligne(pair_enregistre):
    for _ in range(3):
        pair_enregistre.record_failure("localhost", 50051, "timeout")

    pair_enregistre.record_heartbeat("localhost", 50051, "node-a")

    pair = pair_enregistre.get_peer("localhost", 50051)
    assert pair.status == "online"
    assert pair.consecutive_failures == 0
    assert pair.last_error is None
    assert pair.last_heartbeat is not None


# ---------------------------------------------------------------------------
# Lecture, copies et erreurs pour les pairs inconnus
# ---------------------------------------------------------------------------


def test_get_peer_retourne_une_copie(pair_enregistre):
    copie = pair_enregistre.get_peer("localhost", 50051)
    copie.status = "offline"
    copie.host = "autre-hote"

    pair = pair_enregistre.get_peer("localhost", 50051)
    assert pair.status == "unknown"
    assert pair.host == "localhost"


def test_get_all_peers_retourne_des_copies(pair_enregistre):
    pair_enregistre.register_peer("localhost", 50052)

    copies = pair_enregistre.get_all_peers()
    copies[0].status = "offline"
    copies.clear()

    assert len(pair_enregistre.get_all_peers()) == 2
    assert pair_enregistre.get_peer("localhost", 50051).status == "unknown"


def test_operations_sur_un_pair_inconnu_levent_key_error(registre):
    with pytest.raises(KeyError, match="Pair inconnu"):
        registre.record_heartbeat("localhost", 50051, "node-a")

    with pytest.raises(KeyError, match="Pair inconnu"):
        registre.record_failure("localhost", 50051, "timeout")


def test_echecs_concurrents_sont_comptabilises(pair_enregistre):
    nombre_echecs = 100
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(
            pool.map(
                lambda _: pair_enregistre.record_failure(
                    "localhost", 50051, "timeout"
                ),
                range(nombre_echecs),
            )
        )

    pair = pair_enregistre.get_peer("localhost", 50051)
    assert pair.consecutive_failures == nombre_echecs
    assert pair.status == "offline"