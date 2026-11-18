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

from fastapi import FastAPI, HTTPException, Request, status  # noqa: E402
from fastapi.exceptions import RequestValidationError  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402

try:
    from models import HealthResponse  # noqa: E402
    from routes.authenticate import router as authenticate_router  # noqa: E402
    from routes.nonce import router as nonce_router  # noqa: E402
    from routes.register import router as register_router  # noqa: E402
    from services.grpc_bridge import DEFAULT_NODES, fermer_canaux  # noqa: E402
except ImportError:
    from api.models import HealthResponse  # noqa: E402
    from api.routes.authenticate import router as authenticate_router  # noqa: E402
    from api.routes.nonce import router as nonce_router  # noqa: E402
    from api.routes.register import router as register_router  # noqa: E402
    from api.services.grpc_bridge import DEFAULT_NODES, fermer_canaux  # noqa: E402

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
    try:
        yield
    finally:
        fermer_canaux()
        logger.info("Arrêt de la passerelle API FaceIn.")


# Initialisation de l'application FastAPI
app = FastAPI(
    title="FaceIn - API Gateway",
    description="Passerelle d'authentification biométrique décentralisée préservant la vie privée (ZKP)",
    version="1.0.0",
    lifespan=lifespan,
)

# Configuration CORS dynamique et sécurisée par variable d'environnement
raw_origins = os.getenv(
    "CORS_ALLOWED_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000,http://localhost:8000,http://127.0.0.1:8000",
)
cors_origins = [orig.strip() for orig in raw_origins.split(",") if orig.strip()]
allow_credentials = "*" not in cors_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=allow_credentials,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
)


# Middleware de protection contre les requêtes de taille excessive (max 1 Mo)
MAX_REQUEST_BYTES = 1024 * 1024  # 1 Mo


@app.middleware("http")
async def limit_request_size(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > MAX_REQUEST_BYTES:
                return JSONResponse(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    content={
                        "success": False,
                        "code": "PAYLOAD_TOO_LARGE",
                        "message": "La taille de la requête dépasse la limite autorisée (1 Mo).",
                    },
                )
        except ValueError:
            pass
    return await call_next(request)


# --- Gestionnaires centralisés d'exceptions ---
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    first_err = errors[0]["msg"] if errors else "Paramètres de requête invalides."
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "code": "VALIDATION_ERROR",
            "message": first_err,
            "detail": str(errors),
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        headers=exc.headers,
        content={
            "success": False,
            "code": f"HTTP_{exc.status_code}",
            "message": exc.detail if isinstance(exc.detail, str) else "Erreur HTTP",
            "detail": exc.detail if isinstance(exc.detail, str) else str(exc.detail),
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error("Exception non interceptée sur '%s %s' : %s", request.method, request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "code": "INTERNAL_SERVER_ERROR",
            "message": "Une erreur interne est survenue lors du traitement de la requête.",
        },
    )


# Enregistrement des routeurs préfixés par /api
app.include_router(register_router, prefix="/api", tags=["Enregistrement"])
app.include_router(nonce_router, prefix="/api", tags=["Nonce"])
app.include_router(authenticate_router, prefix="/api", tags=["Authentification"])


@app.get("/api/health", response_model=HealthResponse, tags=["Statut"])
def health_check():
    """Endpoint de contrôle de l'état de santé du service et de ses dépendances."""
    backend_stockage = os.getenv("STORE_BACKEND", "memory").lower()
    return HealthResponse(
        statut="en_ligne",
        service="FaceIn API Gateway",
        version="1.0.0",
        stockage=backend_stockage,
        noeuds_configures=len(DEFAULT_NODES),
    )


# Service du frontend de démonstration partenaire (port 8000 unifié)
PROJECT_ROOT = os.path.dirname(BASE_DIR)
PARTNER_DEMO_DIR = os.path.join(PROJECT_ROOT, "partner-demo")

if os.path.isdir(PARTNER_DEMO_DIR):
    app.mount("/demo", StaticFiles(directory=PARTNER_DEMO_DIR, html=True), name="partner-demo-alias")
    app.mount("/", StaticFiles(directory=PARTNER_DEMO_DIR, html=True), name="partner-demo")
else:
    @app.get("/", tags=["Statut"])
    def root_status():
        return health_check()


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run("main:app", host=host, port=port, reload=True)
