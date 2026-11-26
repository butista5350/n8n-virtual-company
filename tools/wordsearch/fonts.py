"""Embeddable fonts for KDP-ready PDFs (T0: local files only, no network).
Registers Liberation Sans (metric-compatible with Helvetica) so the fonts are embedded in the PDF.
Falls back to the built-in Helvetica (not embedded) if no TTF is found."""
import os

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

_CANDIDATES = [
    "/usr/share/fonts/truetype/liberation",
    "/usr/share/fonts/liberation",
    "/usr/share/fonts/truetype/liberation2",
    "C:/Windows/Fonts",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts"),
]
_FILES = {
    "WS-Regular": ("LiberationSans-Regular.ttf", "arial.ttf"),
    "WS-Bold": ("LiberationSans-Bold.ttf", "arialbd.ttf"),
    "WS-Italic": ("LiberationSans-Italic.ttf", "ariali.ttf"),
}
_FALLBACK = {"WS-Regular": "Helvetica", "WS-Bold": "Helvetica-Bold", "WS-Italic": "Helvetica-Oblique"}


def _register(name):
    for folder in _CANDIDATES:
        for fname in _FILES[name]:
            path = os.path.join(folder, fname)
            if os.path.isfile(path):
                pdfmetrics.registerFont(TTFont(name, path))
                return name
    return _FALLBACK[name]


REG = _register("WS-Regular")
BOLD = _register("WS-Bold")
OBL = _register("WS-Italic")
EMBEDDED = REG == "WS-Regular" and BOLD == "WS-Bold" and OBL == "WS-Italic"
