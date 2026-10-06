"""
Structure d'arbre de Merkle utilisée pour vérifier la cohérence des
engagements/données d'aide entre noeuds sans transférer toute la base.

A implémenter :
    - construction de l'arbre à partir de la liste des engagements connus
    - calcul de la racine (hash récursif des feuilles vers le sommet)
    - fonction de comparaison entre deux racines
    - fonction d'identification des branches divergentes (resync ciblée)

Peut être développé avec des données de test factices en attendant
le schéma final de la table engagements_cryptographiques côté BDD.
"""
