/**
 * FaceIn - Module de capture faciale et extraction de descripteurs
 * Utilise la webcam de l'appareil et face-api.js pour extraire un vecteur 128D du visage.
 */
class FaceCapture {
    constructor() {
        this.videoElement = null;
        this.stream = null;
        this.modelsLoaded = false;
        this.modelsLoadingPromise = null;
    }

    /**
     * Initialise la capture vidéo et charge les réseaux de neurones face-api.js
     * @param {HTMLVideoElement} videoElement - Élément HTML video pour la prévisualisation webcam
     * @returns {Promise<void>}
     */
    async init(videoElement) {
        if (!videoElement) {
            throw new Error("Un élément HTMLVideoElement valide doit être fourni à FaceCapture.init().");
        }

        this.videoElement = videoElement;

        // 1. Accès à la webcam
        try {
            if (!this.stream || !this.stream.active) {
                console.log("[FaceCapture] Demande d'accès au périphérique webcam...");
                this.stream = await navigator.mediaDevices.getUserMedia({
                    video: {
                        width: { ideal: 640 },
                        height: { ideal: 480 },
                        facingMode: 'user'
                    },
                    audio: false
                });
            }

            this.videoElement.srcObject = this.stream;
            await this.videoElement.play();
            console.log("[FaceCapture] Flux vidéo démarré et lié à l'élément vidéo.");
        } catch (error) {
            console.error("[FaceCapture] Impossible d'accéder à la webcam:", error);
            throw new Error(`Accès à la caméra refusé ou non disponible : ${error.message}`);
        }

        // 2. Chargement des modèles face-api.js (ssdMobilenetv1, faceLandmark68Net, faceRecognitionNet)
        if (!this.modelsLoaded) {
            if (!this.modelsLoadingPromise) {
                const modelsPath = (window.CONFIG && window.CONFIG.MODELS_PATH) || './models';
                console.log(`[FaceCapture] Chargement des modèles face-api.js depuis '${modelsPath}'...`);

                this.modelsLoadingPromise = Promise.all([
                    faceapi.nets.ssdMobilenetv1.loadFromUri(modelsPath),
                    faceapi.nets.faceLandmark68Net.loadFromUri(modelsPath),
                    faceapi.nets.faceRecognitionNet.loadFromUri(modelsPath)
                ]).then(() => {
                    this.modelsLoaded = true;
                    console.log("[FaceCapture] Modèles ssdMobilenetv1, landmark68 et recognition chargés avec succès.");
                }).catch(err => {
                    this.modelsLoadingPromise = null;
                    console.error("[FaceCapture] Erreur critique lors du chargement des modèles face-api:", err);
                    throw new Error(`Échec du chargement des modèles de reconnaissance faciale : ${err.message}`);
                });
            }
            await this.modelsLoadingPromise;
        }
    }

    /**
     * Attache le flux caméra existant à un nouvel élément vidéo (ex: changement d'onglet)
     * @param {HTMLVideoElement} videoElement 
     */
    attachTo(videoElement) {
        if (!videoElement) return;
        this.videoElement = videoElement;
        if (this.stream && this.stream.active) {
            this.videoElement.srcObject = this.stream;
            this.videoElement.play().catch(e => console.warn("[FaceCapture] Lecture automatique bloquée:", e));
        }
    }

    /**
     * Détecte le visage, exécute (optionnellement) le test de vie anti-photo,
     * puis extrait le descripteur facial normalisé de 128 dimensions
     * @param {Object} [params]
     * @param {string[]} [params.defis] - Défis imposés par le serveur (ex: ["blink","smile"])
     * @param {Function} [params.onStatus] - Callback de progression (message affiché à l'utilisateur)
     * @param {Function} [params.onErreur] - Callback appelé en cas d'échec d'un défi
     * @returns {Promise<Float32Array>} Vecteur descripteur facial 128D
     */
    async captureDescriptor(params = {}) {
        const { defis = null, onStatus = null, onErreur = null } = params;

        if (!this.videoElement) {
            throw new Error("La caméra n'est pas initialisée. Veuillez d'abord démarrer la capture.");
        }

        if (!this.modelsLoaded) {
            throw new Error("Les modèles IA ne sont pas encore prêts.");
        }

        // --- NOUVEAU : test de vie avant l'extraction du descripteur ---
        // Une photo ne peut pas exécuter les défis → aucun descripteur n'est extrait.
        if (Array.isArray(defis) && defis.length > 0) {
            await window.LivenessModule.executerDefis(this.videoElement, defis, { onStatus, onErreur });
        }

        console.log("[FaceCapture] Détection faciale et extraction du descripteur en cours...");

        // Détection du visage avec seuil de confiance minimal (évite les faux positifs / objets)
        const options = new faceapi.SsdMobilenetv1Options({ minConfidence: 0.65 });
        const detection = await faceapi
            .detectSingleFace(this.videoElement, options)
            .withFaceLandmarks()
            .withFaceDescriptor();

        if (!detection || !detection.descriptor) {
            console.warn("[FaceCapture] Aucun visage détecté sur la vidéo.");
            throw new Error("Aucun visage détecté. Veuillez vous positionner bien en face de la caméra avec un bon éclairage.");
        }

        if (detection.descriptor.length !== 128) {
            throw new Error(`Taille de descripteur inattendue (${detection.descriptor.length} au lieu de 128).`);
        }

        console.log("[FaceCapture] Visage détecté avec succès ! Descripteur 128D extrait.");
        return detection.descriptor;
    }

    /**
     * Arrête le flux vidéo webcam et libère les pistes matérielles
     */
    stop() {
        if (this.stream) {
            console.log("[FaceCapture] Arrêt des pistes du flux webcam.");
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }
        if (this.videoElement) {
            this.videoElement.srcObject = null;
        }
    }
}

// Exposition globale
window.FaceCapture = new FaceCapture();
