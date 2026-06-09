"""Render shareable activity cards (PNG) for social sharing.

1080x1920 Instagram Stories format. Pillow.
Fonts: tries DejaVuSans (common on Linux/macOS); falls back to default bitmap font.
"""
import io
import logging
from pathlib import Path

import qrcode
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

WIDTH = 1080
HEIGHT = 1920
MARGIN = 80

BG_TOP = (255, 230, 220)  # warm pastel peach
BG_BOTTOM = (220, 235, 255)  # soft blue
TEXT_DARK = (40, 40, 60)
TEXT_MUTED = (110, 110, 130)
ACCENT = (255, 130, 100)

_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "DejaVuSans-Bold.ttf",
]
_FONT_REGULAR_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/Library/Fonts/Arial.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "DejaVuSans.ttf",
]


def _load_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    candidates = _FONT_CANDIDATES if bold else _FONT_REGULAR_CANDIDATES
    for path in candidates:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _draw_gradient(img: Image.Image) -> None:
    strip = Image.new("RGB", (1, HEIGHT))
    for y in range(HEIGHT):
        ratio = y / HEIGHT
        r = int(BG_TOP[0] * (1 - ratio) + BG_BOTTOM[0] * ratio)
        g = int(BG_TOP[1] * (1 - ratio) + BG_BOTTOM[1] * ratio)
        b = int(BG_TOP[2] * (1 - ratio) + BG_BOTTOM[2] * ratio)
        strip.putpixel((0, y), (r, g, b))
    img.paste(strip.resize((WIDTH, HEIGHT), Image.NEAREST))


def _wrap(text: str, font: ImageFont.ImageFont, max_width: int, draw: ImageDraw.ImageDraw) -> list[str]:
    words = text.split()
    if not words:
        return []
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        bbox = draw.textbbox((0, 0), candidate, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def _make_qr(url: str, size: int) -> Image.Image:
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    return img.resize((size, size), Image.LANCZOS)


def render_activity_card(
    *,
    title: str,
    description: str,
    materials: list[str],
    cta_label: str,
    share_url: str,
) -> bytes:
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_TOP)
    _draw_gradient(img)
    draw = ImageDraw.Draw(img)

    title_font = _load_font(80, bold=True)
    desc_font = _load_font(38)
    mat_font = _load_font(36)
    footer_font = _load_font(34, bold=True)
    cta_font = _load_font(28)

    y = MARGIN + 260

    draw.rectangle((MARGIN, y, MARGIN + 120, y + 12), fill=ACCENT)
    y += 80

    title_lines = _wrap(title, title_font, WIDTH - 2 * MARGIN, draw)[:3]
    for line in title_lines:
        draw.text((MARGIN, y), line, fill=TEXT_DARK, font=title_font)
        bbox = draw.textbbox((0, 0), line, font=title_font)
        y += (bbox[3] - bbox[1]) + 20

    y += 70
    if description:
        for line in _wrap(description, desc_font, WIDTH - 2 * MARGIN, draw)[:10]:
            draw.text((MARGIN, y), line, fill=TEXT_MUTED, font=desc_font)
            bbox = draw.textbbox((0, 0), line, font=desc_font)
            y += (bbox[3] - bbox[1]) + 14

    y += 120
    if materials:
        draw.rectangle((MARGIN, y, MARGIN + 80, y + 6), fill=ACCENT)
        y += 30
        for material in materials[:6]:
            text = f"·  {material}"
            for line in _wrap(text, mat_font, WIDTH - 2 * MARGIN, draw)[:1]:
                draw.text((MARGIN, y), line, fill=TEXT_DARK, font=mat_font)
                bbox = draw.textbbox((0, 0), line, font=mat_font)
                y += (bbox[3] - bbox[1]) + 16

    qr_size = 240
    qr_x = WIDTH - MARGIN - qr_size
    qr_y = HEIGHT - MARGIN - qr_size
    try:
        qr_img = _make_qr(share_url, qr_size)
        img.paste(qr_img, (qr_x, qr_y))
    except Exception:
        logger.exception("QR generation failed for url=%s", share_url)

    url_font = _load_font(30, bold=True)
    footer_y = HEIGHT - MARGIN - 260
    draw.text((MARGIN, footer_y), "PlayDay", fill=TEXT_DARK, font=footer_font)
    draw.text((MARGIN, footer_y + 48), "playday.app", fill=ACCENT, font=url_font)
    cta_y = footer_y + 96
    cta_max_width = qr_x - MARGIN - 40
    for line in _wrap(cta_label, cta_font, cta_max_width, draw):
        draw.text((MARGIN, cta_y), line, fill=TEXT_MUTED, font=cta_font)
        bbox = draw.textbbox((0, 0), line, font=cta_font)
        cta_y += (bbox[3] - bbox[1]) + 8

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
