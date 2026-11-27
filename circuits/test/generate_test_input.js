#!/usr/bin/env node
// ==============================================================================
// FaceIn - Générateur de données de test pour le circuit ZKP
// ==============================================================================
// Ce script :
// 1. Simule deux vecteurs 128D (même individu avec légère variation quotidienne)
// 2. Quantifie les composantes flottantes avec un facteur d'échelle de 10 000
// 3. Calcule l'engagement Poseidon de l'arbre Merkle (8xPoseidon(16) -> 2xPoseidon(4) -> Poseidon(2))
// 4. Calcule la distance euclidienne au carré entre les deux vecteurs
// 5. Définit un seuil maximal admissible légèrement supérieur à cette distance
// 6. Écrit 'input.json' (cas passant)
// 7. Écrit 'input_impostor.json' (cas d'usurpation avec faux vecteurOriginal)
//
// Variables d'environnement optionnelles :
//   NONCE_HEX   : nonce de session 256 bits en hexadécimal (64 caractères).
//                 Par défaut : 32 octets aléatoires (crypto.randomBytes).
//   SEUIL_MAX   : seuil imposé (ex. 16000000, valeur par défaut du serveur).
//                 Par défaut : distance calculée + marge.
//   OUTPUT_DIR  : dossier de sortie des fichiers input*.json (défaut : ce dossier).
//   VECTEURS_JSON : fichier JSON {vecteurOriginal, vecteurDuJour} à réutiliser
//                 (permet plusieurs preuves du même utilisateur avec des nonces différents).
// ==============================================================================

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const { buildPoseidon } = require('circomlibjs');

// Facteur d'échelle pour convertir les flottants face-api.js en entiers
const SCALE_FACTOR = 10000;
const VECTOR_DIM = 128;

/**
 * Génère un vecteur aléatoire simulant un descripteur biométrique 128D
 * Composantes normalisées positives centrées autour de 0.2
 */
function genererVecteurBiometrique() {
  const vecteur = [];
  for (let i = 0; i < VECTOR_DIM; i++) {
    // Valeur simulée entre 0.05 et 0.35
    const val = 0.05 + Math.random() * 0.30;
    vecteur.push(val);
  }
  return vecteur;
}

/**
 * Ajoute une légère variation (bruit réaliste de capture quotidienne : éclairage, angle, etc.)
 */
function ajouterVariation(vecteurReference, amplitudeMax = 0.015) {
  return vecteurReference.map(val => {
    const bruit = (Math.random() * 2 - 1) * amplitudeMax;
    // Maintenir une valeur strictement positive
    return Math.max(0.01, val + bruit);
  });
}

/**
 * Quantifie un vecteur flottant en entiers à l'échelle SCALE_FACTOR
 */
function quantifierVecteur(vecteurFlottant) {
  return vecteurFlottant.map(val => Math.round(val * SCALE_FACTOR));
}

/**
 * Calcule l'arbre de hachage Poseidon selon l'architecture du circuit FaceIn :
 * - Niveau 1 : 8 groupes de 16 composantes -> 8 hachages Poseidon(16)
 * - Niveau 2 : 2 groupes de 4 hachages     -> 2 hachages Poseidon(4)
 * - Niveau 3 : 1 hachage final           -> 1 hachage Poseidon(2)
 *
 * @param {object} poseidon - Instance Poseidon initialisée
 * @param {number[]} vecteur - Vecteur de 128 entiers quantifiés
 * @returns {string} - Hash décimal final (engagement cryptographique)
 */
function calculerArbrePoseidon(poseidon, vecteur) {
  if (vecteur.length !== 128) {
    throw new Error(`Le vecteur doit comporter exactement 128 composantes (reçu: ${vecteur.length})`);
  }

  // --- Niveau 1 : 8 blocs de 16 composantes ---
  const niveau1 = [];
  for (let i = 0; i < 8; i++) {
    const bloc16 = vecteur.slice(i * 16, (i + 1) * 16).map(x => BigInt(x));
    const hash = poseidon(bloc16);
    niveau1.push(poseidon.F.toObject(hash));
  }

  // --- Niveau 2 : 2 blocs de 4 hachages ---
  const niveau2 = [];
  for (let i = 0; i < 2; i++) {
    const bloc4 = niveau1.slice(i * 4, (i + 1) * 4);
    const hash = poseidon(bloc4);
    niveau2.push(poseidon.F.toObject(hash));
  }

  // --- Niveau 3 : Hachage final combinant les 2 sous-arbres ---
  const hashFinal = poseidon([niveau2[0], niveau2[1]]);
  return poseidon.F.toString(hashFinal);
}

/**
 * Décompose un nonce 256 bits (hex) en deux signaux publics de 128 bits
 * (nonceHi = nonce >> 128, nonceLo = nonce & (2^128 - 1)), comme le frontend et l'API.
 */
function decomposerNonce(nonceHex) {
  if (!/^[0-9a-fA-F]{64}$/.test(nonceHex)) {
    throw new Error("NONCE_HEX doit contenir exactement 64 caractères hexadécimaux (256 bits)");
  }
  const valeur = BigInt('0x' + nonceHex);
  const masque = (1n << 128n) - 1n;
  return { nonceHi: (valeur >> 128n).toString(), nonceLo: (valeur & masque).toString() };
}

/**
 * Calcule la distance euclidienne entière au carré
 */
function calculerDistanceCarree(vecteurA, vecteurB) {
  let distanceCarree = 0n;
  for (let i = 0; i < VECTOR_DIM; i++) {
    const diff = BigInt(vecteurA[i]) - BigInt(vecteurB[i]);
    distanceCarree += diff * diff;
  }
  return distanceCarree;
}

async function main() {
  console.log("Initialisation de l'algorithme Poseidon (circomlibjs)...");
  const poseidon = await buildPoseidon();

  console.log(`Génération des descripteurs biométriques 128D (facteur d'échelle: ${SCALE_FACTOR})...`);

  let vecteurOriginal;
  let vecteurDuJour;
  if (process.env.VECTEURS_JSON) {
    // Réutilisation des vecteurs d'un même utilisateur (plusieurs sessions)
    const vecteurs = JSON.parse(fs.readFileSync(process.env.VECTEURS_JSON, 'utf-8'));
    vecteurOriginal = vecteurs.vecteurOriginal;
    vecteurDuJour = vecteurs.vecteurDuJour;
  } else {
    // 1. Vecteur original de référence (enrôlement)
    const flotOriginal = genererVecteurBiometrique();
    vecteurOriginal = quantifierVecteur(flotOriginal);

    // 2. Vecteur du jour pour la même personne (authentification avec variation)
    const flotDuJour = ajouterVariation(flotOriginal, 0.015);
    vecteurDuJour = quantifierVecteur(flotDuJour);
  }

  // 3. Vecteur d'un imposteur (personne totalement différente)
  const flotImposteur = genererVecteurBiometrique();
  const vecteurImposteur = quantifierVecteur(flotImposteur);

  // 4. Calcul de l'engagement attendu (Poseidon Tree Hash du vecteur original)
  console.log("Calcul de l'arbre de hachage Poseidon (8xP16 -> 2xP4 -> 1xP2)...");
  const engagementAttendu = calculerArbrePoseidon(poseidon, vecteurOriginal);

  // 5. Calcul de la distance euclidienne au carré
  const distanceCarree = calculerDistanceCarree(vecteurOriginal, vecteurDuJour);

  // 6. Fixation d'un seuil admissible légèrement supérieur à la distance calculée
  // Marge de 25% + constante pour tolérer la variation quotidienne
  const marge = (distanceCarree * 25n) / 100n + 50000n;
  const seuilMax = process.env.SEUIL_MAX
    ? BigInt(process.env.SEUIL_MAX).toString()
    : (distanceCarree + marge).toString();
  if (BigInt(seuilMax) < distanceCarree) {
    throw new Error(`SEUIL_MAX (${seuilMax}) est inférieur à la distance calculée (${distanceCarree})`);
  }

  // Liaison au challenge de session (signaux publics nonceHi / nonceLo du circuit)
  const nonceHex = process.env.NONCE_HEX || crypto.randomBytes(32).toString('hex');
  const { nonceHi, nonceLo } = decomposerNonce(nonceHex);

  console.log("\n------------------------------------------------------------");
  console.log(`Distance euclidienne au carré calculée : ${distanceCarree}`);
  console.log(`Seuil maximum toléré (seuilMax)         : ${seuilMax}`);
  console.log(`Engagement Poseidon attendu             : ${engagementAttendu}`);
  console.log(`Nonce de session                        : ${nonceHex}`);
  console.log("------------------------------------------------------------\n");

  // 7. Préparation des jeux de test
  const inputValide = {
    vecteurOriginal: vecteurOriginal,
    vecteurDuJour: vecteurDuJour,
    engagementAttendu: engagementAttendu,
    seuilMax: seuilMax,
    nonceHi: nonceHi,
    nonceLo: nonceLo
  };

  // Cas d'usurpation : un imposteur tente de présenter un vecteur original non conforme
  // pour usurper l'engagement public de la victime légitime
  const inputImposteur = {
    vecteurOriginal: vecteurImposteur,
    vecteurDuJour: vecteurDuJour,
    engagementAttendu: engagementAttendu, // engagement de la victime légitime
    seuilMax: seuilMax,
    nonceHi: nonceHi,
    nonceLo: nonceLo
  };

  const outputDir = process.env.OUTPUT_DIR || __dirname;
  fs.mkdirSync(outputDir, { recursive: true });
  const cheminInputValide = path.join(outputDir, 'input.json');
  const cheminInputImposteur = path.join(outputDir, 'input_impostor.json');

  fs.writeFileSync(cheminInputValide, JSON.stringify(inputValide, null, 2), 'utf-8');
  console.log(`✓ Fichier de test valide écrit : ${cheminInputValide}`);

  fs.writeFileSync(cheminInputImposteur, JSON.stringify(inputImposteur, null, 2), 'utf-8');
  console.log(`✓ Fichier de test imposteur écrit : ${cheminInputImposteur}`);

  // Vecteurs conservés pour générer d'autres sessions du même utilisateur
  const cheminVecteurs = path.join(outputDir, 'vecteurs.json');
  fs.writeFileSync(cheminVecteurs, JSON.stringify({ vecteurOriginal, vecteurDuJour }), 'utf-8');
}

main().catch(err => {
  console.error("Erreur lors de la génération des entrées de test :", err);
  process.exit(1);
});
