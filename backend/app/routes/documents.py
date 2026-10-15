import logging
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from sqlmodel import select

from app.deps import DB, LLM, Storage
from app.meetings import load_meetings
from app.models import ConvocationRequest, ConvocationResult, Document, Meeting
from app.pdf import render_convocation

logger = logging.getLogger("ffk.documents")

router = APIRouter(prefix="/api", tags=["convocations"])


@router.get("/meetings", response_model=list[Meeting])
def list_meetings():
    return load_meetings()


@router.get("/documents", response_model=list[Document])
def list_documents(db: DB):
    return db.exec(select(Document).order_by(Document.created_at.desc())).all()


@router.post("/documents/generate", response_model=ConvocationResult)
def generate_convocation(body: ConvocationRequest, db: DB, llm: LLM, storage: Storage):
    """Le LLM choisit une réunion du calendrier et rédige l'introduction ; le reste vient du calendrier."""
    meetings = load_meetings()
    choice = llm.choose_meeting(body.request, meetings)
    if choice.meeting_id is None:
        return ConvocationResult(clarification=choice.clarification)

    meeting = next((m for m in meetings if m.id == choice.meeting_id), None)
    if meeting is None:
        raise HTTPException(502, "L'IA a choisi une réunion absente du calendrier. Précisez la demande.")

    document_id = uuid4().hex
    document = Document(
        id=document_id,
        title=meeting.title,
        meeting_date=meeting.meeting_date,
        storage_key=f"{document_id}.pdf",
    )
    pdf = render_convocation(meeting, choice.text)
    try:
        storage.put(document.storage_key, pdf)
    except Exception:
        logger.exception("storage_put_failed key=%s", document.storage_key)
        raise HTTPException(502, "Stockage des PDF indisponible. Détail dans les logs du backend.")

    db.add(document)
    db.commit()
    db.refresh(document)
    return ConvocationResult(document=document, meeting=meeting, text=choice.text)


@router.get("/documents/{document_id}/download")
def download_document(document_id: str, db: DB, storage: Storage):
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(404, "Document introuvable.")
    try:
        content = storage.get(document.storage_key)
    except Exception:
        logger.exception("storage_get_failed key=%s", document.storage_key)
        raise HTTPException(502, "PDF inaccessible dans le stockage. Détail dans les logs du backend.")
    return Response(
        content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="convocation-{document.meeting_date}.pdf"'},
    )
