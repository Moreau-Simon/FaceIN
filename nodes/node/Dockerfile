# Important : ce Dockerfile attend un contexte de build = ./nodes
# (et non ./nodes/node), pour pouvoir copier aussi shared/.
# Voir docker-compose.yml : context: ./nodes, dockerfile: node/Dockerfile

FROM python:3.12-slim

WORKDIR /app

COPY node/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY node/ .
COPY shared/ /app/shared

RUN python -m grpc_tools.protoc \
    -I /app/shared/proto \
    --python_out=/app \
    --grpc_python_out=/app \
    /app/shared/proto/verification.proto \
    /app/shared/proto/sync.proto \
    /app/shared/proto/revocation.proto
    
CMD ["python", "main.py"]
