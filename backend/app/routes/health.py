import logging

from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.deps import DB

logger = logging.getLogger("ffk.health")

router = APIRouter(prefix="/health", tags=["santé"])


@router.get("/live")
def live():
    """Le processus répond."""
    return {"status": "ok"}


@router.get("/ready")
def ready(db: DB):
    """Le backend peut travailler : la base de données répond."""
    try:
        db.exec(text("SELECT 1"))
    except Exception:
        logger.exception("readiness_failed")
        raise HTTPException(503, "Base de données indisponible.")
    return {"status": "ok"}
