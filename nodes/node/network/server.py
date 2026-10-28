"""
Serveur gRPC du noeud pour les échanges de synchronisation entre pairs.

Le service SyncService répond actuellement aux heartbeats.
"""
import logging
import uuid
from concurrent import futures

import grpc

import sync_pb2
import sync_pb2_grpc
import consensus_pb2
import consensus_pb2_grpc
import verification_pb2
import verification_pb2_grpc

logger = logging.getLogger(__name__)


class ErreurDemarrageServeur(RuntimeError):
    """Échec du démarrage du serveur gRPC du nœud."""


class SyncService(sync_pb2_grpc.SyncServiceServicer):
    """Implémente le service de synchronisation exposé par le noeud."""

    def __init__(self, node_id):
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

class ConsensusService(consensus_pb2_grpc.ConsensusServiceServicer):
    def __init__(self, node_id, verifier):
        self.node_id = node_id
        self._verifier = verifier

    def DemanderVote(self, request, context):
        try:
            accepte = self._verifier(
                request.utilisateur_id,
                request.preuve_zkp,
                request.nonce,
                request.service_cible,
            )
            raison = ""
        except Exception:
            logger.exception("[%s] Erreur de vérification", self.node_id)
            accepte, raison = False, "erreur de vérification"

        return consensus_pb2.ReponseVote(
            noeud_id=self.node_id,
            id_demande=request.id_demande,
            vote=consensus_pb2.VOTE_POUR if accepte
                 else consensus_pb2.VOTE_CONTRE,
            raison=raison,
        )

class VerificationService(verification_pb2_grpc.VerificationServiceServicer):
    def __init__(self, node_id, nonces, decider_fn, fabriquer_token):
        self.node_id = node_id
        self._nonces = nonces
        self._decider = decider_fn          # demande -> bool
        self._fabriquer_token = fabriquer_token

    def RecupererDonneeAide(self, request, context):
        # À brancher sur la BDD. Provisoire : utilisateur inconnu.
        return verification_pb2.ReponseDonneeAide(trouve=False)

    def DemanderNonce(self, request, context):
        if not request.utilisateur_id:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "utilisateur_id requis")
        nonce, expiration = self._nonces.emettre(request.utilisateur_id)
        return verification_pb2.ReponseNonce(
            nonce=nonce, expiration_timestamp=expiration)

    def VerifierPreuve(self, request, context):
        if not self._nonces.consommer(request.utilisateur_id, request.nonce):
            return verification_pb2.ReponseVerification(
                accepte=False, raison_refus="nonce invalide ou expiré")

        demande = consensus_pb2.DemandeVote(
            id_demande=str(uuid.uuid4()),
            noeud_initiateur=self.node_id,
            utilisateur_id=request.utilisateur_id,
            preuve_zkp=request.preuve_zkp,
            nonce=request.nonce,
            service_cible=request.service_cible,
            timestamp=request.timestamp,
        )
        if not self._decider(demande):
            return verification_pb2.ReponseVerification(
                accepte=False, raison_refus="consensus non atteint")

        return verification_pb2.ReponseVerification(
            accepte=True, token=self._fabriquer_token(request.utilisateur_id),
            score_anomalie=0)

def start_grpc_server(
    node_id,
    port,
    verifier,
    nonces,
    decider_fn,
    fabriquer_token,
):
    """Démarre le service gRPC et retourne son serveur actif."""
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10)
    )

    sync_pb2_grpc.add_SyncServiceServicer_to_server(
        SyncService(node_id),
        server,
    )

    consensus_pb2_grpc.add_ConsensusServiceServicer_to_server(
        ConsensusService(node_id, verifier),
        server,
    )

    verification_pb2_grpc.add_VerificationServiceServicer_to_server(
        VerificationService(node_id, nonces, decider_fn, fabriquer_token),
        server,
    )

    bound_port = server.add_insecure_port(f"0.0.0.0:{port}")
    if bound_port == 0:
        raise ErreurDemarrageServeur(
            f"[{node_id}] Impossible d'ouvrir le port gRPC {port}"
        )

    server.start()

    logger.info(
        "[%s] Serveur gRPC démarré sur 0.0.0.0:%s",
        node_id,
        bound_port,
    )

    return server