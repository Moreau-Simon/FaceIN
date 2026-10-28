# FaceIn — Interface Web Frontend (Phase 3)

Ce module fournit l'interface utilisateur pour le système d'authentification biométrique décentralisé **FaceIn**.

L'application s'exécute **intégralement dans le navigateur** en utilisant :
- **face-api.js** : Détection du visage et extraction du vecteur descripteur 128D.
- **snarkjs & circomlibjs** : Calcul de l'engagement Poseidon et génération de preuve Zero-Knowledge Proof (Groth16).
- **IndexedDB (`FaceInDB`)** : Stockage chiffré/local du vecteur de référence sur l'appareil de l'utilisateur.

> 🔒 **Garantie de confidentialité :** Aucune image ni vecteur biométrique brut ne transite sur le réseau. Seul l'engagement cryptographique (lors de l'inscription) et la preuve mathématique ZKP (lors de la connexion) sont transmis aux nœuds du réseau.

---

## 📁 Architecture des fichiers

```text
frontend/
├── index.html              # Page principale (onglets Inscription & Connexion, affichage vidéo, statut et logs)
├── css/
│   └── style.css           # Thème sombre moderne et ergonomique
├── js/
│   ├── config.js           # Constantes globales (URL API, facteur d'échelle, seuil ZKP, chemins)
│   ├── storage.js          # Gestionnaire IndexedDB (sauvegarde locale du descripteur Float64Array)
│   ├── face-capture.js     # Gestion du flux vidéo webcam et modèles face-api.js
│   ├── zkp-engine.js       # Arbre Poseidon (circomlibjs) et générateur de preuve Groth16 (snarkjs)
│   └── facein-core.js      # Orchestrateur liant l'UI, l'IA, la crypto et les appels API Gateway
├── models/                 # Modèles de réseaux de neurones face-api.js
├── circuit/                # Fichiers compilés du circuit Circom (distance.wasm, distance.zkey)
└── README.md               # Ce guide d'installation et d'exécution
```

---

## 🚀 Guide d'installation et démarrage

### 1. Télécharger les modèles face-api.js

L'application nécessite les modèles pré-entraînés pour la détection SSD MobileNet V1, les 68 points de repère faciaux, et l'extraction de descripteur de visage.

Placez-vous dans le dossier `frontend/models/` et téléchargez les 7 fichiers requis depuis le dépôt officiel :

```bash
cd frontend/models

# Base URL des poids officiels
BASE_URL="https://raw.githubusercontent.com/justadudewhohacks/face-api.js/master/weights"

# 1. ssdMobilenetv1
curl -O "$BASE_URL/ssd_mobilenetv1_model-weights_manifest.json"
curl -O "$BASE_URL/ssd_mobilenetv1_model-shard1"

# 2. faceLandmark68Net
curl -O "$BASE_URL/face_landmark_68_model-weights_manifest.json"
curl -O "$BASE_URL/face_landmark_68_model-shard1"

# 3. faceRecognitionNet
curl -O "$BASE_URL/face_recognition_model-weights_manifest.json"
curl -O "$BASE_URL/face_recognition_model-shard1"
curl -O "$BASE_URL/face_recognition_model-shard2"

cd ../..
```

---

### 2. Copier les fichiers du circuit ZKP

Après compilation du circuit Circom (Phase 2), copiez les artéfacts vers `frontend/circuit/` :

```bash
mkdir -p frontend/circuit
cp circuits/build/distance_js/distance.wasm frontend/circuit/
cp circuits/build/distance.zkey frontend/circuit/
```

Vérifiez que les chemins correspondent à ceux définis dans [js/config.js](file:///Users/ddeci/Documents/BUT3/SEMESTRE_5/SAE/FaceIN/frontend/js/config.js) :
- `WASM_PATH`: `./circuit/distance.wasm`
- `ZKEY_PATH`: `./circuit/distance.zkey`

---

### 3. Démarrer un serveur HTTP statique

Pour des raisons de sécurité du navigateur (`getUserMedia`, WebAssembly et requêtes CORS vers l'API), la page doit impérativement être servie via HTTP/HTTPS (l'ouverture directe en `file://` bloque la caméra et les Web Workers).

Vous pouvez utiliser n'importe quel serveur statique :

#### Avec Python 3 :
```bash
cd frontend
python3 -m http.server 3000
```

#### Avec Node.js (npx serve) :
```bash
npx serve frontend -p 3000
```

---

### 4. Ouvrir dans le navigateur

1. Rendez-vous sur [http://localhost:3000](http://localhost:3000).
2. Autorisez l'accès à la webcam lorsque le navigateur vous le demande.
3. Vérifiez dans le **Journal d'activité** au bas de la page que la caméra et les bibliothèques sont correctement initialisées.

---

## 🔄 Flux opérationnels

### Inscription (Tab "Inscription")
1. Saisissez votre identifiant / pseudo (ex : `alice_92`).
2. Positionnez votre visage dans l'ovale guide de la caméra.
3. Cliquez sur **S'inscrire** :
   - Le modèle face-api extrait le vecteur descripteur à 128 dimensions.
   - Le vecteur est sauvegardé localement dans `IndexedDB` sous la base `FaceInDB` (clé `alice_92`).
   - Le descripteur est mis à l'échelle ($\times 10\,000$) et condensé via un arbre Poseidon (8×Poseidon(16) → 2×Poseidon(4) → 1×Poseidon(2)).
   - L'engagement Poseidon public est transmis à l'API Gateway via `POST http://localhost:8000/api/register` avec `{ user_id, commitment }`.

### Connexion (Tab "Connexion")
1. Saisissez votre pseudo (doit correspondre à l'inscription).
2. Cliquez sur **Se connecter** :
   - Le vecteur de référence est extrait de l'IndexedDB locale.
   - Un nouveau vecteur du jour est capturé via la caméra.
   - Le client réclame un nonce anti-rejeu frais via `GET http://localhost:8000/api/nonce/{userId}`.
   - Le moteur ZKP génère une preuve Groth16 prouvant que :
     1. La distance euclidienne au carré entre les deux vecteurs est $\le \text{seuil}$ (`6000000`).
     2. Le haché Poseidon du vecteur de référence correspond exactement à l'engagement public.
   - La preuve et les signaux publics sont envoyés via `POST http://localhost:8000/api/authenticate`.
   - Le réseau valide la preuve sans jamais avoir eu accès au visage ni aux vecteurs.
