"""Checks the content lists in the frontend. The UI itself is exercised in a browser."""

import re
from pathlib import Path

FRONTEND = Path(__file__).resolve().parents[2] / "frontend" / "src"


def strings_in(text):
    return re.findall(r"^\s*'((?:[^'\\]|\\.)+)',\s*$", text, re.M)


def test_quote_library_size_and_uniqueness():
    text = (FRONTEND / "data" / "quotes.js").read_text(encoding="utf-8")
    quotes = strings_in(text)
    assert 50 <= len(quotes) <= 100, len(quotes)
    assert len({q.lower() for q in quotes}) == len(quotes), "duplicate quote"
    assert all(len(q) <= 90 for q in quotes), "a quote is too long for the card"


def test_mascot_phrases_are_short_enough_for_the_bubble():
    text = (FRONTEND / "data" / "phrases.js").read_text(encoding="utf-8")
    phrases = re.findall(r"'((?:[^'\\]|\\.){3,})'", text)
    phrases = [p for p in phrases if p not in ("night", "morning", "afternoon", "evening", "worried", "happy", "sleepy", "cheer")]
    assert len(phrases) >= 30
    assert all(len(p.replace("\\", "")) <= 24 for p in phrases), [p for p in phrases if len(p) > 24]


def test_theme_stays_blue():
    css = (FRONTEND / "styles.css").read_text(encoding="utf-8")
    for token in ("--blue-deep", "--blue-pale", "--sky"):
        assert token in css
    assert "pink" not in css, "D-031: the theme is blue"


def test_phone_layout_essentials_are_present():
    css = (FRONTEND / "styles.css").read_text(encoding="utf-8")
    html = (FRONTEND.parent / "index.html").read_text(encoding="utf-8")
    assert "viewport-fit=cover" in html, "needed for safe-area insets"
    assert "safe-area-inset-bottom" in css and "pointer: coarse" in css and "hover: none" in css
    assert "prefers-reduced-motion" in css

