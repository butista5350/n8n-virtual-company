#!/usr/bin/env python3
"""Generate a full-wrap paperback cover PDF (KDP, white paper, B&W interior).
Spine = pages x 0.002252 in (white paper). Bleed 0.125 in. T0 tool: no network, no LLM.
Design: original artwork only (gradient, drawn letter grid, highlight bars, badge)."""
import argparse
import json
import math
import os
import random
import string
import sys

from reportlab.lib.colors import Color, HexColor, white
from reportlab.lib.utils import simpleSplit
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fonts import REG, BOLD, OBL  # noqa: E402

IN = 72.0
TRIM_W, TRIM_H, BLEED = 8.5, 11.0, 0.125
SPINE_PER_PAGE = 0.002252      # white paper, black ink
SPINE_TEXT_MIN_PAGES = 79      # KDP guidance: spine text only on thicker books

DEFAULT_PALETTE = {
    "bg_top": "#0B3C5D", "bg_bottom": "#1D7A8C",
    "accent": "#F5B83D", "coral": "#F4785B", "mint": "#7ED6B2", "sky": "#8EC9F2",
    "card": "#FFFDF7", "ink": "#12324A", "text": "#FFFFFF",
}


def cover_dimensions(pages):
    spine = pages * SPINE_PER_PAGE
    width = BLEED + TRIM_W + spine + TRIM_W + BLEED
    height = BLEED + TRIM_H + BLEED
    return {"spine_in": spine, "width_in": width, "height_in": height}


def fit_font(text, font, max_w, start, minimum=20):
    size = start
    while size > minimum and stringWidth(text, font, size) > max_w:
        size -= 1
    return size


def spaced(c, text, x, y, font, size, spacing, align="center"):
    """Draw letter-spaced text."""
    total = sum(stringWidth(ch, font, size) for ch in text) + spacing * (len(text) - 1)
    cur = x - total / 2 if align == "center" else x
    c.setFont(font, size)
    for ch in text:
        c.drawString(cur, y, ch)
        cur += stringWidth(ch, font, size) + spacing


def alpha(c, a):
    c.setFillAlpha(a)
    c.setStrokeAlpha(a)


def gradient_bg(c, W, H, top, bottom):
    c.saveState()
    c.linearGradient(0, H, 0, 0, (top, bottom))
    c.restoreState()


def circles(c, W, H, pal, rng):
    c.saveState()
    c.setFillColor(white)
    alpha(c, 0.06)
    for cx, cy, r in ((0.12, 0.88, 2.4), (0.95, 0.12, 3.0), (0.5, 0.5, 4.2)):
        c.circle(W * cx, H * cy, r * IN, stroke=0, fill=1)
    c.restoreState()


def sample_grid(seed, words):
    """9x9 teaser grid. words: list of (word, row, col, (dr, dc))."""
    n = 9
    g = [[""] * n for _ in range(n)]
    for w, r, col, (dr, dc) in words:
        for i, ch in enumerate(w):
            g[r + dr * i][col + dc * i] = ch
    rng = random.Random(seed)
    for r in range(n):
        for col in range(n):
            if not g[r][col]:
                g[r][col] = rng.choice("AEIOULNRSTMDPCHBGFWYK")
    return g


def draw_front(c, x0, pal, cfg, pages):
    if cfg.get("cover", {}).get("layout") == "garden":
        return draw_front_garden(c, x0, pal, cfg, pages)
    if cfg.get("cover", {}).get("layout") == "birds":
        return draw_front_birds(c, x0, pal, cfg, pages)
    ink, acc, coral, mint, sky = (HexColor(pal[k]) for k in ("ink", "accent", "coral", "mint", "sky"))
    txt = HexColor(pal["text"])
    ox, oy = x0, BLEED * IN                       # origin of the trim box
    cx = ox + TRIM_W * IN / 2
    # --- headline ---
    c.setFillColor(acc)
    spaced(c, "LARGE PRINT", cx, oy + 10.28 * IN, BOLD, 24, 7)
    title = cfg["title"].upper().replace("LARGE PRINT", "").strip() or cfg["title"].upper()
    parts = title.split(" ", 1)
    y = oy + 9.12 * IN
    for p in parts:
        size = fit_font(p, BOLD, 6.6 * IN, 90)
        c.setFillColor(txt)
        c.setFont(BOLD, size)
        c.drawCentredString(cx, y, p)
        last = y
        y -= size * 0.98
    c.setStrokeColor(acc)
    c.setLineWidth(4)
    c.line(cx - 1.0 * IN, last - 0.2 * IN, cx + 1.0 * IN, last - 0.2 * IN)
    sub = cfg["subtitle"].upper().lstrip("0123456789 ")   # the badge already says the number
    c.setFillColor(txt)
    spaced(c, sub, cx, last - 0.52 * IN, BOLD, 15.5, 2.2)

    # --- white card with the teaser grid ---
    card_w, card_h = 5.6 * IN, 5.6 * IN
    card_x, card_y = cx - card_w / 2, oy + 1.45 * IN
    c.saveState()
    c.setFillColor(Color(0, 0, 0, alpha=0.22))
    c.roundRect(card_x + 6, card_y - 8, card_w, card_h, 22, stroke=0, fill=1)   # soft shadow
    c.restoreState()
    c.setFillColor(HexColor(pal["card"]))
    c.setStrokeColor(acc)
    c.setLineWidth(5)
    c.roundRect(card_x, card_y, card_w, card_h, 22, stroke=1, fill=1)

    cell = 0.57 * IN
    gx = cx - 9 * cell / 2
    gy_top = card_y + card_h - 0.28 * IN
    words = [("RELAX", 1, 2, (0, 1)), ("SMILE", 3, 7, (1, 0)), ("SUNNY", 4, 0, (1, 1)), ("JOY", 8, 2, (0, 1))]
    grid = sample_grid(f"front-{cfg['seed']}", words)
    marks = {"RELAX": coral, "SMILE": mint, "SUNNY": sky, "JOY": acc}
    for w, r, col, (dr, dc) in words:
        px = gx + (col + 0.5) * cell
        py = gy_top - (r + 0.5) * cell
        length = (len(w) - 1) * cell * math.hypot(dr, dc)
        ang = math.degrees(math.atan2(-dr, dc))
        c.saveState()
        c.translate(px, py)
        c.rotate(ang)
        c.setFillColor(marks[w])
        alpha(c, 0.72)
        c.roundRect(-cell * 0.46, -cell * 0.44, length + cell * 0.92, cell * 0.88, cell * 0.44, stroke=0, fill=1)
        c.restoreState()
    c.setFillColor(ink)
    c.setFont(BOLD, 29)
    for r in range(9):
        for col in range(9):
            c.drawCentredString(gx + (col + 0.5) * cell, gy_top - (r + 0.5) * cell - 11, grid[r][col])

    # --- gold badge overlapping the card corner ---
    bx, by, br = ox + 7.3 * IN, oy + 9.72 * IN, 0.74 * IN
    c.saveState()
    c.translate(bx, by)
    c.rotate(-10)
    c.setFillColor(Color(0, 0, 0, alpha=0.25))
    c.circle(4, -6, br, stroke=0, fill=1)
    c.setFillColor(acc)
    c.setStrokeColor(white)
    c.setLineWidth(4)
    c.circle(0, 0, br, stroke=1, fill=1)
    c.setFillColor(ink)
    c.setFont(BOLD, 44)
    c.drawCentredString(0, -4, str(cfg["puzzle_count"]))
    spaced(c, "PUZZLES", 0, -27, BOLD, 12.5, 1.3)
    c.restoreState()

    # --- bottom ribbon ---
    rw, rh = 6.6 * IN, 0.52 * IN
    rx, ry = cx - rw / 2, oy + 0.36 * IN
    c.setFillColor(acc)
    c.roundRect(rx, ry, rw, rh, 12, stroke=0, fill=1)
    c.setFillColor(ink)
    spaced(c, "BIG CLEAR LETTERS  •  SOLUTIONS INCLUDED", cx, ry + 0.19 * IN, BOLD, 14.5, 1.6)
    if cfg.get("volume"):
        c.setFillColor(txt)
        spaced(c, cfg["volume"].upper(), cx, oy + 1.08 * IN, BOLD, 15, 4)



def flower(c, x, y, r, petal, center, n=6):
    c.saveState()
    c.setFillColor(petal)
    for k in range(n):
        a = math.radians(k * 360 / n)
        c.circle(x + math.cos(a) * r * 0.62, y + math.sin(a) * r * 0.62, r * 0.42, stroke=0, fill=1)
    c.setFillColor(center)
    c.circle(x, y, r * 0.36, stroke=0, fill=1)
    c.restoreState()


def leaf(c, x, y, length, angle, color):
    c.saveState()
    c.translate(x, y)
    c.rotate(angle)
    c.setFillColor(color)
    p = c.beginPath()
    p.moveTo(0, 0)
    p.curveTo(length * 0.3, length * 0.32, length * 0.75, length * 0.28, length, 0)
    p.curveTo(length * 0.75, -length * 0.28, length * 0.3, -length * 0.32, 0, 0)
    c.drawPath(p, stroke=0, fill=1)
    c.restoreState()


def side_garden(c, x, oy, direction, pal):
    """A stem with leaves and flowers running up the side of the front cover."""
    stem = HexColor("#86EFAC")
    petals = [HexColor(pal["coral"]), HexColor(pal["accent"]), HexColor("#F9A8D4"), HexColor("#C4B5FD")]
    c.saveState()
    c.setStrokeColor(stem)
    c.setLineWidth(5)
    c.line(x, oy + 1.2 * IN, x, oy + 6.6 * IN)
    c.restoreState()
    ys = [1.7, 2.7, 3.7, 4.7, 5.7, 6.4]
    for i, yy in enumerate(ys):
        leaf(c, x, oy + yy * IN, 0.42 * IN, 35 if direction > 0 else 145, stem)
        flower(c, x + direction * 0.28 * IN, oy + (yy + 0.35) * IN, 0.26 * IN, petals[i % 4], HexColor("#FFF7ED"))


def _ell(c, cx, cy, rx, ry, rot=0, fill=None):
    c.saveState()
    c.translate(cx, cy)
    c.rotate(rot)
    c.setFillColor(fill)
    c.ellipse(-rx, -ry, rx, ry, stroke=0, fill=1)
    c.restoreState()


def _poly(c, pts, fill):
    c.saveState()
    c.setFillColor(fill)
    p = c.beginPath()
    p.moveTo(*pts[0])
    for q in pts[1:]:
        p.lineTo(*q)
    p.close()
    c.drawPath(p, stroke=0, fill=1)
    c.restoreState()


def bird(c, x, y, s, kind="cardinal", flip=False):
    """Original stylised songbird perched with feet at (x, y). s = body length in points."""
    cols = {
        "cardinal": dict(body="#D62839", belly="#E8505B", wing="#A4161A", head="#D62839", beak="#F59E0B", mask="#1F1F1F", crest=True),
        "bluebird": dict(body="#2F80ED", belly="#F2A65A", wing="#1D5FBF", head="#2F80ED", beak="#2B2B2B", mask=None, crest=False),
        "goldfinch": dict(body="#FFD60A", belly="#FFE66D", wing="#2B2B2B", head="#FFD60A", beak="#F59E0B", mask="#1F1F1F", crest=False),
    }[kind]
    c.saveState()
    c.translate(x, y)
    if flip:
        c.scale(-1, 1)
    # legs
    c.setStrokeColor(HexColor("#5B4636"))
    c.setLineWidth(s * 0.035)
    for dx in (-0.06, 0.1):
        c.line(dx * s, 0.1 * s, dx * s, 0)
    # tail
    _poly(c, [(-0.30 * s, 0.34 * s), (-0.98 * s, 0.12 * s), (-0.92 * s, 0.30 * s), (-0.28 * s, 0.50 * s)], HexColor(cols["wing"]))
    # body, belly
    _ell(c, 0, 0.42 * s, 0.50 * s, 0.31 * s, 8, HexColor(cols["body"]))
    _ell(c, 0.10 * s, 0.33 * s, 0.34 * s, 0.20 * s, 10, HexColor(cols["belly"]))
    # head
    hx, hy = 0.40 * s, 0.72 * s
    _ell(c, hx, hy, 0.25 * s, 0.24 * s, 0, HexColor(cols["head"]))
    if cols["crest"]:
        _poly(c, [(hx - 0.18 * s, hy + 0.10 * s), (hx - 0.12 * s, hy + 0.46 * s), (hx + 0.10 * s, hy + 0.20 * s)], HexColor(cols["head"]))
    if cols["mask"]:
        if kind == "goldfinch":
            _ell(c, hx - 0.05 * s, hy + 0.17 * s, 0.17 * s, 0.07 * s, 0, HexColor(cols["mask"]))
        else:
            _ell(c, hx + 0.12 * s, hy - 0.04 * s, 0.11 * s, 0.10 * s, 0, HexColor(cols["mask"]))
    # beak
    big = 0.20 if kind == "cardinal" else 0.15
    _poly(c, [(hx + 0.20 * s, hy + 0.06 * s), (hx + 0.20 * s + big * s, hy - 0.02 * s), (hx + 0.20 * s, hy - 0.09 * s)], HexColor(cols["beak"]))
    # eye
    _ell(c, hx + 0.08 * s, hy + 0.06 * s, 0.050 * s, 0.050 * s, 0, white)
    _ell(c, hx + 0.095 * s, hy + 0.06 * s, 0.026 * s, 0.026 * s, 0, HexColor("#111111"))
    # wing
    _ell(c, -0.04 * s, 0.45 * s, 0.34 * s, 0.17 * s, -22, HexColor(cols["wing"]))
    _ell(c, -0.02 * s, 0.50 * s, 0.22 * s, 0.06 * s, -22, HexColor("#FFFFFF") if kind in ("goldfinch", "bluebird") else HexColor("#C1121F"))
    c.restoreState()


def sunburst(c, cx, cy, W, H, n=22):
    c.saveState()
    c.setFillColor(white)
    alpha(c, 0.07)
    R = max(W, H) * 1.2
    for i in range(n):
        a0 = math.radians(i * 360 / n)
        a1 = a0 + math.radians(360 / n / 2)
        p = c.beginPath()
        p.moveTo(cx, cy)
        p.lineTo(cx + R * math.cos(a0), cy + R * math.sin(a0))
        p.lineTo(cx + R * math.cos(a1), cy + R * math.sin(a1))
        p.close()
        c.drawPath(p, stroke=0, fill=1)
    c.restoreState()


def branch(c, x, y, length, ang, leaves_col, bark="#6B4423"):
    """A leafy twig starting at (x,y) pointing at angle ang (degrees)."""
    c.saveState()
    c.translate(x, y)
    c.rotate(ang)
    c.setStrokeColor(HexColor(bark))
    c.setLineWidth(6)
    c.setLineCap(1)
    c.line(0, 0, length, 0)
    for i in range(1, 7):
        t = length * i / 7
        for sgn in (1, -1):
            c.saveState()
            c.translate(t, 0)
            c.rotate(sgn * 55)
            c.setFillColor(leaves_col)
            c.ellipse(0, -0.09 * IN, 0.55 * IN, 0.09 * IN, stroke=0, fill=1)
            c.restoreState()
    c.restoreState()


def flyer(c, x, y, s, col):
    c.saveState()
    c.setStrokeColor(col)
    c.setLineWidth(3)
    c.setLineCap(1)
    p = c.beginPath()
    p.moveTo(x - s, y + s * 0.35)
    p.curveTo(x - s * 0.5, y + s * 0.5, x - s * 0.2, y + s * 0.3, x, y)
    p.curveTo(x + s * 0.2, y + s * 0.3, x + s * 0.5, y + s * 0.5, x + s, y + s * 0.35)
    c.drawPath(p, stroke=1, fill=0)
    c.restoreState()


def draw_front_birds(c, x0, pal, cfg, pages):
    cv = cfg["cover"]
    ink, acc, coral, mint, sky = (HexColor(pal[k]) for k in ("ink", "accent", "coral", "mint", "sky"))
    txt = HexColor(pal["text"])
    ox, oy = x0, BLEED * IN
    cx = ox + TRIM_W * IN / 2
    # sunrise rays and sun glow behind the title
    sunburst(c, cx, oy + 8.3 * IN, TRIM_W * IN, TRIM_H * IN)
    c.saveState()
    c.setFillColor(acc)
    alpha(c, 0.18)
    c.circle(cx, oy + 8.3 * IN, 3.2 * IN, stroke=0, fill=1)
    alpha(c, 0.14)
    c.circle(cx, oy + 8.3 * IN, 2.3 * IN, stroke=0, fill=1)
    c.restoreState()
    # leafy twigs rising along the lower sides, and a few distant birds in flight
    leafc = HexColor("#7BD389")
    branch(c, ox + 0.45 * IN, oy + 1.4 * IN, 2.0 * IN, 78, leafc)
    branch(c, ox + 8.05 * IN, oy + 1.4 * IN, 2.0 * IN, 102, leafc)
    for fx, fy, fs in ((1.0, 7.9, 0.30), (7.4, 8.0, 0.26), (7.0, 7.45, 0.18)):
        flyer(c, ox + fx * IN, oy + fy * IN, fs * IN, white)
    # tag pill
    tag = cv["tag"]
    tw = sum(stringWidth(ch, BOLD, 14) for ch in tag) + 2.4 * (len(tag) - 1) + 40
    c.setFillColor(coral)
    c.roundRect(cx - tw / 2, oy + 10.2 * IN, tw, 0.4 * IN, 14, stroke=0, fill=1)
    c.setFillColor(white)
    spaced(c, tag, cx, oy + 10.2 * IN + 0.14 * IN, BOLD, 14, 2.4)
    # title
    c.setFillColor(txt)
    size = fit_font(cv["headline"], BOLD, 7.0 * IN, 96)
    c.setFont(BOLD, size)
    y = oy + 9.3 * IN
    c.drawCentredString(cx, y, cv["headline"])
    size2 = fit_font(cv["main"], BOLD, 6.9 * IN, 80)
    c.setFillColor(acc)
    c.setFont(BOLD, size2)
    y2 = y - 0.98 * IN
    c.drawCentredString(cx, y2, cv["main"])
    c.setFillColor(txt)
    spaced(c, cv["sub"], cx, y2 - 0.56 * IN, BOLD, 26, 9)
    # card with teaser grid (a little lower so the birds can perch on its top edge)
    card_w = card_h = 5.2 * IN
    card_x, card_y = cx - card_w / 2, oy + 1.25 * IN
    c.saveState()
    c.setFillColor(Color(0, 0, 0, alpha=0.22))
    c.roundRect(card_x + 6, card_y - 8, card_w, card_h, 22, stroke=0, fill=1)
    c.restoreState()
    c.setFillColor(HexColor(pal["card"]))
    c.setStrokeColor(acc)
    c.setLineWidth(5)
    c.roundRect(card_x, card_y, card_w, card_h, 22, stroke=1, fill=1)
    cell = 0.53 * IN
    gx = cx - 9 * cell / 2
    gy_top = card_y + card_h - 0.2 * IN
    words = [(w, r, col, tuple(d)) for w, r, col, d in cv["teaser"]]
    grid = sample_grid(f"front-{cfg['seed']}", words)
    colors = [coral, mint, sky, acc]
    for i, (w, r, col, (dr, dc)) in enumerate(words):
        px, py = gx + (col + 0.5) * cell, gy_top - (r + 0.5) * cell
        length = (len(w) - 1) * cell * math.hypot(dr, dc)
        c.saveState()
        c.translate(px, py)
        c.rotate(math.degrees(math.atan2(-dr, dc)))
        c.setFillColor(colors[i % 4])
        alpha(c, 0.75)
        c.roundRect(-cell * 0.46, -cell * 0.44, length + cell * 0.92, cell * 0.88, cell * 0.44, stroke=0, fill=1)
        c.restoreState()
    c.setFillColor(ink)
    c.setFont(BOLD, 27)
    for r in range(9):
        for col in range(9):
            c.drawCentredString(gx + (col + 0.5) * cell, gy_top - (r + 0.5) * cell - 9.5, grid[r][col])
    # birds perched on the card
    top = card_y + card_h + 2.5
    bird(c, card_x + 1.4 * IN, top, 1.0 * IN, "cardinal")
    bird(c, card_x + card_w - 2.4 * IN, top, 0.85 * IN, "goldfinch", flip=True)
    bird(c, card_x + card_w - 0.9 * IN, top, 0.98 * IN, "bluebird", flip=True)
    # badge
    bx, by, br = ox + 0.98 * IN, card_y + 3.5 * IN, 0.68 * IN
    c.saveState()
    c.translate(bx, by)
    c.rotate(-10)
    c.setFillColor(Color(0, 0, 0, alpha=0.25))
    c.circle(4, -6, br, stroke=0, fill=1)
    c.setFillColor(coral)
    c.setStrokeColor(white)
    c.setLineWidth(4)
    c.circle(0, 0, br, stroke=1, fill=1)
    c.setFillColor(white)
    c.setFont(BOLD, 38)
    c.drawCentredString(0, -2, str(cfg["puzzle_count"]))
    spaced(c, "PUZZLES", 0, -24, BOLD, 11.5, 1.2)
    c.restoreState()
    # audience line + ribbon + volume
    c.setFillColor(txt)
    spaced(c, cv["audience"], cx, oy + 0.9 * IN, BOLD, 13.5, 1.8)
    rw, rh = 6.4 * IN, 0.5 * IN
    rx, ry = cx - rw / 2, oy + 0.3 * IN
    c.setFillColor(acc)
    c.roundRect(rx, ry, rw, rh, 12, stroke=0, fill=1)
    c.setFillColor(ink)
    spaced(c, cv["ribbon"], cx, ry + 0.18 * IN, BOLD, 13.5, 1.5)


def draw_front_garden(c, x0, pal, cfg, pages):
    cv = cfg["cover"]
    ink, acc, coral, mint, sky = (HexColor(pal[k]) for k in ("ink", "accent", "coral", "mint", "sky"))
    txt = HexColor(pal["text"])
    ox, oy = x0, BLEED * IN
    cx = ox + TRIM_W * IN / 2
    # decorative stems on both sides (kept clear of the 0.25 in safe zone)
    side_garden(c, ox + 0.55 * IN, oy, 1, pal)
    side_garden(c, ox + 7.95 * IN, oy, -1, pal)
    # tag pill
    tag = cv["tag"]
    tw = sum(stringWidth(ch, BOLD, 14) for ch in tag) + 2.4 * (len(tag) - 1) + 40
    c.setFillColor(coral)
    c.roundRect(cx - tw / 2, oy + 10.2 * IN, tw, 0.4 * IN, 14, stroke=0, fill=1)
    c.setFillColor(white)
    spaced(c, tag, cx, oy + 10.2 * IN + 0.14 * IN, BOLD, 14, 2.4)
    # LARGE PRINT is the most prominent element
    c.setFillColor(txt)
    size = fit_font(cv["headline"], BOLD, 7.0 * IN, 96)
    c.setFont(BOLD, size)
    y = oy + 9.3 * IN
    c.drawCentredString(cx, y, cv["headline"])
    size2 = fit_font(cv["main"], BOLD, 6.9 * IN, 80)
    c.setFillColor(acc)
    c.setFont(BOLD, size2)
    y2 = y - 0.98 * IN
    c.drawCentredString(cx, y2, cv["main"])
    c.setFillColor(txt)
    spaced(c, cv["sub"], cx, y2 - 0.56 * IN, BOLD, 26, 9)
    spaced(c, cv["audience"], cx, y2 - 0.98 * IN, BOLD, 13.5, 1.8)
    # card with teaser grid
    card_w = card_h = 5.45 * IN
    card_x, card_y = cx - card_w / 2, oy + 1.5 * IN
    c.saveState()
    c.setFillColor(Color(0, 0, 0, alpha=0.22))
    c.roundRect(card_x + 6, card_y - 8, card_w, card_h, 22, stroke=0, fill=1)
    c.restoreState()
    c.setFillColor(HexColor(pal["card"]))
    c.setStrokeColor(acc)
    c.setLineWidth(5)
    c.roundRect(card_x, card_y, card_w, card_h, 22, stroke=1, fill=1)
    cell = 0.555 * IN
    gx = cx - 9 * cell / 2
    gy_top = card_y + card_h - 0.22 * IN
    words = [(w, r, col, tuple(d)) for w, r, col, d in cv["teaser"]]
    grid = sample_grid(f"front-{cfg['seed']}", words)
    colors = [coral, mint, sky, acc]
    for i, (w, r, col, (dr, dc)) in enumerate(words):
        px, py = gx + (col + 0.5) * cell, gy_top - (r + 0.5) * cell
        length = (len(w) - 1) * cell * math.hypot(dr, dc)
        c.saveState()
        c.translate(px, py)
        c.rotate(math.degrees(math.atan2(-dr, dc)))
        c.setFillColor(colors[i % 4])
        alpha(c, 0.75)
        c.roundRect(-cell * 0.46, -cell * 0.44, length + cell * 0.92, cell * 0.88, cell * 0.44, stroke=0, fill=1)
        c.restoreState()
    c.setFillColor(ink)
    c.setFont(BOLD, 28)
    for r in range(9):
        for col in range(9):
            c.drawCentredString(gx + (col + 0.5) * cell, gy_top - (r + 0.5) * cell - 10, grid[r][col])
    # badge on the card corner
    bx, by, br = card_x + card_w + 0.12 * IN, card_y + card_h - 0.7 * IN, 0.72 * IN
    c.saveState()
    c.translate(bx, by)
    c.rotate(-10)
    c.setFillColor(Color(0, 0, 0, alpha=0.25))
    c.circle(4, -6, br, stroke=0, fill=1)
    c.setFillColor(coral)
    c.setStrokeColor(white)
    c.setLineWidth(4)
    c.circle(0, 0, br, stroke=1, fill=1)
    c.setFillColor(white)
    c.setFont(BOLD, 38)
    c.drawCentredString(0, -2, str(cfg["puzzle_count"]))
    spaced(c, "PUZZLES", 0, -24, BOLD, 11.5, 1.2)
    c.restoreState()
    # ribbon + volume
    rw, rh = 6.4 * IN, 0.5 * IN
    rx, ry = cx - rw / 2, oy + 0.4 * IN
    c.setFillColor(acc)
    c.roundRect(rx, ry, rw, rh, 12, stroke=0, fill=1)
    c.setFillColor(ink)
    spaced(c, cv["ribbon"], cx, ry + 0.18 * IN, BOLD, 13.5, 1.5)
    if cfg.get("volume"):
        c.setFillColor(txt)
        spaced(c, cfg["volume"].upper(), cx, oy + 1.13 * IN, BOLD, 14, 4)


def check(c, x, y, size, color):
    c.saveState()
    c.setFillColor(color)
    c.circle(x, y, size, stroke=0, fill=1)
    c.setStrokeColor(HexColor("#12324A"))
    c.setLineWidth(size * 0.28)
    c.setLineCap(1)
    c.setLineJoin(1)
    p = c.beginPath()
    p.moveTo(x - size * 0.42, y - size * 0.02)
    p.lineTo(x - size * 0.1, y - size * 0.34)
    p.lineTo(x + size * 0.46, y + size * 0.34)
    c.drawPath(p, stroke=1, fill=0)
    c.restoreState()


def draw_back(c, x0, H, pal, cfg):
    acc = HexColor(pal["accent"])
    txt = HexColor(pal["text"])
    ox, oy = x0, BLEED * IN
    left = ox + 0.8 * IN
    width = TRIM_W * IN - 1.6 * IN
    top = oy + TRIM_H * IN
    c.setFillColor(acc)
    c.setFont(BOLD, 38)
    bt = cfg.get("cover", {}).get("back_title", ["Big print.", "Big fun."])
    c.drawString(left, top - 1.25 * IN, bt[0])
    c.drawString(left, top - 1.25 * IN - 46, bt[1])
    c.setStrokeColor(acc)
    c.setLineWidth(4)
    c.line(left, top - 1.25 * IN - 66, left + 1.2 * IN, top - 1.25 * IN - 66)
    c.setFillColor(txt)
    c.setFont(REG, 16.5)
    y = top - 1.25 * IN - 100
    for line in simpleSplit(cfg["back_cover_text"], REG, 16.5, width):
        c.drawString(left, y, line)
        y -= 24
    # feature panel
    py = y - 0.25 * IN
    feats = cfg.get("cover", {}).get("features") or [
        f"{cfg['puzzle_count']} themed puzzles", "Large, easy-to-read letters",
        "12 words in every puzzle", "One puzzle per page", "Full solutions included"]
    ph = (len(feats) * 0.5 + 0.35) * IN
    c.saveState()
    c.setFillColor(white)
    alpha(c, 0.12)
    c.roundRect(left, py - ph, width, ph, 16, stroke=0, fill=1)
    c.restoreState()
    fy = py - 0.5 * IN
    for f in feats:
        check(c, left + 0.38 * IN, fy + 5, 10, acc)
        c.setFillColor(txt)
        c.setFont(BOLD, 17)
        c.drawString(left + 0.7 * IN, fy, f)
        fy -= 0.5 * IN
    c.setFillColor(txt)
    alpha(c, 0.8)
    c.setFont(OBL, 14)
    c.drawString(left, py - ph - 0.5 * IN, cfg.get("cover", {}).get("gift_line", "A friendly gift for anyone who enjoys a calm, screen-free break."))
    alpha(c, 1)
    tile = 0.62 * IN
    cols = [HexColor(pal["coral"]), HexColor(pal["mint"]), HexColor(pal["sky"]), acc, HexColor(pal["coral"]), HexColor(pal["mint"])]
    for i, ch in enumerate(cfg.get("cover", {}).get("tiles", "ENJOY")):
        tx = left + i * (tile + 0.1 * IN)
        c.setFillColor(cols[i])
        c.roundRect(tx, oy + 0.62 * IN, tile, tile, 10, stroke=0, fill=1)
        c.setFillColor(HexColor(pal["ink"]))
        c.setFont(BOLD, 34)
        c.drawCentredString(tx + tile / 2, oy + 0.62 * IN + 0.16 * IN, ch)
    # barcode keep-out (white 2.0 x 1.2 in box; KDP overlays its own barcode)
    bar_w, bar_h = 2.0 * IN, 1.2 * IN
    c.setFillColor(white)
    c.rect(ox + TRIM_W * IN - 0.25 * IN - bar_w, (BLEED + 0.25) * IN, bar_w, bar_h, stroke=0, fill=1)


def build(cfg, pages, out_path):
    d = cover_dimensions(pages)
    W, H = d["width_in"] * IN, d["height_in"] * IN
    spine = d["spine_in"] * IN
    pal = dict(DEFAULT_PALETTE)
    pal.update(cfg.get("cover_palette", {}))
    c = canvas.Canvas(out_path, pagesize=(W, H), initialFontName=REG)
    c.setTitle(cfg["title"] + " (cover)")
    gradient_bg(c, W, H, HexColor(pal["bg_top"]), HexColor(pal["bg_bottom"]))
    circles(c, W, H, pal, random.Random(cfg["seed"]))
    back_x0 = BLEED * IN
    front_x0 = (BLEED + TRIM_W) * IN + spine
    draw_back(c, back_x0, H, pal, cfg)
    draw_front(c, front_x0, pal, cfg, pages)
    if pages >= SPINE_TEXT_MIN_PAGES:
        c.saveState()
        c.translate((BLEED + TRIM_W) * IN + spine / 2, H / 2)
        c.rotate(-90)
        c.setFillColor(HexColor(pal["text"]))
        c.setFont(BOLD, min(18, spine * 0.55))
        c.drawCentredString(0, -spine * 0.2, cfg["title"].upper())
        c.restoreState()
    c.save()
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--pages", type=int, required=True, help="interior page count")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    with open(a.config, encoding="utf-8") as f:
        cfg = json.load(f)
    d = build(cfg, a.pages, a.out)
    print(json.dumps({"cover_pdf": a.out, **{k: round(v, 4) for k, v in d.items()}}))


if __name__ == "__main__":
    main()
