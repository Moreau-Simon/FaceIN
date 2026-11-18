"""
Service de limitation de débit (Rate Limiting) pour l'API Gateway FaceIn.
Protège les endpoints sensibles contre le déni de service, le spam et
les attaques par force brute via un algorithme de fenêtre glissante en mémoire.
"""

import logging
import os
import threading
import time
from typing import Dict, List, Optional
from fastapi import HTTPException, Request, status

logger = logging.getLogger("facein.rate_limiter")


class SlidingWindowRateLimiter:
    """
    Limiteur de débit thread-safe en mémoire utilisant une fenêtre glissante.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._hits: Dict[str, List[float]] = {}
        self._last_cleanup = time.time()
        self._cleanup_interval = 300.0  # Nettoyage toutes les 5 minutes

    def is_enabled(self) -> bool:
        """Vérifie si le rate limiting est activé dans l'environnement."""
        return os.getenv("RATE_LIMIT_ENABLED", "true").lower() in ("1", "true", "yes", "on")

    def _cleanup_expired(self, current_time: float, window_seconds: float) -> None:
        """Purge les entrées expirées pour prévenir toute fuite mémoire."""
        if current_time - self._last_cleanup < self._cleanup_interval:
            return

        cutoff = current_time - window_seconds
        keys_to_delete = []
        for key, timestamps in self._hits.items():
            valid_stamps = [t for t in timestamps if t > cutoff]
            if valid_stamps:
                self._hits[key] = valid_stamps
            else:
                keys_to_delete.append(key)

        for key in keys_to_delete:
            del self._hits[key]

        self._last_cleanup = current_time

    def check_rate_limit(
        self,
        key: str,
        max_requests: int,
        window_seconds: float = 60.0,
    ) -> tuple[bool, int]:
        """
        Vérifie si une clé a dépassé sa limite autorisée.

        Retourne :
            (allowed: bool, retry_after_seconds: int)
        """
        if not self.is_enabled():
            return True, 0

        now = time.time()
        cutoff = now - window_seconds

        with self._lock:
            self._cleanup_expired(now, window_seconds)

            timestamps = self._hits.get(key, [])
            # Filtrer les horodatages dans la fenêtre glissante courante
            active_timestamps = [t for t in timestamps if t > cutoff]

            if len(active_timestamps) >= max_requests:
                oldest_timestamp = active_timestamps[0]
                retry_after = max(1, int(oldest_timestamp + window_seconds - now))
                self._hits[key] = active_timestamps
                return False, retry_after

            active_timestamps.append(now)
            self._hits[key] = active_timestamps
            return True, 0

    def reset(self) -> None:
        """Réinitialise l'historique (principalement utile pour les tests unitaires)."""
        with self._lock:
            self._hits.clear()
            self._last_cleanup = time.time()


# Instance singleton du limiteur
_limiter = SlidingWindowRateLimiter()


def get_client_ip(request: Request) -> str:
    """Extrait l'adresse IP du client en tenant compte des en-têtes proxy si présents."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Prendre la première IP de la liste séparée par des virgules
        return forwarded.split(",")[0].strip()
    client = request.client
    return client.host if client else "unknown_ip"


def enforce_rate_limit(
    request: Request,
    endpoint_name: str,
    default_max_requests: int,
    window_seconds: float = 60.0,
    identifier: Optional[str] = None,
) -> None:
    """
    Dépendance / guard de rate limiting à appeler dans les routes FastAPI.
    Lève un HTTPException(429) si le quota est dépassé.
    """
    env_var_name = f"RATE_LIMIT_{endpoint_name.upper()}"
    try:
        max_requests = int(os.getenv(env_var_name, str(default_max_requests)))
    except ValueError:
        max_requests = default_max_requests

    ip = get_client_ip(request)
    limit_key = f"{endpoint_name}:{ip}"
    if identifier:
        limit_key += f":{identifier}"

    allowed, retry_after = _limiter.check_rate_limit(
        key=limit_key,
        max_requests=max_requests,
        window_seconds=window_seconds,
    )

    if not allowed:
        logger.warning(
            "Rate limit dépassé pour [%s] sur l'endpoint '%s' (quota: %d/%ds, attente: %ds)",
            ip,
            endpoint_name,
            max_requests,
            int(window_seconds),
            retry_after,
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Trop de requêtes. Veuillez patienter {retry_after} seconde(s) avant de réessayer.",
            headers={"Retry-After": str(retry_after)},
        )


def reset_rate_limiter() -> None:
    """Fonction utilitaire pour les tests."""
    _limiter.reset()
