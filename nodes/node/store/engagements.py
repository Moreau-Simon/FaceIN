"""
Gestionnaire de stockage en mémoire pour les engagements cryptographiques (commitments).

Ce module permet de conserver les engagements calculés (hachage Poseidon du vecteur
biométrique de référence) associés à chaque identifiant utilisateur.
Il est conçu pour être thread-safe afin de supporter les accès concurrents
via le serveur gRPC du noeud.
"""

import threading
from typing import Dict, Optional


class EngagementsStore:
    """
    Magasin en mémoire thread-safe pour les engagements cryptographiques.
    """

    def __init__(self) -> None:
        """Initialise le magasin d'engagements avec un dictionnaire vide et un verrou."""
        self._engagements: Dict[str, str] = {}
        self._lock = threading.Lock()

    def save(self, user_id: str, commitment: str) -> None:
        """
        Enregistre ou met à jour l'engagement cryptographique pour un utilisateur donné.

        Args:
            user_id: Identifiant unique de l'utilisateur.
            commitment: Hachage Poseidon de référence (sous forme de chaîne).
        """
        with self._lock:
            self._engagements[user_id] = str(commitment)

    def get(self, user_id: str) -> Optional[str]:
        """
        Récupère l'engagement cryptographique associé à un utilisateur.

        Args:
            user_id: Identifiant de l'utilisateur recherché.

        Returns:
            L'engagement sous forme de chaîne si trouvé, sinon None.
        """
        with self._lock:
            return self._engagements.get(user_id)

    def exists(self, user_id: str) -> bool:
        """
        Vérifie si un engagement est enregistré pour cet utilisateur.

        Args:
            user_id: Identifiant de l'utilisateur.

        Returns:
            True si l'utilisateur existe dans le magasin, False sinon.
        """
        with self._lock:
            return user_id in self._engagements

    def all(self) -> Dict[str, str]:
        """
        Retourne une copie de tous les engagements stockés.
        Utilisé notamment pour la construction ou la synchronisation de l'arbre de Merkle.

        Returns:
            Un dictionnaire associant chaque identifiant à son engagement.
        """
        with self._lock:
            return dict(self._engagements)

    def count(self) -> int:
        """
        Retourne le nombre total d'engagements actuellement stockés.

        Returns:
            Nombre d'engagements enregistrés.
        """
        with self._lock:
            return len(self._engagements)
