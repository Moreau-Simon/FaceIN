"""
Test de bout en bout du parcours d'authentification FaceIN sur une stack réelle
(API + 3 nœuds en mTLS + PostgreSQL), sans aucune simulation.

Parcours vérifié :
  1. /api/health : stockage, vérificateur ZKP et quorum disponibles
  2. /api/register : inscription d'un engagement Poseidon
  3. /api/nonce : nonce émis par un nœud + défis de vie
  4. Preuve Groth16 réelle liée au nonce (snarkjs + WASM/zkey du circuit)
  5. /api/authenticate : consensus des nœuds et émission d'un JWT
Puis les refus attendus :
  - même requête rejouée (nonce déjà consommé)
  - ancienne preuve présentée avec un nouveau nonce
  - authentification sans rapport de défis de vie
  - seconde inscription du même identifiant (409)

Le rapport de défis est construit à partir de la réponse de /api/nonce, comme le
ferait un client : c'est la limite documentée de l'architecture B (le serveur
vérifie l'association à la session, pas l'exécution réelle des défis).

Usage :
    python scripts/e2e_authentication.py \\
        --api http://localhost:8000/api \\
        --wasm circuits/build/distance_js/distance.wasm \\
        --zkey circuits/build/distance.zkey

Prérequis : Node.js, snarkjs (circuits/node_modules/.bin) et circomlibjs
(cd circuits && npm ci). Code retour 0 si tout est conforme, 1 sinon.
"""

import argparse
import json
import os
import secrets
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
GENERATEUR = os.path.join(ROOT_DIR, "circuits", "test", "generate_test_input.js")
SNARKJS_LOCAL = os.path.join(ROOT_DIR, "circuits", "node_modules", ".bin")
SEUIL_MAX = os.getenv("DISTANCE_THRESHOLD", "16000000")

echecs = []


def verifier(condition: bool, libelle: str, detail: str = "") -> None:
    print(f"  [{'OK' if condition else 'ÉCHEC'}] {libelle}" + (f" — {detail}" if detail and not condition else ""))
    if not condition:
        echecs.append(libelle)


def appel(methode: str, url: str, corps=None, timeout: float = 30.0):
    """Requête HTTP JSON ; retourne (code HTTP, corps décodé)."""
    donnees = json.dumps(corps).encode("utf-8") if corps is not None else None
    requete = urllib.request.Request(
        url, data=donnees, method=methode, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(requete, timeout=timeout) as reponse:
            return reponse.status, json.loads(reponse.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as erreur:
        try:
            return erreur.code, json.loads(erreur.read().decode("utf-8") or "{}")
        except ValueError:
            return erreur.code, {}


def executer(commande, env=None):
    res = subprocess.run(commande, capture_output=True, text=True, env=env, check=False, timeout=300)
    if res.returncode != 0:
        raise RuntimeError(f"Échec de {' '.join(commande[:3])} : {res.stderr.strip()[-500:]}")
    return res.stdout


def attendre_api(api: str, delai_s: int) -> dict:
    fin = time.time() + delai_s
    dernier = {}
    while time.time() < fin:
        try:
            code, dernier = appel("GET", f"{api}/health", timeout=5)
            if code == 200 and dernier.get("statut") == "en_ligne":
                return dernier
        except (urllib.error.URLError, OSError):
            pass
        time.sleep(3)
    return dernier


def generer_entrees(dossier: str, nonce_hex: str, vecteurs=None) -> dict:
    """Entrées du circuit pour un nonce donné (vecteurs conservés entre sessions)."""
    env = dict(os.environ, NONCE_HEX=nonce_hex, SEUIL_MAX=SEUIL_MAX, OUTPUT_DIR=dossier)
    if vecteurs:
        env["VECTEURS_JSON"] = vecteurs
    executer(["node", GENERATEUR], env=env)
    with open(os.path.join(dossier, "input.json"), encoding="utf-8") as f:
        return json.load(f)


def prouver(dossier: str, wasm: str, zkey: str):
    executer(["snarkjs", "wtns", "calculate", wasm, os.path.join(dossier, "input.json"),
              os.path.join(dossier, "w.wtns")])
    executer(["snarkjs", "groth16", "prove", zkey, os.path.join(dossier, "w.wtns"),
              os.path.join(dossier, "proof.json"), os.path.join(dossier, "public.json")])
    with open(os.path.join(dossier, "proof.json"), encoding="utf-8") as f:
        preuve = json.load(f)
    with open(os.path.join(dossier, "public.json"), encoding="utf-8") as f:
        signaux = json.load(f)
    return preuve, signaux


def rapport_defis(reponse_nonce: dict) -> dict:
    debut = int(time.time() * 1000)
    return {
        "expires_at": reponse_nonce["expires_at"],
        "jeton": reponse_nonce["defis_jeton"],
        "defis": [
            {"type": d, "debut_ms": debut + 2500 * i, "fin_ms": debut + 2500 * i + 1200}
            for i, d in enumerate(reponse_nonce["defis"])
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Test de bout en bout FaceIN")
    parser.add_argument("--api", default="http://localhost:8000/api")
    parser.add_argument("--wasm", required=True)
    parser.add_argument("--zkey", required=True)
    parser.add_argument("--attente", type=int, default=120, help="délai max de disponibilité (s)")
    args = parser.parse_args()

    if os.path.isdir(SNARKJS_LOCAL):
        os.environ["PATH"] = SNARKJS_LOCAL + os.pathsep + os.environ.get("PATH", "")
    for outil in ("node", "snarkjs"):
        if shutil.which(outil) is None:
            print(f"[ERREUR] '{outil}' introuvable dans le PATH.")
            return 1

    api = args.api.rstrip("/")
    utilisateur = f"e2e_{secrets.token_hex(4)}"
    print(f"Test de bout en bout sur {api} (utilisateur {utilisateur})")

    print("1. Disponibilité")
    sante = attendre_api(api, args.attente)
    verifier(sante.get("statut") == "en_ligne", "API en ligne", json.dumps(sante))
    verifier(bool(sante.get("quorum_atteint")), "quorum des nœuds disponible")
    if echecs:
        return 1

    with tempfile.TemporaryDirectory(prefix="facein_e2e_") as tmp:
        s1, s2 = os.path.join(tmp, "s1"), os.path.join(tmp, "s2")
        os.makedirs(s1)
        os.makedirs(s2)

        print("2. Inscription")
        code, rep = appel("GET", f"{api}/nonce/{utilisateur}")
        verifier(code == 200, "nonce de préparation", f"HTTP {code}")
        entrees = generer_entrees(s1, rep["nonce"])  # crée aussi vecteurs.json
        code, rep = appel("POST", f"{api}/register",
                          {"user_id": utilisateur, "commitment": entrees["engagementAttendu"]})
        verifier(code == 200 and rep.get("success") is True, "inscription acceptée", f"HTTP {code} {rep}")
        code, _ = appel("POST", f"{api}/register",
                        {"user_id": utilisateur, "commitment": entrees["engagementAttendu"]})
        verifier(code == 409, "seconde inscription refusée (409)", f"HTTP {code}")

        print("3. Authentification réelle")
        code, nonce1 = appel("GET", f"{api}/nonce/{utilisateur}")
        verifier(code == 200 and len(nonce1.get("nonce", "")) == 64, "nonce 256 bits émis", f"HTTP {code}")
        generer_entrees(s1, nonce1["nonce"], os.path.join(s1, "vecteurs.json"))
        preuve1, signaux1 = prouver(s1, args.wasm, args.zkey)
        requete1 = {
            "user_id": utilisateur, "proof": preuve1, "public_signals": signaux1,
            "nonce": nonce1["nonce"], "liveness": rapport_defis(nonce1),
        }
        code, rep = appel("POST", f"{api}/authenticate", requete1)
        verifier(code == 200 and rep.get("authenticated") is True and bool(rep.get("token")),
                 "authentification acceptée et JWT émis", f"HTTP {code} {rep.get('raison_refus')}")

        print("4. Refus attendus")
        code, rep = appel("POST", f"{api}/authenticate", requete1)
        verifier(rep.get("authenticated") is False, "rejeu de la même requête refusé", str(rep))

        code, nonce2 = appel("GET", f"{api}/nonce/{utilisateur}")
        rejeu = dict(requete1, nonce=nonce2["nonce"], liveness=rapport_defis(nonce2))
        code, rep = appel("POST", f"{api}/authenticate", rejeu)
        verifier(rep.get("authenticated") is False, "ancienne preuve avec un nouveau nonce refusée", str(rep))

        code, nonce3 = appel("GET", f"{api}/nonce/{utilisateur}")
        generer_entrees(s2, nonce3["nonce"], os.path.join(s1, "vecteurs.json"))
        preuve3, signaux3 = prouver(s2, args.wasm, args.zkey)
        code, rep = appel("POST", f"{api}/authenticate", {
            "user_id": utilisateur, "proof": preuve3, "public_signals": signaux3, "nonce": nonce3["nonce"],
        })
        verifier(rep.get("authenticated") is False and "liveness" in str(rep.get("raison_refus", "")),
                 "authentification sans rapport de défis refusée", str(rep))

    print("=" * 60)
    if echecs:
        print(f"ÉCHEC : {len(echecs)} vérification(s) en échec")
        return 1
    print("RÉUSSI : parcours d'authentification de bout en bout conforme")
    return 0


if __name__ == "__main__":
    sys.exit(main())
