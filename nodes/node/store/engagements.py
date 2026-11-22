"""
Gestionnaire de stockage persistant pour les engagements cryptographiques (commitments).

Conserve les engagements calculés (hachage Poseidon du vecteur biométrique de référence)
associés à chaque identifiant utilisateur sur les nœuds de vérification.

Caractéristiques (PROMPT 4) :
- Thread-safe pour les accès concurrents gRPC.
- Persistance atomique sur disque (écriture temporaire + os.replace pour éviter la corruption).
- Prise en charge des statuts (actif / révoqué) et de l'horodatage.
- Idempotence face aux messages reçus en double ou désordonnés.
- Résistant aux redémarrages et arrêts intempestifs.
"""

import json
import logging
import os
import tempfile
import threading
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_PERSISTENCE_PATH = "/app/data/engagements.json"


class EngagementsStore:
    """Magasin thread-safe et persistant pour les engagements cryptographiques."""

    def __init__(self, persistence_file: Optional[str] = None) -> None:
        """Initialise le magasin d'engagements et charge les données persistantes."""
        self._engagements: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._file = persistence_file or os.getenv(
            "ENGAGEMENTS_STORE_FILE", DEFAULT_PERSISTENCE_PATH
        )
        self._load()

    def _load(self) -> None:
        """Charge les engagements depuis le fichier JSON persistant si présent."""
        if self._file and os.path.exists(self._file):
            try:
                with open(self._file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        for k, v in data.items():
                            user_id = str(k)
                            # Rétrocompatibilité : prise en charge format chaîne ou dictionnaire
                            if isinstance(v, str):
                                self._engagements[user_id] = {
                                    "commitment": v,
                                    "statut": "actif",
                                    "updated_at": 0.0,
                                    "version": 1,
                                }
                            elif isinstance(v, dict) and "commitment" in v:
                                self._engagements[user_id] = {
                                    "commitment": str(v["commitment"]),
                                    "statut": str(v.get("statut", "actif")),
                                    "updated_at": float(v.get("updated_at", 0.0)),
                                    "version": int(v.get("version", 1)),
                                    "raison": v.get("raison", ""),
                                }
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
        """Sauvegarde les engagements sur disque de manière atomique."""
        if not self._file:
            return

        try:
            parent_dir = os.path.dirname(os.path.abspath(self._file))
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)

            # Écriture dans un fichier temporaire dans le même répertoire puis remplacement atomique
            tmp_fd, tmp_path = tempfile.mkstemp(
                dir=parent_dir, prefix="engagements_", suffix=".tmp"
            )
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                json.dump(self._engagements, f, indent=2)

            os.replace(tmp_path, self._file)
        except Exception as e:
            logger.warning(
                "Impossible de persister les engagements dans %s : %s",
                self._file,
                e,
            )
            if "tmp_path" in locals() and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

    def save(
        self,
        user_id: str,
        commitment: str,
        timestamp: Optional[float] = None,
        version: Optional[int] = None,
    ) -> None:
        """Enregistre ou met à jour l'engagement pour un utilisateur (idempotent)."""
        now = time.time() if timestamp is None else float(timestamp)
        with self._lock:
            current = self._engagements.get(user_id)
            if current and current.get("updated_at", 0.0) > now:
                logger.info(
                    "Mise à jour ignorée pour '%s' : version plus récente déjà présente.",
                    user_id,
                )
                return

            new_version = (
                (current.get("version", 0) + 1)
                if current and version is None
                else (int(version) if version is not None else 1)
            )

            self._engagements[user_id] = {
                "commitment": str(commitment),
                "statut": "actif",
                "updated_at": now,
                "version": new_version,
            }
            self._persist()

    def revoke(
        self,
        user_id: str,
        raison: str = "",
        timestamp: Optional[float] = None,
    ) -> bool:
        """Révoque un engagement existant de façon idempotente."""
        now = time.time() if timestamp is None else float(timestamp)
        with self._lock:
            current = self._engagements.get(user_id)
            if not current:
                return False

            if current.get("statut") == "revoque":
                return True

            current["statut"] = "revoque"
            current["raison"] = str(raison)
            current["updated_at"] = now
            current["version"] = current.get("version", 1) + 1
            self._persist()
            return True

    def get(self, user_id: str) -> Optional[str]:
        """Retourne l'engagement actif de l'utilisateur s'il existe et n'est pas révoqué."""
        with self._lock:
            item = self._engagements.get(user_id)
            if item and item.get("statut") == "actif":
                return item["commitment"]
            return None

    def exists(self, user_id: str) -> bool:
        """Vérifie si un engagement actif existe pour cet utilisateur."""
        with self._lock:
            item = self._engagements.get(user_id)
            return bool(item and item.get("statut") == "actif")

    def all(self) -> Dict[str, str]:
        """Retourne une copie de tous les engagements ACTIFS sous forme {user_id: commitment}."""
        with self._lock:
            return {
                k: v["commitment"]
                for k, v in self._engagements.items()
                if v.get("statut") == "actif"
            }

    def all_entries(self) -> Dict[str, Dict[str, Any]]:
        """Retourne une copie intégrale de toutes les entrées (actives et révoquées)."""
        with self._lock:
            return {k: dict(v) for k, v in self._engagements.items()}

    def count(self) -> int:
        """Retourne le nombre d'engagements actifs stockés."""
        with self._lock:
            return sum(
                1 for v in self._engagements.values() if v.get("statut") == "actif"
            )

    def sync_batch(self, entries: List[Dict[str, Any]]) -> int:
        """Synchronise un lot d'engagements (rattrapage de nœud) de façon idempotente."""
        nb_updates = 0
        with self._lock:
            for entry in entries:
                uid = str(entry.get("utilisateur_id") or entry.get("user_id"))
                comm = str(entry.get("commitment") or entry.get("valeur", ""))
                statut = str(entry.get("statut", "actif"))
                ts = float(entry.get("updated_at") or entry.get("timestamp") or time.time())
                ver = int(entry.get("version", 1))

                current = self._engagements.get(uid)
                if current and current.get("updated_at", 0.0) >= ts:
                    continue

                self._engagements[uid] = {
                    "commitment": comm,
                    "statut": statut,
                    "updated_at": ts,
                    "version": ver,
                    "raison": entry.get("raison", ""),
                }
                nb_updates += 1

            if nb_updates > 0:
                self._persist()

        return nb_updates
