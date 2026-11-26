# Word Search book generator (T0)

Pure Python + reportlab. No network, no LLM, no cost. Deterministic: same config and seed give the same book.

```bash
pip install reportlab pypdf            # pypdf only for tests
python3 tools/wordsearch/generate_book.py  --config tools/wordsearch/data/book.gardening.json --out output/interior.pdf
python3 tools/wordsearch/generate_cover.py --config tools/wordsearch/data/book.gardening.json --pages <pages printed by the first command> --out output/cover.pdf
python3 -m unittest discover -s tools/wordsearch/tests
```

- Interior: 8.5 x 11 in, black and white, one 13x13 puzzle per page with 22 pt letters, 12 words, a tip on every page, solutions and back-matter pages.
- Back matter: `"bonus_pages": true` gives the gardening planner pages; a list of page specs (`log`, `checklist`, `lines`, `plan`) sets them per book (see `data/book.birds.json`).
- Cover: full wrap, 0.125 in bleed, spine = pages x 0.002252 in (white paper). `cover.layout`: default, `garden`, `birds`, or `sunrise` (bright sky, perched birds; `cover_sunrise.py`).
- Add themes in `data/themes_gardening.json` (12 words each, A-Z, 3-13 letters, no word contained in another, plus an original `fact`). `data/themes.json` is the 50-theme mixed sample used only for tests.
- Copy `data/book.gardening.json` to a local file outside the repo and put the real publisher name there.
- `output/` is git-ignored.
