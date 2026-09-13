import logging

from fastapi import APIRouter, Response, status
from sqlalchemy import text

from app.core.database import engine

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict[str, str]:
    """Liveness: the process is up and serving requests. Deliberately checks
    nothing external — a dependency outage should make /ready fail, not make
    an orchestrator think the whole process needs restarting."""
    return {"status": "ok"}


@router.get("/ready")
def readiness_check(response: Response) -> dict[str, str]:
    """Readiness: required dependencies (currently: the database) are
    actually reachable. A load balancer or orchestrator should stop routing
    traffic here (without restarting the process) when this returns 503."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:
        logger.warning("Readiness check failed: database unreachable", exc_info=True)
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "not_ready", "detail": "database unavailable"}
    return {"status": "ready"}
