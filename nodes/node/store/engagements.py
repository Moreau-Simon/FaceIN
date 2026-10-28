"""
Gestionnaire de stockage en mémoire pour les engagements cryptographiques (commitments).

Ce module permet de conserver les engagements calculés (hachage Poseidon du vecteur
biométrique de référence) associés à chaque identifiant utilisateur.
Il est conçu pour être thread-safe afin de supporter les accès concurrents
via le serveur gRPC du noeud.
"""

import json
import logging
import os
import threading
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class EngagementsStore:
    """
    Magasin thread-safe pour les engagements cryptographiques,
    avec support d'une persistance sur disque (fichier JSON optionnel).
    """

    def __init__(self, persistence_file: Optional[str] = None) -> None:
        """Initialise le magasin d'engagements avec un dictionnaire vide et charge la persistance."""
        self._engagements: Dict[str, str] = {}
        self._lock = threading.Lock()
        self._file = persistence_file or os.getenv("ENGAGEMENTS_STORE_FILE")
        self._load()

    def _load(self) -> None:
        """Charge les engagements depuis le fichier de persistance si disponible."""
        if self._file and os.path.exists(self._file):
            try:
                with open(self._file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        self._engagements.update(
                            {str(k): str(v) for k, v in data.items()}
                        )
                        logger.info(
                            "Engagements chargés depuis %s (%d entrées)",
                            self._file,
                            len(self._engagements),
                        )
            except Exception as e:
                logger.warning(
                    "Impossible de charger les engagements depuis %s : %s",
                    self._file,
                    e,
                )

    def _persist(self) -> None:
        """Sauvegarde les engagements dans le fichier persistant sous verrou."""
        if self._file:
            try:
                parent_dir = os.path.dirname(os.path.abspath(self._file))
                if parent_dir:
                    os.makedirs(parent_dir, exist_ok=True)
                with open(self._file, "w", encoding="utf-8") as f:
                    json.dump(self._engagements, f, indent=2)
            except Exception as e:
                logger.warning(
                    "Impossible de persister les engagements dans %s : %s",
                    self._file,
                    e,
                )

    def save(self, user_id: str, commitment: str) -> None:
        """
        Enregistre ou met à jour l'engagement cryptographique pour un utilisateur donné.

        Args:
            user_id: Identifiant unique de l'utilisateur.
            commitment: Hachage Poseidon de référence (sous forme de chaîne).
        """
        with self._lock:
            self._engagements[user_id] = str(commitment)
            self._persist()

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
