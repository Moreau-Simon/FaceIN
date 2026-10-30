"""
Point d'entrée principal de l'API Gateway FaceIn.

Expose les endpoints REST pour le frontend et orchestre les vérifications
avec le moteur ZKP local et le réseau de pairs gRPC.
"""

from contextlib import asynccontextmanager
import logging
import os
import sys

# Ajout du répertoire courant au PYTHONPATH pour garantir des imports directs fiables
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from routes.authenticate import router as authenticate_router  # noqa: E402
from routes.nonce import router as nonce_router  # noqa: E402
from routes.register import router as register_router  # noqa: E402

# Configuration du format des logs
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(name)s : %(message)s",
)
logger = logging.getLogger("facein.main")

BANNER = r"""
======================================================================
  ______               _____       
 |  ____|             |_   _|      
 | |__   __ _   ___ ___ | |  _ __  
 |  __| / _` | / __/ _ \| | | '_ \ 
 | |   | (_| || (_|  __/| |_| | | |
 |_|    \__,_| \___\___|_____|_| |_|
                                   
  FaceIn - Passerelle API (API Gateway)
  Authentification biométrique décentralisée ZKP
======================================================================
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Journalise le démarrage et l'arrêt de l'API."""
    logger.info("%s", BANNER)
    logger.info("Passerelle API FaceIn démarrée.")
    yield
    logger.info("Arrêt de la passerelle API FaceIn.")


# Initialisation de l'application FastAPI
app = FastAPI(
    title="FaceIn - API Gateway",
    description="Passerelle d'authentification biométrique décentralisée préservant la vie privée (ZKP)",
    version="1.0.0",
    lifespan=lifespan,
)

# Configuration du middleware CORS (ouvert pour l'environnement de développement)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Enregistrement des routeurs préfixés par /api
app.include_router(register_router, prefix="/api", tags=["Enregistrement"])
app.include_router(nonce_router, prefix="/api", tags=["Nonce"])
app.include_router(authenticate_router, prefix="/api", tags=["Authentification"])


@app.get("/", tags=["Statut"])
@app.get("/api/health", tags=["Statut"])
def health_check():
    """Endpoint de contrôle de l'état de santé du service."""
    return {
        "statut": "en_ligne",
        "service": "FaceIn API Gateway",
        "version": "1.0.0",
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run("main:app", host=host, port=port, reload=True)
