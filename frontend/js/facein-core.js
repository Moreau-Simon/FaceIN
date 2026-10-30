/**
 * FaceIn - Orchestrateur Principal (Core)
 * Coordonne la capture biométrique, la persistance locale IndexedDB,
 * la génération de preuve ZKP et la communication avec l'API Gateway.
 */
class FaceInCore {
    constructor() {
        this.currentTab = 'register'; // 'register' ou 'auth'
        this.isProcessing = false;
    }

    /**
     * Initialise les composants matériels, cryptographiques et l'interface utilisateur
     */
    async init() {
        this.log("Initialisation de l'application FaceIn...", "info");

        // 1. Liaison des écouteurs d'événements de l'interface
        this.setupTabs();
        this.setupButtons();

        // 2. Initialisation de la base IndexedDB locale
        try {
            await window.StorageManager.init();
            this.log("IndexedDB (FaceInDB) initialisée avec succès.", "success");
        } catch (err) {
            this.log(`Erreur IndexedDB: ${err.message}`, "error");
        }

        // 3. Initialisation du moteur ZKP
        try {
            const wasm = window.CONFIG?.WASM_PATH || './circuit/distance.wasm';
            const zkey = window.CONFIG?.ZKEY_PATH || './circuit/distance.zkey';
            await window.ZkpEngine.init(wasm, zkey);
            this.log("Moteur ZKP et Poseidon initialisés.", "success");
        } catch (err) {
            this.log(`Attention lors de l'initialisation ZKP: ${err.message}`, "warn");
        }

        // 4. Initialisation de la webcam sur le flux de l'onglet actif
        try {
            const urlParams = new URLSearchParams(window.location.search);
            const mode = urlParams.get('mode');
            const targetTab = (mode === 'login' || mode === 'auth') ? 'auth' : 'register';

            if (targetTab === 'auth') {
                this.switchTab('auth');
            }

            const initialVideo = document.getElementById(targetTab === 'auth' ? 'video-auth' : 'video-register');
            if (initialVideo) {
                await window.FaceCapture.init(initialVideo);
                this.log("Webcam et modèles d'IA faciale prêts.", "success");
                this.updateStatus("Caméra et modèles IA prêts. Entrez un identifiant pour commencer.", false);
            }
        } catch (err) {
            this.log(`Erreur d'initialisation caméra/IA: ${err.message}`, "error");
            this.updateStatus(`Erreur caméra/IA: ${err.message}`, true);
        }
    }

    /**
     * Configure le basculement entre les onglets Inscription et Connexion
     */
    setupTabs() {
        const tabBtns = document.querySelectorAll('.tab-button');
        tabBtns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const targetTab = e.currentTarget.getAttribute('data-tab');
                this.switchTab(targetTab);
            });
        });
    }

    /**
     * Bascule l'affichage entre les onglets et réassigne le flux vidéo
     * @param {'register'|'auth'} tab 
     */
    switchTab(tab) {
        if (this.currentTab === tab) return;
        this.currentTab = tab;

        document.querySelectorAll('.tab-button').forEach(btn => {
            btn.classList.toggle('active', btn.getAttribute('data-tab') === tab);
        });

        document.querySelectorAll('.tab-content').forEach(section => {
            section.classList.toggle('active', section.id === `tab-${tab}`);
        });

        // Transfère le flux vidéo sur l'élément vidéo de l'onglet actif
        const activeVideo = document.getElementById(tab === 'register' ? 'video-register' : 'video-auth');
        if (activeVideo && window.FaceCapture) {
            window.FaceCapture.attachTo(activeVideo);
        }

        // Copie éventuelle du pseudo saisi pour faciliter les tests
        const srcId = tab === 'register' ? 'user-id-auth' : 'user-id-register';
        const dstId = tab === 'register' ? 'user-id-register' : 'user-id-auth';
        const srcVal = document.getElementById(srcId)?.value;
        const dstEl = document.getElementById(dstId);
        if (srcVal && dstEl && !dstEl.value) {
            dstEl.value = srcVal;
        }

        this.log(`Basculement vers l'onglet : ${tab === 'register' ? 'Inscription' : 'Connexion'}`);
    }

    /**
     * Attache les événements aux boutons d'action
     */
    setupButtons() {
        const btnRegister = document.getElementById('btn-register');
        if (btnRegister) {
            btnRegister.addEventListener('click', async () => {
                const userId = document.getElementById('user-id-register')?.value?.trim();
                await this.register(userId);
            });
        }

        const btnAuth = document.getElementById('btn-auth');
        if (btnAuth) {
            btnAuth.addEventListener('click', async () => {
                const userId = document.getElementById('user-id-auth')?.value?.trim();
                await this.authenticate(userId);
            });
        }

        const btnClear = document.getElementById('btn-clear-logs');
        if (btnClear) {
            btnClear.addEventListener('click', () => {
                const container = document.getElementById('debug-logs');
                if (container) container.innerHTML = '';
            });
        }
    }

    /**
     * Processus d'inscription d'un nouvel utilisateur
     * 1. Capture du descripteur facial 128D
     * 2. Stockage local dans IndexedDB
     * 3. Calcul de l'engagement Poseidon
     * 4. Envoi de l'engagement au serveur
     * @param {string} userId - Identifiant / pseudo de l'utilisateur
     */
    async register(userId) {
        if (this.isProcessing) return;

        if (!userId) {
            this.updateStatus("❌ Veuillez renseigner un identifiant (pseudo).", true, 'register');
            return;
        }

        this.setProcessing(true, 'register');

        try {
            // Étape 1 : Capture du visage
            this.updateStatus("Capture du visage...", false, 'register');
            this.log(`[Inscription] Capture faciale pour l'utilisateur '${userId}'...`);
            const descriptor = await window.FaceCapture.captureDescriptor();
            this.log(`[Inscription] Descripteur 128D extrait avec succès.`);

            // Étape 2 : Sauvegarde locale du vecteur dans IndexedDB
            this.updateStatus("Sauvegarde locale du vecteur...", false, 'register');
            await window.StorageManager.saveVector(userId, descriptor);
            this.log(`[Inscription] Vecteur stocké dans IndexedDB (FaceInDB) pour '${userId}'.`);

            // Étape 3 : Calcul de l'engagement cryptographique Poseidon
            this.updateStatus("Calcul de l'engagement cryptographique...", false, 'register');
            const scaledVector = window.ZkpEngine.scaleVector(descriptor);
            const commitment = await window.ZkpEngine.computeCommitment(scaledVector);
            this.log(`[Inscription] Engagement calculé: ${commitment}`);

            // Étape 4 : Envoi de l'engagement au serveur
            this.updateStatus("Envoi de l'engagement au serveur...", false, 'register');
            const apiUrl = `${window.CONFIG.API_BASE_URL}/register`;
            this.log(`[Inscription] POST ${apiUrl} avec identifiant et engagement.`);

            const response = await fetch(apiUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    user_id: userId,
                    commitment: commitment
                })
            });

            if (!response.ok) {
                let errorDetails = `Code HTTP ${response.status}`;
                try {
                    const errJson = await response.json();
                    errorDetails = errJson.message || errJson.detail || errorDetails;
                } catch (e) {
                    const errText = await response.text();
                    if (errText) errorDetails = errText;
                }
                throw new Error(errorDetails);
            }

            const responseData = await response.json().catch(() => ({}));
            this.log(`[Inscription] Réponse serveur: ${JSON.stringify(responseData)}`, "success");
            this.updateStatus("✅ Inscription réussie !", false, 'register');

        } catch (error) {
            console.error("[Inscription] Erreur:", error);
            this.log(`[Inscription] Erreur: ${error.message}`, "error");
            this.updateStatus(`❌ Erreur: ${error.message}`, true, 'register');
        } finally {
            this.setProcessing(false, 'register');
        }
    }

    /**
    * Processus d'authentification biométrique Zero-Knowledge
    * 1. Récupération du vecteur de référence depuis IndexedDB
    * 2. Demande du nonce anti-rejeu et des défis de vie au serveur
    * 3. Capture du visage actuel (avec test de vie anti-photo)
    * 4. Calcul de l'engagement de référence
    * 5. Génération de la preuve ZPK
    * 6. Envoi de la preuve au serveur pour vérification
     * @param {string} userId - Identifiant de l'utilisateur
     */
    async authenticate(userId) {
        if (this.isProcessing) return;

        if (!userId) {
            this.updateStatus("❌ Veuillez renseigner votre identifiant.", true, 'auth');
            return;
        }

        this.setProcessing(true, 'auth');

        try {
            // Étape 1 : Récupération du vecteur d'inscription
            this.updateStatus("Récupération du vecteur d'inscription...", false, 'auth');
            this.log(`[Connexion] Recherche du vecteur local pour '${userId}'...`);
            const originalVector = await window.StorageManager.getVector(userId);

            if (!originalVector) {
                const msg = "Aucun vecteur trouvé. Inscrivez-vous d'abord sur cet appareil.";
                this.log(`[Connexion] ${msg}`, "warn");
                this.updateStatus(`❌ ${msg}`, true, 'auth');
                return;
            }
            this.log(`[Connexion] Vecteur original récupéré depuis IndexedDB.`);

            // Étape 2 : Demande du nonce anti-rejeu + défis de vie auprès du serveur
            // (AVANT la capture : les défis doivent être imposés par le serveur,
            //  aléatoires et frais — le nonce vit 60 s, le test de vie ~18 s max)
            this.updateStatus("Demande du nonce anti-rejeu...", false, 'auth');
            const nonceUrl = `${window.CONFIG.API_BASE_URL}/nonce/${encodeURIComponent(userId)}`;
            this.log(`[Connexion] GET ${nonceUrl}`);

            const nonceResp = await fetch(nonceUrl);
            if (!nonceResp.ok) {
                let errText = `Erreur HTTP ${nonceResp.status}`;
                try {
                    const errJson = await nonceResp.json();
                    errText = errJson.message || errJson.detail || errText;
                } catch (e) {}
                throw new Error(`Impossible d'obtenir un nonce: ${errText}`);
            }

            const nonceData = await nonceResp.json();
            const nonce = nonceData.nonce || nonceData;
            const defis = Array.isArray(nonceData.defis) ? nonceData.defis : [];
            this.log(`[Connexion] Nonce anti-rejeu obtenu: ${nonce}`);
            this.log(`[Connexion] Défis de vie imposés par le serveur : ${defis.join(', ') || 'aucun'}`);

            // Étape 3 : Capture du visage actuel AVEC test de vie anti-photo
            this.updateStatus("Capture du visage (suivez les instructions)...", false, 'auth');
            this.log(`[Connexion] Capture du visage actuel avec test de vie...`);
            const currentVector = await window.FaceCapture.captureDescriptor({
                defis: defis,
                onStatus: (msg) => this.updateStatus(msg, false, 'auth'),
                onErreur: (msg) => this.log(`[Liveness] ${msg}`, "warn"),
            });
            this.log(`[Connexion] Vecteur actuel extrait (test de vie réussi).`);

            // Étape 4 : Calcul de l'engagement de référence
            this.log(`[Connexion] Calcul de l'engagement Poseidon de référence...`);
            const scaledOriginal = window.ZkpEngine.scaleVector(originalVector);
            const commitment = await window.ZkpEngine.computeCommitment(scaledOriginal);

            // Étape 5 : Génération de la preuve ZKP
            this.updateStatus("Génération de la preuve ZKP (peut prendre quelques secondes)...", false, 'auth');
            this.log(`[Connexion] Génération de la preuve Groth16 avec seuil ${window.CONFIG.DISTANCE_THRESHOLD}...`);
            const { proof, publicSignals } = await window.ZkpEngine.generateProof(
                originalVector,
                currentVector,
                commitment,
                window.CONFIG.DISTANCE_THRESHOLD
            );
            
            // Calcul et affichage clair de la distance pour l'utilisateur
            let floatDistSq = 0;
            for (let i = 0; i < 128; i++) {
                const diff = originalVector[i] - currentVector[i];
                floatDistSq += diff * diff;
            }
            const floatDist = Math.sqrt(floatDistSq);
            this.log(`[Biométrie] Distance euclidienne calculée : ${floatDist.toFixed(4)} (Seuil max : 0.6000)`);
            this.log(`[Connexion] Preuve générée avec succès.`);

            // Étape 6 : Envoi de la preuve au serveur
            this.updateStatus("Envoi de la preuve au serveur...", false, 'auth');
            const authUrl = `${window.CONFIG.API_BASE_URL}/authenticate`;
            this.log(`[Connexion] POST ${authUrl} avec preuve, signaux publics et nonce.`);

            const authResp = await fetch(authUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    user_id: userId,
                    proof: proof,
                    public_signals: publicSignals,
                    nonce: nonce
                })
            });

            if (!authResp.ok) {
                let errDetails = `Code HTTP ${authResp.status}`;
                try {
                    const errJson = await authResp.json();
                    errDetails = errJson.raison_refus || errJson.message || errJson.detail || errDetails;
                } catch (e) {
                    const text = await authResp.text();
                    if (text) errDetails = text;
                }
                throw new Error(errDetails);
            }

            const authResult = await authResp.json();
            this.log(`[Connexion] Réponse d'authentification: ${JSON.stringify(authResult)}`);

            if (authResult.accepte === true || authResult.success === true || authResult.token) {
                const token = authResult.token || "SESSION_OK";
                this.updateStatus(`✅ Authentifié ! Token: ${token}`, false, 'auth');
                this.log(`[Connexion] Authentification confirmée avec token ${token}`, "success");

                // Transmission automatique du jeton au site partenaire (popup opener) si présent
                if (window.opener && !window.opener.closed) {
                    try {
                        this.log("[Connexion] Transmission du jeton à la fenêtre parente...");
                        window.opener.postMessage({
                            type: 'FACEIN_AUTH_SUCCESS',
                            token: token,
                            user_id: userId
                        }, '*');
                        setTimeout(() => window.close(), 1500);
                    } catch (openerErr) {
                        console.warn("[Connexion] Impossible de notifier window.opener:", openerErr);
                    }
                }
            } else {
                const raison = authResult.raison_refus || authResult.message || "Authentification refusée par les nœuds.";
                this.updateStatus(`❌ Échec: ${raison}`, true, 'auth');
                this.log(`[Connexion] Rejet: ${raison}`, "error");
            }

        } catch (error) {
            console.error("[Connexion] Erreur:", error);
            let displayMsg = error.message;
            if (error.message && error.message.includes("FaceInVerifier_230 line: 145")) {
                displayMsg = "Visage non reconnu (distance biométrique supérieure au seuil autorisé). Veuillez bien vous positionner face à la webcam avec un bon éclairage.";
            }
            this.log(`[Connexion] Erreur: ${displayMsg}`, "error");
            this.updateStatus(`❌ Échec: ${displayMsg}`, true, 'auth');
        } finally {
            this.setProcessing(false, 'auth');
        }
    }

    /**
     * Met à jour le message d'état sur l'interface et dans la console de debug
     * @param {string} message - Message à afficher
     * @param {boolean} isError - Indique s'il s'agit d'une erreur
     * @param {'register'|'auth'|'all'} [section='all'] - Section cible
     */
    updateStatus(message, isError = false, section = 'all') {
        const updateElem = (id) => {
            const el = document.getElementById(id);
            if (!el) return;
            el.textContent = message;
            el.className = 'status-box ' + (isError ? 'status-error' : (message.includes('✅') ? 'status-success' : 'status-info'));
        };

        if (section === 'register' || section === 'all') {
            updateElem('status-register');
        }
        if (section === 'auth' || section === 'all') {
            updateElem('status-auth');
        }
    }

    /**
     * Active/désactive l'état d'attente sur les contrôles
     * @param {boolean} processing 
     * @param {'register'|'auth'} tab 
     */
    setProcessing(processing, tab) {
        this.isProcessing = processing;
        const btn = document.getElementById(tab === 'register' ? 'btn-register' : 'btn-auth');
        if (btn) {
            btn.disabled = processing;
            btn.classList.toggle('loading', processing);
        }
    }

    /**
     * Ajoute une entrée horodatée dans la console de débogage de la page
     * @param {string} message 
     * @param {'info'|'success'|'warn'|'error'} [type='info'] 
     */
    log(message, type = 'info') {
        const timestamp = new Date().toLocaleTimeString('fr-FR');
        const container = document.getElementById('debug-logs');

        console.log(`[FaceIn][${type.toUpperCase()}] ${message}`);

        if (container) {
            const entry = document.createElement('div');
            entry.className = `log-entry log-${type}`;
            entry.textContent = `[${timestamp}] ${message}`;
            container.appendChild(entry);
            container.scrollTop = container.scrollHeight;
        }
    }
}

// Exposition globale
window.FaceInCore = new FaceInCore();

// Démarrage automatique au chargement du DOM
document.addEventListener('DOMContentLoaded', () => {
    window.FaceInCore.init().catch(err => {
        console.error("[FaceIn] Erreur fatale au démarrage:", err);
    });
});
