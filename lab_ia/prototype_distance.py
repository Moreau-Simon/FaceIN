import face_recognition
import numpy as np
import sys
import argparse

def main():
    parser = argparse.ArgumentParser(description="Laboratoire IA - Calcul de distance biométrique (Euclidienne)")
    parser.add_argument("image1", help="Chemin vers la première image de référence (ex: inscription.jpg)")
    parser.add_argument("image2", help="Chemin vers la deuxième image à tester (ex: connexion.jpg)")
    args = parser.parse_args()

    print(f"Chargement des images: {args.image1} et {args.image2}...")
    try:
        img1 = face_recognition.load_image_file(args.image1)
        img2 = face_recognition.load_image_file(args.image2)
    except FileNotFoundError as e:
        print(f"Erreur : Image introuvable. {e}")
        sys.exit(1)

    print("Extraction des vecteurs à 128 dimensions...")
    # Extraire les encodages (on prend le premier visage trouvé sur l'image)
    encodings1 = face_recognition.face_encodings(img1)
    encodings2 = face_recognition.face_encodings(img2)
    
    if not encodings1:
        print(f"Erreur : Aucun visage détecté dans {args.image1}")
        sys.exit(1)
    if not encodings2:
        print(f"Erreur : Aucun visage détecté dans {args.image2}")
        sys.exit(1)
        
    vector1 = encodings1[0]
    vector2 = encodings2[0]

    # Calcul de la distance Euclidienne
    # C'est ce calcul exact (une boucle de soustractions au carré) qui sera recodé dans Circom (ZKP) !
    distance = np.linalg.norm(vector1 - vector2)
    
    # La documentation de face_recognition recommande un seuil strict de 0.6
    seuil = 0.6
    
    print("\n" + "="*40)
    print("      RÉSULTATS DU LABORATOIRE IA")
    print("="*40)
    print(f"Taille du vecteur IA : {len(vector1)} (Parfait pour alléger le ZKP)")
    print(f"Distance mathématique: {distance:.4f}")
    
    print("\n--- DÉCISION ---")
    if distance <= seuil:
        print(f"✅ AUTHENTIFICATION RÉUSSIE (Distance <= {seuil})")
        print("L'IA considère que c'est la même personne.")
    else:
        print(f"❌ AUTHENTIFICATION ÉCHOUÉE (Distance > {seuil})")
        print("L'IA considère qu'il s'agit d'un imposteur (ou de mauvaises conditions).")

if __name__ == "__main__":
    main()
