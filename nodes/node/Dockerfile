# Important : ce Dockerfile attend un contexte de build = ./nodes
# (et non ./nodes/node), pour pouvoir copier aussi shared/.
# Voir docker-compose.yml : context: ./nodes, dockerfile: node/Dockerfile

FROM python:3.12-slim

WORKDIR /app

# Installation de Node.js, npm et snarkjs pour la vérification des preuves ZKP Groth16
RUN apt-get update && apt-get install -y nodejs npm && npm install -g snarkjs && rm -rf /var/lib/apt/lists/*

COPY node/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY node/ .
COPY shared/ /app/shared
COPY shared/verification_key.json /app/shared/verification_key.json

# Compilation gRPC Protobuf
RUN python -m grpc_tools.protoc \
    -I /app/shared/proto \
    --python_out=/app \
    --grpc_python_out=/app \
    /app/shared/proto/verification.proto \
    /app/shared/proto/sync.proto \
    /app/shared/proto/revocation.proto

CMD ["python", "main.py"]
