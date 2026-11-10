"""Santé, CORS et stockage : les points touchés lors d'un déploiement."""

import pytest

import app.storage as storage_module
from app.config import Settings
from app.storage import BlobStorage, LocalStorage


def test_health_endpoints(client):
    assert client.get("/health/live").json() == {"status": "ok"}
    assert client.get("/health/ready").json() == {"status": "ok"}


@pytest.mark.parametrize("origin,allowed", [("http://localhost:5173", True), ("https://inconnu.test", False)])
def test_cors_allows_only_configured_origins(client, origin, allowed):
    response = client.options(
        "/api/documents", headers={"Origin": origin, "Access-Control-Request-Method": "GET"}
    )
    assert (response.headers.get("access-control-allow-origin") == origin) is allowed


def test_cors_origins_tolerate_spaces_and_trailing_slash():
    settings = Settings(_env_file=None, cors_origins=" https://front.test/ , http://localhost:5173")
    assert settings.cors_origin_list == ["https://front.test", "http://localhost:5173"]


def test_local_storage_round_trip(tmp_path):
    LocalStorage(tmp_path).put("doc.pdf", b"%PDF-test")
    assert LocalStorage(tmp_path).get("doc.pdf") == b"%PDF-test"  # nouvelle instance : fichier persistant


def test_local_storage_rejects_path_escape(tmp_path):
    with pytest.raises(ValueError):
        LocalStorage(tmp_path).get("../../secret.txt")


def test_blob_storage_uses_azure_client(monkeypatch):
    class FakeContainer:
        def __init__(self):
            self.upload = None

        def upload_blob(self, **kwargs):
            self.upload = kwargs

        def download_blob(self, key):
            assert key == "doc.pdf"
            return type("FakeBlob", (), {"readall": lambda self: b"%PDF-test"})()

    container = FakeContainer()
    client_options = {}

    class FakeBlobServiceClient:
        def __init__(self, account_url, credential):
            client_options.update(account_url=account_url, credential=credential)

        def get_container_client(self, container_name):
            assert container_name == "documents"
            return container

    monkeypatch.setattr(storage_module, "BlobServiceClient", FakeBlobServiceClient)
    monkeypatch.setattr(storage_module, "DefaultAzureCredential", lambda: "fake-credential")

    storage = BlobStorage("https://account.blob.core.windows.net", "documents")
    storage.put("doc.pdf", b"%PDF-test")

    assert client_options == {
        "account_url": "https://account.blob.core.windows.net",
        "credential": "fake-credential",
    }
    assert container.upload["name"] == "doc.pdf"
    assert container.upload["data"] == b"%PDF-test"
    assert container.upload["overwrite"] is True
    assert container.upload["content_settings"].content_type == "application/pdf"
    assert storage.get("doc.pdf") == b"%PDF-test"
