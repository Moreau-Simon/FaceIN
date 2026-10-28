# Laboratoire IA : Prototypage du Seuil Biométrique

Ce dossier vous sert d'environnement de test pour comprendre et valider la biométrie (Phase 1 du projet) avant d'écrire le circuit cryptographique en Circom.

Nous utilisons `face_recognition` tel que recommandé par la SAE, car il génère des vecteurs de taille réduite (128 dimensions), ce qui est beaucoup plus léger à calculer mathématiquement pour la Preuve à Divulgation Nulle (ZKP).

## Comment l'utiliser ?

1. **Préparez un environnement virtuel Python** pour ne pas polluer votre système global :
   ```bash
   cd lab_ia
   python3 -m venv venv
   source venv/bin/activate
   ```

2. **Installez les dépendances** :
   ```bash
   pip install -r requirements.txt
   ```
   *(Note : `face_recognition` utilise `dlib` en coulisses. Sur Mac, vous aurez peut-être besoin d'installer cmake au préalable avec `brew install cmake`)*

3. **Faites vos tests avec deux photos !**
   Prenez une photo de vous (ex: `photo_inscription.jpg`) et une autre photo de vous (ex: `photo_connexion.jpg`), puis un imposteur (ex: `inconnu.jpg`). Mettez-les dans ce dossier.

   Lancez le script :
   ```bash
   python prototype_distance.py photo_inscription.jpg photo_connexion.jpg
   ```

## Pourquoi est-ce important pour la suite ?
Le calcul qui se passe à la ligne `np.linalg.norm(vector1 - vector2)` (La Distance Euclidienne) dans le script `prototype_distance.py` est **EXACTEMENT** la formule mathématique qu'il faudra programmer dans votre circuit **Circom** (Phase 2). Ce script vous permet de tester si un seuil d'acceptation de `0.6` est optimal pour votre projet réel.
