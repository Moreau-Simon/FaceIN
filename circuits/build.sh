#!/usr/bin/env bash
# ==============================================================================
# FaceIn - Script de compilation et configuration ZKP (Groth16)
# ==============================================================================
# Ce script prépare le circuit ZKP pour la vérification biométrique :
# 1. Crée le répertoire build/
# 2. Compile le circuit distance.circom (R1CS, WASM, symboles)
# 3. Télécharge la clé Powers of Tau (Hermez ptau 18) si elle n'est pas présente
# 4. Effectue le setup cryptographique Groth16 (phase 2)
# 5. Apporte une contribution aléatoire à la cérémonie (entropy)
# 6. Exporte la clé de vérification publique verification_key.json
# ==============================================================================

set -euo pipefail

# Se positionner dans le dossier du script (circuits/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Ajouter node_modules/.bin au PATH pour utiliser snarkjs local si besoin
export PATH="./node_modules/.bin:$PATH"

# Couleurs pour l'affichage console
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================================================${NC}"
echo -e "${BLUE}           FaceIn - Compilation du Circuit ZKP Groth16           ${NC}"
echo -e "${BLUE}================================================================${NC}"

# ------------------------------------------------------------------------------
# 1. Vérification des prérequis
# ------------------------------------------------------------------------------
if ! command -v circom &> /dev/null; then
    echo -e "${RED}[ERREUR] 'circom' n'est pas installé ou introuvable dans le PATH.${NC}"
    echo -e "Pour installer circom 2.x :"
    echo -e "  git clone https://github.com/iden3/circom.git"
    echo -e "  cd circom && cargo build --release"
    echo -e "  cargo install --path circom"
    exit 1
fi

if ! command -v snarkjs &> /dev/null; then
    echo -e "${RED}[ERREUR] 'snarkjs' n'est pas installé.${NC}"
    echo -e "Installez les dépendances avec : npm install"
    exit 1
fi

# ------------------------------------------------------------------------------
# 2. Création du répertoire de sortie build/
# ------------------------------------------------------------------------------
BUILD_DIR="build"
echo -e "${YELLOW}[1/6] Création du répertoire ${BUILD_DIR}/...${NC}"
mkdir -p "$BUILD_DIR"

# ------------------------------------------------------------------------------
# 3. Compilation du circuit circom
# ------------------------------------------------------------------------------
echo -e "${YELLOW}[2/6] Compilation de distance.circom...${NC}"
circom distance.circom --r1cs --wasm --sym -o "$BUILD_DIR" -l node_modules

echo -e "${GREEN}✓ Circuit compilé avec succès dans ${BUILD_DIR}/${NC}"

# ------------------------------------------------------------------------------
PTAU_FILE="pot15_final.ptau"

echo -e "${YELLOW}[3/6] Préparation du fichier Powers of Tau (${PTAU_FILE})...${NC}"
if [ ! -f "$PTAU_FILE" ]; then
    echo -e "Génération locale d'un fichier Powers of Tau 15 (2^15 = 32768 contraintes max)..."
    rm -f pot15_*.ptau
    npx snarkjs powersoftau new bn128 15 pot15_0000.ptau -v
    npx snarkjs powersoftau contribute pot15_0000.ptau pot15_0001.ptau --name="FaceIn-Dev" -v -e="FaceInEntropySeed123"
    npx snarkjs powersoftau prepare phase2 pot15_0001.ptau "$PTAU_FILE" -v
    rm -f pot15_0000.ptau pot15_0001.ptau
    echo -e "${GREEN}✓ ${PTAU_FILE} généré avec succès en local.${NC}"
else
    echo -e "${GREEN}✓ ${PTAU_FILE} déjà présent.${NC}"
fi

# ------------------------------------------------------------------------------
# 5. Groth16 Setup initial (phase 2 spécifique au circuit)
# ------------------------------------------------------------------------------
ZKEY_INIT="${BUILD_DIR}/distance_0000.zkey"
echo -e "${YELLOW}[4/6] Génération du setup Groth16 initial (${ZKEY_INIT})...${NC}"
snarkjs groth16 setup "${BUILD_DIR}/distance.r1cs" "$PTAU_FILE" "$ZKEY_INIT"
echo -e "${GREEN}✓ Setup initial terminé.${NC}"

# ------------------------------------------------------------------------------
# 6. Contribution à la cérémonie de confiance (génération de la zkey finale)
# ------------------------------------------------------------------------------
ZKEY_FINAL="${BUILD_DIR}/distance.zkey"
echo -e "${YELLOW}[5/6] Contribution d'entropie pour la cérémonie (${ZKEY_FINAL})...${NC}"
snarkjs zkey contribute "$ZKEY_INIT" "$ZKEY_FINAL" --name="FaceIn" -v -e="FaceIn-Biometric-Auth-Entropy-Phase1"
echo -e "${GREEN}✓ Clé de prouveur finale générée avec succès.${NC}"

# ------------------------------------------------------------------------------
# 7. Exportation de la clé de vérification publique
# ------------------------------------------------------------------------------
VK_FILE="${BUILD_DIR}/verification_key.json"
echo -e "${YELLOW}[6/6] Exportation de la clé de vérification (${VK_FILE})...${NC}"
snarkjs zkey export verificationkey "$ZKEY_FINAL" "$VK_FILE"
echo -e "${GREEN}✓ Clé de vérification exportée.${NC}"

# ------------------------------------------------------------------------------
# Résumé et fichiers générés
# ------------------------------------------------------------------------------
echo -e "\n${BLUE}================================================================${NC}"
echo -e "${GREEN}✓ Compilation et configuration Groth16 terminées avec succès !${NC}"
echo -e "${BLUE}================================================================${NC}"
echo -e "Fichiers produits dans ${BUILD_DIR}/ :"
echo -e "  - ${BUILD_DIR}/distance.r1cs             (Système de contraintes R1CS)"
echo -e "  - ${BUILD_DIR}/distance_js/distance.wasm (Générateur de témoin WebAssembly)"
echo -e "  - ${BUILD_DIR}/distance.sym              (Table des symboles de signaux)"
echo -e "  - ${BUILD_DIR}/distance.zkey             (Clé de prouveur pour générer des preuves)"
echo -e "  - ${BUILD_DIR}/verification_key.json     (Clé publique pour vérifier les preuves)"
echo -e "${BLUE}================================================================${NC}"
