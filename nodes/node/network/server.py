"""
Serveur gRPC du noeud pour les échanges de synchronisation entre pairs,
le consensus de vote et la vérification des preuves cryptographiques ZKP.
"""

import logging
import os
import uuid
from concurrent import futures
from pathlib import Path

import grpc
from grpc_health.v1 import health, health_pb2, health_pb2_grpc

import sync_pb2
import sync_pb2_grpc
import consensus_pb2
import consensus_pb2_grpc
import verification_pb2
import verification_pb2_grpc

from consensus.validation import empaqueter_preuve

logger = logging.getLogger(__name__)

GRPC_SERVER_OPTIONS = (
    ("grpc.keepalive_permit_without_calls", 1),
    ("grpc.http2.min_ping_interval_without_data_ms", 300_000),
    ("grpc.http2.max_ping_strikes", 2),
)


class ErreurDemarrageServeur(RuntimeError):
    """Échec du démarrage du serveur gRPC du nœud."""


def _tls_enabled() -> bool:
    return os.getenv("TLS_ENABLED", "true").strip().lower() in {
        "1", "true", "yes", "on"
    }


def charger_credentials_serveur():
    """Charge les certificats TLS du nœud courant."""
    ca_path = os.getenv("TLS_CA_CERT", "/app/certs/ca.crt")
    cert_path = os.getenv("TLS_CERT")
    key_path = os.getenv("TLS_KEY")

    if not cert_path or not key_path:
        raise ErreurDemarrageServeur(
            "TLS_CERT et TLS_KEY doivent être configurés"
        )

    try:
        ca = Path(ca_path).read_bytes()
        cert = Path(cert_path).read_bytes()
        key = Path(key_path).read_bytes()
    except OSError as exc:
        raise ErreurDemarrageServeur(
            f"Impossible de charger les certificats TLS : {exc}"
        ) from exc

    return grpc.ssl_server_credentials(
        [(key, cert)],
        root_certificates=ca,
        require_client_auth=True,
    )

class SyncService(sync_pb2_grpc.SyncServiceServicer):
    """Implémente le service de synchronisation exposé par le noeud."""

    def __init__(self, node_id: str):
        self.node_id = node_id

    def Heartbeat(self, request, context):
        """Confirme que le noeud répond aux appels gRPC."""
        logger.debug(
            "[%s] Battement de cœur reçu de %s",
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
    """Service de vérification exposé aux clients (API, démo partenaire).

    ``store`` (optionnel) est le magasin d'engagements du noeud : sans lui,
    ``RecupererDonneeAide`` répond « utilisateur inconnu ».
    """

    def __init__(self, node_id, nonces, decider_fn, fabriquer_token, store=None):
        self.node_id = node_id
        self._nonces = nonces
        self._decider = decider_fn          # demande -> bool
        self._fabriquer_token = fabriquer_token
        self._store = store

    def RecupererDonneeAide(self, request, context):
        """Retourne l'engagement cryptographique (Poseidon) de l'utilisateur.

        Nom de méthode conservé pour rétro-compatibilité avec le protocole initial.
        """
        engagement = (
            self._store.get(request.utilisateur_id)
            if self._store is not None
            else None
        )
        if engagement is None:
            logger.warning(
                "[%s] Aucun engagement trouvé pour l'utilisateur %s",
                self.node_id,
                request.utilisateur_id,
            )
            return verification_pb2.ReponseDonneeAide(trouve=False)

        return verification_pb2.ReponseDonneeAide(
            trouve=True,
            donnee_aide=str(engagement),
            parametres_extraction="",
        )

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

        # Les signaux publics ZKP voyagent avec la preuve dans le champ
        # ``preuve_zkp`` de la demande de vote (voir empaqueter_preuve).
        # Sans signaux publics, la preuve est transmise telle quelle.
        preuve = request.preuve_zkp
        if request.public_signals:
            try:
                preuve = empaqueter_preuve(preuve, request.public_signals)
            except ValueError:
                return verification_pb2.ReponseVerification(
                    accepte=False, raison_refus="preuve ZKP illisible")

        demande = consensus_pb2.DemandeVote(
            id_demande=str(uuid.uuid4()),
            noeud_initiateur=self.node_id,
            utilisateur_id=request.utilisateur_id,
            preuve_zkp=preuve,
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
    """Démarre le service gRPC et retourne son serveur actif.

    Le magasin d'engagements est celui du ``verifier`` (attribut ``store``),
    s'il en expose un : ``VerificateurZKP`` le fait, ``valider_avec_mock`` non.
    """
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10),
        options=GRPC_SERVER_OPTIONS,
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
        VerificationService(
            node_id,
            nonces,
            decider_fn,
            fabriquer_token,
            store=getattr(verifier, "store", None),
        ),
        server,
    )

    health_servicer = health.HealthServicer()
    health_servicer.set("", health_pb2.HealthCheckResponse.SERVING)
    health_pb2_grpc.add_HealthServicer_to_server(health_servicer, server)

    if _tls_enabled():
        credentials = charger_credentials_serveur()
        bound_port = server.add_secure_port(
            f"0.0.0.0:{port}", credentials
        )
    else:
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