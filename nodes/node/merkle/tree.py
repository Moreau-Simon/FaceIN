"""
Arbre de Merkle SHA-256 pour la synchronisation d'état des engagements entre nœuds.

Choix cryptographique :
- Algorithme : SHA-256 (standard, déterministe, rapide, natif Python).
- Distinction architecturale : cet arbre sert uniquement à la détection de
  divergence et à la resynchronisation ciblée des engagements (actifs et
  révoqués) entre nœuds gRPC. Il est distinct du hachage Poseidon utilisé dans
  le circuit ZKP Groth16 pour les vecteurs biométriques.
- Séparation de domaine :
  - Arbre vide : SHA256(b"FACEIN:MERKLE:EMPTY")
  - Feuille    : SHA256(b"FACEIN:MERKLE:LEAF:" + json_canonique)
  - Nœud       : SHA256(b"FACEIN:MERKLE:NODE:" + gauche + b":" + droite)
- Ordre déterministe : les feuilles sont triées par ``user_id`` croissant.
"""

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Callable, Dict, List, Optional


EMPTY_ROOT_HASH = hashlib.sha256(b"FACEIN:MERKLE:EMPTY").hexdigest()


@dataclass(frozen=True)
class NoeudArbre:
    """Représente un nœud (interne ou feuille) dans l'arbre de Merkle."""

    chemin: str
    hash: str
    est_feuille: bool
    utilisateur_id: str = ""
    payload: Optional[Dict[str, Any]] = None
    gauche: Optional["NoeudArbre"] = None
    droite: Optional["NoeudArbre"] = None


def _hash_feuille(user_id: str, entry: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
    """Calcule le hash SHA-256 canonique d'une feuille d'engagement."""
    canonique = {
        "utilisateur_id": str(user_id),
        "commitment": str(entry.get("commitment", "")),
        "statut": str(entry.get("statut", "actif")),
        "version": int(entry.get("version", 1)),
        "updated_at": round(float(entry.get("updated_at", 0.0)), 6),
        "raison": str(entry.get("raison", "")),
    }
    serial = json.dumps(canonique, sort_keys=True, separators=(",", ":")).encode("utf-8")
    digest = hashlib.sha256(b"FACEIN:MERKLE:LEAF:" + serial).hexdigest()
    return digest, canonique


def _hash_noeud_interne(gauche_hash: str, droite_hash: str) -> str:
    """Calcule le hash SHA-256 d'un nœud interne à partir de ses deux enfants."""
    data = b"FACEIN:MERKLE:NODE:" + gauche_hash.encode("ascii") + b":" + droite_hash.encode("ascii")
    return hashlib.sha256(data).hexdigest()


class MerkleTree:
    """Arbre de Merkle binaire déterministe construit sur les engagements."""

    def __init__(self, entries: Optional[Dict[str, Dict[str, Any]]] = None) -> None:
        self._entries: Dict[str, Dict[str, Any]] = dict(entries or {})
        self._index: Dict[str, NoeudArbre] = {}
        self.racine: Optional[NoeudArbre] = self._construire()

    @property
    def root_hash(self) -> str:
        """Retourne le hash hexadécimal de la racine (stable même si vide)."""
        return self.racine.hash if self.racine is not None else EMPTY_ROOT_HASH

    @property
    def nb_feuilles(self) -> int:
        return len(self._entries)

    def _construire(self) -> Optional[NoeudArbre]:
        self._index.clear()
        if not self._entries:
            return None

        # Tri déterministe par user_id croissant
        feuilles_data: List[tuple[str, str, Dict[str, Any]]] = []
        for uid in sorted(self._entries.keys()):
            h, payload = _hash_feuille(uid, self._entries[uid])
            feuilles_data.append((uid, h, payload))

        def _build_sub(items: List[tuple[str, str, Dict[str, Any]]], chemin: str) -> NoeudArbre:
            if len(items) == 1:
                uid, h, payload = items[0]
                noeud = NoeudArbre(
                    chemin=chemin,
                    hash=h,
                    est_feuille=True,
                    utilisateur_id=uid,
                    payload=payload,
                )
                self._index[chemin] = noeud
                return noeud

            milieu = (len(items) + 1) // 2
            chemin_g = f"{chemin}.0" if chemin else "0"
            chemin_d = f"{chemin}.1" if chemin else "1"
            gauche = _build_sub(items[:milieu], chemin_g)
            droite = _build_sub(items[milieu:], chemin_d)
            noeud = NoeudArbre(
                chemin=chemin,
                hash=_hash_noeud_interne(gauche.hash, droite.hash),
                est_feuille=False,
                gauche=gauche,
                droite=droite,
            )
            self._index[chemin] = noeud
            return noeud

        return _build_sub(feuilles_data, "")

    def get_node(self, chemin: str = "") -> Optional[NoeudArbre]:
        """Retourne le nœud situé au chemin donné ('' = racine)."""
        return self._index.get(chemin)

    def get_branch(self, chemin: str = "") -> List[NoeudArbre]:
        """
        Retourne les nœuds à exposer pour ``RecupererBranche(chemin)``.

        - Si ``chemin`` désigne un nœud interne, retourne ses enfants directs.
        - Si ``chemin`` désigne une feuille, retourne la feuille elle-même.
        - Si l'arbre est vide ou le chemin inconnu, retourne une liste vide.
        """
        noeud = self._index.get(chemin)
        if noeud is None:
            return []
        if noeud.est_feuille:
            return [noeud]
        enfants: List[NoeudArbre] = []
        if noeud.gauche is not None:
            enfants.append(noeud.gauche)
        if noeud.droite is not None:
            enfants.append(noeud.droite)
        return enfants

    def all_leaves(self) -> List[NoeudArbre]:
        """Retourne toutes les feuilles de l'arbre dans l'ordre canonique."""
        return [
            self._index[c]
            for c in sorted(self._index.keys())
            if self._index[c].est_feuille
        ]

    @staticmethod
    def racines_identiques(racine_a: str, racine_b: str) -> bool:
        """Compare deux racines Merkle de façon stricte."""
        return bool(racine_a and racine_b and racine_a == racine_b)

    def trouver_feuilles_divergentes(
        self,
        fetch_branch_fn: Callable[[str], List[Any]],
        racine_distante: str,
    ) -> List[Dict[str, Any]]:
        """
        Identifie les feuilles divergentes ou manquantes par rapport à un pair
        sans transférer les branches dont les hashes coïncident.

        ``fetch_branch_fn(chemin)`` retourne la liste des nœuds distants
        (objets dotés des attributs ``chemin``, ``hash``, ``est_feuille``,
        ``utilisateur_id``, ``payload_json``).
        """
        if self.racines_identiques(self.root_hash, racine_distante):
            return []

        if racine_distante == EMPTY_ROOT_HASH:
            return []

        feuilles_a_sync: List[Dict[str, Any]] = []
        a_visiter: List[str] = [""]
        visites = set()

        while a_visiter:
            chemin = a_visiter.pop(0)
            if chemin in visites:
                continue
            visites.add(chemin)

            enfants_distants = fetch_branch_fn(chemin)
            if not enfants_distants:
                continue

            for enfant in enfants_distants:
                c = getattr(enfant, "chemin", "")
                h = getattr(enfant, "hash", "")
                est_feuille = bool(getattr(enfant, "est_feuille", False))
                noeud_local = self.get_node(c)

                # Sous-arbre identique -> on ne descend pas
                if noeud_local is not None and noeud_local.hash == h:
                    continue

                if est_feuille:
                    payload_raw = getattr(enfant, "payload_json", "")
                    if payload_raw:
                        try:
                            payload = json.loads(payload_raw)
                            if isinstance(payload, dict):
                                feuilles_a_sync.append(payload)
                        except json.JSONDecodeError:
                            pass
                else:
                    # Sous-arbre divergent ou inexistant localement -> descente ciblée
                    a_visiter.append(c)

        return feuilles_a_sync
