"""
Test de base : vérifie que la configuration se charge correctement
depuis les variables d'environnement (NODE_ID, NODE_PORT, PEERS).
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from main import charger_configuration  # noqa: E402


def test_charger_configuration_basique():
    os.environ["NODE_ID"] = "node-test"
    os.environ["NODE_PORT"] = "50099"
    os.environ["PEERS"] = "node-a:50051,node-b:50052"

    config = charger_configuration()

    assert config["node_id"] == "node-test"
    assert config["port"] == 50099
    assert len(config["peers"]) == 2
    assert config["peers"][0] == {"host": "node-a", "port": 50051}


def test_node_id_manquant_leve_erreur():
    os.environ.pop("NODE_ID", None)
    try:
        charger_configuration()
        assert False, "Aurait dû lever une RuntimeError"
    except RuntimeError:
        pass
