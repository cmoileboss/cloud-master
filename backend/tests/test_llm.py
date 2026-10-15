"""Le vrai client OpenAI est utilisé, mais ses requêtes HTTP arrivent sur un faux fournisseur local."""

import json
from types import SimpleNamespace

import httpx2
import pytest
from openai import OpenAI
from pydantic import SecretStr

import app.llm as llm_module

VALID_CHOICE = {"meeting_id": 1, "text": "Madame, Monsieur, voici l'invitation.", "clarification": None}


def generate(client, **kwargs):
    return client.post("/api/documents/generate", json={"request": "La prochaine réunion."}, **kwargs)


def chat_completion(content: str) -> dict:
    """Réponse minimale au format « chat/completions »."""
    return {
        "id": "test",
        "object": "chat.completion",
        "created": 0,
        "model": "test-model",
        "choices": [
            {"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop"}
        ],
    }


@pytest.fixture
def provider(app, monkeypatch):
    """Configure le LLM vers un faux fournisseur. Modifier `provider.status` / `provider.body` pour simuler."""
    settings = app.state.llm.settings
    settings.llm_base_url = "https://llm.test/v1"
    settings.llm_model = "test-model"
    settings.llm_api_key = SecretStr("fake-key")

    provider = SimpleNamespace(requests=[], status=200, body=chat_completion(json.dumps(VALID_CHOICE)))

    def handle(request):
        provider.requests.append(request)
        return httpx2.Response(provider.status, json=provider.body)

    transport = httpx2.MockTransport(handle)
    monkeypatch.setattr(
        llm_module,
        "OpenAI",
        lambda **kwargs: OpenAI(**kwargs, http_client=httpx2.Client(transport=transport)),
    )
    return provider


def test_request_follows_chat_completions_with_json_mode(client, provider):
    response = generate(client)
    assert response.status_code == 200
    assert response.json()["meeting"]["id"] == 1

    request = provider.requests[0]
    assert str(request.url) == "https://llm.test/v1/chat/completions"
    assert request.headers["authorization"] == "Bearer fake-key"
    payload = json.loads(request.content)
    assert payload["model"] == "test-model"
    assert payload["response_format"] == {"type": "json_object"}
    system, user = payload["messages"]
    assert "générer une convocation" in system["content"] and "JSON" in system["content"]
    assert "La prochaine réunion." in user["content"] and "meetings" in user["content"]
    assert "fake-key" not in json.dumps(payload)


@pytest.mark.parametrize(
    "status,expected_status,expected_message",
    [
        (401, 502, "LLM_API_KEY"),
        (404, 502, "LLM_MODEL"),
        (429, 429, "Quota"),
        (400, 502, "mode JSON"),
        (500, 502, "logs du backend"),
    ],
)
def test_provider_errors_name_the_setting_to_check(
    client, provider, status, expected_status, expected_message
):
    provider.status, provider.body = status, {"error": {"message": "détail du fournisseur"}}
    response = generate(client)
    assert response.status_code == expected_status
    assert expected_message in response.json()["detail"]
    assert client.get("/api/documents").json() == []  # aucun document créé


def test_unreachable_provider(client, provider, monkeypatch):
    def refuse(request):
        raise httpx2.ConnectError("connexion refusée")

    monkeypatch.setattr(
        llm_module,
        "OpenAI",
        lambda **kwargs: OpenAI(**kwargs, http_client=httpx2.Client(transport=httpx2.MockTransport(refuse))),
    )
    response = generate(client)
    assert response.status_code == 502
    assert "LLM_BASE_URL" in response.json()["detail"]


@pytest.mark.parametrize("content", ["pas du JSON", json.dumps({"meeting_id": None, "text": ""})])
def test_invalid_model_output_is_rejected(client, provider, content):
    provider.body = chat_completion(content)
    response = generate(client)
    assert response.status_code == 502
    assert "format attendu" in response.json()["detail"]


def test_missing_configuration_sends_nothing(client, provider):
    client.app.state.llm.settings.llm_api_key = SecretStr("")
    response = generate(client)
    assert response.status_code == 503
    assert "LLM_API_KEY" in response.json()["detail"]
    assert provider.requests == []


def test_base_url_with_endpoint_path_is_explained(client, provider):
    client.app.state.llm.settings.llm_base_url = "https://llm.test/v1/chat/completions"
    response = generate(client)
    assert response.status_code == 503
    assert "/chat/completions" in response.json()["detail"]
    assert provider.requests == []


def test_llm_errors_reach_the_browser_with_cors_headers(client):
    response = generate(client, headers={"Origin": "http://localhost:5173"})
    assert response.status_code == 503
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
