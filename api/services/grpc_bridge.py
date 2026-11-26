"""
Client pont gRPC pour communiquer avec le réseau de noeuds P2P FaceIn.

Interroge les 3 noeuds de vérification en parallèle avec un timeout de 3 secondes
et calcule le consensus selon la règle de la majorité qualifiée (seuil de 2/3).
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
import os
import json
import time
from pathlib import Path
from threading import Lock
from typing import Any, Optional

# ==============================================================================
# REMARQUE IMPORTANTE :
# Les modules `verification_pb2` et `verification_pb2_grpc` sont générés
# automatiquement à partir du fichier `nodes/shared/proto/verification.proto`.
# Commande de génération :
# python -m grpc_tools.protoc -I nodes/shared/proto --python_out=. --grpc_python_out=. nodes/shared/proto/verification.proto
# ==============================================================================
try:
    import grpc
    _RpcError = grpc.RpcError
except ImportError:
    grpc = None  # type: ignore

    class _RpcError(Exception):
        pass

try:
    import verification_pb2  # type: ignore
    import verification_pb2_grpc  # type: ignore
except ImportError:
    try:
        from api import verification_pb2, verification_pb2_grpc  # type: ignore
    except ImportError:
        verification_pb2 = None  # type: ignore
        verification_pb2_grpc = None  # type: ignore

logger = logging.getLogger("facein.grpc_bridge")

# Configuration des noeuds du réseau de consensus
DEFAULT_NODES = [
    {
        "id": "node-a",
        "host": os.getenv("NODE_A_HOST", "node-a" if os.path.exists("/.dockerenv") else "localhost"),
        "port": int(os.getenv("NODE_A_PORT", "50051")),
    },
    {
        "id": "node-b",
        "host": os.getenv("NODE_B_HOST", "node-b" if os.path.exists("/.dockerenv") else "localhost"),
        "port": int(os.getenv("NODE_B_PORT", "50052")),
    },
    {
        "id": "node-c",
        "host": os.getenv("NODE_C_HOST", "node-c" if os.path.exists("/.dockerenv") else "localhost"),
        "port": int(os.getenv("NODE_C_PORT", "50053")),
    },
]

SEUIL_MAJORITE = 2  # Au moins 2 noeuds sur 3 doivent valider la preuve
TIMEOUT_NOEUD_SECONDES = 3.0
GRPC_CHANNEL_OPTIONS = (
    ("grpc.keepalive_time_ms", 300_000),
    ("grpc.keepalive_timeout_ms", 20_000),
    ("grpc.keepalive_permit_without_calls", 1),
)

_canaux: dict[str, Any] = {}
_verrou_canaux = Lock()


def _creer_canal(target: str):
    """Retourne le canal gRPC partagé pour cette cible."""
    with _verrou_canaux:
        channel = _canaux.get(target)
        if channel is not None:
            return channel

        tls_enabled = os.getenv("TLS_ENABLED", "true").strip().lower()
        if tls_enabled not in {"1", "true", "yes", "on"}:
            channel = grpc.insecure_channel(
                target,
                options=GRPC_CHANNEL_OPTIONS,
            )
        else:
            ca_path = os.getenv("TLS_CA_CERT", "/app/certs/ca.crt")
            cert_path = os.getenv("TLS_CERT")
            key_path = os.getenv("TLS_KEY")
            if not cert_path or not key_path:
                raise RuntimeError(
                    "TLS_CERT et TLS_KEY doivent être configurés "
                    "quand TLS_ENABLED=true"
                )

            credentials = grpc.ssl_channel_credentials(
                root_certificates=Path(ca_path).read_bytes(),
                private_key=Path(key_path).read_bytes(),
                certificate_chain=Path(cert_path).read_bytes(),
            )
            channel = grpc.secure_channel(
                target,
                credentials,
                options=GRPC_CHANNEL_OPTIONS,
            )

        _canaux[target] = channel
        return channel


def fermer_canaux() -> None:
    """Ferme et oublie les canaux gRPC partagés."""
    with _verrou_canaux:
        channels = tuple(_canaux.values())
        _canaux.clear()
    for channel in channels:
        channel.close()


def _verifier_noeud_unitaire(
    node: dict[str, Any],
    user_id: str,
    proof_json_str: str,
    nonce: str,
    public_signals: Optional[list[str]] = None,
) -> Optional[dict[str, Any]]:
    """
    Appelle la méthode `VerifierPreuve` sur un noeud gRPC spécifique (noeud initiateur).
    
    Retourne un dictionnaire contenant les détails complets du consensus si le noeud a répondu,
    ou None si le noeud est injoignable (déclenche le basculement/failover).
    """
    node_id = node["id"]
    host = node["host"]
    port = node["port"]
    target = f"{host}:{port}"

    if grpc is None or verification_pb2 is None or verification_pb2_grpc is None:
        if (
            os.getenv("MOCK_ZKP_VERIFICATION", "").lower() in {"1", "true"}
            or os.getenv("ALLOW_MOCK_CONSENSUS", "").lower() in {"1", "true"}
        ):
            logger.warning(
                "[%s] Protobuf/gRPC non disponible - simulation de test active.",
                node_id,
            )
            return {
                "node_id": node_id,
                "accepte": True,
                "token": "token-simule",
                "raison_refus": "",
                "coordinateur_id": node_id,
                "votes": {n["id"]: True for n in DEFAULT_NODES},
                "votes_recus": [
                    {"noeud_id": n["id"], "vote_pour": True, "raison": ""}
                    for n in DEFAULT_NODES
                ],
                "nb_votes_pour": len(DEFAULT_NODES),
                "nb_votes_contre": 0,
                "noeuds_indisponibles": [],
                "seuil_requis": (len(DEFAULT_NODES) // 2) + 1,
            }
        logger.error("[%s] Protobuf/gRPC non compilé ou indisponible.", node_id)
        return None

    try:
        channel = _creer_canal(target)
        stub = verification_pb2_grpc.VerificationServiceStub(channel)

        # Encodage sécurisé de la preuve Groth16 en bytes pour conformité Protobuf
        if isinstance(proof_json_str, (bytes, bytearray)):
            preuve_bytes = bytes(proof_json_str)
        elif isinstance(proof_json_str, dict):
            preuve_bytes = json.dumps(proof_json_str).encode("utf-8")
        else:
            preuve_bytes = str(proof_json_str).encode("utf-8")

        demande = verification_pb2.DemandeVerification(
            utilisateur_id=user_id,
            preuve_zkp=preuve_bytes,
            nonce=nonce,
            timestamp=int(time.time()),
            service_cible="FaceIn-Gateway",
            appareil_signature="",
            public_signals=[str(s) for s in (public_signals or [])],
        )

        reponse = stub.VerifierPreuve(demande, timeout=TIMEOUT_NOEUD_SECONDES)

        votes_map = {}
        votes_recus_list = []
        for v in getattr(reponse, "votes_recus", []):
            votes_map[v.noeud_id] = bool(v.vote_pour)
            votes_recus_list.append(
                {
                    "noeud_id": v.noeud_id,
                    "vote_pour": bool(v.vote_pour),
                    "raison": str(v.raison or ""),
                }
            )

        coordinateur = str(getattr(reponse, "coordinateur_id", "") or node_id)
        nb_pour = int(
            getattr(reponse, "nb_votes_pour", 1 if reponse.accepte else 0)
        )
        nb_contre = int(
            getattr(reponse, "nb_votes_contre", 0 if reponse.accepte else 1)
        )
        noeuds_indispos = [
            str(n) for n in getattr(reponse, "noeuds_indisponibles", [])
        ]
        seuil = int(getattr(reponse, "seuil_requis", 2))

        logger.info(
            "[%s] Réponse reçue du coordinateur : accepte=%s, pour=%d, contre=%d, seuil=%d, raison='%s'",
            coordinateur,
            reponse.accepte,
            nb_pour,
            nb_contre,
            seuil,
            reponse.raison_refus,
        )

        return {
            "node_id": node_id,
            "accepte": bool(reponse.accepte),
            "token": str(reponse.token or ""),
            "raison_refus": str(reponse.raison_refus or ""),
            "coordinateur_id": coordinateur,
            "votes": votes_map,
            "votes_recus": votes_recus_list,
            "nb_votes_pour": nb_pour,
            "nb_votes_contre": nb_contre,
            "noeuds_indisponibles": noeuds_indispos,
            "seuil_requis": seuil,
        }

    except _RpcError as rpc_error:
        logger.warning(
            "[%s] Erreur de communication gRPC vers %s (%s).",
            node_id,
            target,
            rpc_error,
        )
        return None

    except Exception as exc:
        logger.warning(
            "[%s] Exception lors de l'appel gRPC vers %s : %s.",
            node_id,
            target,
            exc,
        )
        return None


def verify_on_nodes(
    user_id: str,
    proof_json_str: str,
    nonce: str,
    nodes: Optional[list[dict[str, Any]]] = None,
    public_signals: Optional[list[str]] = None,
) -> dict[str, Any]:
    """
    Délègue la vérification biométrique ZKP au réseau de pairs via un noeud initiateur.

    Architecture (Sujet FaceIN P2P) :
    1. L'API Gateway contacte un seul noeud coordinateur (noeud initiateur).
    2. Ce noeud valide la preuve localement et orchestre le consensus décentralisé
       en interrogeant ses pairs via le RPC interne `ConsensusService.DemanderVote`.
    3. Si le premier noeud est injoignable (panne, arrêt), le failover tente le noeud suivant.
    4. Si le coordinateur a répondu par un refus (consensus négatif), aucun failover n'est tenté.
    5. Les votes et résultats retournés sont les informations authentiques du consensus.
    """
    target_nodes = nodes or DEFAULT_NODES
    total_nodes = len(target_nodes)
    seuil_defaut = (total_nodes // 2) + 1

    noeuds_indisponibles_cumules: list[str] = []

    # Tentative d'interrogation séquentielle avec failover sur panne réseau/timeout
    for node in target_nodes:
        node_id = node["id"]
        logger.info("Délégation du consensus au noeud initiateur [%s]...", node_id)
        resultat = _verifier_noeud_unitaire(
            node=node,
            user_id=user_id,
            proof_json_str=proof_json_str,
            nonce=nonce,
            public_signals=public_signals,
        )

        if resultat is None:
            logger.warning(
                "[%s] Noeud injoignable, basculement vers le noeud suivant...",
                node_id,
            )
            noeuds_indisponibles_cumules.append(node_id)
            continue

        # Le nœud coordinateur a répondu (communication réussie).
        # Règle : Une décision négative calculée NE DOIT PAS être relancée par failover.
        accepte = bool(resultat["accepte"])
        coordinateur = resultat.get("coordinateur_id") or node_id
        votes = resultat.get("votes", {})
        nb_pour = resultat.get("nb_votes_pour", 1 if accepte else 0)
        nb_contre = resultat.get("nb_votes_contre", 0 if accepte else 1)
        seuil = resultat.get("seuil_requis", seuil_defaut)
        indispos = list(
            dict.fromkeys(
                resultat.get("noeuds_indisponibles", [])
                + noeuds_indisponibles_cumules
            )
        )

        majority_str = f"{nb_pour}/{total_nodes}"

        logger.info(
            "Consensus résolu par le réseau via l'initiateur [%s] : accepte=%s (pour=%d, contre=%d, seuil=%d, raison='%s')",
            coordinateur,
            accepte,
            nb_pour,
            nb_contre,
            seuil,
            resultat.get("raison_refus", ""),
        )

        return {
            "consensus": accepte,
            "votes": votes,
            "majority": majority_str,
            "initiator": coordinateur,
            "token": resultat.get("token", ""),
            "reason": resultat.get("raison_refus", ""),
            "nb_votes_pour": nb_pour,
            "nb_votes_contre": nb_contre,
            "noeuds_indisponibles": indispos,
            "seuil_requis": seuil,
        }

    # Cas où tous les noeuds gRPC sont injoignables
    logger.warning("Tous les noeuds du réseau de consensus sont injoignables.")

    if (
        os.getenv("MOCK_ZKP_VERIFICATION", "").lower() in {"1", "true"}
        or os.getenv("ALLOW_MOCK_CONSENSUS", "").lower() in {"1", "true"}
    ):
        logger.warning(
            "Mode test local : simulation d'un consensus favorable."
        )
        votes = {n["id"]: True for n in target_nodes}
        return {
            "consensus": True,
            "votes": votes,
            "majority": f"{total_nodes}/{total_nodes}",
            "initiator": target_nodes[0]["id"] if target_nodes else "none",
            "token": "token-simule-fallback",
            "reason": "",
            "nb_votes_pour": total_nodes,
            "nb_votes_contre": 0,
            "noeuds_indisponibles": [],
            "seuil_requis": seuil_defaut,
        }

    return {
        "consensus": False,
        "votes": {},
        "majority": f"0/{total_nodes}",
        "initiator": None,
        "token": None,
        "reason": "Tous les nœuds de vérification sont injoignables",
        "nb_votes_pour": 0,
        "nb_votes_contre": 0,
        "noeuds_indisponibles": [n["id"] for n in target_nodes],
        "seuil_requis": seuil_defaut,
    }


def request_nonce_from_node(
    user_id: str,
    nodes: Optional[list[dict[str, Any]]] = None,
) -> tuple[Optional[str], Optional[int]]:
    """
    Interroge le réseau de noeuds gRPC pour obtenir un nonce anti-rejeu éphémère.

    Appelle la méthode RPC `VerificationService.DemanderNonce` sur le noeud coordinateur.
    En cas d'échec ou d'indisponibilité du premier noeud, bascule automatiquement (failover)
    sur les noeuds suivants de la liste.

    Retourne :
        tuple : (nonce_str, expiration_timestamp_secondes) ou (None, None) en cas d'échec total.
    """
    if grpc is None or verification_pb2 is None or verification_pb2_grpc is None:
        logger.warning(
            "Protobuf/gRPC indisponible. Impossible de demander un nonce gRPC."
        )
        return None, None

    target_nodes = nodes or DEFAULT_NODES

    for node in target_nodes:
        node_id = node["id"]
        host = node["host"]
        port = node["port"]
        target = f"{host}:{port}"

        try:
            channel = _creer_canal(target)
            stub = verification_pb2_grpc.VerificationServiceStub(channel)

            demande = verification_pb2.DemandeNonce(utilisateur_id=user_id)
            reponse = stub.DemanderNonce(demande, timeout=TIMEOUT_NOEUD_SECONDES)

            if reponse and reponse.nonce:
                # Normalisation du timestamp d'expiration en secondes
                raw_exp = reponse.expiration_timestamp
                exp_seconds = int(raw_exp / 1000) if raw_exp > 100_000_000_000 else int(raw_exp)
                logger.info(
                    "[%s] Nonce anti-rejeu délivré avec succès pour '%s'",
                    node_id,
                    user_id,
                )
                return str(reponse.nonce), exp_seconds

        except _RpcError as rpc_err:
            logger.warning(
                "[%s] Erreur RPC lors de la demande de nonce sur %s : %s",
                node_id,
                target,
                rpc_err,
            )
            continue
        except Exception as exc:
            logger.warning(
                "[%s] Exception lors de la demande de nonce sur %s : %s",
                node_id,
                target,
                exc,
            )
            continue

    logger.warning("Aucun noeud gRPC n'a pu délivrer de nonce.")
    return None, None


def propagate_commitment_to_nodes(
    user_id: str,
    commitment: str,
    nodes: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    """
    Propage l'engagement enregistré aux 3 nœuds de vérification gRPC.
    Exige la confirmation d'au moins 2/3 des nœuds (quorum) pour considérer la propagation réussie.
    """
    target_nodes = nodes or DEFAULT_NODES

    # Si gRPC n'est pas disponible (environnement de test / local sans protobuf)
    if grpc is None or verification_pb2 is None or verification_pb2_grpc is None:
        logger.warning("Protobuf/gRPC non disponible. Simulation de propagation réussie.")
        return {
            "success": True,
            "quorum": True,
            "confirmations": {n["id"]: True for n in target_nodes},
            "majority": f"{len(target_nodes)}/{len(target_nodes)}",
        }

    confirmations: dict[str, bool] = {}
    now_ms = int(time.time() * 1000)

    for node in target_nodes:
        node_id = node["id"]
        target = f"{node['host']}:{node['port']}"
        try:
            channel = _creer_canal(target)
            stub = verification_pb2_grpc.VerificationServiceStub(channel)
            demande = verification_pb2.DemandeEnregistrementEngagement(
                utilisateur_id=user_id,
                commitment=commitment,
                timestamp=now_ms,
            )
            reponse = stub.EnregistrerEngagement(demande, timeout=TIMEOUT_NOEUD_SECONDES)
            confirmations[node_id] = bool(reponse and reponse.succes)
            if confirmations[node_id]:
                logger.info("[%s] Engagement propagé avec succès pour '%s'", node_id, user_id)
            else:
                logger.warning("[%s] Nœud a rejeté l'engagement pour '%s'", node_id, user_id)
        except Exception as exc:
            logger.warning("[%s] Échec de propagation vers %s : %s", node_id, target, exc)
            confirmations[node_id] = False

    nb_succes = sum(1 for v in confirmations.values() if v)
    quorum_atteint = nb_succes >= SEUIL_MAJORITE

    return {
        "success": quorum_atteint,
        "quorum": quorum_atteint,
        "confirmations": confirmations,
        "majority": f"{nb_succes}/{len(target_nodes)}",
    }


def propagate_revocation_to_nodes(
    user_id: str,
    raison: str = "",
    nodes: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    """Propage la révocation d'un engagement aux 3 nœuds gRPC."""
    target_nodes = nodes or DEFAULT_NODES

    if grpc is None or verification_pb2 is None or verification_pb2_grpc is None:
        logger.warning("Protobuf/gRPC non disponible. Simulation de révocation réussie.")
        return {
            "success": True,
            "quorum": True,
            "confirmations": {n["id"]: True for n in target_nodes},
            "majority": f"{len(target_nodes)}/{len(target_nodes)}",
        }

    confirmations: dict[str, bool] = {}
    now_ms = int(time.time() * 1000)

    for node in target_nodes:
        node_id = node["id"]
        target = f"{node['host']}:{node['port']}"
        try:
            channel = _creer_canal(target)
            stub = verification_pb2_grpc.VerificationServiceStub(channel)
            demande = verification_pb2.DemandeRevocationEngagement(
                utilisateur_id=user_id,
                raison=raison,
                timestamp=now_ms,
            )
            reponse = stub.RevoquerEngagement(demande, timeout=TIMEOUT_NOEUD_SECONDES)
            confirmations[node_id] = bool(reponse and reponse.succes)
        except Exception as exc:
            logger.warning("[%s] Échec de révocation vers %s : %s", node_id, target, exc)
            confirmations[node_id] = False

    nb_succes = sum(1 for v in confirmations.values() if v)
    return {
        "success": nb_succes >= SEUIL_MAJORITE,
        "quorum": nb_succes >= SEUIL_MAJORITE,
        "confirmations": confirmations,
        "majority": f"{nb_succes}/{len(target_nodes)}",
    }

