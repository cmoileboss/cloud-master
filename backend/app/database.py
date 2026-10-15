from sqlmodel import SQLModel, create_engine

from app import models  # noqa: F401  (déclare les tables auprès de SQLModel)


def make_engine(database_url: str):
    # SQLite (utilisé par les tests) doit accepter les accès depuis plusieurs threads.
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(database_url, pool_pre_ping=True, connect_args=connect_args)


def init_db(engine):
    """Crée les tables manquantes. Une table existante n'est jamais modifiée."""
    SQLModel.metadata.create_all(engine)
