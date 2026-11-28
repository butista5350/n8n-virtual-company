import json
import os
import re
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import wordsearch as ws          # noqa: E402
import generate_book as gb       # noqa: E402
import generate_cover as gc      # noqa: E402
from pypdf import PdfReader      # noqa: E402

THEMES = json.load(open(os.path.join(ROOT, "data", "themes.json"), encoding="utf-8"))
CFG = json.load(open(os.path.join(ROOT, "data", "book.example.json"), encoding="utf-8"))


class TestThemes(unittest.TestCase):
    def test_fifty_themes_twelve_words(self):
        self.assertEqual(len(THEMES), 50)
        for name, words in THEMES.items():
            self.assertEqual(len(words), 12, name)
            self.assertEqual(len(set(words)), 12, name)

    def test_word_format_and_no_substrings(self):
        for name, words in THEMES.items():
            for w in words:
                self.assertRegex(w, r"^[A-Z]{3,13}$", f"{name}:{w}")
                for o in words:
                    if o != w:
                        self.assertNotIn(w, o, f"{name}: {w} in {o}")


class TestGenerator(unittest.TestCase):
    def test_all_words_placed_once_forward_only(self):
        for name in list(THEMES)[:50]:
            p = ws.make_puzzle(THEMES[name], size=13, seed=f"t-{name}")
            g = p["grid"]
            self.assertEqual(len(g), 13)
            for row in g:
                self.assertEqual(len(row), 13)
                for ch in row:
                    self.assertRegex(ch, r"^[A-Z]$")
            for w in THEMES[name]:
                self.assertEqual(ws.count_occurrences(g, 13, w), 1, f"{name}:{w}")
                cells = p["placements"][w]
                self.assertEqual("".join(g[r][c] for r, c in cells), w)
                dr, dc = cells[1][0] - cells[0][0], cells[1][1] - cells[0][1]
                self.assertIn((dr, dc), ws.DIRECTIONS)

    def test_deterministic(self):
        a = ws.make_puzzle(THEMES["Fruits"], seed="x")
        b = ws.make_puzzle(THEMES["Fruits"], seed="x")
        self.assertEqual(a["grid"], b["grid"])
        c = ws.make_puzzle(THEMES["Fruits"], seed="y")
        self.assertNotEqual(a["grid"], c["grid"])

    def test_rejects_bad_words(self):
        with self.assertRaises(ws.PlacementError):
            ws.make_puzzle(["TOOLONGWORDFORGRID"], size=13)
        with self.assertRaises(ws.PlacementError):
            ws.make_puzzle(["AB1"], size=13)


class TestPdf(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.interior = os.path.join(cls.tmp, "interior.pdf")
        cls.pages = gb.build(CFG, os.path.join(ROOT, "data", "themes.json"), cls.interior)
        cls.cover = os.path.join(cls.tmp, "cover.pdf")
        cls.dim = gc.build(CFG, cls.pages, cls.cover)

    def test_interior_page_count_and_size(self):
        r = PdfReader(self.interior)
        self.assertEqual(len(r.pages), self.pages)
        self.assertEqual(self.pages % 2, 0)
        self.assertGreaterEqual(self.pages, 24)
        self.assertLessEqual(self.pages, 150)   # margins assume 24-150 pages
        for p in r.pages:
            self.assertAlmostEqual(float(p.mediabox.width), 612, delta=0.5)
            self.assertAlmostEqual(float(p.mediabox.height), 792, delta=0.5)

    def test_interior_text(self):
        r = PdfReader(self.interior)
        self.assertIn("Puzzle 1", r.pages[3].extract_text())
        self.assertIn("Solutions", r.pages[53].extract_text())
        self.assertIn(CFG["title"], " ".join(r.pages[0].extract_text().split()))

    def test_gutter_margin_not_below_kdp_minimum(self):
        self.assertGreaterEqual(gb.INNER / 72, 0.375)
        self.assertGreaterEqual(gb.OUTER / 72, 0.25)
        for page_no in (1, 2, 3, 4):
            x0, x1 = gb.live_area(page_no)
            gutter = x0 if page_no % 2 == 1 else gb.W - x1
            self.assertGreaterEqual(gutter / 72, 0.375)

    def test_cover_size_matches_formula(self):
        spine = self.pages * 0.002252
        self.assertAlmostEqual(self.dim["spine_in"], spine, places=6)
        self.assertAlmostEqual(self.dim["width_in"], 0.125 + 8.5 + spine + 8.5 + 0.125, places=6)
        self.assertAlmostEqual(self.dim["height_in"], 11.25, places=6)
        r = PdfReader(self.cover)
        self.assertAlmostEqual(float(r.pages[0].mediabox.width) / 72, self.dim["width_in"], delta=0.01)
        self.assertAlmostEqual(float(r.pages[0].mediabox.height) / 72, 11.25, delta=0.01)


GARDEN_CFG = json.load(open(os.path.join(ROOT, "data", "book.gardening.json"), encoding="utf-8"))
GARDEN = json.load(open(os.path.join(ROOT, "data", "themes_gardening.json"), encoding="utf-8"))


class TestGardeningEdition(unittest.TestCase):
    def test_hundred_themes_with_facts(self):
        self.assertEqual(len(GARDEN), 100)
        facts = set()
        for name, v in GARDEN.items():
            self.assertEqual(len(v["words"]), 12, name)
            self.assertEqual(len(set(v["words"])), 12, name)
            for w in v["words"]:
                self.assertRegex(w, r"^[A-Z]{3,13}$", f"{name}:{w}")
                for o in v["words"]:
                    if o != w:
                        self.assertNotIn(w, o, f"{name}: {w} in {o}")
            self.assertTrue(20 <= len(v["fact"]) <= 115, name)
            facts.add(v["fact"])
        self.assertEqual(len(facts), 100)           # no repeated tip

    def test_no_duplicate_word_lists(self):
        lists = {tuple(sorted(v["words"])) for v in GARDEN.values()}
        self.assertEqual(len(lists), 100)

    def test_all_hundred_puzzles_build(self):
        for i, (name, v) in enumerate(GARDEN.items(), 1):
            p = ws.make_puzzle(v["words"], size=13, seed=f"g-{i}")
            for w in v["words"]:
                self.assertEqual(ws.count_occurrences(p["grid"], 13, w), 1, f"{name}:{w}")

    def test_book_and_cover(self):
        tmp = tempfile.mkdtemp()
        out = os.path.join(tmp, "g.pdf")
        pages = gb.build(GARDEN_CFG, os.path.join(ROOT, "data", "themes_gardening.json"), out)
        self.assertEqual(pages, 132)
        r = PdfReader(out)
        self.assertEqual(len(r.pages), pages)
        self.assertIn("Garden Tip", r.pages[3].extract_text())
        self.assertIn("My Garden Plan", r.pages[-4].extract_text())
        cov = os.path.join(tmp, "c.pdf")
        d = gc.build(GARDEN_CFG, pages, cov)
        self.assertAlmostEqual(d["spine_in"], pages * 0.002252, places=6)
        self.assertEqual(len(PdfReader(cov).pages), 1)


BIRDS_CFG = json.load(open(os.path.join(ROOT, "data", "book.birds.json"), encoding="utf-8"))
BIRDS = json.load(open(os.path.join(ROOT, "data", "themes_birds.json"), encoding="utf-8"))


class TestBirdsEdition(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.interior = os.path.join(cls.tmp, "b.pdf")
        cls.pages = gb.build(BIRDS_CFG, os.path.join(ROOT, "data", "themes_birds.json"), cls.interior)
        cls.cover = os.path.join(cls.tmp, "bc.pdf")
        cls.dim = gc.build(BIRDS_CFG, cls.pages, cls.cover)

    def test_hundred_themes_twelve_words(self):
        self.assertEqual(len(BIRDS), 100)
        for name, v in BIRDS.items():
            self.assertEqual(len(set(v["words"])), 12, name)
        for old in ("Famous Bird Names", "Birds of Mexico and South", "Birder Snacks"):
            self.assertNotIn(old, BIRDS)

    def test_back_matter_is_about_birds(self):
        r = PdfReader(self.interior)
        self.assertEqual(self.pages, 132)
        back = " ".join(p.extract_text() for p in r.pages[-4:])
        self.assertIn("My Bird Watching Log", back)
        self.assertIn("Birds I Have Spotted", back)
        self.assertIn("Bird Notes", back)
        self.assertNotIn("Garden", back)

    def test_sunrise_cover(self):
        self.assertEqual(BIRDS_CFG["cover"]["layout"], "sunrise")
        r = PdfReader(self.cover)
        self.assertAlmostEqual(float(r.pages[0].mediabox.width) / 72, self.dim["width_in"], delta=0.01)
        text = r.pages[0].extract_text()
        self.assertIn("BACKYARD BIRDS", text)
        self.assertIn(BIRDS_CFG["author"], text)

    def test_unknown_bonus_kind_rejected(self):
        cfg = dict(BIRDS_CFG, bonus_pages=[{"kind": "nope", "title": "x"}], puzzle_count=1)
        with self.assertRaises(ValueError):
            gb.build(cfg, os.path.join(ROOT, "data", "themes_birds.json"), os.path.join(self.tmp, "x.pdf"))


class TestBakingEdition(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = json.load(open(os.path.join(ROOT, "data", "book.baking.json"), encoding="utf-8"))
        cls.tmp = tempfile.mkdtemp()
        cls.interior = os.path.join(cls.tmp, "k.pdf")
        cls.pages = gb.build(cls.cfg, os.path.join(ROOT, "data", "themes_baking.json"), cls.interior)
        cls.cover = os.path.join(cls.tmp, "kc.pdf")
        gc.build(cls.cfg, cls.pages, cls.cover)

    def test_book_shape(self):
        self.assertEqual(self.pages, 132)
        back = " ".join(p.extract_text() for p in PdfReader(self.interior).pages[-4:])
        self.assertIn("My Baking Log", back)
        self.assertNotIn("Garden", back)

    def test_bakery_cover(self):
        self.assertEqual(self.cfg["cover"]["scene"], "bakery")
        self.assertIn("BAKING", PdfReader(self.cover).pages[0].extract_text())


class TestThemeData(unittest.TestCase):
    def test_no_word_hidden_inside_another(self):
        """A word inside another word of the same puzzle (BERRY / RASPBERRY) confuses solvers."""
        for fname in ("themes_birds.json", "themes_baking.json"):
            themes = json.load(open(os.path.join(ROOT, "data", fname), encoding="utf-8"))
            self.assertEqual(len(themes), 100, fname)
            for name, v in themes.items():
                ws = v["words"]
                self.assertEqual(len(set(ws)), 12, name)
                for a in ws:
                    self.assertTrue(a.isalpha() and len(a) <= 13, (name, a))
                    for b in ws:
                        if a != b:
                            self.assertNotIn(a, b, (fname, name))


class TestPolicy(unittest.TestCase):
    """T0 policy: no network, no LLM; repository hygiene."""
    FILES = [os.path.join(ROOT, n) for n in ("wordsearch.py", "generate_book.py", "generate_cover.py", "cover_sunrise.py")]

    def test_no_network_or_llm_imports(self):
        banned = re.compile(r"^\s*(import|from)\s+(requests|urllib|http|socket|openai|anthropic|httpx|aiohttp)\b", re.M)
        for f in self.FILES:
            with open(f, encoding="utf-8") as fh:
                self.assertIsNone(banned.search(fh.read()), f)

    def test_no_sensitive_values(self):
        ip = re.compile(r"\b(?!127\.|0\.|10\.|192\.168\.)\d{1,3}(\.\d{1,3}){3}\b")
        chat = re.compile(r"(chat_?id)[^\n]{0,15}\d{8,12}", re.I)
        token = re.compile(r"ghp_[A-Za-z0-9]{20,}|github_pat_|\d{8,12}:[A-Za-z0-9_-]{30,}|sk-[A-Za-z0-9]{20,}")
        for dirpath, _, names in os.walk(ROOT):
            for n in names:
                if n.endswith((".py", ".json", ".md")) and n != os.path.basename(__file__):
                    with open(os.path.join(dirpath, n), encoding="utf-8") as fh:
                        t = fh.read()
                    self.assertIsNone(ip.search(t), n)
                    self.assertIsNone(chat.search(t), n)
                    self.assertIsNone(token.search(t), n)

    def test_example_config_has_placeholder_author(self):
        self.assertTrue(CFG["author"].startswith("REPLACE_"))


if __name__ == "__main__":
    unittest.main()
