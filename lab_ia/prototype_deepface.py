import sys
import argparse
# Importation de DeepFace
from deepface import DeepFace

def main():
    parser = argparse.ArgumentParser(description="Laboratoire IA - Test avec DeepFace (ArcFace)")
    parser.add_argument("image1", help="Image 1")
    parser.add_argument("image2", help="Image 2")
    args = parser.parse_args()

    print(f"Comparaison avec DeepFace (Modèle: ArcFace) en cours...")
    
    try:
        # 1. Extraction pure du vecteur (pour comprendre ce qui ira dans le ZKP)
        # On demande à extraire les caractéristiques avec le modèle ArcFace
        representations = DeepFace.represent(img_path=args.image1, model_name="ArcFace", enforce_detection=False)
        vector = representations[0]["embedding"]
        
        print("\n" + "="*40)
        print("      EXTRACTION DU VECTEUR")
        print("="*40)
        print(f"Taille du vecteur : {len(vector)} dimensions (Attention, c'est lourd pour Circom !)")
        print(f"Aperçu du vecteur : {vector[:5]}...\n")

        # 2. Vérification complète automatique (calcul de distance + seuil intégré)
        result = DeepFace.verify(
            img1_path=args.image1, 
            img2_path=args.image2, 
            model_name="ArcFace",
            distance_metric="euclidean_l2" # Métrique recommandée pour ZKP
        )
        
        print("="*40)
        print("      RÉSULTATS DE LA VÉRIFICATION")
        print("="*40)
        print(f"Distance calculée : {result['distance']:.4f}")
        print(f"Seuil maximum autorisé par ArcFace : {result['threshold']:.4f}")
        
        if result["verified"]:
            print("✅ AUTHENTIFICATION RÉUSSIE : C'est la même personne.")
        else:
            print("❌ AUTHENTIFICATION ÉCHOUÉE : Personnes différentes.")

    except Exception as e:
        print(f"Erreur avec DeepFace : {e}")

if __name__ == "__main__":
    main()
