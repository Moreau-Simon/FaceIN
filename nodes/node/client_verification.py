"""Client manuel de démonstration du parcours nonce puis preuve."""

import argparse
import sys
import time

import grpc

import verification_pb2
import verification_pb2_grpc


def main():
    parser = argparse.ArgumentParser(
        description="Demande un nonce puis envoie une preuve de démonstration."
    )
    parser.add_argument(
        "--address",
        default="localhost:50051",
        help="adresse gRPC du noeud (défaut : localhost:50051)",
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
        with grpc.insecure_channel(args.address) as channel:
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
