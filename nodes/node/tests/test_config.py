"""Tests de config.py : chargement et validation de la configuration.

Chaque test utilise un YAML temporaire (CONFIG_PATH) et des variables
d'environnement isolées par `monkeypatch` : aucun test ne dépend du vrai
fichier noeuds.yaml ni de l'environnement de la machine, et rien ne fuit
d'un test à l'autre.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import charger_configuration  # noqa: E402


YAML_VALIDE = """\
consensus:
  seuil_majorite: 2
  timeout_ms: 1500
sync_merkle:
  intervalle_secondes: 10
"""

YAML_SANS_SEUIL = """\
consensus:
  timeout_ms: 1500
sync_merkle:
  intervalle_secondes: 10
"""


# ---------------------------------------------------------------------------
# Outils
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def env_propre(monkeypatch):
    """Retire les variables de configuration avant chaque test."""
    for nom in ("NODE_ID", "NODE_PORT", "PEERS", "CONFIG_PATH"):
        monkeypatch.delenv(nom, raising=False)


@pytest.fixture
def ecrire_yaml(tmp_path, monkeypatch):
    """Écrit un YAML temporaire et le désigne via CONFIG_PATH."""
    def _ecrire(contenu: str):
        fichier = tmp_path / "noeuds.yaml"
        fichier.write_text(contenu, encoding="utf-8")
        monkeypatch.setenv("CONFIG_PATH", str(fichier))
        return fichier
    return _ecrire


@pytest.fixture
def noeud_a(monkeypatch, ecrire_yaml):
    """Configuration valide de node-a avec ses deux pairs."""
    ecrire_yaml(YAML_VALIDE)
    monkeypatch.setenv("NODE_ID", "node-a")
    monkeypatch.setenv("NODE_PORT", "50051")
    monkeypatch.setenv("PEERS", "node-b:50052,node-c:50053")


# ---------------------------------------------------------------------------
# Cas nominaux
# ---------------------------------------------------------------------------

def test_configuration_valide(noeud_a):
    config = charger_configuration()

    assert config["node_id"] == "node-a"
    assert config["port"] == 50051
    assert config["peers"] == [
        {"host": "node-b", "port": 50052},
        {"host": "node-c", "port": 50053},
    ]
    assert config["seuil_majorite"] == 2
    assert config["timeout_ms_consensus"] == 1500
    assert config["intervalle_sec_merkle"] == 10


def test_port_par_defaut(noeud_a, monkeypatch):
    monkeypatch.delenv("NODE_PORT")

    assert charger_configuration()["port"] == 50051


def test_espaces_dans_peers_ignores(noeud_a, monkeypatch):
    monkeypatch.setenv("PEERS", " node-b:50052 , node-c:50053 ,")

    assert len(charger_configuration()["peers"]) == 2


def test_noeud_seul_sans_pairs(ecrire_yaml, monkeypatch):
    ecrire_yaml(YAML_SANS_SEUIL)
    monkeypatch.setenv("NODE_ID", "node-a")

    config = charger_configuration()

    assert config["peers"] == []
    assert config["seuil_majorite"] == 1


def test_localhost_sur_un_autre_port_est_un_pair_valide(
    ecrire_yaml, monkeypatch
):
    ecrire_yaml(YAML_SANS_SEUIL)
    monkeypatch.setenv("NODE_ID", "node-a")
    monkeypatch.setenv("NODE_PORT", "50061")
    monkeypatch.setenv("PEERS", "localhost:50062")

    assert charger_configuration()["peers"] == [
        {"host": "localhost", "port": 50062}
    ]


# ---------------------------------------------------------------------------
# Seuil de majorité
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "nb_pairs, seuil_attendu",
    [(0, 1), (1, 2), (2, 2), (3, 3), (4, 3)],
)
def test_seuil_automatique_est_la_majorite_stricte(
    ecrire_yaml, monkeypatch, nb_pairs, seuil_attendu
):
    ecrire_yaml(YAML_SANS_SEUIL)
    monkeypatch.setenv("NODE_ID", "node-a")
    pairs = ",".join(f"node-{i}:{50100 + i}" for i in range(nb_pairs))
    monkeypatch.setenv("PEERS", pairs)

    assert charger_configuration()["seuil_majorite"] == seuil_attendu


def test_seuil_explicite_trop_bas_pour_4_noeuds(noeud_a, monkeypatch):
    # YAML : seuil 2, mais 4 nœuds => il faut au moins 3.
    monkeypatch.setenv("PEERS", "node-b:50052,node-c:50053,node-d:50054")

    with pytest.raises(RuntimeError, match="incohérent"):
        charger_configuration()


def test_seuil_explicite_superieur_au_nombre_de_noeuds(
    ecrire_yaml, monkeypatch
):
    ecrire_yaml(YAML_VALIDE.replace("seuil_majorite: 2", "seuil_majorite: 9"))
    monkeypatch.setenv("NODE_ID", "node-a")
    monkeypatch.setenv("PEERS", "node-b:50052,node-c:50053")

    with pytest.raises(RuntimeError, match="incohérent"):
        charger_configuration()


# ---------------------------------------------------------------------------
# Variables d'environnement invalides
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("valeur", ["", "   "])
def test_node_id_vide(noeud_a, monkeypatch, valeur):
    monkeypatch.setenv("NODE_ID", valeur)

    with pytest.raises(RuntimeError, match="NODE_ID manquant"):
        charger_configuration()


def test_node_id_absent(noeud_a, monkeypatch):
    monkeypatch.delenv("NODE_ID")

    with pytest.raises(RuntimeError, match="NODE_ID manquant"):
        charger_configuration()


def test_node_port_non_numerique(noeud_a, monkeypatch):
    monkeypatch.setenv("NODE_PORT", "abc")

    with pytest.raises(RuntimeError, match="NODE_PORT invalide"):
        charger_configuration()


@pytest.mark.parametrize("port", ["0", "65536", "-1"])
def test_node_port_hors_limites(noeud_a, monkeypatch, port):
    monkeypatch.setenv("NODE_PORT", port)

    with pytest.raises(RuntimeError, match="hors limites"):
        charger_configuration()


# ---------------------------------------------------------------------------
# Pairs invalides
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "peers, message",
    [
        ("node-b", "Format de pair invalide"),
        ("node-b:50052:1", "Format de pair invalide"),
        (":50052", "Nom d'hôte vide"),
        ("node-b:abc", "Port invalide"),
        ("node-b:99999", "hors limites"),
        ("node-b:0", "hors limites"),
    ],
)
def test_pair_invalide(noeud_a, monkeypatch, peers, message):
    monkeypatch.setenv("PEERS", peers)

    with pytest.raises(RuntimeError, match=message):
        charger_configuration()


def test_pair_duplique_insensible_a_la_casse(noeud_a, monkeypatch):
    monkeypatch.setenv("PEERS", "node-b:50052,NODE-B:50052")

    with pytest.raises(RuntimeError, match="dupliqué"):
        charger_configuration()


def test_noeud_liste_dans_ses_propres_pairs(noeud_a, monkeypatch):
    monkeypatch.setenv("PEERS", "node-a:50051,node-b:50052")

    with pytest.raises(RuntimeError, match="propres pairs"):
        charger_configuration()


def test_localhost_sur_son_propre_port_refuse(ecrire_yaml, monkeypatch):
    ecrire_yaml(YAML_SANS_SEUIL)
    monkeypatch.setenv("NODE_ID", "node-a")
    monkeypatch.setenv("NODE_PORT", "50061")
    monkeypatch.setenv("PEERS", "localhost:50061")

    with pytest.raises(RuntimeError, match="propres pairs"):
        charger_configuration()


# ---------------------------------------------------------------------------
# Fichier YAML invalide
# ---------------------------------------------------------------------------

def test_config_path_inexistant(monkeypatch):
    monkeypatch.setenv("CONFIG_PATH", "/chemin/qui/n/existe/pas.yaml")
    monkeypatch.setenv("NODE_ID", "node-a")

    with pytest.raises(RuntimeError, match="introuvable") as erreur:
        charger_configuration()

    # Le message doit citer le chemin essayé.
    assert "/chemin/qui/n/existe/pas.yaml" in str(erreur.value)


def test_yaml_syntaxe_invalide(ecrire_yaml, monkeypatch):
    ecrire_yaml("consensus: [ceci n'est pas fermé")
    monkeypatch.setenv("NODE_ID", "node-a")

    with pytest.raises(RuntimeError, match="YAML invalide"):
        charger_configuration()


@pytest.mark.parametrize("contenu", ["", "- une\n- liste\n", "juste du texte"])
def test_yaml_vide_ou_pas_un_dictionnaire(ecrire_yaml, monkeypatch, contenu):
    ecrire_yaml(contenu)
    monkeypatch.setenv("NODE_ID", "node-a")

    with pytest.raises(RuntimeError, match="vide ou invalide"):
        charger_configuration()


def test_section_consensus_absente(ecrire_yaml, monkeypatch):
    ecrire_yaml("sync_merkle:\n  intervalle_secondes: 10\n")
    monkeypatch.setenv("NODE_ID", "node-a")

    with pytest.raises(RuntimeError, match="'consensus'"):
        charger_configuration()


def test_section_sync_merkle_absente(ecrire_yaml, monkeypatch):
    ecrire_yaml("consensus:\n  timeout_ms: 1500\n")
    monkeypatch.setenv("NODE_ID", "node-a")

    with pytest.raises(RuntimeError, match="'sync_merkle'"):
        charger_configuration()


@pytest.mark.parametrize(
    "ancien, nouveau",
    [
        ("timeout_ms: 1500", "timeout_ms: 0"),
        ("timeout_ms: 1500", "timeout_ms: -5"),
        ("timeout_ms: 1500", "timeout_ms: 1.5"),
        ("timeout_ms: 1500", "timeout_ms: abc"),
        ("timeout_ms: 1500", "timeout_ms: true"),
        ("intervalle_secondes: 10", "intervalle_secondes: 0"),
        ("seuil_majorite: 2", "seuil_majorite: -1"),
    ],
)
def test_parametre_yaml_invalide(ecrire_yaml, monkeypatch, ancien, nouveau):
    ecrire_yaml(YAML_VALIDE.replace(ancien, nouveau))
    monkeypatch.setenv("NODE_ID", "node-a")

    with pytest.raises(RuntimeError, match="invalide"):
        charger_configuration()


def test_parametre_obligatoire_manquant(ecrire_yaml, monkeypatch):
    ecrire_yaml(
        "consensus:\n  seuil_majorite: 2\n"
        "sync_merkle:\n  intervalle_secondes: 10\n"
    )
    monkeypatch.setenv("NODE_ID", "node-a")

    with pytest.raises(RuntimeError, match="timeout_ms"):
        charger_configuration()


# ---------------------------------------------------------------------------
# Le vrai fichier partagé du dépôt
# ---------------------------------------------------------------------------

def test_le_vrai_noeuds_yaml_du_depot_est_valide(monkeypatch):
    """Garde-fou : un YAML cassé par un commit fait échouer la CI.

    Sans CONFIG_PATH, config.py retombe sur nodes/shared/config/noeuds.yaml.
    """
    monkeypatch.setenv("NODE_ID", "node-a")
    monkeypatch.setenv("PEERS", "node-b:50052,node-c:50053")

    config = charger_configuration()

    assert config["seuil_majorite"] >= 2
    assert config["timeout_ms_consensus"] > 0
    assert config["intervalle_sec_merkle"] > 0