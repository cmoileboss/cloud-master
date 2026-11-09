import logging

from sqlmodel import SQLModel, create_engine

from app import models  # noqa: F401  (déclare les tables auprès de SQLModel)

logger = logging.getLogger("ffk.database")


def make_engine(database_url: str):
    # SQLite (utilisé par les tests) doit accepter les accès depuis plusieurs threads.
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(database_url, pool_pre_ping=True, connect_args=connect_args)


def init_db(engine):
    """Crée les tables manquantes. Une table existante n'est jamais modifiée."""
    try:
        SQLModel.metadata.create_all(engine)
    except Exception:
        logger.exception("init_db_failed dialect=%s", engine.dialect.name)
        raise
    logger.info("init_db_ok dialect=%s tables=%d", engine.dialect.name, len(SQLModel.metadata.tables))
