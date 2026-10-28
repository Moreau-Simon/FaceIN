/**
 * FaceIn - Configuration Frontend
 * Centralisation des constantes et paramètres de l'application
 */
const CONFIG = {
    // URL de base de l'API Gateway FaceIn
    API_BASE_URL: 'http://localhost:8000/api',

    // Facteur d'échelle pour convertir les descripteurs flottants face-api.js (-1..1) en entiers Circom
    SCALE_FACTOR: 10000,

    // Seuil de distance euclidienne au carré dans l'espace mis à l'échelle
    // Pour une distance euclidienne seuil de 0.6 :
    // (0.6 * 10000)^2 = 6000^2 = 36 000 000
    DISTANCE_THRESHOLD: 36000000,

    // Chemins vers les fichiers compilés du circuit ZKP
    WASM_PATH: './circuit/distance.wasm',
    ZKEY_PATH: './circuit/distance.zkey',

    // Chemin vers les modèles pré-entraînés face-api.js
    MODELS_PATH: './models'
};

// Exposition sur l'objet global window pour les autres modules
window.CONFIG = CONFIG;
