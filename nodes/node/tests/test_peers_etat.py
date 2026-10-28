"""Tests des ajouts à network/peers.py : clé de pair, seuil du registre,
transitions retournées, pairs non hors ligne, validation stricte des types."""

import pytest

from network.peers import PeerRegistry, cle_pair


@pytest.fixture
def registre():
    reg = PeerRegistry()
    reg.register_peer("localhost", 50051)
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
    reg.register_peer("localhost", 50051)

    for _ in range(2):
        reg.record_failure("localhost", 50051, "timeout")
    assert reg.get_peer("localhost", 50051).status == "suspect"

    reg.record_failure("localhost", 50051, "timeout")
    assert reg.get_peer("localhost", 50051).status == "offline"


def test_le_seuil_ne_peut_plus_etre_change_a_chaque_appel(registre):
    with pytest.raises(TypeError):
        registre.record_failure(
            "localhost", 50051, "x", failures_before_offline=1
        )


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
        PeerRegistry().register_peer("localhost", port)


# ---------------------------------------------------------------------------
# Transitions retournées
# ---------------------------------------------------------------------------

def test_record_failure_retourne_ancien_et_nouveau_statut():
    reg = PeerRegistry(failures_before_offline=2)
    reg.register_peer("localhost", 50051)

    assert reg.record_failure("localhost", 50051, "x") == (
        "unknown",
        "suspect",
    )
    assert reg.record_failure("localhost", 50051, "x") == (
        "suspect",
        "offline",
    )
    assert reg.record_failure("localhost", 50051, "x") == (
        "offline",
        "offline",
    )


def test_record_heartbeat_retourne_ancien_et_nouveau_statut(registre):
    assert registre.record_heartbeat("localhost", 50051, "node-a") == (
        "unknown",
        "online",
    )
    assert registre.record_heartbeat("localhost", 50051, "node-a") == (
        "online",
        "online",
    )


def test_retour_apres_panne_est_signale(registre):
    for _ in range(3):
        registre.record_failure("localhost", 50051, "x")

    assert registre.record_heartbeat("localhost", 50051, "node-a") == (
        "offline",
        "online",
    )


def test_identite_est_associee_apres_heartbeat(registre):
    pair = registre.get_peer("localhost", 50051)
    assert pair.node_id is None

    registre.record_heartbeat("localhost", 50051, "node-a")

    assert registre.get_peer("LOCALHOST", 50051).node_id == "node-a"


def test_identite_differente_pour_la_meme_adresse_est_refusee(registre):
    registre.record_heartbeat("localhost", 50051, "node-a")

    with pytest.raises(ValueError, match="déjà annoncé"):
        registre.record_heartbeat("localhost", 50051, "node-b")


def test_identite_meme_casse_differente_est_acceptee_pour_la_meme_adresse(
    registre,
):
    registre.record_heartbeat("localhost", 50051, "node-a")

    registre.record_heartbeat("localhost", 50051, "Node-A")

    pair = registre.get_peer("localhost", 50051)
    assert pair.node_id == "node-a"
    assert pair.status == "online"


def test_identite_deja_associee_a_une_autre_adresse_est_refusee(registre):
    registre.register_peer("localhost", 50052)
    registre.record_heartbeat("localhost", 50051, "node-a")

    with pytest.raises(ValueError, match="déjà associé"):
        registre.record_heartbeat("localhost", 50052, "node-a")

    with pytest.raises(ValueError, match="déjà associé"):
        registre.record_heartbeat("localhost", 50052, "NODE-A")


def test_identite_vide_est_refusee_sans_changer_le_pair(registre):
    with pytest.raises(ValueError, match="node_id ne peut pas être vide"):
        registre.record_heartbeat("localhost", 50051, " ")

    pair = registre.get_peer("localhost", 50051)
    assert pair.node_id is None
    assert pair.status == "unknown"


# ---------------------------------------------------------------------------
# Pairs non hors ligne
# ---------------------------------------------------------------------------

def test_pairs_non_hors_ligne_excluent_uniquement_les_offline():
    reg = PeerRegistry(failures_before_offline=2)
    for nom, port in (("u", 1), ("o", 2), ("s", 3), ("x", 4)):
        reg.register_peer("localhost", port)

    reg.record_heartbeat("localhost", 2, "o")  # online
    reg.record_failure("localhost", 3, "e")  # suspect
    reg.record_failure("localhost", 4, "e")
    reg.record_failure("localhost", 4, "e")  # offline

    retenus = {cle_pair(p.host, p.port) for p in reg.get_non_offline_peers()}

    assert retenus == {"localhost:1", "localhost:2", "localhost:3"}


def test_un_pair_hors_ligne_reste_dans_get_all_peers():
    """Le heartbeat doit continuer à sonder un pair hors ligne, sinon son
    retour ne serait jamais détecté."""
    reg = PeerRegistry(failures_before_offline=1)
    reg.register_peer("localhost", 50051)
    reg.record_failure("localhost", 50051, "x")

    assert reg.get_non_offline_peers() == []
    assert [(p.host, p.port) for p in reg.get_all_peers()] == [
        ("localhost", 50051)
    ]


def test_pairs_non_hors_ligne_retourne_des_copies(registre):
    registre.get_non_offline_peers()[0].status = "offline"

    assert registre.get_peer("localhost", 50051).status == "unknown"