from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _register_font() -> str:
    try:
        import reportlab

        font_path = Path(reportlab.__file__).parent / "fonts" / "Vera.ttf"
        pdfmetrics.registerFont(TTFont("Q2SCVera", str(font_path)))
        return "Q2SCVera"
    except Exception:
        return "Helvetica"


def build_quantum_report(payload: dict[str, Any]) -> bytes:
    buffer = BytesIO()
    font_name = _register_font()
    styles = getSampleStyleSheet()
    for style in styles.byName.values():
        style.fontName = font_name

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        title=str(payload.get("title") or "Q2SC quantum report"),
        author="Q2SC",
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )
    molecule = payload.get("molecule") or {}
    result = payload.get("result") or {}
    interpretation = payload.get("interpretation") or {}
    story = [
        Paragraph(str(payload.get("title") or "Отчёт Q2SC"), styles["Title"]),
        Spacer(1, 12),
        Paragraph(
            f"Профиль: {payload.get('profile', 'unknown')}<br/>"
            f"Молекула: {molecule.get('name', '—')}<br/>"
            f"Формула: {molecule.get('formula', '—')}<br/>"
            f"SMILES: {molecule.get('canonical_smiles', molecule.get('input_smiles', '—'))}",
            styles["BodyText"],
        ),
        Spacer(1, 12),
        Paragraph("Основные результаты", styles["Heading2"]),
    ]
    rows = [
        ["Движок", f"{result.get('engine', '—')} {result.get('engine_version', '')}"],
        ["Метод", f"{result.get('method', '—')}/{result.get('basis', '—')}"],
        ["Энергия, Eh", str(result.get("electronic_energy_hartree", "—"))],
        ["HOMO-LUMO, эВ", str(result.get("gap_ev", "—"))],
        ["Время, с", str(result.get("elapsed_sec", "—"))],
    ]
    table = Table(rows, colWidths=[150, 330])
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), font_name),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#64748b")),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#e2e8f0")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("PADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.extend([table, Spacer(1, 12), Paragraph("Интерпретация", styles["Heading2"])])
    story.append(Paragraph(str(interpretation.get("summary") or "Интерпретация отсутствует."), styles["BodyText"]))
    for finding in interpretation.get("findings") or []:
        story.append(Paragraph(f"• {finding}", styles["BodyText"]))
    story.extend([Spacer(1, 12), Paragraph("Ограничения", styles["Heading2"])])
    for limitation in (result.get("provenance") or {}).get("limitations") or []:
        story.append(Paragraph(f"• {limitation}", styles["BodyText"]))
    document.build(story)
    return buffer.getvalue()
