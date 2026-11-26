#!/usr/bin/env python3
"""Generate the interior PDF (8.5x11 in, B&W, large print) for a Word Search book.
T0 tool: pure Python + reportlab, no network, no LLM."""
import argparse
import json
import os
import sys

from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import simpleSplit
from reportlab.pdfgen import canvas

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wordsearch import make_puzzle  # noqa: E402

W, H = letter                      # 612 x 792 pt = 8.5 x 11 in
OUTER, INNER, TOP, BOTTOM = 43.2, 54.0, 43.2, 46.8   # 0.6 / 0.75 / 0.6 / 0.65 in
CELL = 36.0                        # 0.5 in cells -> 22pt letters
FONT, FONT_B = "Helvetica", "Helvetica-Bold"


def live_area(page_no):
    """x range of the live area. Odd pages are right-hand pages (gutter on the left)."""
    if page_no % 2 == 1:
        return INNER, W - OUTER
    return OUTER, W - INNER


def center_x(page_no):
    x0, x1 = live_area(page_no)
    return (x0 + x1) / 2


def load_themes(path):
    """Return {name: {"words": [...], "fact": str}}. Accepts the old {name: [words]} form too."""
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    out = {}
    for name, v in raw.items():
        out[name] = v if isinstance(v, dict) else {"words": v, "fact": ""}
    return out


def draw_grid(c, grid, x, y_top, cell, font_size, placements=None, gray=0.72, border=1.5):
    size = len(grid)
    hit = set()
    if placements:
        for cells in placements.values():
            hit.update(cells)
    for r in range(size):
        for col in range(size):
            ch = grid[r][col]
            cx = x + col * cell + cell / 2
            cy = y_top - r * cell - cell / 2 - font_size * 0.35
            if placements is None or (r, col) in hit:
                c.setFillGray(0)
                c.setFont(FONT_B, font_size)
            else:
                c.setFillGray(gray)
                c.setFont(FONT, font_size)
            c.drawCentredString(cx, cy, ch)
    c.setStrokeGray(0)
    c.setLineWidth(border)
    c.rect(x, y_top - size * cell, size * cell, size * cell)
    c.setFillGray(0)


def footer(c, page_no):
    c.setFont(FONT, 11)
    c.setFillGray(0)
    c.drawCentredString(center_x(page_no), 34, str(page_no))


def page_title(c, page_no, cfg):
    c.setFont(FONT_B, 40)
    c.drawCentredString(center_x(page_no), H * 0.62, cfg["title"])
    c.setFont(FONT, 22)
    y = H * 0.62 - 44
    for line in simpleSplit(cfg["subtitle"], FONT, 22, W - INNER - OUTER - 40):
        c.drawCentredString(center_x(page_no), y, line)
        y -= 28
    if cfg.get("volume"):
        c.setFont(FONT_B, 20)
        c.drawCentredString(center_x(page_no), y - 14, cfg["volume"])


def page_copyright(c, page_no, cfg):
    c.setFont(FONT, 12)
    lines = [
        f"Copyright © {cfg['year']} {cfg['author']}. All rights reserved.",
        "No part of this book may be reproduced without written permission",
        "from the publisher, except for brief quotations in reviews.",
        "",
        "This is a work of puzzles. All word lists are original compilations.",
    ]
    y = 230
    for ln in lines:
        c.drawCentredString(center_x(page_no), y, ln)
        y -= 18


def page_howto(c, page_no, cfg):
    cx = center_x(page_no)
    c.setFont(FONT_B, 30)
    c.drawCentredString(cx, H - 120, "How to Play")
    c.setFont(FONT, 18)
    text = [
        "1. Find every word in the list below the puzzle.",
        "2. Words run left to right, top to bottom,",
        "    or diagonally down to the right.",
        "3. Circle each word you find and cross it off the list.",
        "4. Each word appears exactly once in its puzzle.",
        "5. Stuck? Answers are in the Solutions section at the back.",
        "",
        "Take your time and enjoy!",
    ]
    y = H - 190
    for ln in text:
        c.drawString(cx - 230, y, ln)
        y -= 30


def page_puzzle(c, page_no, number, theme, puzzle, words, fact="", fact_label="Garden Tip"):
    cx = center_x(page_no)
    c.setFont(FONT_B, 26)
    c.drawCentredString(cx, H - TOP - 26, f"Puzzle {number}")
    c.setFont(FONT, 18)
    c.drawCentredString(cx, H - TOP - 52, theme)
    size = len(puzzle["grid"])
    gx = cx - size * CELL / 2
    y_top = H - TOP - 74
    draw_grid(c, puzzle["grid"], gx, y_top, CELL, 22)
    # word list: 3 columns x 4 rows, 18pt
    cols, per_col = 3, 4
    col_w = size * CELL / cols
    y0 = y_top - size * CELL - 32
    lead = 24 if fact else 26
    c.setFont(FONT_B, 18)
    for i, w in enumerate(sorted(words)):
        col, row = divmod(i, per_col)
        c.drawString(gx + col * col_w + 8, y0 - row * lead, w)
    if fact:
        text = f"{fact_label}: {fact}"
        lines = simpleSplit(text, "Helvetica-Oblique", 12.5, size * CELL - 10)
        yy = y0 - per_col * lead + 6
        c.setFont("Helvetica-Oblique", 12.5)
        for ln in lines[:2]:
            c.drawString(gx + 8, yy, ln)
            yy -= 15
    footer(c, page_no)


def page_solutions(c, page_no, items, first):
    cx = center_x(page_no)
    c.setFont(FONT_B, 26)
    c.drawCentredString(cx, H - TOP - 26, "Solutions" if first else "Solutions (continued)")
    cell = 17.0
    gsize = 13 * cell
    x0, x1 = live_area(page_no)
    gap_x = (x1 - x0 - 2 * gsize) / 3
    y_start = H - TOP - 70
    for idx, (number, theme, puzzle) in enumerate(items):
        row, col = divmod(idx, 2)
        gx = x0 + gap_x + col * (gsize + gap_x)
        gy = y_start - row * (gsize + 62)
        c.setFont(FONT_B, 12)
        c.setFillGray(0)
        c.drawString(gx, gy + 4, f"Puzzle {number}: {theme}")
        draw_grid(c, puzzle["grid"], gx, gy - 8, cell, 11, puzzle["placements"], border=1.0)
    footer(c, page_no)


def page_bonus(c, page_no, kind, title):
    cx = center_x(page_no)
    x0, x1 = live_area(page_no)
    c.setFont(FONT_B, 28)
    c.drawCentredString(cx, H - TOP - 28, title)
    c.setStrokeGray(0.35)
    c.setLineWidth(0.8)
    top = H - TOP - 70
    if kind == "lines":
        y = top
        while y > BOTTOM + 20:
            c.line(x0 + 10, y, x1 - 10, y)
            y -= 34
    elif kind == "log":
        cols = [("Plant", 0.38), ("Planted on", 0.2), ("Where", 0.2), ("Notes", 0.22)]
        wtot = x1 - x0 - 20
        c.setFont(FONT_B, 13)
        xx = x0 + 10
        for name, frac in cols:
            c.drawString(xx + 4, top - 14, name)
            xx += wtot * frac
        y = top - 24
        while y > BOTTOM + 20:
            c.line(x0 + 10, y, x1 - 10, y)
            y -= 38
        xx = x0 + 10
        for name, frac in cols:
            c.line(xx, top, xx, y + 38)
            xx += wtot * frac
        c.line(x1 - 10, top, x1 - 10, y + 38)
    elif kind == "plan":
        c.setFont(FONT, 14)
        c.drawCentredString(cx, top - 6, "Sketch your garden: each square is one step.")
        step = 24
        gx0 = x0 + 10
        gy_top = top - 24
        cols_n = int((x1 - x0 - 20) // step)
        rows_n = int((gy_top - BOTTOM - 20) // step)
        c.setStrokeGray(0.75)
        for r in range(rows_n + 1):
            c.line(gx0, gy_top - r * step, gx0 + cols_n * step, gy_top - r * step)
        for k in range(cols_n + 1):
            c.line(gx0 + k * step, gy_top, gx0 + k * step, gy_top - rows_n * step)
    footer(c, page_no)


def build(cfg, themes_path, out_path):
    themes = load_themes(themes_path)
    names = list(themes.keys())[: cfg["puzzle_count"]]
    fact_label = cfg.get("fact_label", "Garden Tip")
    size = cfg["grid_size"]
    puzzles = []
    for i, name in enumerate(names, 1):
        p = make_puzzle(themes[name]["words"], size=size, seed=f"{cfg['seed']}-{i}")
        puzzles.append((i, name, p, themes[name]["words"], themes[name]["fact"]))

    c = canvas.Canvas(out_path, pagesize=letter)
    c.setTitle(f"{cfg['title']} {cfg.get('volume', '')}".strip())
    c.setAuthor(cfg["author"])
    page_no = 1
    page_title(c, page_no, cfg); c.showPage(); page_no += 1
    page_copyright(c, page_no, cfg); c.showPage(); page_no += 1
    page_howto(c, page_no, cfg); footer(c, page_no); c.showPage(); page_no += 1
    for number, name, p, words, fact in puzzles:
        page_puzzle(c, page_no, number, name, p, words, fact, fact_label)
        c.showPage(); page_no += 1
    per_page = 4
    for k in range(0, len(puzzles), per_page):
        chunk = [(n, nm, p) for n, nm, p, _, _ in puzzles[k:k + per_page]]
        page_solutions(c, page_no, chunk, first=(k == 0))
        c.showPage(); page_no += 1
    if cfg.get("bonus_pages"):
        for kind, title in (("plan", "My Garden Plan"), ("log", "Plant and Seed Log"),
                            ("lines", "Garden Notes"), ("lines", "Garden Notes")):
            page_bonus(c, page_no, kind, title)
            c.showPage(); page_no += 1
    total = page_no - 1
    if total % 2 == 1:   # keep an even page count
        footer(c, page_no); c.showPage(); total += 1
    c.save()
    return total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--themes", default=None, help="themes JSON (default: themes_file from config, else data/themes.json)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    with open(a.config, encoding="utf-8") as f:
        cfg = json.load(f)
    base = os.path.dirname(os.path.abspath(__file__))
    themes = a.themes or os.path.join(base, "data", cfg.get("themes_file", "themes.json"))
    pages = build(cfg, themes, a.out)
    print(json.dumps({"interior_pdf": a.out, "pages": pages}))


if __name__ == "__main__":
    main()
