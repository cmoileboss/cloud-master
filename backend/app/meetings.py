import json
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field

from app.config import BACKEND_DIR
from app.models import Meeting


class MeetingSource(BaseModel):
    """Une réunion telle qu'écrite dans fixtures/meetings.json."""

    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=200)
    in_days: int = Field(ge=1)  # la réunion a lieu dans N jours (décalée au lundi si week-end)
    start_time: str
    end_time: str
    location: str = Field(min_length=1, max_length=500)
    recipients: list[str] = Field(min_length=1)
    agenda: list[str] = Field(min_length=1)
    confirm_days_before: int = Field(ge=0)
    contact: str


def today_paris() -> date:
    return datetime.now(ZoneInfo("Europe/Paris")).date()


def load_meetings(today: date | None = None) -> list[Meeting]:
    """Lit le calendrier fictif. Les dates sont calculées depuis aujourd'hui pour ne jamais expirer."""
    today = today or today_paris()
    items = json.loads((BACKEND_DIR / "fixtures" / "meetings.json").read_text(encoding="utf-8"))
    meetings = []
    for meeting_id, item in enumerate(items, start=1):
        source = MeetingSource.model_validate(item)
        meeting_date = today + timedelta(days=source.in_days)
        while meeting_date.weekday() >= 5:  # samedi ou dimanche
            meeting_date += timedelta(days=1)
        meetings.append(
            Meeting(
                id=meeting_id,
                meeting_date=meeting_date,
                confirmation_date=meeting_date - timedelta(days=source.confirm_days_before),
                **source.model_dump(exclude={"in_days", "confirm_days_before"}),
            )
        )
    return meetings
