/**
 * FaceIn - Configuration Frontend
 * Centralisation des constantes et paramètres de l'application
 */
const CONFIG = {
  // URL de base de l'API Gateway FaceIn
  API_BASE_URL: "http://localhost:8000/api",

  // Facteur d'échelle pour convertir les descripteurs flottants face-api.js (-1..1) en entiers Circom
  SCALE_FACTOR: 10000,

  // Seuil de distance euclidienne au carré dans l'espace mis à l'échelle.
  // 0.40 : une photo de l'utilisateur teste à 0.4587 (REJETÉE), les visages
  // réels à 0.29-0.32 (ACCEPTÉS). L'ancien 0.6 laissait passer la photo.
  DISTANCE_THRESHOLD: 16000000, // = (0.40 * 10000)^2

  // Chemins vers les fichiers compilés du circuit ZKP
  WASM_PATH: "./circuit/distance.wasm",
  ZKEY_PATH: "./circuit/distance.zkey",

  // Chemin vers les modèles pré-entraînés face-api.js
  MODELS_PATH: "./models",
};

// Exposition sur l'objet global window pour les autres modules
window.CONFIG = CONFIG;
