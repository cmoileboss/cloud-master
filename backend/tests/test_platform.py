"""Santé, CORS et stockage : les points touchés lors d'un déploiement."""

import pytest

from app.config import Settings
from app.storage import LocalStorage


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
