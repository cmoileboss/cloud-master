from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from app.models import Meeting


def date_fr(value):
    return value.strftime("%d/%m/%Y")


def render_convocation(meeting: Meeting, text: str) -> bytes:
    """Construit le PDF : faits issus du calendrier, introduction rédigée par l'IA."""
    buffer = BytesIO()
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle("Letter", fontName="Helvetica", fontSize=11, leading=17, spaceAfter=10))
    styles.add(
        ParagraphStyle("Brand", fontName="Helvetica-Bold", fontSize=21, textColor=colors.HexColor("#173c35"))
    )
    styles.add(ParagraphStyle("SmallGrey", fontSize=8, leading=11, textColor=colors.HexColor("#66756f")))
    styles.add(ParagraphStyle("Headline", fontName="Helvetica-Bold", fontSize=16, leading=21, spaceAfter=14))
    styles.add(ParagraphStyle("Footer", fontSize=8, textColor=colors.grey, alignment=TA_CENTER))

    def p(value, style="Letter"):
        return Paragraph(escape(value).replace("\n", "<br/>"), styles[style])

    elements = [
        p("FFK / SERVICE DES GRADES", "Brand"),
        Spacer(1, 3 * mm),
        p("ENVIRONNEMENT PÉDAGOGIQUE • DOCUMENT FICTIF", "SmallGrey"),
        Spacer(1, 14 * mm),
        p(f"Convocation — {meeting.title}", "Headline"),
        p("À l'attention de : " + "; ".join(meeting.recipients)),
        p(
            f"Date : {date_fr(meeting.meeting_date)} — "
            f"{meeting.start_time.strftime('%H:%M')} à {meeting.end_time.strftime('%H:%M')} (Europe/Paris)"
        ),
        p("Lieu : " + meeting.location),
        Spacer(1, 4 * mm),
    ]
    for paragraph in text.strip().split("\n\n"):
        elements.append(p(paragraph))
    elements += [Spacer(1, 3 * mm), p("Ordre du jour", "Heading2")]
    for index, point in enumerate(meeting.agenda, 1):
        elements.append(p(f"{index}. {point}"))
    elements += [
        Spacer(1, 6 * mm),
        p(
            f"Merci de confirmer votre présence avant le {date_fr(meeting.confirmation_date)} "
            f"auprès de {meeting.contact}."
        ),
        Spacer(1, 6 * mm),
        p("Cordialement,\nLe secrétariat des grades"),
    ]

    def footer(canvas, document):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#66756f"))
        canvas.drawCentredString(A4[0] / 2, 16 * mm, "Exercice de formation — sans valeur officielle")
        canvas.drawRightString(A4[0] - 23 * mm, 16 * mm, f"Page {document.page}")
        canvas.restoreState()

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=22 * mm,
        bottomMargin=28 * mm,
        leftMargin=23 * mm,
        rightMargin=23 * mm,
        title=f"Convocation - {meeting.title}",
        author="Service des Grades - atelier pédagogique",
    )
    document.build(elements, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()
