"""Fixtures partagées : une application neuve par test, avec SQLite et un dossier temporaire."""

import os

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.models import ConvocationChoice


def pytest_configure():
    # app.main crée une application au chargement du module.
    os.environ["AZURE_STORAGE_ACCOUNT_URL"] = "https://test.blob.core.windows.net"
    os.environ["AZURE_STORAGE_CONTAINER"] = "test-container"


class FakeBlobStorage:
    """Stockage Blob en mémoire pour éviter tout accès au compte Azure pendant les tests."""

    def __init__(self):
        self.blobs = {}

    def put(self, key, content, content_type="application/pdf"):
        self.blobs[key] = content

    def get(self, key):
        return self.blobs[key]


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
        azure_storage_account_url="https://test.blob.core.windows.net",
        azure_storage_container="test-container",
        llm_base_url="",
        llm_model="",
        llm_api_key="",
    )


@pytest.fixture
def blob_storage():
    return FakeBlobStorage()


@pytest.fixture
def app(settings, blob_storage):
    from app.main import create_app

    app = create_app(settings)
    app.state.blob_storage = blob_storage
    return app


@pytest.fixture
def client(app):
    with TestClient(app) as client:  # « with » déclenche le démarrage (création des tables)
        yield client


@pytest.fixture
def fake_llm(app):
    app.state.llm = FakeLLM()
    return app.state.llm
