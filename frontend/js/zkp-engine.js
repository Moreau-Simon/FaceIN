/**
 * FaceIn - Moteur Zero-Knowledge Proof (ZKP)
 * Génération de preuves Groth16 côté client avec snarkjs et calcul d'engagements Poseidon avec circomlibjs.
 * Garantit que l'image et les descripteurs restent confidentiels sur le terminal utilisateur.
 */
class ZkpEngine {
    constructor() {
        this.wasmPath = (window.CONFIG && window.CONFIG.WASM_PATH) || './circuit/distance.wasm';
        this.zkeyPath = (window.CONFIG && window.CONFIG.ZKEY_PATH) || './circuit/distance.zkey';
        this.poseidon = null;
        this.poseidonInitPromise = null;
    }

    /**
     * Initialise le moteur ZKP en configurant les chemins du circuit et en préparant Poseidon
     * @param {string} [wasmPath] - Chemin vers le fichier WASM du circuit
     * @param {string} [zkeyPath] - Chemin vers la clé de preuve zkey
     * @returns {Promise<void>}
     */
    async init(wasmPath, zkeyPath) {
        if (wasmPath) this.wasmPath = wasmPath;
        if (zkeyPath) this.zkeyPath = zkeyPath;

        console.log(`[ZkpEngine] Initialisation du moteur ZKP (WASM: ${this.wasmPath}, ZKEY: ${this.zkeyPath})...`);
        await this.ensurePoseidon();
        console.log("[ZkpEngine] Moteur ZKP prêt.");
    }

    /**
     * Charge et instancie l'implémentation Poseidon de circomlibjs
     * @returns {Promise<Function>}
     */
    async ensurePoseidon() {
        if (this.poseidon) {
            return this.poseidon;
        }

        if (this.poseidonInitPromise) {
            return this.poseidonInitPromise;
        }

        let attempts = 0;
        while ((typeof window.circomlibjs === 'undefined' || typeof window.circomlibjs.buildPoseidon !== 'function') && attempts < 20) {
            await new Promise(resolve => setTimeout(resolve, 150));
            attempts++;
        }

        if (typeof window.circomlibjs === 'undefined' || typeof window.circomlibjs.buildPoseidon !== 'function') {
            throw new Error("La bibliothèque circomlibjs n'est pas chargée. Vérifiez l'inclusion du script CDN dans index.html.");
        }

        this.poseidonInitPromise = window.circomlibjs.buildPoseidon().then(pos => {
            this.poseidon = pos;
            console.log("[ZkpEngine] Poseidon (circomlibjs) initialisé avec succès.");
            return pos;
        }).catch(err => {
            this.poseidonInitPromise = null;
            console.error("[ZkpEngine] Erreur lors de l'initialisation de Poseidon:", err);
            throw err;
        });

        return this.poseidonInitPromise;
    }

    /**
     * Convertit un descripteur flottant (-1..1) en un tableau d'entiers sous forme de chaînes de caractères.
     * Circom opérant sur des entiers modulo un grand nombre premier, les flottants sont multipliés par un facteur d'échelle.
     * @param {Float32Array|Float64Array|number[]} floatVector - Vecteur de 128 flottants
     * @returns {string[]} Tableau de 128 chaînes d'entiers
     */
    scaleVector(floatVector) {
        if (!floatVector || floatVector.length !== 128) {
            throw new Error(`Le vecteur d'entrée doit contenir exactement 128 dimensions (${floatVector ? floatVector.length : 0} reçues).`);
        }

        const factor = (window.CONFIG && window.CONFIG.SCALE_FACTOR) || 10000;
        return Array.from(floatVector).map(val => Math.round(val * factor).toString());
    }

    /**
     * Calcule l'engagement cryptographique Poseidon d'un vecteur mis à l'échelle.
     * Reproduit fidèlement la structure arborescente du circuit Circom :
     * 128 entrées -> 8x Poseidon(16) -> 2x Poseidon(4) -> 1x Poseidon(2).
     * @param {string[]|number[]|BigInt[]} scaledVector - Tableau de 128 entiers mis à l'échelle
     * @returns {Promise<string>} Valeur décimale de l'engagement (racine Poseidon)
     */
    async computeCommitment(scaledVector) {
        if (!scaledVector || scaledVector.length !== 128) {
            throw new Error(`Le vecteur pour le calcul de l'engagement doit avoir 128 éléments (${scaledVector ? scaledVector.length : 0} fournis).`);
        }

        const poseidon = await this.ensurePoseidon();
        const F = poseidon.F;
        const prime = F.p;

        // Fonction pour projeter un entier (même négatif) dans le corps fini BN128 [0, p-1]
        const toField = (val) => {
            let b = BigInt(val);
            b = ((b % prime) + prime) % prime;
            return b;
        };

        // Étage 1 : 8 blocs de 16 éléments -> 8 condensats
        const layer1 = [];
        for (let i = 0; i < 8; i++) {
            const chunk = [];
            for (let j = 0; j < 16; j++) {
                chunk.push(toField(scaledVector[i * 16 + j]));
            }
            const h = poseidon(chunk);
            layer1.push(F.toObject(h));
        }

        // Étage 2 : 2 blocs de 4 éléments -> 2 condensats
        const layer2 = [
            F.toObject(poseidon(layer1.slice(0, 4))),
            F.toObject(poseidon(layer1.slice(4, 8)))
        ];

        // Étage 3 : 1 bloc de 2 éléments -> 1 engagement final
        const rootHash = poseidon(layer2);

        const commitmentStr = F.toString(rootHash);
        console.log(`[ZkpEngine] Engagement Poseidon calculé : ${commitmentStr}`);
        return commitmentStr;
    }

    /**
     * Décompose un nonce 256 bits (hexadécimal de 64 caractères) en deux entiers de 128 bits
     * (nonceHi et nonceLo) pour le circuit Circom et les signaux publics BN254.
     * @param {string} nonceHex - Nonce hexadécimal de 64 caractères
     * @returns {{ nonceHi: string, nonceLo: string }}
     */
    decomposeNonce(nonceHex) {
        if (!nonceHex || typeof nonceHex !== 'string') {
            throw new Error("Le nonce doit être une chaîne hexadécimale.");
        }
        let cleanHex = nonceHex.trim();
        if (cleanHex.startsWith("0x") || cleanHex.startsWith("0X")) {
            cleanHex = cleanHex.slice(2);
        }
        if (cleanHex.length < 64) {
            cleanHex = cleanHex.padStart(64, '0');
        } else if (cleanHex.length > 64) {
            throw new Error(`Le nonce doit comporter au maximum 64 caractères hexadécimaux (${cleanHex.length} reçus).`);
        }
        const hiHex = cleanHex.slice(0, 32);
        const loHex = cleanHex.slice(32);
        const nonceHi = BigInt("0x" + hiHex).toString();
        const nonceLo = BigInt("0x" + loHex).toString();
        return { nonceHi, nonceLo };
    }

    /**
     * Génère la preuve ZKP Groth16 via snarkjs
     * @param {Float32Array|Float64Array|number[]} originalVector - Vecteur original de référence (privé)
     * @param {Float32Array|Float64Array|number[]} currentVector - Vecteur actuel capturé (privé)
     * @param {string} commitment - Engagement attendu (signal public)
     * @param {number|string} [threshold] - Seuil de distance au carré (signal public)
     * @param {string} [nonce] - Nonce anti-rejeu 256 bits (64 hex chars) lié à la session
     * @returns {Promise<{ proof: object, publicSignals: string[] }>}
     */
    async generateProof(originalVector, currentVector, commitment, threshold, nonce) {
        if (typeof window.snarkjs === 'undefined' || !window.snarkjs.groth16) {
            throw new Error("La bibliothèque snarkjs n'est pas chargée. Impossible de générer la preuve ZKP.");
        }

        const seuil = threshold !== undefined ? threshold : ((window.CONFIG && window.CONFIG.DISTANCE_THRESHOLD) || 6000000);

        let nonceHi = "0";
        let nonceLo = "0";
        if (nonce) {
            const decomposed = this.decomposeNonce(nonce);
            nonceHi = decomposed.nonceHi;
            nonceLo = decomposed.nonceLo;
            console.log(`[ZkpEngine] Nonce décomposé en signaux publics: nonceHi=${nonceHi}, nonceLo=${nonceLo}`);
        }

        // 1. Mise à l'échelle des vecteurs flottants
        const scaledOriginal = this.scaleVector(originalVector);
        const scaledCurrent = this.scaleVector(currentVector);

        // Calcul de contrôle côté JS pour diagnostiquer la distance
        let distSq = 0;
        let floatDistSq = 0;
        for (let i = 0; i < 128; i++) {
            const diff = Number(scaledOriginal[i]) - Number(scaledCurrent[i]);
            distSq += diff * diff;
            const fDiff = originalVector[i] - currentVector[i];
            floatDistSq += fDiff * fDiff;
        }
        const floatDist = Math.sqrt(floatDistSq);
        console.log(`[ZkpEngine] Diagnostic distance : distance euclidienne réelle = ${floatDist.toFixed(4)}, dist^2 quantifiée = ${distSq}, seuilMax = ${seuil}`);
        if (distSq > seuil) {
            console.warn(`[ZkpEngine] ATTENTION : la distance mesurée (${distSq}) dépasse le seuil configuré (${seuil}). Le circuit ZKP va rejeter la preuve car les visages sont jugés trop différents.`);
        }

        // 2. Préparation du témoin / entrées du circuit Circom (avec liaison nonce anti-rejeu)
        const circuitInput = {
            vecteurOriginal: scaledOriginal,
            vecteurDuJour: scaledCurrent,
            engagementAttendu: commitment.toString(),
            seuilMax: seuil.toString(),
            nonceHi: nonceHi,
            nonceLo: nonceLo
        };

        console.log("[ZkpEngine] Lancement de snarkjs.groth16.fullProve avec :", {
            wasmPath: this.wasmPath,
            zkeyPath: this.zkeyPath,
            seuilMax: seuil.toString(),
            engagementAttendu: commitment.toString(),
            nonceHi,
            nonceLo
        });

        // 3. Calcul du témoin et génération de la preuve
        const { proof, publicSignals } = await window.snarkjs.groth16.fullProve(
            circuitInput,
            this.wasmPath,
            this.zkeyPath
        );

        console.log("[ZkpEngine] Preuve Groth16 générée avec succès.", {
            publicSignals,
            curve: proof.curve
        });

        return { proof, publicSignals };
    }
}

// Exposition globale
window.ZkpEngine = new ZkpEngine();
