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

RENDERER_VERSION = "v3"

_LABELS = {
    "uk": {
        "materials": "Матеріали",
        "instructions": "Інструкції",
        "goals": "Цілі розвитку",
        "cta": "Завантажте застосунок — перший тиждень безкоштовно",
        "min": "хв",
        "year": "р",
        "months": "міс",
        "meta_type": "Тип",
        "meta_time": "Час",
        "meta_age": "Вік",
        "meta_energy": "Енергія",
        "cat_creative": "Творчість",
        "cat_science": "Наука",
        "cat_sport": "Спорт",
        "cat_cooking": "Кулінарія",
        "cat_outdoor": "На вулиці",
        "cat_social": "Соціальна",
        "cat_sensory": "Сенсорна",
        "cat_music": "Музика",
        "cat_logic": "Логіка",
        "energy_calm": "Спокійна",
        "energy_moderate": "Помірна",
        "energy_active": "Активна",
    },
    "en": {
        "materials": "Materials",
        "instructions": "Instructions",
        "goals": "Developmental Goals",
        "cta": "Download the app — first week free",
        "min": "min",
        "year": "y",
        "months": "mo",
        "meta_type": "Type",
        "meta_time": "Time",
        "meta_age": "Age",
        "meta_energy": "Energy",
        "cat_creative": "Creative",
        "cat_science": "Science",
        "cat_sport": "Sport",
        "cat_cooking": "Cooking",
        "cat_outdoor": "Outdoor",
        "cat_social": "Social",
        "cat_sensory": "Sensory",
        "cat_music": "Music",
        "cat_logic": "Logic",
        "energy_calm": "Calm",
        "energy_moderate": "Moderate",
        "energy_active": "Active",
    },
}


def _format_category(category: str, lbl: dict) -> str:
    return lbl.get(f"cat_{category.lower()}", category.capitalize())


def _format_energy(energy: str, lbl: dict) -> str:
    return lbl.get(f"energy_{energy.lower()}", energy.capitalize())


def _format_age_range(min_months: int, max_months: int, lbl: dict) -> str:
    """Render an age range. Months for ranges where the upper bound is
    < 24 months (babies and explorers); years otherwise. Single-value
    ranges (min == max) collapse to one number."""
    if max_months < 24:
        if min_months == max_months:
            return f"{min_months} {lbl['months']}"
        return f"{min_months}–{max_months} {lbl['months']}"
    min_y = min_months // 12
    max_y = max_months // 12
    if min_y == max_y:
        return f"{min_y} {lbl['year']}"
    return f"{min_y}–{max_y} {lbl['year']}"


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
        self.multi_cell(CONTENT_W, 10, text, align="L",
                        new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(3)

    def body_text(self, text: str, indent: float = 0) -> None:
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
        self._color(TEXT_DARK)
        self._font(size=13)
        self.set_x(MARGIN + indent)
        self.multi_cell(CONTENT_W - indent, 6.5, text, align="L",
                        new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def numbered_step(self, num: int, text: str,
                      num_w: float = 8, text_indent: float = 3) -> None:
        """Render a numbered step with hanging indent: the number sits in
        its own fixed-width column; wrapped lines of the step text align
        under the first letter of the text, not under the number."""
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
        self._color(TEXT_DARK)
        self._font(size=13)
        line_h = 6.5
        start_y = self.get_y()
        self.set_xy(MARGIN + text_indent, start_y)
        self.cell(num_w, line_h, f"{num}.", align="L",
                  new_x=XPos.RIGHT, new_y=YPos.TOP)
        self.multi_cell(CONTENT_W - text_indent - num_w, line_h, text,
                        align="L", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

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
    pdf.multi_cell(CONTENT_W, 13, title, align="L",
                   new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(4)

    # ── meta line ─────────────────────────────────────────────────────────────
    meta_parts = [
        f"{lbl['meta_type']}: {_format_category(category, lbl)}",
        f"{lbl['meta_time']}: {duration_minutes} {lbl['min']}",
        f"{lbl['meta_age']}: {_format_age_range(min_age_months, max_age_months, lbl)}",
        f"{lbl['meta_energy']}: {_format_energy(energy_level, lbl)}",
    ]
    meta = "  ·  ".join(meta_parts)
    pdf._color(TEXT_MUTED)
    pdf._font(size=13)
    pdf.multi_cell(CONTENT_W, 8, meta, align="L",
                   new_x=XPos.LMARGIN, new_y=YPos.NEXT)

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
            pdf.numbered_step(i, step)
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
    pdf.multi_cell(text_col_w, 6, lbl["cta"], align="L",
                   new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # Right column: QR pinned absolutely — never pushed by text
    try:
        pdf.image(_make_qr_buf(share_url),
                  x=PAGE_W - MARGIN - qr_size, y=footer_y,
                  w=qr_size, h=qr_size)
    except Exception:
        logger.exception("QR embed failed for url=%s", share_url)

    return bytes(pdf.output())
