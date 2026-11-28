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
from reportlab.pdfbase.pdfmetrics import stringWidth

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wordsearch import make_puzzle  # noqa: E402
from fonts import REG, BOLD, OBL  # noqa: E402

W, H = letter                      # 612 x 792 pt = 8.5 x 11 in
OUTER, INNER, TOP, BOTTOM = 43.2, 54.0, 43.2, 46.8   # 0.6 / 0.75 / 0.6 / 0.65 in
CELL = 36.0                        # 0.5 in cells -> 22pt letters
FONT, FONT_B = REG, BOLD


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


def c_width(text, font, size):
    from reportlab.pdfbase.pdfmetrics import stringWidth
    return stringWidth(text, font, size)


def balanced_lines(text, font, start, min_size, max_width, max_lines):
    """Split text on word boundaries into <= max_lines lines whose widest line is as narrow as possible,
    then return the largest size (start..min_size) at which every line fits max_width."""
    import itertools
    words = text.split()
    best = None
    for k in range(1, min(max_lines, len(words)) + 1):
        for cuts in itertools.combinations(range(1, len(words)), k - 1):
            idx = (0,) + cuts + (len(words),)
            lines = [" ".join(words[idx[i]:idx[i + 1]]) for i in range(k)]
            widest = max(c_width(l, font, 100) for l in lines)
            if best is None or widest < best[0] - 1e-6 or (abs(widest - best[0]) < 1e-6 and len(lines) < len(best[1])):
                best = (widest, lines)
    widest, lines = best
    size = min(start, max_width / widest * 100)
    return max(min_size, size), lines


def fit_lines(text, font, start, min_size, max_width, max_lines):
    return balanced_lines(text, font, start, min_size, max_width, max_lines)


def page_title(c, page_no, cfg):
    cx = center_x(page_no)
    x0, x1 = live_area(page_no)
    max_w = (x1 - x0) - 40
    # Title: wrapped on word boundaries, never wider than the live area
    size, lines = fit_lines(cfg["title"], FONT_B, 56, 30, max_w, 3)
    lead = size * 1.18
    y = H * 0.70
    c.setStrokeGray(0)
    c.setLineWidth(2.5)
    c.line(cx - max_w / 2, y + size * 0.95, cx + max_w / 2, y + size * 0.95)
    c.setFillGray(0)
    c.setFont(FONT_B, size)
    for line in lines:
        c.drawCentredString(cx, y, line)
        y -= lead
    c.setLineWidth(2.5)
    c.line(cx - max_w / 2, y + lead * 0.55, cx + max_w / 2, y + lead * 0.55)
    # Subtitle
    y -= lead * 0.55 + 14
    s_size, s_lines = fit_lines(cfg["subtitle"], FONT, 24, 16, max_w, 2)
    c.setFont(FONT, s_size)
    for line in s_lines:
        c.drawCentredString(cx, y, line)
        y -= s_size * 1.3
    if cfg.get("volume"):
        c.setFont(FONT_B, 22)
        c.drawCentredString(cx, y - 18, cfg["volume"])
    # Author at the foot of the page
    c.setFont(FONT, 18)
    c.drawCentredString(cx, 110, cfg.get("author", ""))


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
    fs = 18.0                      # shrink only when a word would leave < 4pt before the next column
    while fs > 14 and max(stringWidth(w, FONT_B, fs) for w in words) > col_w - 4:
        fs -= 0.5
    c.setFont(FONT_B, fs)
    for i, w in enumerate(sorted(words)):
        col, row = divmod(i, per_col)
        c.drawString(gx + col * col_w + 8, y0 - row * lead, w)
    if fact:
        text = f"{fact_label}: {fact}"
        lines = simpleSplit(text, OBL, 12.5, size * CELL - 10)
        yy = y0 - per_col * lead + 6
        c.setFont(OBL, 12.5)
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


# Back-matter pages. A config may set "bonus_pages" to a list of page specs, e.g.
#   {"kind": "log", "title": "My Bird Watching Log", "subtitle": "...", "columns": [["Date", 0.18], ...]}
#   {"kind": "checklist", "title": "Birds I Have Spotted", "items": [...], "extra_label": "More birds I have seen:"}
#   {"kind": "lines", "title": "Bird Notes"}     {"kind": "plan", "title": "...", "subtitle": "..."}
# "bonus_pages": true keeps the original gardening set below.
GARDEN_BONUS = [
    {"kind": "plan", "title": "My Garden Plan", "subtitle": "Sketch your garden: each square is one step."},
    {"kind": "log", "title": "Plant and Seed Log",
     "columns": [["Plant", 0.38], ["Planted on", 0.2], ["Where", 0.2], ["Notes", 0.22]]},
    {"kind": "lines", "title": "Garden Notes"},
    {"kind": "lines", "title": "Garden Notes"},
]


def bonus_specs(cfg):
    b = cfg.get("bonus_pages")
    if b is True:
        return GARDEN_BONUS
    return list(b or [])


def page_bonus(c, page_no, spec):
    kind, title = spec["kind"], spec["title"]
    cx = center_x(page_no)
    x0, x1 = live_area(page_no)
    c.setFillGray(0)
    c.setFont(FONT_B, 28)
    c.drawCentredString(cx, H - TOP - 28, title)
    top = H - TOP - 70
    if spec.get("subtitle"):
        c.setFont(FONT, 14)
        c.drawCentredString(cx, top - 6, spec["subtitle"])
        top -= 30
    c.setStrokeGray(0.35)
    c.setLineWidth(0.8)
    if kind == "lines":
        y = top
        while y > BOTTOM + 20:
            c.line(x0 + 10, y, x1 - 10, y)
            y -= 34
    elif kind == "log":
        cols = spec.get("columns") or [["Plant", 0.38], ["Planted on", 0.2], ["Where", 0.2], ["Notes", 0.22]]
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
    elif kind == "checklist":
        items = spec.get("items", [])
        half = (len(items) + 1) // 2
        colw = (x1 - x0 - 20) / 2
        y0 = top - 20
        rh = 28
        c.setFont(FONT, 15)
        c.setLineWidth(1.2)
        c.setStrokeGray(0)
        for k, item in enumerate(items):
            col, row = divmod(k, half)
            x = x0 + 10 + col * colw
            y = y0 - row * rh
            c.rect(x, y - 2, 15, 15, stroke=1, fill=0)
            c.drawString(x + 24, y + 1, item)
        y = y0 - half * rh - 14
        if spec.get("extra_label"):
            c.setFont(FONT_B, 15)
            c.drawString(x0 + 10, y, spec["extra_label"])
            c.setStrokeGray(0.35)
            c.setLineWidth(0.8)
            y -= 34
            while y > BOTTOM + 20:
                c.line(x0 + 10, y, x1 - 10, y)
                y -= 34
    elif kind == "plan":
        step = 24
        gx0 = x0 + 10
        gy_top = top + 6 if spec.get("subtitle") else top - 24
        cols_n = int((x1 - x0 - 20) // step)
        rows_n = int((gy_top - BOTTOM - 20) // step)
        c.setStrokeGray(0.75)
        for r in range(rows_n + 1):
            c.line(gx0, gy_top - r * step, gx0 + cols_n * step, gy_top - r * step)
        for k in range(cols_n + 1):
            c.line(gx0 + k * step, gy_top, gx0 + k * step, gy_top - rows_n * step)
    else:
        raise ValueError(f"unknown bonus page kind: {kind}")
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

    c = canvas.Canvas(out_path, pagesize=letter, initialFontName=REG)
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
    for spec in bonus_specs(cfg):
        page_bonus(c, page_no, spec)
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
