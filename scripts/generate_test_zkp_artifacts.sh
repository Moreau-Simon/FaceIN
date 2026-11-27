#!/usr/bin/env bash
# ==============================================================================
# FaceIn - Génération d'artefacts Groth16 de TEST (jetables)
# ==============================================================================
# Produit de vraies preuves Groth16 pour la suite de tests cryptographiques
# (api/tests/test_zkp_crypto.py), sans jamais toucher aux clés du dépôt :
#   - frontend/circuit/distance.{wasm,zkey}  : NON modifiés
#   - nodes/shared/verification_key.json      : NON modifié
#
# Contenu généré dans circuits/build/test-zkp/ (ignoré par Git) :
#   vk_a.json                      clé de vérification de la cérémonie de test A
#   vk_b.json                      clé d'une seconde cérémonie B (« mauvaise clé »)
#   commitment.txt                 engagement Poseidon de l'utilisateur de test
#   session1/{nonce.txt,proof.json,public.json}  preuve liée au nonce 1 (clé A)
#   session2/{nonce.txt,proof.json,public.json}  preuve liée au nonce 2 (clé A)
#   legacy/{proof.json,public.json}  preuve de l'ANCIEN circuit (2 signaux publics),
#                                  produite avec frontend/circuit (si présent)
#
# ATTENTION : ces cérémonies sont des cérémonies de TEST à un seul contributeur,
# avec une entropie aléatoire jetable. Elles ne remplacent en aucun cas une
# véritable cérémonie de confiance et ne doivent jamais servir en production.
#
# Prérequis : circom 2.x dans le PATH, Node.js, dépendances de circuits/
# installées (cd circuits && npm ci) pour snarkjs et circomlibjs.
# ==============================================================================

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CIRCUITS_DIR="${ROOT_DIR}/circuits"
OUT_DIR="${FACEIN_TEST_ZKP_DIR:-${CIRCUITS_DIR}/build/test-zkp}"
PTAU_FILE="${CIRCUITS_DIR}/pot15_final.ptau"
SEUIL_MAX="${DISTANCE_THRESHOLD:-16000000}"

export PATH="${CIRCUITS_DIR}/node_modules/.bin:${PATH}"

for outil in circom snarkjs node openssl; do
    if ! command -v "$outil" > /dev/null 2>&1; then
        echo "[ERREUR] '$outil' est introuvable dans le PATH." >&2
        exit 1
    fi
done

if [ ! -f "$PTAU_FILE" ]; then
    echo "[ERREUR] Fichier Powers of Tau introuvable : $PTAU_FILE" >&2
    exit 1
fi

rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR/session1" "$OUT_DIR/session2" "$OUT_DIR/legacy"
cd "$OUT_DIR"

echo "[1/5] Compilation du circuit courant (distance.circom)..."
circom "${CIRCUITS_DIR}/distance.circom" --r1cs --wasm -o "$OUT_DIR" -l "${CIRCUITS_DIR}/node_modules" > /dev/null

echo "[2/5] Cérémonies de TEST A et B (entropie aléatoire jetable)..."
for cle in a b; do
    snarkjs groth16 setup distance.r1cs "$PTAU_FILE" "setup_${cle}_0.zkey" > /dev/null
    snarkjs zkey contribute "setup_${cle}_0.zkey" "setup_${cle}.zkey" \
        --name="FaceIn-TEST-${cle}" -e="$(openssl rand -hex 64)" > /dev/null
    snarkjs zkey export verificationkey "setup_${cle}.zkey" "vk_${cle}.json" > /dev/null
    rm -f "setup_${cle}_0.zkey"
done

echo "[3/5] Génération des entrées de deux sessions du même utilisateur..."
NONCE_1="$(openssl rand -hex 32)"
NONCE_2="$(openssl rand -hex 32)"
NONCE_HEX="$NONCE_1" SEUIL_MAX="$SEUIL_MAX" OUTPUT_DIR="$OUT_DIR/session1" \
    node "${CIRCUITS_DIR}/test/generate_test_input.js" > /dev/null
NONCE_HEX="$NONCE_2" SEUIL_MAX="$SEUIL_MAX" OUTPUT_DIR="$OUT_DIR/session2" \
    VECTEURS_JSON="$OUT_DIR/session1/vecteurs.json" \
    node "${CIRCUITS_DIR}/test/generate_test_input.js" > /dev/null
echo -n "$NONCE_1" > session1/nonce.txt
echo -n "$NONCE_2" > session2/nonce.txt

echo "[4/5] Preuves Groth16 réelles (clé A)..."
for session in session1 session2; do
    snarkjs wtns calculate distance_js/distance.wasm "$session/input.json" "$session/witness.wtns" > /dev/null
    snarkjs groth16 prove setup_a.zkey "$session/witness.wtns" "$session/proof.json" "$session/public.json" > /dev/null
    snarkjs groth16 verify vk_a.json "$session/public.json" "$session/proof.json" > /dev/null
done
node -e 'process.stdout.write(JSON.parse(require("fs").readFileSync(process.argv[1]))[0])' \
    session1/public.json > commitment.txt

echo "[5/5] Preuve de l'ancienne version du circuit (frontend/circuit, 2 signaux)..."
LEGACY_WASM="${ROOT_DIR}/frontend/circuit/distance.wasm"
LEGACY_ZKEY="${ROOT_DIR}/frontend/circuit/distance.zkey"
if [ -f "$LEGACY_WASM" ] && [ -f "$LEGACY_ZKEY" ] \
    && [ "$(snarkjs zkey export verificationkey "$LEGACY_ZKEY" legacy/vk.json > /dev/null && \
          node -e 'process.stdout.write(String(JSON.parse(require("fs").readFileSync("legacy/vk.json")).nPublic))')" = "2" ]; then
    node -e '
        const fs = require("fs");
        const i = JSON.parse(fs.readFileSync("session1/input.json"));
        delete i.nonceHi; delete i.nonceLo;
        fs.writeFileSync("legacy/input.json", JSON.stringify(i));'
    snarkjs wtns calculate "$LEGACY_WASM" legacy/input.json legacy/witness.wtns > /dev/null
    snarkjs groth16 prove "$LEGACY_ZKEY" legacy/witness.wtns legacy/proof.json legacy/public.json > /dev/null
else
    echo "  (ignoré : frontend/circuit n'est pas l'ancien circuit à 2 signaux)"
    rm -rf legacy
fi

rm -f setup_a.zkey setup_b.zkey distance.r1cs session*/witness.wtns legacy/witness.wtns
echo "Artefacts de test générés dans : $OUT_DIR"
