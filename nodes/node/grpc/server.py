"""
Serveur gRPC du noeud - expose VerificationService aux clients.

A implémenter (étape suivante) :
    1. generer le code gRPC a partir des .proto :
       python -m grpc_tools.protoc -I../shared/proto --python_out=. \
           --grpc_python_out=. ../shared/proto/verification.proto

    2. Créer la classe VerificationServiceServicer(verification_pb2_grpc.VerificationServiceServicer)
       et implémenter RecupererDonneeAide / DemanderNonce / VerifierPreuve.

    3. Démarrer le serveur :
       server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
       verification_pb2_grpc.add_VerificationServiceServicer_to_server(..., server)
       server.add_insecure_port(f"[::]:{port}")   # TLS a ajouter ensuite
       server.start()
"""
