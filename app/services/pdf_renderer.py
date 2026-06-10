"""Render full activity details as a shareable A4 PDF."""
import io
import logging
import re
from pathlib import Path

import qrcode
from fpdf import FPDF
from fpdf.enums import XPos, YPos

logger = logging.getLogger(__name__)

_REGULAR_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/Library/Fonts/Arial.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
]
_BOLD_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
]

ACCENT = (196, 113, 74)      # #C4714A terracotta
TEXT_DARK = (61, 43, 31)     # #3D2B1F dark brown
TEXT_MUTED = (139, 112, 94)  # #8B705E warm muted
PAGE_BG = (253, 246, 238)    # #FDF6EE cream

MARGIN = 15      # mm
PAGE_W = 210     # A4
CONTENT_W = PAGE_W - 2 * MARGIN   # 180 mm

_LABELS = {
    "uk": {
        "materials": "Матеріали",
        "instructions": "Інструкції",
        "goals": "Цілі розвитку",
        "cta": "Завантажте застосунок — перший тиждень безкоштовно",
        "min": "хв",
        "year": "р",
    },
    "en": {
        "materials": "Materials",
        "instructions": "Instructions",
        "goals": "Developmental Goals",
        "cta": "Download the app — first week free",
        "min": "min",
        "year": "y",
    },
}


def _find_font_path(bold: bool = False) -> str | None:
    candidates = _BOLD_PATHS if bold else _REGULAR_PATHS
    return next((p for p in candidates if Path(p).exists()), None)


def _parse_steps(text: str) -> list[str]:
    """Split instruction text into individual steps."""
    text = text.strip()
    parts = re.split(r"\s*(?=\d+[\.\)]\s)", text)
    parts = [p.strip() for p in parts if p.strip()]
    if len(parts) > 1:
        return [re.sub(r"^\d+[\.\)]\s*", "", p) for p in parts]
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    return lines if lines else [text]


def _make_qr_buf(url: str) -> io.BytesIO:
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


class _PDF(FPDF):
    def __init__(self) -> None:
        super().__init__(orientation="P", unit="mm", format="A4")
        self.set_margins(MARGIN, 20, MARGIN)
        self.set_auto_page_break(auto=True, margin=MARGIN + 12)

        regular = _find_font_path(bold=False)
        bold = _find_font_path(bold=True)
        self._unicode = bool(regular and bold)
        if self._unicode:
            self.add_font("DejaVu", fname=regular)
            self.add_font("DejaVu", style="B", fname=bold)
        self._fam = "DejaVu" if self._unicode else "Helvetica"

    def _font(self, bold: bool = False, size: float = 11) -> None:
        self.set_font(self._fam, style="B" if bold else "", size=size)

    def _color(self, which: tuple[int, int, int]) -> None:
        self.set_text_color(*which)

    def header(self) -> None:
        self.set_fill_color(*PAGE_BG)
        self.rect(0, 0, PAGE_W, 297, style="F")
        self.set_fill_color(*ACCENT)
        self.rect(0, 0, PAGE_W, 5, style="F")
        self.set_xy(MARGIN, 7)
        self._color(TEXT_MUTED)
        self._font(size=10)
        self.cell(CONTENT_W, 5, "Kids Activity", align="R",
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_y(self.t_margin)

    def footer(self) -> None:
        self.set_y(-10)
        self._color(TEXT_MUTED)
        self._font(size=8)
        self.cell(0, 5, str(self.page_no()), align="C",
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # ── helpers ──────────────────────────────────────────────────────────────

    def section_header(self, text: str) -> None:
        self._color(ACCENT)
        self._font(bold=True, size=18)
        self.multi_cell(CONTENT_W, 10, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(3)

    def body_text(self, text: str, indent: float = 0) -> None:
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
        self._color(TEXT_DARK)
        self._font(size=16)
        self.set_x(MARGIN + indent)
        self.multi_cell(CONTENT_W - indent, 10, text,
                        new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def separator(self) -> None:
        self.ln(2)
        y = self.get_y()
        self.set_draw_color(*TEXT_MUTED)
        self.set_line_width(0.3)
        self.line(MARGIN, y, PAGE_W - MARGIN, y)
        self.ln(5)


def render_activity_pdf(
    *,
    title: str,
    description: str,
    instructions: str,
    materials: list[str],
    goals: list[str],
    category: str,
    energy_level: str,
    duration_minutes: int,
    min_age_months: int,
    max_age_months: int,
    share_url: str,
    lang: str = "uk",
) -> bytes:
    lbl = _LABELS.get(lang, _LABELS["en"])
    pdf = _PDF()
    pdf.add_page()

    # ── title ─────────────────────────────────────────────────────────────────
    pdf._color(TEXT_DARK)
    pdf._font(bold=True, size=28)
    pdf.multi_cell(CONTENT_W, 13, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(4)

    # ── meta line ─────────────────────────────────────────────────────────────
    min_y = min_age_months // 12
    max_y = max_age_months // 12
    age = f"{min_y}–{max_y} {lbl['year']}" if min_y != max_y else f"{min_y} {lbl['year']}"
    meta = f"{category}  ·  {duration_minutes} {lbl['min']}  ·  {age}  ·  {energy_level}"
    pdf._color(TEXT_MUTED)
    pdf._font(size=13)
    pdf.multi_cell(CONTENT_W, 8, meta, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.separator()

    # ── description ───────────────────────────────────────────────────────────
    pdf.body_text(description)
    pdf.ln(4)

    # ── materials ─────────────────────────────────────────────────────────────
    if materials:
        pdf.section_header(lbl["materials"])
        for m in materials:
            pdf.body_text(f"·  {m}", indent=3)
        pdf.ln(4)

    # ── instructions ─────────────────────────────────────────────────────────
    if instructions:
        pdf.section_header(lbl["instructions"])
        for i, step in enumerate(_parse_steps(instructions), 1):
            pdf.body_text(f"{i}.  {step}", indent=3)
            pdf.ln(1)
        pdf.ln(3)

    # ── goals ─────────────────────────────────────────────────────────────────
    if goals:
        pdf.section_header(lbl["goals"])
        for g in goals:
            pdf.body_text(f"·  {g}", indent=3)
        pdf.ln(4)

    # ── footer: kids-activity.app + QR ───────────────────────────────────────
    qr_size = 52  # mm
    if pdf.get_y() + qr_size + 20 > pdf.h - pdf.b_margin:
        pdf.add_page()
    pdf.separator()
    footer_y = pdf.get_y()
    text_col_w = CONTENT_W - qr_size - 8

    # Left column: URL + CTA — reset to footer_y so columns start at same line
    pdf.set_xy(MARGIN, footer_y)
    pdf._color(ACCENT)
    pdf._font(bold=True, size=13)
    pdf.cell(text_col_w, 8, "kids-activity.app",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_x(MARGIN)
    pdf._color(TEXT_MUTED)
    pdf._font(size=10)
    pdf.multi_cell(text_col_w, 6, lbl["cta"],
                   new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # Right column: QR pinned absolutely — never pushed by text
    try:
        pdf.image(_make_qr_buf(share_url),
                  x=PAGE_W - MARGIN - qr_size, y=footer_y,
                  w=qr_size, h=qr_size)
    except Exception:
        logger.exception("QR embed failed for url=%s", share_url)

    return bytes(pdf.output())
