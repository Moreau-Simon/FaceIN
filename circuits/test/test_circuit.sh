#!/usr/bin/env bash
# ==============================================================================
# FaceIn - Script de test et validation du circuit ZKP
# ==============================================================================
# Ce script teste le flux complet de preuve et vérification Groth16 :
# 1. Génère les données de test (input.json et input_impostor.json)
# 2. Calcule le témoin (witness) avec le WebAssembly compilé
# 3. Génère la preuve ZKP Groth16 (proof.json, public.json)
# 4. Vérifie cryptographiquement la preuve avec verification_key.json
# 5. Tente de générer une preuve pour l'imposteur et s'assure du rejet
# ==============================================================================

set -euo pipefail

# Se positionner dans le dossier du script (circuits/test/)
TEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$TEST_DIR"

# Ajouter node_modules/.bin au PATH (dossier local et parent)
export PATH="../node_modules/.bin:../../node_modules/.bin:$PATH"

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}================================================================${NC}"
echo -e "${BLUE}          FaceIn - Test d'Intégration du Circuit ZKP            ${NC}"
echo -e "${BLUE}================================================================${NC}"

# ------------------------------------------------------------------------------
# 1. Vérification des artefacts de compilation
# ------------------------------------------------------------------------------
WASM_FILE="../build/distance_js/distance.wasm"
ZKEY_FILE="../build/distance.zkey"
VK_FILE="../build/verification_key.json"

if [ ! -f "$WASM_FILE" ] || [ ! -f "$ZKEY_FILE" ] || [ ! -f "$VK_FILE" ]; then
    echo -e "${RED}[ERREUR] Les fichiers compilés sont introuvables.${NC}"
    echo -e "Veuillez d'abord exécuter le script de build :"
    echo -e "  cd .. && ./build.sh"
    exit 1
fi

# ------------------------------------------------------------------------------
# 2. Étape 1 : Génération des entrées de test
# ------------------------------------------------------------------------------
echo -e "${YELLOW}[1/4] Génération des vecteurs et entrées de test...${NC}"
node generate_test_input.js

if [ ! -f "input.json" ] || [ ! -f "input_impostor.json" ]; then
    echo -e "${RED}[ERREUR] Les fichiers input.json ou input_impostor.json n'ont pas été créés.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Entrées de test générées avec succès.${NC}"

# ------------------------------------------------------------------------------
# 3. Étape 2 : Calcul du témoin (Witness) pour l'utilisateur légitime
# ------------------------------------------------------------------------------
echo -e "\n${YELLOW}[2/4] Calcul du témoin (witness) pour l'utilisateur légitime...${NC}"
snarkjs wtns calculate "$WASM_FILE" input.json witness.wtns
echo -e "${GREEN}✓ Témoin calculé avec succès (witness.wtns).${NC}"

# ------------------------------------------------------------------------------
# 4. Étape 3 : Génération de la preuve Groth16
# ------------------------------------------------------------------------------
echo -e "\n${YELLOW}[3/4] Génération de la preuve ZKP Groth16...${NC}"
snarkjs groth16 prove "$ZKEY_FILE" witness.wtns proof.json public.json
echo -e "${GREEN}✓ Preuve générée avec succès (proof.json, public.json).${NC}"

# ------------------------------------------------------------------------------
# 5. Étape 4 : Vérification de la preuve légitime
# ------------------------------------------------------------------------------
echo -e "\n${YELLOW}[4/4] Vérification de la preuve avec la clé publique...${NC}"
if snarkjs groth16 verify "$VK_FILE" public.json proof.json; then
    echo -e "${GREEN}✓ SUCCÈS : La preuve ZKP de l'utilisateur légitime est VALIDE !${NC}"
else
    echo -e "${RED}✗ ÉCHEC : La preuve ZKP de l'utilisateur légitime a été rejetée !${NC}"
    exit 1
fi

# ------------------------------------------------------------------------------
# 6. Test d'usurpation (Imposteur) : Doit échouer
# ------------------------------------------------------------------------------
echo -e "\n${BLUE}================================================================${NC}"
echo -e "${YELLOW}Test de sécurité : Tentative d'usurpation par un imposteur...${NC}"
echo -e "${BLUE}================================================================${NC}"

# La tentative de calcul de témoin avec un engagement frauduleux doit échouer
set +e
snarkjs wtns calculate "$WASM_FILE" input_impostor.json witness_imposteur.wtns 2>&1
IMPOSTEUR_STATUS=$?
set -e

if [ $IMPOSTEUR_STATUS -ne 0 ]; then
    echo -e "${GREEN}✓ SUCCÈS ATTENDU : Le calcul du témoin a été rejeté pour l'imposteur !${NC}"
    echo -e "${GREEN}  La contrainte d'intégrité Poseidon ou de distance seuil a bloqué l'attaque.${NC}"
else
    echo -e "${RED}✗ ALERTE SÉCURITÉ : Le témoin pour l'imposteur a été généré sans erreur !${NC}"
    # Nettoyage
    rm -f witness_imposteur.wtns
    exit 1
fi

# Nettoyage des fichiers temporaires de témoin
rm -f witness.wtns

echo -e "\n${GREEN}================================================================${NC}"
echo -e "${GREEN}✓ TOUS LES TESTS DU CIRCUIT FACEIN ONT RÉUSSI AVEC SUCCÈS !      ${NC}"
echo -e "${GREEN}================================================================${NC}"
