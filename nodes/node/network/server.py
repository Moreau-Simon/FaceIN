"""
Serveur gRPC du noeud pour les échanges de synchronisation entre pairs
et la vérification des preuves cryptographiques ZKP.
"""

import logging
import secrets
import threading
import time
from concurrent import futures
from typing import Optional

try:
    import grpc
except ImportError:
    grpc = None

try:
    import sync_pb2
    import sync_pb2_grpc
except ImportError:
    sync_pb2 = None
    sync_pb2_grpc = None

if sync_pb2 is None:
    class _MockSyncPb2:
        class PongNoeud:
            def __init__(self, noeud_id="", en_sante=False):
                self.noeud_id = noeud_id
                self.en_sante = en_sante

    sync_pb2 = _MockSyncPb2()

try:
    import verification_pb2
    import verification_pb2_grpc
except ImportError:
    verification_pb2 = None
    verification_pb2_grpc = None

if verification_pb2 is None:
    class _MockVerificationPb2:
        class ReponseDonneeAide:
            def __init__(self, trouve=False, donnee_aide="", parametres_extraction=""):
                self.trouve = trouve
                self.donnee_aide = donnee_aide
                self.parametres_extraction = parametres_extraction

        class ReponseNonce:
            def __init__(self, nonce="", expiration_timestamp=0):
                self.nonce = nonce
                self.expiration_timestamp = expiration_timestamp

        class ReponseVerification:
            def __init__(self, accepte=False, raison_refus="", token="", score_anomalie=0):
                self.accepte = accepte
                self.raison_refus = raison_refus
                self.token = token
                self.score_anomalie = score_anomalie

    verification_pb2 = _MockVerificationPb2()

try:
    from consensus import validation
    from store.engagements import EngagementsStore
except ImportError:
    try:
        from ..consensus import validation
        from ..store.engagements import EngagementsStore
    except ImportError:
        import sys
        import os
        sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
        from consensus import validation
        from store.engagements import EngagementsStore

logger = logging.getLogger(__name__)

# Classes de base conditionnelles pour permettre le chargement même hors conteneur
_SyncBase = sync_pb2_grpc.SyncServiceServicer if sync_pb2_grpc else object
_VerifBase = verification_pb2_grpc.VerificationServiceServicer if verification_pb2_grpc else object


class SyncService(_SyncBase):
    """Implémente le service de synchronisation exposé par le noeud."""

    def __init__(self, node_id: str):
        self.node_id = node_id

    def Heartbeat(self, request, context):
        """Confirme que le noeud répond aux appels gRPC."""
        logger.info(
            "[%s] Heartbeat reçu de %s",
            self.node_id,
            request.noeud_id,
        )

        return sync_pb2.PongNoeud(
            noeud_id=self.node_id,
            en_sante=True,
        )


class VerificationServiceImpl(_VerifBase):
    """
    Implémente le service gRPC de vérification d'authentification biométrique ZKP.
    """

    def __init__(self, node_id: str, store: Optional[EngagementsStore] = None):
        self.node_id = node_id
        self.store = store if store is not None else EngagementsStore()
        self._nonces = {}
        self._nonces_lock = threading.Lock()

    def RecupererDonneeAide(self, request, context):
        """
        Récupère l'engagement cryptographique (Poseidon) associé à un utilisateur.
        Nom de méthode conservé pour rétro-compatibilité avec le protocole initial.
        """
        user_id = request.utilisateur_id
        engagement = self.store.get(user_id)

        if engagement is not None:
            logger.info(
                "[%s] Engagement trouvé pour l'utilisateur %s",
                self.node_id,
                user_id,
            )
            return verification_pb2.ReponseDonneeAide(
                trouve=True,
                donnee_aide=str(engagement),
                parametres_extraction="",
            )
        else:
            logger.warning(
                "[%s] Aucun engagement trouvé pour l'utilisateur %s",
                self.node_id,
                user_id,
            )
            return verification_pb2.ReponseDonneeAide(
                trouve=False,
                donnee_aide="",
                parametres_extraction="",
            )

    def DemanderNonce(self, request, context):
        """
        Génère un nonce cryptographique éphémère anti-rejeu avec expiration à 60 secondes.
        """
        nonce = secrets.token_hex(16)
        expiration = int(time.time()) + 60

        with self._nonces_lock:
            now = time.time()
            # Nettoyage des nonces déjà expirés
            self._nonces = {k: v for k, v in self._nonces.items() if v["expires_at"] > now}
            self._nonces[nonce] = {
                "utilisateur_id": request.utilisateur_id,
                "expires_at": expiration,
            }

        logger.info(
            "[%s] Nonce généré pour l'utilisateur %s (expiration: %d)",
            self.node_id,
            request.utilisateur_id,
            expiration,
        )

        return verification_pb2.ReponseNonce(
            nonce=nonce,
            expiration_timestamp=expiration,
        )

    def VerifierPreuve(self, request, context):
        """
        Vérifie la preuve ZKP fournie par le client.
        1. Journalise la requête de vérification
        2. Recherche l'engagement enregistré de l'utilisateur
        3. Appelle validation.verifier_preuve() avec la preuve et l'engagement
        4. Retourne ReponseVerification(accepte=result, ...)
        """
        # 1. Journalisation de la demande
        logger.info(
            "[%s] Demande de vérification de preuve ZKP pour utilisateur=%s, service=%s",
            self.node_id,
            request.utilisateur_id,
            request.service_cible,
        )

        # 2. Recherche de l'engagement de l'utilisateur
        commitment = self.store.get(request.utilisateur_id)
        public_signals = list(request.public_signals) if hasattr(request, "public_signals") else []

        if commitment is None:
            if public_signals:
                # Lors des flux API récents, l'API transmet le commitment dans public_signals[0]
                commitment = public_signals[0]
                self.store.save(request.utilisateur_id, commitment)
                logger.info(
                    "[%s] Engagement pour %s synchronisé depuis les signaux publics : %s",
                    self.node_id,
                    request.utilisateur_id,
                    commitment,
                )
            else:
                logger.warning(
                    "[%s] Vérification échouée : utilisateur %s inconnu dans le magasin",
                    self.node_id,
                    request.utilisateur_id,
                )
                return verification_pb2.ReponseVerification(
                    accepte=False,
                    raison_refus="Utilisateur ou engagement introuvable",
                    token="",
                    score_anomalie=0,
                )

        # Vérification optionnelle du nonce si présent dans le cache
        with self._nonces_lock:
            info_nonce = self._nonces.pop(request.nonce, None)
            if info_nonce and info_nonce["expires_at"] < time.time():
                logger.warning(
                    "[%s] Nonce expiré pour l'utilisateur %s",
                    self.node_id,
                    request.utilisateur_id,
                )
                return verification_pb2.ReponseVerification(
                    accepte=False,
                    raison_refus="Nonce anti-rejeu expiré",
                    token="",
                    score_anomalie=0,
                )

        # Préparation des signaux publics : [engagementAttendu, seuilMax]
        public_signals = list(request.public_signals) if hasattr(request, "public_signals") else []
        if not public_signals:
            public_signals = [str(commitment)]
        else:
            # Vérifier que le signal public d'engagement correspond à la valeur enregistrée
            if str(public_signals[0]) != str(commitment):
                logger.warning(
                    "[%s] Incohérence d'engagement : stocké '%s' vs public '%s'",
                    self.node_id,
                    commitment,
                    public_signals[0],
                )
                return verification_pb2.ReponseVerification(
                    accepte=False,
                    raison_refus="L'engagement public ne correspond pas à l'engagement enregistré",
                    token="",
                    score_anomalie=0,
                )

        # 3. Appel de validation.verifier_preuve()
        est_valide = validation.verifier_preuve(
            preuve_zkp_json=request.preuve_zkp,
            public_signals=public_signals,
        )

        # 4. Renvoi du résultat
        if est_valide:
            jeton_auth = secrets.token_urlsafe(32)
            logger.info(
                "[%s] Authentification validée pour l'utilisateur %s",
                self.node_id,
                request.utilisateur_id,
            )
            return verification_pb2.ReponseVerification(
                accepte=True,
                raison_refus="",
                token=jeton_auth,
                score_anomalie=0,
            )
        else:
            logger.warning(
                "[%s] Preuve ZKP rejetée pour l'utilisateur %s",
                self.node_id,
                request.utilisateur_id,
            )
            return verification_pb2.ReponseVerification(
                accepte=False,
                raison_refus="Preuve ZKP invalide",
                token="",
                score_anomalie=0,
            )


def start_grpc_server(node_id: str, port: int, store: Optional[EngagementsStore] = None):
    """
    Démarre le serveur gRPC du noeud avec SyncService et VerificationService.
    """
    if store is None:
        store = EngagementsStore()

    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10)
    )

    if sync_pb2_grpc:
        sync_pb2_grpc.add_SyncServiceServicer_to_server(
            SyncService(node_id),
            server,
        )

    if verification_pb2_grpc:
        verification_pb2_grpc.add_VerificationServiceServicer_to_server(
            VerificationServiceImpl(node_id, store),
            server,
        )

    bound_port = server.add_insecure_port(f"0.0.0.0:{port}")
    if bound_port == 0:
        raise RuntimeError(
            f"[{node_id}] Impossible d'ouvrir le port gRPC {port}"
        )

    server.start()

    logger.info(
        "[%s] Serveur gRPC démarré sur 0.0.0.0:%s (SyncService + VerificationService)",
        node_id,
        bound_port,
    )

    return server