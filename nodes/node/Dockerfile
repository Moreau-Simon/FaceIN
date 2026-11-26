# Important : ce Dockerfile attend un contexte de build = ./nodes
# (et non ./nodes/node), pour pouvoir copier aussi shared/.
# Voir docker-compose.yml : context: ./nodes, dockerfile: node/Dockerfile

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Installation de Node.js, npm et snarkjs (version épinglée) pour la vérification Groth16
RUN apt-get update && apt-get install -y --no-install-recommends \
    nodejs \
    npm \
    && npm install -g snarkjs@0.7.5 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

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
    /app/shared/proto/revocation.proto \
    /app/shared/proto/consensus.proto

# Répertoire persistant et utilisateur système non privilégié
RUN mkdir -p /app/data \
    && groupadd --gid 10001 facein \
    && useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin facein \
    && chown -R facein:facein /app

USER facein

HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=6 \
    CMD ["python", "-m", "healthcheck"]

CMD ["python", "main.py"]
