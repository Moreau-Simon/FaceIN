"""Client manuel de démonstration du parcours nonce puis preuve."""

import argparse
import os
import sys
import time
from pathlib import Path

import grpc

import verification_pb2
import verification_pb2_grpc


def creer_canal(address: str, insecure: bool = False):
    """Crée un canal mTLS, sauf demande explicite d'un canal de test."""
    if insecure:
        return grpc.insecure_channel(address)

    tls_enabled = os.getenv("TLS_ENABLED", "true").strip().lower() in {
        "1", "true", "yes", "on"
    }
    if not tls_enabled:
        raise RuntimeError(
            "TLS_ENABLED doit être activé. Utilisez --insecure uniquement "
            "pour un test avec un serveur sans TLS."
        )

    ca_path = os.getenv("TLS_CA_CERT", "/app/certs/ca.crt")
    cert_path = os.getenv("TLS_CERT")
    key_path = os.getenv("TLS_KEY")
    if not cert_path or not key_path:
        raise RuntimeError("TLS_CERT et TLS_KEY doivent être configurés")

    try:
        credentials = grpc.ssl_channel_credentials(
            root_certificates=Path(ca_path).read_bytes(),
            private_key=Path(key_path).read_bytes(),
            certificate_chain=Path(cert_path).read_bytes(),
        )
    except OSError as error:
        raise RuntimeError(
            f"Impossible de charger les certificats mTLS : {error}"
        ) from error

    return grpc.secure_channel(address, credentials)


def main():
    parser = argparse.ArgumentParser(
        description="Demande un nonce puis envoie une preuve de démonstration."
    )
    parser.add_argument(
        "--address",
        default="node-a:50051",
        help="adresse gRPC du noeud (défaut : node-a:50051)",
    )
    parser.add_argument(
        "--insecure",
        action="store_true",
        help="désactive explicitement TLS (tests uniquement)",
    )
    parser.add_argument("--utilisateur-id", required=True)
    parser.add_argument(
        "--preuve",
        required=True,
        help="preuve de démonstration, encodée en UTF-8 (pas une preuve ZKP)",
    )
    parser.add_argument("--service-cible", default="service-demo")
    args = parser.parse_args()

    try:
        with creer_canal(args.address, insecure=args.insecure) as channel:
            stub = verification_pb2_grpc.VerificationServiceStub(channel)
            nonce = stub.DemanderNonce(
                verification_pb2.DemandeNonce(
                    utilisateur_id=args.utilisateur_id,
                ),
                timeout=2,
            )
            resultat = stub.VerifierPreuve(
                verification_pb2.DemandeVerification(
                    utilisateur_id=args.utilisateur_id,
                    preuve_zkp=args.preuve.encode("utf-8"),
                    nonce=nonce.nonce,
                    timestamp=int(time.time() * 1000),
                    service_cible=args.service_cible,
                ),
                timeout=5,
            )
    except RuntimeError as error:
        print(f"Configuration mTLS invalide : {error}", file=sys.stderr)
        return 1
    except grpc.RpcError as error:
        print(
            f"Échec de l'appel gRPC ({error.code()}): {error.details()}",
            file=sys.stderr,
        )
        return 1

    print(f"Nonce reçu (expiration ms) : {nonce.expiration_timestamp}")
    print(f"Vérification acceptée : {resultat.accepte}")
    if resultat.accepte:
        print(f"Token : {resultat.token}")
        return 0

    print(f"Refus : {resultat.raison_refus}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
