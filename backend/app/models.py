from datetime import date, datetime, time, timezone

from pydantic import BaseModel, ConfigDict, model_validator
from pydantic import Field as PydanticField
from sqlalchemy import DateTime
from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Document(SQLModel, table=True):
    """Convocation générée : les informations sont en base, le fichier PDF dans le stockage."""

    id: str = Field(primary_key=True)
    title: str
    meeting_date: date
    storage_key: str
    created_at: datetime = Field(default_factory=utc_now, sa_type=DateTime(timezone=True))


class Meeting(BaseModel):
    """Réunion du calendrier fictif (voir app/meetings.py)."""

    id: int
    title: str
    meeting_date: date
    start_time: time
    end_time: time
    location: str
    recipients: list[str]
    agenda: list[str]
    confirmation_date: date
    contact: str


class ConvocationRequest(BaseModel):
    """Demande envoyée par le frontend."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    request: str = PydanticField(min_length=5, max_length=3000)


class ConvocationChoice(BaseModel):
    """Réponse attendue du LLM, validée avant utilisation."""

    model_config = ConfigDict(extra="forbid")
    meeting_id: int | None = None
    text: str = PydanticField(default="", max_length=3000)
    clarification: str | None = PydanticField(default=None, max_length=500)

    @model_validator(mode="after")
    def complete_answer(self):
        if self.meeting_id is None and not self.clarification:
            raise ValueError("Une question de précision est attendue lorsqu'aucune réunion ne correspond.")
        if self.meeting_id is not None and not self.text.strip():
            raise ValueError("Le texte de la convocation est attendu.")
        return self


class ConvocationResult(BaseModel):
    """Réponse au frontend : soit une question de précision, soit le document créé et son contenu."""

    clarification: str | None = None
    document: Document | None = None
    meeting: Meeting | None = None
    text: str = ""
