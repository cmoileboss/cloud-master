"""Fixtures partagées : une application neuve par test, avec SQLite et un dossier temporaire."""

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.models import ConvocationChoice


class FakeLLM:
    """Remplace le fournisseur LLM : réponses fixes et modifiables, aucun appel réseau."""

    def __init__(self):
        self.choice = ConvocationChoice(meeting_id=2, text="Madame, Monsieur,\n\nInvitation de test.")

    def choose_meeting(self, request, meetings):
        return self.choice


@pytest.fixture
def settings(tmp_path):
    return Settings(
        _env_file=None,  # ne pas lire le .env du développeur
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        data_dir=tmp_path / "data",
        cors_origins="http://localhost:5173",
        llm_base_url="",
        llm_model="",
        llm_api_key="",
    )


@pytest.fixture
def app(settings):
    return create_app(settings)


@pytest.fixture
def client(app):
    with TestClient(app) as client:  # « with » déclenche le démarrage (création des tables)
        yield client


@pytest.fixture
def fake_llm(app):
    app.state.llm = FakeLLM()
    return app.state.llm
