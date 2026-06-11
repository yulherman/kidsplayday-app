"""Load static AI prompt instructions from .txt files at import time."""

from pathlib import Path

_DIR = Path(__file__).parent


def _load(name: str) -> str:
    return (_DIR / name).read_text(encoding="utf-8").strip()


def _load_dir(subdir: str) -> dict[str, str]:
    d = _DIR / subdir
    return {f.stem: f.read_text(encoding="utf-8").strip() for f in sorted(d.glob("*.txt"))}


GENERATE_INSTRUCTIONS = _load("generate_instructions.txt")
TRANSLATE_INSTRUCTIONS = _load("translate_instructions.txt")
VERIFY_INSTRUCTIONS = _load("verify_instructions.txt")
MONTESSORI_PRINCIPLES = _load("montessori.txt")
AGE_PROFILES = _load_dir("ages")
LANGUAGE_HINTS = _load_dir("languages")
ENCOURAGEMENT_EXAMPLES = _load_dir("encouragement")
