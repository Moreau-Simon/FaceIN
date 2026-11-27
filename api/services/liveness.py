"""
Défis de vie (liveness) liés cryptographiquement à la session FaceIN.

Architecture B (chantier 11) :
- Les défis sont DÉRIVÉS du nonce de session : HMAC(secret, utilisateur, service, nonce).
  Aucun stockage n'est nécessaire, toutes les instances de l'API obtiennent la même
  liste, et le failover entre nœuds n'a aucun effet sur les défis.
- Le nonce étant déjà un signal public de la preuve Groth16, les défis sont liés
  indirectement à la preuve : une preuve d'une autre session impose d'autres défis.
- /api/nonce renvoie la liste ordonnée des défis, leur expiration et un jeton HMAC
  qui authentifie (utilisateur, service, nonce, expiration, défis).
- /api/authenticate exige un rapport d'exécution : le serveur vérifie le jeton,
  l'expiration, la liste exacte et ORDONNÉE des défis, et la plausibilité temporelle.

LIMITE DE SÉCURITÉ (à ne pas sur-interpréter) :
le rapport est produit par le navigateur, c'est-à-dire par du JavaScript que
l'utilisateur contrôle. Ce contrôle garantit qu'un rapport ne peut être ni rejoué,
ni transposé à une autre session, un autre utilisateur ou un autre service, et qu'un
client sans module de liveness est refusé. Il NE PROUVE PAS que les défis ont
réellement été exécutés devant la caméra : un client modifié peut produire un
rapport conforme. Seule une attestation matérielle (passkey WebAuthn avec
vérification de l'utilisateur, voir services/webauthn_service.py) apporte une
garantie côté serveur, sans que les images ne quittent l'appareil.
"""

import hashlib
import hmac
import time
from typing import Any, List, Optional, Tuple

try:
    from services.challenge_secret import charger_secret, comparer, signer
except ImportError:
    from api.services.challenge_secret import charger_secret, comparer, signer

# Défis reconnus par frontend/js/liveness.js
DEFIS_DISPONIBLES = ["blink", "turn_left", "turn_right", "smile"]
NOMBRE_DEFIS = 2

# Service destinataire des nonces émis pour l'API Gateway (identique au
# service_cible transmis aux nœuds par services/grpc_bridge.py)
SERVICE_CIBLE = "FaceIn-Gateway"

# Bornes de plausibilité temporelle (alignées sur frontend/js/liveness.js)
DUREE_MIN_DEFI_MS = 150        # un défi réel prend au moins quelques images
DUREE_MAX_DEFI_MS = 10_000     # DUREE_MAX_DEFI_MS du frontend
DUREE_MAX_SEQUENCE_MS = 60_000  # durée de vie d'un nonce
TAILLE_MAX_RAPPORT = 16         # nombre maximal d'entrées acceptées

DOMAINE_DERIVATION = "FaceIN-liveness-derivation-v1"
DOMAINE_JETON = "FaceIN-liveness-jeton-v1"


def _flux_aleatoire(user_id: str, service: str, nonce: str):
    """Flux d'octets déterministe : HMAC-SHA256 en mode compteur."""
    cle = charger_secret()
    compteur = 0
    while True:
        message = "|".join(
            (DOMAINE_DERIVATION, str(compteur), user_id, service, nonce.lower())
        ).encode("utf-8")
        for octet in hmac.new(cle, message, hashlib.sha256).digest():
            yield octet
        compteur += 1


def deriver_defis(user_id: str, nonce: str, service: str = SERVICE_CIBLE) -> List[str]:
    """
    Tire NOMBRE_DEFIS défis distincts et ordonnés, de façon déterministe à partir du
    nonce (tirage sans biais : rejet des octets hors plage).
    """
    restants = list(DEFIS_DISPONIBLES)
    choisis: List[str] = []
    flux = _flux_aleatoire(user_id, service, nonce)
    while len(choisis) < min(NOMBRE_DEFIS, len(DEFIS_DISPONIBLES)):
        n = len(restants)
        limite = 256 - (256 % n)
        octet = next(flux)
        if octet >= limite:
            continue
        choisis.append(restants.pop(octet % n))
    return choisis


def calculer_jeton(
    user_id: str, nonce: str, expires_at: int, defis: List[str], service: str = SERVICE_CIBLE
) -> str:
    """Jeton HMAC authentifiant le contexte complet des défis de la session."""
    return signer(
        DOMAINE_JETON, user_id, service, nonce.lower(), str(int(expires_at)), ",".join(defis)
    )


def preparer_defis(user_id: str, nonce: str, expires_at: int) -> Tuple[List[str], str]:
    """Retourne (défis ordonnés, jeton) à transmettre au client avec le nonce."""
    defis = deriver_defis(user_id, nonce)
    return defis, calculer_jeton(user_id, nonce, expires_at, defis)


def verifier_rapport(
    user_id: str,
    nonce: str,
    rapport: Optional[Any],
    maintenant: Optional[float] = None,
    service: str = SERVICE_CIBLE,
) -> Tuple[bool, str]:
    """
    Vérifie le rapport de défis transmis à /authenticate.

    rapport : objet avec expires_at (int), jeton (hex) et defis
              (liste de {type, debut_ms, fin_ms}) — voir models.LivenessReport.
    Retourne (True, "") si conforme, sinon (False, raison).
    """
    if rapport is None:
        return False, "Rapport de défis de vie absent : module de liveness requis"

    instant = time.time() if maintenant is None else float(maintenant)
    expires_at = int(rapport.expires_at)

    # 1. Contexte authentifié (utilisateur, service, nonce, expiration, liste des défis)
    defis_attendus = deriver_defis(user_id, nonce, service)
    jeton_attendu = calculer_jeton(user_id, nonce, expires_at, defis_attendus, service)
    if not comparer(jeton_attendu, rapport.jeton):
        return False, "Défis de vie non associés à cette session"

    # 2. Expiration (l'horloge du serveur fait foi)
    if instant > expires_at:
        return False, "Défis de vie expirés"

    # 3. Liste exacte et ordre d'exécution
    executes = list(rapport.defis)
    if len(executes) > TAILLE_MAX_RAPPORT:
        return False, "Rapport de défis de vie trop volumineux"
    types = [d.type for d in executes]
    if sorted(types) != sorted(defis_attendus):
        return False, "Défis de vie incomplets ou non conformes"
    if types != defis_attendus:
        return False, "Défis de vie exécutés dans le mauvais ordre"

    # 4. Plausibilité temporelle (horodatages du client, contrôle de cohérence seulement)
    fin_precedente = None
    for defi in executes:
        duree = defi.fin_ms - defi.debut_ms
        if duree < DUREE_MIN_DEFI_MS or duree > DUREE_MAX_DEFI_MS:
            return False, "Durée d'exécution d'un défi de vie non plausible"
        if fin_precedente is not None and defi.debut_ms < fin_precedente:
            return False, "Chronologie des défis de vie incohérente"
        fin_precedente = defi.fin_ms
    if executes[-1].fin_ms - executes[0].debut_ms > DUREE_MAX_SEQUENCE_MS:
        return False, "Séquence de défis de vie trop longue"

    return True, ""
