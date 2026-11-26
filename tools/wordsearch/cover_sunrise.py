"""'sunrise' cover layout: bright sunrise sky, illustrated birds perched on the puzzle card.
Original artwork only (drawn shapes). T0 tool: no network, no LLM.
Text comes from cfg["cover"]; colours from cfg["cover_palette"] (see data/book.birds.json)."""
import math
import random

from reportlab.lib.colors import Color, HexColor, white
from reportlab.lib.utils import simpleSplit
from reportlab.pdfbase.pdfmetrics import stringWidth

from fonts import REG, BOLD, OBL

IN = 72.0

SUNRISE_PALETTE = {
    "sky_top": "#8ECAE6", "sky_mid": "#BDE0FE", "sky_glow": "#FFC8A2", "sky_low": "#FFE8A3",
    "sun": "#FFD166", "ray": "#FFB703", "ink": "#1D3557", "coral": "#E63946", "teal": "#2A9D8F",
    "orange": "#F4A261", "leaf": "#57CC99", "leaf_dark": "#2D936C", "bark": "#7A4E2D", "card": "#FFFAF0",
}
HIGHLIGHTS = ["#FF8FAB", "#FFD166", "#A0E7E5", "#CDB4DB", "#F4A261", "#BDE0FE"]
BIRDS = {
    "cardinal": dict(body="#D62828", belly="#E85D5D", wing="#A4161A", beak="#FF9F1C", tail="#9D0208"),
    "goldfinch": dict(body="#FFD60A", belly="#FFE566", wing="#1B1B1B", beak="#F4A261", tail="#1B1B1B"),
    "bluebird": dict(body="#3A86FF", belly="#F28C28", wing="#1D4ED8", beak="#2B2D42", tail="#1D4ED8"),
}


def _lerp(a, b, t):
    return Color(a.red + (b.red - a.red) * t, a.green + (b.green - a.green) * t, a.blue + (b.blue - a.blue) * t)


def _path(c, pts_or_fn, fill, stroke=None):
    p = c.beginPath()
    pts_or_fn(p)
    c.setFillColor(fill)
    c.drawPath(p, stroke=0, fill=1)


def sky(c, W, H, pal):
    stops = [(0, pal["sky_low"]), (0.35, pal["sky_glow"]), (0.62, pal["sky_mid"]), (1, pal["sky_top"])]
    stops = [(t, HexColor(v)) for t, v in stops]
    n = 160
    for i in range(n):
        t = i / (n - 1)
        for (t0, c0), (t1, c1) in zip(stops, stops[1:]):
            if t0 <= t <= t1:
                col = _lerp(c0, c1, (t - t0) / (t1 - t0))
                break
        c.setFillColor(col)
        c.rect(0, H * i / n, W, H / n + 1, stroke=0, fill=1)


def cloud(c, x, y, s, a=0.9):
    c.saveState()
    c.setFillColor(white)
    c.setFillAlpha(a)
    for dx, dy, r in ((0, 0, 22), (24, 8, 28), (52, 0, 22), (26, -8, 20)):
        c.circle(x + dx * s, y + dy * s, r * s, stroke=0, fill=1)
    c.restoreState()


def sun(c, cx, cy, r, pal):
    c.saveState()
    for k, a in ((2.3, 0.10), (1.8, 0.16), (1.4, 0.25)):
        c.setFillColor(HexColor("#FFF3B0"))
        c.setFillAlpha(a)
        c.circle(cx, cy, r * k, stroke=0, fill=1)
    c.setFillAlpha(1)
    c.setStrokeColor(HexColor(pal["ray"]))
    c.setLineWidth(6)
    c.setLineCap(1)
    for i in range(16):
        a = 2 * math.pi * i / 16
        c.line(cx + math.cos(a) * r * 1.15, cy + math.sin(a) * r * 1.15,
               cx + math.cos(a) * r * 1.38, cy + math.sin(a) * r * 1.38)
    c.setFillColor(HexColor(pal["sun"]))
    c.circle(cx, cy, r, stroke=0, fill=1)
    c.restoreState()


def flyer(c, x, y, s, col):
    c.saveState()
    c.setStrokeColor(col)
    c.setLineWidth(2.4 * s)
    c.setLineCap(1)
    p = c.beginPath()
    p.moveTo(x - 14 * s, y + 5 * s)
    p.curveTo(x - 9 * s, y + 9 * s, x - 3 * s, y + 6 * s, x, y)
    p.curveTo(x + 3 * s, y + 6 * s, x + 9 * s, y + 9 * s, x + 14 * s, y + 5 * s)
    c.drawPath(p, stroke=1, fill=0)
    c.restoreState()


def flower(c, x, y, r, petal, center):
    c.saveState()
    c.setFillColor(petal)
    for i in range(5):
        a = 2 * math.pi * i / 5 + 0.3
        c.circle(x + math.cos(a) * r * 0.9, y + math.sin(a) * r * 0.9, r * 0.72, stroke=0, fill=1)
    c.setFillColor(center)
    c.circle(x, y, r * 0.55, stroke=0, fill=1)
    c.restoreState()


def leaf(c, x, y, ang, s, pal):
    c.saveState()
    c.translate(x, y)
    c.rotate(ang)
    p = c.beginPath()
    p.moveTo(0, 0)
    p.curveTo(8 * s, 10 * s, 22 * s, 10 * s, 30 * s, 0)
    p.curveTo(22 * s, -10 * s, 8 * s, -10 * s, 0, 0)
    c.setFillColor(HexColor(pal["leaf"]))
    c.drawPath(p, stroke=0, fill=1)
    c.setStrokeColor(HexColor(pal["leaf_dark"]))
    c.setLineWidth(1)
    c.line(2 * s, 0, 26 * s, 0)
    c.restoreState()


def bird(c, x, y, s, kind, flip=False):
    """Perched songbird; (x, y) = feet on the perch."""
    b = {k: HexColor(v) for k, v in BIRDS[kind].items()}
    c.saveState()
    c.translate(x, y)
    c.scale(-s if flip else s, s)
    c.setStrokeColor(HexColor("#6B4226"))
    c.setLineWidth(2.2)
    c.setLineCap(1)
    c.line(-6, 0, -4, 14)
    c.line(6, 0, 4, 14)

    def tail(p):
        p.moveTo(-22, 22); p.lineTo(-58, 2); p.lineTo(-52, -6); p.lineTo(-18, 14); p.close()
    _path(c, tail, b["tail"])

    def body(p):
        p.moveTo(-30, 26)
        p.curveTo(-28, 52, 8, 62, 22, 50)
        p.curveTo(34, 38, 30, 12, 12, 8)
        p.curveTo(-6, 4, -30, 10, -30, 26)
    _path(c, body, b["body"])

    def belly(p):
        p.moveTo(-4, 10); p.curveTo(14, 8, 30, 18, 26, 40); p.curveTo(18, 30, 6, 22, -4, 10)
    _path(c, belly, b["belly"])
    if kind == "bluebird":
        c.setFillColor(white)
        c.ellipse(-2, 8, 18, 20, stroke=0, fill=1)
    c.setFillColor(b["body"])
    c.circle(20, 58, 17, stroke=0, fill=1)
    if kind == "cardinal":
        _path(c, lambda p: (p.moveTo(8, 66), p.lineTo(4, 92), p.lineTo(24, 70), p.close()), b["body"])
        _path(c, lambda p: (p.moveTo(26, 64), p.curveTo(36, 66, 40, 56, 38, 48),
                            p.curveTo(30, 46, 24, 52, 26, 64)), HexColor("#1B1B1B"))
    if kind == "goldfinch":
        _path(c, lambda p: (p.moveTo(10, 70), p.curveTo(18, 78, 32, 76, 36, 64),
                            p.curveTo(28, 66, 18, 66, 10, 70)), HexColor("#1B1B1B"))
    _path(c, lambda p: (p.moveTo(-26, 30), p.curveTo(-20, 50, 6, 52, 12, 38),
                        p.curveTo(4, 26, -14, 22, -26, 30)), b["wing"])
    if kind == "goldfinch":
        c.setStrokeColor(white)
        c.setLineWidth(2.6)
        c.line(-16, 36, 4, 42)
        c.line(-18, 30, 2, 34)
    c.setFillColor(HexColor("#1B1B1B"))
    c.circle(25, 61, 4.2, stroke=0, fill=1)
    c.setFillColor(white)
    c.circle(26.4, 62.6, 1.5, stroke=0, fill=1)
    c.saveState()
    c.setFillColor(HexColor("#FF8FAB"))
    c.setFillAlpha(0.55)
    c.circle(23, 50, 4, stroke=0, fill=1)
    c.restoreState()
    _path(c, lambda p: (p.moveTo(34, 62), p.lineTo(50, 56), p.lineTo(34, 51), p.close()), b["beak"])
    c.restoreState()


def pill(c, x, y, w, h, col):
    c.setFillColor(col)
    c.roundRect(x, y, w, h, h / 2, stroke=0, fill=1)


def spaced(c, text, cx, y, font, size, spacing, col):
    c.setFillColor(col)
    c.setFont(font, size)
    total = sum(stringWidth(ch, font, size) for ch in text) + spacing * (len(text) - 1)
    x = cx - total / 2
    for ch in text:
        c.drawString(x, y, ch)
        x += stringWidth(ch, font, size) + spacing


def outlined(c, text, cx, y, font, size, fill, stroke, sw, max_w=None):
    while max_w and size > 20 and stringWidth(text, font, size) > max_w:
        size -= 1
    w = stringWidth(text, font, size)
    t = c.beginText()
    t.setFont(font, size)
    t.setTextOrigin(cx - w / 2, y)
    t.setTextRenderMode(2)
    t.textOut(text)
    c.saveState()
    c.setLineJoin(1)
    c.setStrokeColor(stroke)
    c.setFillColor(stroke)
    c.setLineWidth(sw)
    c.drawText(t)
    c.restoreState()
    c.setFillColor(fill)
    c.setFont(font, size)
    c.drawCentredString(cx, y, text)


def teaser_grid(seed, words, n=9):
    g = [[None] * n for _ in range(n)]
    for w, r, col, (dr, dc) in words:
        for k, ch in enumerate(w):
            g[r + dr * k][col + dc * k] = ch
    rng = random.Random(seed)
    for r in range(n):
        for col in range(n):
            if g[r][col] is None:
                g[r][col] = rng.choice("ABCDEFGHKLMNOPRSTUVWY")
    return g


def draw_front(c, fx0, oy, trim_w, pal, cfg):
    """fx0 = left edge of the front trim; oy = bottom of trim (bleed)."""
    cv = cfg.get("cover", {})
    ink, coral, teal = HexColor(pal["ink"]), HexColor(pal["coral"]), HexColor(pal["teal"])
    fcx = fx0 + trim_w / 2
    Y = lambda v: oy + v - 9        # design coordinates were laid out on a 0.125 in bleed
    sun(c, fx0 + trim_w - 62, Y(445), 54, pal)
    cloud(c, fx0 + 22, Y(470), 0.9)
    for dx, dy, s in ((70, 515, 0.8), (104, 530, 0.6), (40, 735, 0.7)):
        flyer(c, fx0 + dx, Y(dy), s, ink)

    tag = cv.get("tag", "")
    if tag:
        rw = stringWidth(tag, BOLD, 13) + 2.8 * len(tag) + 40
        pill(c, fcx - rw / 2, Y(752), rw, 28, coral)
        spaced(c, tag, fcx, Y(761), BOLD, 13, 2.8, white)
    outlined(c, cv.get("headline", "LARGE PRINT"), fcx, Y(680), BOLD, 68, ink, white, 10, trim_w - 60)
    outlined(c, cv.get("main", cfg["title"].upper()), fcx, Y(612), BOLD, 58, coral, white, 10, trim_w - 60)
    spaced(c, cv.get("sub", "WORD SEARCH"), fcx, Y(568), BOLD, 32, 9, ink)
    spaced(c, cv.get("audience", ""), fcx, Y(540), BOLD, 13, 1.6, ink)

    # puzzle card with highlighted teaser words
    n, cell = 9, 32
    card_w = card_h = n * cell + 36
    card_x, card_y = fcx - card_w / 2 - 30, Y(92)
    words = [tuple(w[:3]) + (tuple(w[3]),) for w in cv.get("teaser", [])]
    g = teaser_grid(cfg["seed"], words, n)
    c.saveState()
    c.setFillColor(HexColor("#000000"))
    c.setFillAlpha(0.12)
    c.roundRect(card_x + 6, card_y - 8, card_w, card_h, 22, stroke=0, fill=1)
    c.restoreState()
    c.setFillColor(HexColor(pal["card"]))
    c.setStrokeColor(teal)
    c.setLineWidth(5)
    c.roundRect(card_x, card_y, card_w, card_h, 22, stroke=1, fill=1)
    gx0, gy0 = card_x + 18, card_y + card_h - 18
    cc = lambda r, col: (gx0 + col * cell + cell / 2, gy0 - r * cell - cell / 2)
    for i, (w, r, col, (dr, dc)) in enumerate(words):
        x0, y0 = cc(r, col)
        x1, y1 = cc(r + dr * (len(w) - 1), col + dc * (len(w) - 1))
        c.saveState()
        c.setStrokeColor(HexColor(HIGHLIGHTS[i % len(HIGHLIGHTS)]))
        c.setLineCap(1)
        c.setLineWidth(cell * 0.84)
        c.line(x0, y0, x1, y1)
        c.restoreState()
    c.setFillColor(ink)
    c.setFont(BOLD, 21)
    for r in range(n):
        for col in range(n):
            x, y = cc(r, col)
            c.drawCentredString(x, y - 7.5, g[r][col])

    # branch, leaves and perched birds
    by = card_y + card_h + 6
    c.saveState()
    c.setStrokeColor(HexColor(pal["bark"]))
    c.setLineCap(1)
    c.setLineWidth(11)
    p = c.beginPath()
    p.moveTo(fx0 - 4, by - 18)
    p.curveTo(card_x + 60, by + 8, card_x + card_w - 40, by - 4, card_x + card_w + 70, by + 18)
    c.drawPath(p, stroke=1, fill=0)
    c.setLineWidth(5)
    c.line(card_x + card_w - 10, by + 6, card_x + card_w + 30, by + 46)
    c.restoreState()
    for lx, ly, a in ((fx0 + 30, by - 12, 150), (card_x + 30, by + 4, 120), (card_x + card_w + 20, by + 40, 40),
                      (card_x + card_w + 36, by + 44, 100), (card_x + card_w - 30, by + 6, 70), (card_x + 150, by + 4, 60)):
        leaf(c, lx, ly, a, 1.05, pal)
    kinds = cv.get("birds", ["cardinal", "goldfinch", "bluebird"])[:3]
    spots = ((70, 4, 0.95, False), (185, 4, 0.9, False), (300, 2, 0.92, True))
    for kind, (dx, dy, s, flip) in zip(kinds, spots):
        bird(c, card_x + dx, by + dy, s, kind, flip)

    # starburst badge beside the card (never over letters)
    bx, byy = card_x + card_w + 66, card_y + 150
    c.saveState()
    c.translate(bx, byy)
    c.rotate(12)
    pts = [(math.cos(math.pi * i / 16) * (64 if i % 2 == 0 else 54),
            math.sin(math.pi * i / 16) * (64 if i % 2 == 0 else 54)) for i in range(32)]
    p = c.beginPath()
    p.moveTo(*pts[0])
    for q in pts[1:]:
        p.lineTo(*q)
    p.close()
    c.setFillColor(coral)
    c.drawPath(p, stroke=0, fill=1)
    c.setFillColor(white)
    c.setFont(BOLD, 40)
    c.drawCentredString(0, -2, str(cfg["puzzle_count"]))
    c.setFont(BOLD, 11)
    c.drawCentredString(0, -20, "PUZZLES")
    c.restoreState()
    c.setFillColor(ink)
    c.setFont(BOLD, 14)
    c.drawCentredString(bx, card_y + 60, cfg.get("volume", "").upper())
    c.setFont(REG, 13)
    c.drawCentredString(bx, card_y + 38, cfg["author"])

    # meadow + flowers
    c.setFillColor(HexColor(pal["leaf"]))
    p = c.beginPath()
    p.moveTo(fx0, 0)
    p.lineTo(fx0, Y(70))
    p.curveTo(fx0 + 200, Y(100), fx0 + 420, Y(60), fx0 + trim_w + 20, Y(90))
    p.lineTo(fx0 + trim_w + 20, 0)
    p.close()
    c.drawPath(p, stroke=0, fill=1)
    sunc, orange = HexColor(pal["sun"]), HexColor(pal["orange"])
    for dx, dy, r, colr in ((30, 70, 13, "#FF8FAB"), (card_w + 120, 95, 14, "#CDB4DB"), (card_w + 160, 78, 11, pal["sun"]),
                            (card_w + 200, 100, 12, "#FF8FAB"), (card_w + 240, 80, 10, "#FFFFFF")):
        flower(c, fx0 + dx, Y(dy), r, HexColor(colr), orange if colr == pal["sun"] else sunc)

    strip = cv.get("ribbon", "")
    if strip:
        size = 11.5
        while stringWidth(strip, BOLD, size) > trim_w - 100 and size > 8:
            size -= 0.5
        sw = stringWidth(strip, BOLD, size) + 40
        pill(c, fcx - sw / 2, Y(30), sw, 28, ink)
        c.setFillColor(white)
        c.setFont(BOLD, size)
        c.drawCentredString(fcx, Y(39.5), strip)


def check(c, x, y, colr):
    c.setFillColor(colr)
    c.circle(x, y + 5, 10, stroke=0, fill=1)
    c.saveState()
    c.setStrokeColor(white)
    c.setLineWidth(2.4)
    c.setLineCap(1)
    c.setLineJoin(1)
    p = c.beginPath()
    p.moveTo(x - 5, y + 5)
    p.lineTo(x - 1, y + 1)
    p.lineTo(x + 5, y + 10)
    c.drawPath(p, stroke=1, fill=0)
    c.restoreState()


def draw_back(c, bx_trim0, oy, trim_w, pal, cfg):
    """bx_trim0 = left edge of the back trim."""
    cv = cfg.get("cover", {})
    ink, coral = HexColor(pal["ink"]), HexColor(pal["coral"])
    Y = lambda v: oy + v - 9
    left = bx_trim0 + 36
    cloud(c, bx_trim0 + 380, Y(700), 0.8)
    flyer(c, bx_trim0 + 470, Y(740), 0.9, ink)
    flyer(c, bx_trim0 + 510, Y(725), 0.7, ink)
    bt = cv.get("back_title", ["Big print.", "Big fun!"])
    for i, (line, col) in enumerate(zip(bt, (ink, coral))):
        w = stringWidth(line, BOLD, 44)
        outlined(c, line, left + w / 2, Y(700 - 50 * i), BOLD, 44, col, white, 8)
    c.setFillColor(ink)
    c.setFont(REG, 15)
    y = Y(600)
    for line in simpleSplit(cfg["back_cover_text"], REG, 15, 470):
        c.drawString(left, y, line)
        y -= 23
    feats = cv.get("features", [])
    fh = 29 * len(feats) + 25
    fy = y - 22 - fh
    c.saveState()
    c.setFillColor(white)
    c.setFillAlpha(0.82)
    c.roundRect(left, fy, 470, fh, 20, stroke=0, fill=1)
    c.restoreState()
    cols = [pal["coral"], pal["teal"], pal["orange"], "#3A86FF", "#9D4EDD"]
    for i, f in enumerate(feats):
        yy = fy + fh - 34 - i * 29
        check(c, left + 26, yy, HexColor(cols[i % len(cols)]))
        c.setFillColor(ink)
        c.setFont(BOLD, 15)
        c.drawString(left + 46, yy, f)
    c.setFillColor(ink)
    c.setFont(OBL, 13)
    c.drawString(left, fy - 32, cv.get("gift_line", ""))

    # meadow, birdhouse, a bird and flowers
    c.setFillColor(HexColor(pal["leaf"]))
    p = c.beginPath()
    p.moveTo(0, 0)
    p.lineTo(0, Y(95))
    p.curveTo(bx_trim0 + 191, Y(70), bx_trim0 + 411, Y(115), bx_trim0 + trim_w, Y(80))
    p.lineTo(bx_trim0 + trim_w, 0)
    p.close()
    c.drawPath(p, stroke=0, fill=1)
    hx = left + 70
    c.setFillColor(HexColor(pal["bark"]))
    c.rect(hx - 4, Y(40), 8, 110, stroke=0, fill=1)
    c.setFillColor(HexColor("#FFB4A2"))
    c.rect(hx - 34, Y(140), 68, 60, stroke=0, fill=1)
    _path(c, lambda p: (p.moveTo(hx - 44, Y(198)), p.lineTo(hx, Y(236)), p.lineTo(hx + 44, Y(198)), p.close()), coral)
    c.setFillColor(HexColor("#5C3D2E"))
    c.circle(hx, Y(174), 12, stroke=0, fill=1)
    c.setStrokeColor(HexColor("#5C3D2E"))
    c.setLineWidth(3)
    c.line(hx, Y(152), hx + 20, Y(152))
    kinds = cv.get("birds", ["cardinal", "goldfinch", "bluebird"])
    bird(c, hx + 110, Y(92), 0.8, kinds[-1], flip=True)
    sunc, orange = HexColor(pal["sun"]), HexColor(pal["orange"])
    for x, yv, r, colr in ((left + 200, 88, 11, pal["sun"]), (left + 240, 70, 12, "#FF8FAB"), (left + 15, 60, 10, "#CDB4DB")):
        flower(c, x, Y(yv), r, HexColor(colr), orange if colr == pal["sun"] else sunc)
    # barcode keep-out (white 2.0 x 1.2 in box; KDP overlays its own barcode)
    c.setFillColor(white)
    c.rect(bx_trim0 + trim_w - 0.25 * IN - 2 * IN, oy + 0.25 * IN, 2 * IN, 1.2 * IN, stroke=0, fill=1)


def draw_spine(c, sx0, spine, H, pal, cfg, with_text=True):
    c.setFillColor(HexColor(pal["ink"]))
    c.rect(sx0, 0, spine, H, stroke=0, fill=1)
    if not with_text:
        return
    text = f"{cfg['title'].upper()}  •  {cfg['author'].upper()}"
    size = min(10, spine * 0.4)
    while stringWidth(text, BOLD, size) > H - 2.5 * IN and size > 6:
        size -= 0.5
    c.saveState()
    c.translate(sx0 + spine / 2 + size * 0.35, H / 2)
    c.rotate(-90)
    c.setFillColor(white)
    c.setFont(BOLD, size)
    c.drawCentredString(0, 0, text)
    c.restoreState()


def build(c, W, H, spine, bleed, trim_w, cfg, spine_text):
    pal = dict(SUNRISE_PALETTE)
    pal.update(cfg.get("cover_palette", {}))
    sky(c, W, H, pal)
    draw_back(c, bleed, bleed, trim_w, pal, cfg)
    draw_front(c, bleed + trim_w + spine, bleed, trim_w, pal, cfg)
    draw_spine(c, bleed + trim_w, spine, H, pal, cfg, with_text=spine_text)
