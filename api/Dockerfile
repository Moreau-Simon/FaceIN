# ==============================================================================
# Dockerfile pour l'API Gateway FaceIn
# Contexte de build recommandé : racine du dépôt (FaceIN/)
# Exemple de build : docker build -t facein-api -f api/Dockerfile .
# ==============================================================================

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# 1. Installation de curl, Node.js et du paquet global snarkjs pour la vérification ZKP
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && npm install -g snarkjs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 2. Copie et installation des dépendances Python
COPY api/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# 3. Copie du code source de l'API Gateway
COPY api/ /app

# 4. Copie des fichiers proto et génération du code gRPC (verification_pb2.py & verification_pb2_grpc.py)
COPY nodes/shared/proto/ /app/proto/
RUN python -m grpc_tools.protoc \
    -I /app/proto \
    --python_out=/app \
    --grpc_python_out=/app \
    /app/proto/verification.proto

# 5. Copie de la clé de vérification du circuit ZKP
RUN mkdir -p /app/circuits/build
#COPY circuits/build/verification_key.json* /app/circuits/build/
COPY nodes/shared/verification_key.json /app/circuits/build/verification_key.json

# Exposition du port standard de l'API Gateway
EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=5 \
    CMD curl --fail --silent http://127.0.0.1:8000/api/health || exit 1

# Lancement du serveur uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
