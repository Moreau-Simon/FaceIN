"""
Serveur gRPC du noeud pour les échanges de synchronisation entre pairs,
le consensus de vote et la vérification des preuves cryptographiques ZKP.
"""

import logging
import os
import threading
import time
import uuid
from concurrent import futures
from pathlib import Path
from types import SimpleNamespace

try:
    import grpc
    from grpc_health.v1 import health, health_pb2, health_pb2_grpc
except ImportError:
    grpc = None
    health = health_pb2 = health_pb2_grpc = None

try:
    import sync_pb2
    import sync_pb2_grpc
    import consensus_pb2
    import consensus_pb2_grpc
    import verification_pb2
    import verification_pb2_grpc
except ImportError:
    sync_pb2 = sync_pb2_grpc = None
    consensus_pb2 = consensus_pb2_grpc = None
    verification_pb2 = verification_pb2_grpc = None

_SyncServicer = sync_pb2_grpc.SyncServiceServicer if sync_pb2_grpc else object
_ConsensusServicer = consensus_pb2_grpc.ConsensusServiceServicer if consensus_pb2_grpc else object
_VerificationServicer = verification_pb2_grpc.VerificationServiceServicer if verification_pb2_grpc else object

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

class SyncService(_SyncServicer):
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

class ConsensusService(_ConsensusServicer):
    def __init__(self, node_id, verifier, max_cache: int = 1000):
        self.node_id = node_id
        self._verifier = verifier
        self._cache_votes: dict = {}
        self._lock = threading.Lock()
        self._max_cache = max_cache

    def DemanderVote(self, request, context):
        if request.id_demande:
            with self._lock:
                if request.id_demande in self._cache_votes:
                    logger.info(
                        "[%s] Demande de vote en doublon détectée (id_demande=%s), réponse servie depuis le cache",
                        self.node_id,
                        request.id_demande,
                    )
                    return self._cache_votes[request.id_demande]

        try:
            accepte = self._verifier(
                request.utilisateur_id,
                request.preuve_zkp,
                request.nonce,
                request.service_cible,
            )
            raison = ""
        except Exception as exc:
            logger.exception("[%s] Erreur de vérification", self.node_id)
            accepte, raison = False, f"erreur de vérification : {exc}"

        if consensus_pb2:
            reponse = consensus_pb2.ReponseVote(
                noeud_id=self.node_id,
                id_demande=request.id_demande,
                vote=consensus_pb2.VOTE_POUR if accepte
                     else consensus_pb2.VOTE_CONTRE,
                raison=raison,
            )
        else:
            reponse = SimpleNamespace(
                noeud_id=self.node_id,
                id_demande=request.id_demande,
                vote=1 if accepte else 2,
                raison=raison,
            )

        if request.id_demande:
            with self._lock:
                if len(self._cache_votes) >= self._max_cache:
                    self._cache_votes.pop(next(iter(self._cache_votes)))
                self._cache_votes[request.id_demande] = reponse

        return reponse

class VerificationService(_VerificationServicer):
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
        """Émet un nonce 256 bits lié à l'utilisateur et au service cible.

        Le service_cible est enregistré avec le nonce : un nonce émis pour
        "facein-web" ne peut pas être consommé pour "facein-mobile".
        """
        if not request.utilisateur_id:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "utilisateur_id requis")
        service = request.service_cible or ""
        nonce, expiration = self._nonces.emettre(request.utilisateur_id, service)
        return verification_pb2.ReponseNonce(
            nonce=nonce,
            expiration_timestamp=expiration,
            service_cible=service,
        )

    def VerifierPreuve(self, request, context):
        """Consomme le nonce et déclenche le consensus ZKP.

        La consommation du nonce est ATOMIQUE et unique :
        - vérification propriétaire + service_cible + expiry avant suppression
        - un nonce invalide n'est PAS supprimé (log possible) mais refusé
        L'API ne doit PAS consommer le nonce localement ; c'est fait ici.
        """
        # Validation de format et consommation atomique
        nonce = request.nonce or ""
        if (
            len(nonce) != 64
            or not all(c in "0123456789abcdefABCDEF" for c in nonce)
            or not self._nonces.consommer(
                request.utilisateur_id, nonce, request.service_cible or ""
            )
        ):
            if verification_pb2:
                return verification_pb2.ReponseVerification(
                    accepte=False, raison_refus="nonce invalide ou expiré"
                )
            return SimpleNamespace(
                accepte=False, raison_refus="nonce invalide ou expiré", token="", score_anomalie=0
            )

        # Les signaux publics ZKP voyagent avec la preuve dans le champ
        # ``preuve_zkp`` de la demande de vote (voir empaqueter_preuve).
        # Sans signaux publics, la preuve est transmise telle quelle.
        preuve = request.preuve_zkp
        if request.public_signals:
            try:
                preuve = empaqueter_preuve(preuve, request.public_signals)
            except ValueError:
                if verification_pb2:
                    return verification_pb2.ReponseVerification(
                        accepte=False, raison_refus="preuve ZKP illisible"
                    )
                return SimpleNamespace(
                    accepte=False, raison_refus="preuve ZKP illisible", token="", score_anomalie=0
                )

        if consensus_pb2:
            demande = consensus_pb2.DemandeVote(
                id_demande=str(uuid.uuid4()),
                noeud_initiateur=self.node_id,
                utilisateur_id=request.utilisateur_id,
                preuve_zkp=preuve,
                nonce=request.nonce,
                service_cible=request.service_cible,
                timestamp=request.timestamp,
            )
        else:
            demande = SimpleNamespace(
                id_demande=str(uuid.uuid4()),
                noeud_initiateur=self.node_id,
                utilisateur_id=request.utilisateur_id,
                preuve_zkp=preuve,
                nonce=request.nonce,
                service_cible=request.service_cible,
                timestamp=request.timestamp,
            )

        decision = self._decider(demande)

        # Extraction des détails du consensus
        if hasattr(decision, "accepte"):
            accepte = bool(decision.accepte)
            coordinateur_id = str(decision.coordinateur_id)
            nb_pour = int(decision.nb_votes_pour)
            nb_contre = int(decision.nb_votes_contre)
            noeuds_indispos = [str(n) for n in decision.noeuds_indisponibles]
            seuil = int(decision.seuil_requis)
            raison = str(
                decision.raison
                or ("consensus non atteint" if not accepte else "")
            )
            proto_votes = []
            for v in getattr(decision, "votes_recus", []):
                if verification_pb2:
                    proto_votes.append(
                        verification_pb2.DetailVote(
                            noeud_id=str(v.noeud_id),
                            vote_pour=bool(v.vote_pour),
                            raison=str(v.raison or ""),
                        )
                    )
                else:
                    proto_votes.append(
                        SimpleNamespace(
                            noeud_id=str(v.noeud_id),
                            vote_pour=bool(v.vote_pour),
                            raison=str(v.raison or ""),
                        )
                    )
        else:
            accepte = bool(decision)
            coordinateur_id = self.node_id
            nb_pour = 1 if accepte else 0
            nb_contre = 0 if accepte else 1
            noeuds_indispos = []
            seuil = 2
            raison = "" if accepte else "consensus non atteint"
            if verification_pb2:
                proto_votes = [
                    verification_pb2.DetailVote(
                        noeud_id=self.node_id,
                        vote_pour=accepte,
                        raison=raison,
                    )
                ]
            else:
                proto_votes = [
                    SimpleNamespace(
                        noeud_id=self.node_id,
                        vote_pour=accepte,
                        raison=raison,
                    )
                ]

        if not accepte:
            logger.warning(
                "[%s] Consensus négatif pour '%s' (%d pour, %d contre, seuil=%d)",
                self.node_id,
                request.utilisateur_id,
                nb_pour,
                nb_contre,
                seuil,
            )
            if verification_pb2:
                return verification_pb2.ReponseVerification(
                    accepte=False,
                    raison_refus=raison
                    or "Consensus non atteint par le réseau de pairs",
                    coordinateur_id=coordinateur_id,
                    votes_recus=proto_votes,
                    nb_votes_pour=nb_pour,
                    nb_votes_contre=nb_contre,
                    noeuds_indisponibles=noeuds_indispos,
                    seuil_requis=seuil,
                )
            return SimpleNamespace(
                accepte=False,
                raison_refus=raison
                or "Consensus non atteint par le réseau de pairs",
                coordinateur_id=coordinateur_id,
                votes_recus=proto_votes,
                nb_votes_pour=nb_pour,
                nb_votes_contre=nb_contre,
                noeuds_indisponibles=noeuds_indispos,
                seuil_requis=seuil,
                token="",
                score_anomalie=0,
            )

        token = self._fabriquer_token(request.utilisateur_id)
        if verification_pb2:
            return verification_pb2.ReponseVerification(
                accepte=True,
                token=token,
                score_anomalie=0,
                coordinateur_id=coordinateur_id,
                votes_recus=proto_votes,
                nb_votes_pour=nb_pour,
                nb_votes_contre=nb_contre,
                noeuds_indisponibles=noeuds_indispos,
                seuil_requis=seuil,
            )
        return SimpleNamespace(
            accepte=True,
            token=token,
            score_anomalie=0,
            coordinateur_id=coordinateur_id,
            votes_recus=proto_votes,
            nb_votes_pour=nb_pour,
            nb_votes_contre=nb_contre,
            noeuds_indisponibles=noeuds_indispos,
            seuil_requis=seuil,
        )

    def EnregistrerEngagement(self, request, context):
        """Enregistre ou met à jour de façon idempotente l'engagement d'un utilisateur."""
        if not request.utilisateur_id or not request.commitment:
            if context:
                context.abort(grpc.StatusCode.INVALID_ARGUMENT, "utilisateur_id et commitment requis")
            return verification_pb2.ReponseEnregistrementEngagement(
                succes=False, message="utilisateur_id et commitment requis"
            )

        if self._store is None:
            if context:
                context.abort(grpc.StatusCode.UNAVAILABLE, "Magasin d'engagements non configuré")
            return verification_pb2.ReponseEnregistrementEngagement(
                succes=False, message="Magasin d'engagements non configuré"
            )

        ts = (
            float(request.timestamp) / 1000.0
            if request.timestamp > 100_000_000_000
            else float(request.timestamp or time.time())
        )
        self._store.save(
            user_id=request.utilisateur_id,
            commitment=request.commitment,
            timestamp=ts,
            version=request.version or None,
        )
        logger.info(
            "[%s] Engagement enregistré pour '%s'",
            self.node_id,
            request.utilisateur_id,
        )
        return verification_pb2.ReponseEnregistrementEngagement(
            succes=True,
            message="Engagement enregistré avec succès",
        )

    def RevoquerEngagement(self, request, context):
        """Révoque de façon idempotente l'engagement d'un utilisateur."""
        if not request.utilisateur_id:
            if context:
                context.abort(grpc.StatusCode.INVALID_ARGUMENT, "utilisateur_id requis")
            return verification_pb2.ReponseRevocationEngagement(
                succes=False, message="utilisateur_id requis"
            )

        if self._store is None:
            if context:
                context.abort(grpc.StatusCode.UNAVAILABLE, "Magasin d'engagements non configuré")
            return verification_pb2.ReponseRevocationEngagement(
                succes=False, message="Magasin d'engagements non configuré"
            )

        ts = (
            float(request.timestamp) / 1000.0
            if request.timestamp > 100_000_000_000
            else float(request.timestamp or time.time())
        )
        ok = self._store.revoke(
            user_id=request.utilisateur_id,
            raison=request.raison or "",
            timestamp=ts,
        )
        logger.info(
            "[%s] Révocation traitée pour '%s' (trouvé=%s)",
            self.node_id,
            request.utilisateur_id,
            ok,
        )
        return verification_pb2.ReponseRevocationEngagement(
            succes=True,
            message="Engagement révoqué avec succès",
        )

    def SynchroniserEngagements(self, request, context):
        """Synchronise un lot d'engagements pour le rattrapage d'état (idempotent)."""
        if self._store is None:
            if context:
                context.abort(grpc.StatusCode.UNAVAILABLE, "Magasin d'engagements non configuré")
            return verification_pb2.ReponseSyncEngagements(
                succes=False, nb_synchronises=0, message="Magasin non disponible"
            )

        entries = []
        for e in request.engagements:
            ts = (
                float(e.timestamp) / 1000.0
                if e.timestamp > 100_000_000_000
                else float(e.timestamp or time.time())
            )
            entries.append(
                {
                    "utilisateur_id": e.utilisateur_id,
                    "commitment": e.commitment,
                    "statut": e.statut or "actif",
                    "timestamp": ts,
                    "version": e.version or 1,
                    "raison": e.raison or "",
                }
            )

        nb_sync = self._store.sync_batch(entries)
        logger.info(
            "[%s] Synchronisation terminée : %d entrées mises à jour",
            self.node_id,
            nb_sync,
        )
        return verification_pb2.ReponseSyncEngagements(
            succes=True,
            nb_synchronises=nb_sync,
            message=f"{nb_sync} engagements synchronisés",
        )

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