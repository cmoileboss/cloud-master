from io import BytesIO

from fastapi.testclient import TestClient
from pypdf import PdfReader

from app.main import create_app
from app.meetings import load_meetings, today_paris
from app.models import ConvocationChoice


def generate(client, request="Prépare la convocation pour le bilan des sessions."):
    return client.post("/api/documents/generate", json={"request": request})


def pdf_text(content: bytes) -> str:
    return "\n".join(page.extract_text() for page in PdfReader(BytesIO(content)).pages)


def test_calendar_dates_are_upcoming_weekdays(client):
    meetings = client.get("/api/meetings").json()
    assert len(meetings) == 2
    for meeting in load_meetings():
        assert meeting.meeting_date > today_paris()
        assert meeting.meeting_date.weekday() < 5
        assert meeting.confirmation_date < meeting.meeting_date


def test_pdf_uses_calendar_facts_and_llm_text(client, fake_llm):
    meeting = load_meetings()[1]  # fake_llm choisit la réunion n°2

    result = generate(client).json()
    assert result["meeting"]["title"] == meeting.title
    assert result["text"] == fake_llm.choice.text

    response = client.get(f"/api/documents/{result['document']['id']}/download")
    assert response.status_code == 200
    text = pdf_text(response.content)
    assert meeting.meeting_date.strftime("%d/%m/%Y") in text
    assert "14:00" in text and "16:00" in text
    assert "Bilan des sessions" in text  # ordre du jour
    assert "Invitation de test." in text
    assert "sans valeur officielle" in text


def test_generated_documents_are_listed(client, fake_llm):
    first = generate(client).json()["document"]
    second = generate(client).json()["document"]
    listed = [doc["id"] for doc in client.get("/api/documents").json()]
    assert set(listed) == {first["id"], second["id"]}


def test_no_matching_meeting_asks_for_clarification(client, fake_llm):
    fake_llm.choice = ConvocationChoice(meeting_id=None, clarification="Quelle réunion ?")
    result = generate(client, "Convocation pour la réunion de février.").json()
    assert result == {"clarification": "Quelle réunion ?", "document": None, "meeting": None, "text": ""}
    assert client.get("/api/documents").json() == []


def test_invented_meeting_is_rejected(client, fake_llm):
    fake_llm.choice = ConvocationChoice(meeting_id=999, text="Une invitation.")
    assert generate(client).status_code == 502
    assert client.get("/api/documents").json() == []


def test_storage_failure_creates_no_document(client, app, fake_llm):
    def storage_down(key, content):
        raise OSError("secret-connection-string")

    app.state.storage.put = storage_down
    response = generate(client)
    assert response.status_code == 502
    assert "Stockage" in response.json()["detail"]
    assert "secret-connection-string" not in response.text
    assert client.get("/api/documents").json() == []


def test_unknown_document_returns_404(client):
    assert client.get("/api/documents/inconnu/download").status_code == 404


def test_documents_survive_a_restart(client, settings, fake_llm):
    document = generate(client).json()["document"]

    with TestClient(create_app(settings)) as restarted:
        assert [doc["id"] for doc in restarted.get("/api/documents").json()] == [document["id"]]
        assert restarted.get(f"/api/documents/{document['id']}/download").status_code == 200
