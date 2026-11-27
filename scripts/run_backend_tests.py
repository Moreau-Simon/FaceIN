"""
Lanceur global des tests Backend FaceIN.

Exécute toutes les suites en une seule commande et affiche un bilan clair :

  1. API Gateway         : api/tests (validation, sécurité anti-mock, concurrence,
                           JWT, nonces, stockage mémoire)
  2. Nœuds               : nodes/node/tests (consensus, réseau, Merkle, révocation)
  3. PostgreSQL réel     : intégration sur une base de TEST (TEST_POSTGRES_URL)
  4. Cryptographie ZKP   : preuves Groth16 réelles (artefacts de
                           scripts/generate_test_zkp_artifacts.sh) et cohérence des clés

Chaque suite tourne dans un processus séparé : api/main.py et nodes/node/main.py
portent le même nom de module et ne peuvent pas être importés dans le même processus.

Aucune simulation positive n'est activée par ce lanceur : il force
MOCK_ZKP_VERIFICATION=false et ne définit aucune variable de simulation de consensus.

Usage :
    python scripts/run_backend_tests.py            # toutes les suites disponibles
    python scripts/run_backend_tests.py --strict   # une suite non exécutable = échec (CI)

Prérequis :
    pip install -r api/requirements.txt -r nodes/node/requirements-dev.txt
    (cd circuits && npm ci)                      # snarkjs, pour les tests Groth16
    bash scripts/generate_test_zkp_artifacts.sh  # nécessite circom 2.x
    TEST_POSTGRES_URL=postgresql://...           # base PostgreSQL de TEST uniquement
"""

import argparse
import glob
import os
import shutil
import subprocess
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
API_DIR = os.path.join(ROOT_DIR, "api")
NODES_DIR = os.path.join(ROOT_DIR, "nodes", "node")
PROTO_DIR = os.path.join(ROOT_DIR, "nodes", "shared", "proto")
ZKP_DIR = os.getenv("FACEIN_TEST_ZKP_DIR", os.path.join(ROOT_DIR, "circuits", "build", "test-zkp"))
SNARKJS_BIN = os.path.join(ROOT_DIR, "circuits", "node_modules", ".bin")

REUSSI, ECHOUE, NON_EXECUTE = "RÉUSSI", "ÉCHOUÉ", "NON EXÉCUTÉ"


def _env_de_test(extra=None):
    env = dict(os.environ)
    env["MOCK_ZKP_VERIFICATION"] = "false"
    env.pop("ALLOW_MOCK_CONSENSUS", None)
    env.setdefault("STORE_BACKEND", "memory")
    env.setdefault("FACEIN_ENV", "test")
    if os.path.isdir(SNARKJS_BIN):
        env["PATH"] = SNARKJS_BIN + os.pathsep + env.get("PATH", "")
    if extra:
        env.update(extra)
    return env


def compiler_protos() -> bool:
    """Compile les .proto (fichiers générés ignorés par Git). Retourne False en cas d'échec."""
    protos = sorted(glob.glob(os.path.join(PROTO_DIR, "*.proto")))
    cibles = [
        (NODES_DIR, protos),
        (API_DIR, [os.path.join(PROTO_DIR, "verification.proto")]),
    ]
    for sortie, fichiers in cibles:
        cmd = [
            sys.executable, "-m", "grpc_tools.protoc", "-I", PROTO_DIR,
            f"--python_out={sortie}", f"--grpc_python_out={sortie}", *fichiers,
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if res.returncode != 0:
            print("[ERREUR] Compilation des fichiers .proto impossible :")
            print(res.stderr.strip())
            return False
    return True


def lancer_pytest(nom, chemins, env, extra_args=None):
    print(f"\n{'=' * 78}\n{nom}\n{'=' * 78}", flush=True)
    cmd = [sys.executable, "-m", "pytest", *chemins, "-q", "-rfEs", "-p", "no:cacheprovider"]
    cmd += extra_args or []
    res = subprocess.run(cmd, cwd=ROOT_DIR, env=env, check=False)
    # Code 5 = aucun test collecté : jamais considéré comme un succès
    return REUSSI if res.returncode == 0 else ECHOUE


def main() -> int:
    parser = argparse.ArgumentParser(description="Tests backend FaceIN")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Considérer une suite non exécutable (PostgreSQL, Groth16) comme un échec",
    )
    args = parser.parse_args()

    bilan = []

    if not compiler_protos():
        bilan.append(("Compilation .proto", ECHOUE, "grpcio-tools requis"))
        return afficher_bilan(bilan, args.strict)

    env_api = _env_de_test()
    env_api.pop("TEST_POSTGRES_URL", None)  # intégration PostgreSQL : suite dédiée
    bilan.append((
        "API Gateway (api/tests)",
        lancer_pytest(
            "API Gateway",
            ["api/tests", "--ignore=api/tests/test_zkp_crypto.py"],
            env_api,
        ),
        "",
    ))

    bilan.append((
        "Nœuds (nodes/node/tests)",
        lancer_pytest(
            "Nœuds de vérification",
            ["nodes/node/tests"],
            _env_de_test({"PYTHONPATH": NODES_DIR}),
        ),
        "",
    ))

    url_pg = os.getenv("TEST_POSTGRES_URL")
    if url_pg:
        bilan.append((
            "PostgreSQL réel",
            lancer_pytest(
                "Intégration PostgreSQL (base de test)",
                ["api/tests/test_store_postgres.py"],
                _env_de_test({"STORE_BACKEND": "postgres"}),
                ["-k", "Integration"],
            ),
            "",
        ))
    else:
        bilan.append(("PostgreSQL réel", NON_EXECUTE, "TEST_POSTGRES_URL non définie"))

    artefacts = os.path.isfile(os.path.join(ZKP_DIR, "vk_a.json"))
    snarkjs = shutil.which("snarkjs", path=_env_de_test()["PATH"]) is not None
    statut_zkp = lancer_pytest(
        "Cryptographie ZKP (Groth16)",
        ["api/tests/test_zkp_crypto.py"],
        _env_de_test({"FACEIN_REQUIRE_REAL_ZKP": "1"} if strict_global(args) else None),
    )
    if artefacts and snarkjs:
        bilan.append(("Cryptographie ZKP", statut_zkp, "preuves Groth16 réelles"))
    else:
        raison = "snarkjs absent" if not snarkjs else "lancer scripts/generate_test_zkp_artifacts.sh"
        bilan.append(("Cryptographie ZKP", statut_zkp, "erreurs d'exécution uniquement"))
        bilan.append(("Preuves Groth16 réelles", NON_EXECUTE, raison))

    return afficher_bilan(bilan, args.strict)


def strict_global(args) -> bool:
    return bool(getattr(args, "strict", False))


def afficher_bilan(bilan, strict) -> int:
    print(f"\n{'=' * 78}\nBILAN DES TESTS BACKEND FACEIN\n{'=' * 78}")
    for nom, statut, detail in bilan:
        suffixe = f"  ({detail})" if detail else ""
        print(f"  {statut:<12} {nom}{suffixe}")
    echecs = [b for b in bilan if b[1] == ECHOUE]
    non_executes = [b for b in bilan if b[1] == NON_EXECUTE]
    print("=" * 78)
    if echecs:
        print(f"ÉTAT : ÉCHEC ({len(echecs)} suite(s) en échec)")
        return 1
    if non_executes and strict:
        print(f"ÉTAT : INCOMPLET ({len(non_executes)} suite(s) non exécutée(s), mode --strict)")
        return 1
    if non_executes:
        print(f"ÉTAT : RÉUSSI, mais {len(non_executes)} suite(s) non exécutée(s)")
        return 0
    print("ÉTAT : RÉUSSI (toutes les suites exécutées)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
