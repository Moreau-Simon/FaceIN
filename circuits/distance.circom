pragma circom 2.1.0;

// ============================================================================
// Projet FaceIn - Circuit ZKP d'Authentification Biométrique
// ============================================================================
// Ce circuit vérifie sans divulgation de connaissance (Zero-Knowledge Proof) que :
// 1. La distance euclidienne au carré entre le vecteur de référence
//    (vecteurOriginal) et le vecteur capturé (vecteurDuJour) est inférieure ou
//    égale à un seuil prédéfini (seuilMax).
// 2. Le vecteurOriginal correspond exactement à l'engagement cryptographique
//    public enregistré au préalable (engagementAttendu), calculé via un arbre de
//    hachage Poseidon (PoseidonTreeHash).
//
// Caractéristiques techniques :
// - Dimension des vecteurs biométriques : 128 flottants issus de face-api.js
// - Facteur d'échelle (quantification) : 10000 (les flottants sont multipliés
//   par 10000 pour devenir des entiers dans le corps fini BN254)
// - Fonction de hachage : Poseidon (optimisée pour les circuits SNARKs)
// - Comparateur : LessEqThan(64) (la distance au carré maximale théorique
//   tient sur environ 37 bits avec le facteur 10000)
// ============================================================================

include "circomlib/circuits/poseidon.circom";
include "circomlib/circuits/comparators.circom";

// ============================================================================
// Template : EuclideanDistanceSquared
// ----------------------------------------------------------------------------
// Calcule la somme des différences au carré entre deux vecteurs de taille n :
// out = SUM_{i=0}^{n-1} (a[i] - b[i])^2
//
// Entrées :
//   - a[n] : premier vecteur quantifié
//   - b[n] : second vecteur quantifié
// Sortie :
//   - out  : distance euclidienne au carré
// ============================================================================
template EuclideanDistanceSquared(n) {
    signal input a[n];
    signal input b[n];
    signal output out;

    signal diff[n];
    signal diffCarre[n];
    signal sommeIntermediaire[n];

    for (var i = 0; i < n; i++) {
        // Différence composante par composante
        diff[i] <== a[i] - b[i];
        // Carré de la différence (contrainte quadratique R1CS)
        diffCarre[i] <== diff[i] * diff[i];
    }

    // Accumulation des carrés pour former la somme euclidienne
    sommeIntermediaire[0] <== diffCarre[0];
    for (var i = 1; i < n; i++) {
        sommeIntermediaire[i] <== sommeIntermediaire[i - 1] + diffCarre[i];
    }

    out <== sommeIntermediaire[n - 1];
}

// ============================================================================
// Template : PoseidonTreeHash
// ----------------------------------------------------------------------------
// Hache un vecteur de 128 composantes selon une arborescence de type Merkle :
// - Niveau 1 : 8 blocs de 16 composantes -> 8 hachages Poseidon(16)
// - Niveau 2 : 2 blocs de 4 hachages     -> 2 hachages Poseidon(4)
// - Niveau 3 : 1 hachage final           -> 1 hachage Poseidon(2) (engagement final)
//
// Entrées :
//   - in[n] : tableau de n éléments (n doit valoir 128)
// Sortie :
//   - out   : empreinte Poseidon finale (l'engagement cryptographique)
// ============================================================================
template PoseidonTreeHash(n) {
    assert(n == 128);

    signal input in[n];
    signal output out;

    // --- Niveau 1 : 8 groupes de 16 composantes ---
    component hashNiveau1[8];
    for (var i = 0; i < 8; i++) {
        hashNiveau1[i] = Poseidon(16);
        for (var j = 0; j < 16; j++) {
            hashNiveau1[i].inputs[j] <== in[i * 16 + j];
        }
    }

    // --- Niveau 2 : 2 groupes de 4 hachages issus du niveau 1 ---
    component hashNiveau2[2];
    for (var i = 0; i < 2; i++) {
        hashNiveau2[i] = Poseidon(4);
        for (var j = 0; j < 4; j++) {
            hashNiveau2[i].inputs[j] <== hashNiveau1[i * 4 + j].out;
        }
    }

    // --- Niveau 3 : Hachage final combinant les 2 racines intermédiaires ---
    component hashNiveau3 = Poseidon(2);
    hashNiveau3.inputs[0] <== hashNiveau2[0].out;
    hashNiveau3.inputs[1] <== hashNiveau2[1].out;

    out <== hashNiveau3.out;
}

// ============================================================================
// Template : FaceInVerifier
// ----------------------------------------------------------------------------
// Vérificateur principal combinant :
// 1. La contrainte de proximité biométrique (distance <= seuilMax)
// 2. La contrainte d'intégrité du vecteur de référence (Poseidon == engagement)
//
// Entrées privées (restent sur le terminal de l'utilisateur) :
//   - vecteurOriginal[n] : vecteur de référence enregistré lors de l'enrôlement
//   - vecteurDuJour[n]   : vecteur extrait lors de la session courante
//
// Entrées publiques (vérifiables par les nœuds du réseau) :
//   - engagementAttendu  : hash Poseidon public de référence
//   - seuilMax           : seuil maximal toléré pour la distance euclidienne carrée
// ============================================================================
template FaceInVerifier(n) {
    // Entrées privées
    signal input vecteurOriginal[n];
    signal input vecteurDuJour[n];

    // Entrées publiques
    signal input engagementAttendu;
    signal input seuilMax;

    // ------------------------------------------------------------------------
    // Contrainte 1 : Distance euclidienne au carré <= seuilMax
    // ------------------------------------------------------------------------
    component distanceCalculateur = EuclideanDistanceSquared(n);
    for (var i = 0; i < n; i++) {
        distanceCalculateur.a[i] <== vecteurOriginal[i];
        distanceCalculateur.b[i] <== vecteurDuJour[i];
    }

    // Comparateur 64 bits : vérifie que distanceCalculateur.out <= seuilMax
    component comparateurSeuil = LessEqThan(64);
    comparateurSeuil.in[0] <== distanceCalculateur.out;
    comparateurSeuil.in[1] <== seuilMax;
    comparateurSeuil.out === 1;

    // ------------------------------------------------------------------------
    // Contrainte 2 : PoseidonTreeHash(vecteurOriginal) === engagementAttendu
    // ------------------------------------------------------------------------
    component arbrePoseidon = PoseidonTreeHash(n);
    for (var i = 0; i < n; i++) {
        arbrePoseidon.in[i] <== vecteurOriginal[i];
    }
    arbrePoseidon.out === engagementAttendu;
}

// Composant principal du circuit avec les signaux publics déclarés
component main {public [engagementAttendu, seuilMax]} = FaceInVerifier(128);
