"""Tests des ajouts à network/peers.py : clé de pair, seuil du registre,
transitions retournées, pairs non hors ligne, validation stricte des types."""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from network.peers import PeerRegistry, cle_pair  # noqa: E402


@pytest.fixture
def registre():
    reg = PeerRegistry()
    reg.register_peer("node-a", "localhost", 50051)
    return reg


# ---------------------------------------------------------------------------
# cle_pair
# ---------------------------------------------------------------------------

def test_cle_pair_normalise_la_casse_et_les_espaces():
    assert cle_pair(" Node-B ", 50052) == "node-b:50052"


def test_cle_pair_distingue_les_ports():
    assert cle_pair("node-b", 1) != cle_pair("node-b", 2)


# ---------------------------------------------------------------------------
# Seuil porté par le registre
# ---------------------------------------------------------------------------

def test_seuil_par_defaut_du_registre_est_trois():
    reg = PeerRegistry()
    reg.register_peer("node-a", "localhost", 50051)

    for _ in range(2):
        reg.record_failure("node-a", "timeout")
    assert reg.get_peer("node-a").status == "suspect"

    reg.record_failure("node-a", "timeout")
    assert reg.get_peer("node-a").status == "offline"


def test_le_seuil_ne_peut_plus_etre_change_a_chaque_appel(registre):
    with pytest.raises(TypeError):
        registre.record_failure("node-a", "x", failures_before_offline=1)


# ---------------------------------------------------------------------------
# Validation stricte des types
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("seuil", [True, False, 2.5, "3", None])
def test_seuil_de_type_invalide_est_refuse(seuil):
    with pytest.raises(TypeError, match="entier"):
        PeerRegistry(failures_before_offline=seuil)


@pytest.mark.parametrize("port", [True, 50051.5, "50051", None])
def test_port_de_type_invalide_est_refuse(port):
    with pytest.raises(TypeError, match="entier"):
        PeerRegistry().register_peer("node-a", "localhost", port)


# ---------------------------------------------------------------------------
# Transitions retournées
# ---------------------------------------------------------------------------

def test_record_failure_retourne_ancien_et_nouveau_statut():
    reg = PeerRegistry(failures_before_offline=2)
    reg.register_peer("node-a", "localhost", 50051)

    assert reg.record_failure("node-a", "x") == ("unknown", "suspect")
    assert reg.record_failure("node-a", "x") == ("suspect", "offline")
    assert reg.record_failure("node-a", "x") == ("offline", "offline")


def test_record_heartbeat_retourne_ancien_et_nouveau_statut(registre):
    assert registre.record_heartbeat("node-a") == ("unknown", "online")
    assert registre.record_heartbeat("node-a") == ("online", "online")


def test_retour_apres_panne_est_signale(registre):
    for _ in range(3):
        registre.record_failure("node-a", "x")

    assert registre.record_heartbeat("node-a") == ("offline", "online")


# ---------------------------------------------------------------------------
# Pairs non hors ligne
# ---------------------------------------------------------------------------

def test_pairs_non_hors_ligne_excluent_uniquement_les_offline():
    reg = PeerRegistry(failures_before_offline=2)
    for nom, port in (("u", 1), ("o", 2), ("s", 3), ("x", 4)):
        reg.register_peer(nom, "localhost", port)

    reg.record_heartbeat("o")              # online
    reg.record_failure("s", "e")           # suspect
    reg.record_failure("x", "e")
    reg.record_failure("x", "e")           # offline

    retenus = {p.node_id for p in reg.get_non_offline_peers()}

    assert retenus == {"u", "o", "s"}


def test_un_pair_hors_ligne_reste_dans_get_all_peers():
    """Le heartbeat doit continuer à sonder un pair hors ligne, sinon son
    retour ne serait jamais détecté."""
    reg = PeerRegistry(failures_before_offline=1)
    reg.register_peer("node-a", "localhost", 50051)
    reg.record_failure("node-a", "x")

    assert reg.get_non_offline_peers() == []
    assert [p.node_id for p in reg.get_all_peers()] == ["node-a"]


def test_pairs_non_hors_ligne_retourne_des_copies(registre):
    registre.get_non_offline_peers()[0].status = "offline"

    assert registre.get_peer("node-a").status == "unknown"