"""Word Search core: deterministic grid generation. T0 tool: no network, no LLM."""
import random
import string

# Easy / large-print mode: words run left-to-right, top-to-bottom, or diagonally down-right.
DIRECTIONS = [(0, 1), (1, 0), (1, 1)]  # (d_row, d_col)


class PlacementError(Exception):
    pass


def _try_place(grid, size, word, rng, attempts=400):
    for _ in range(attempts):
        dr, dc = rng.choice(DIRECTIONS)
        max_r = size - 1 - dr * (len(word) - 1)
        max_c = size - 1 - dc * (len(word) - 1)
        if max_r < 0 or max_c < 0:
            continue
        r0, c0 = rng.randint(0, max_r), rng.randint(0, max_c)
        cells = [(r0 + dr * i, c0 + dc * i) for i in range(len(word))]
        if all(grid[r][c] in ("", word[i]) for i, (r, c) in enumerate(cells)):
            for i, (r, c) in enumerate(cells):
                grid[r][c] = word[i]
            return cells
    return None


def count_occurrences(grid, size, word):
    """Count occurrences of word in any of the allowed directions."""
    n = 0
    for r in range(size):
        for c in range(size):
            for dr, dc in DIRECTIONS:
                er, ec = r + dr * (len(word) - 1), c + dc * (len(word) - 1)
                if er >= size or ec >= size:
                    continue
                if all(grid[r + dr * i][c + dc * i] == word[i] for i in range(len(word))):
                    n += 1
    return n


def make_puzzle(words, size=13, seed=0, max_tries=300):
    """Return dict(grid, placements, seed_used). Every word placed exactly once."""
    words = [w.upper() for w in words]
    if any(len(w) > size or not w.isalpha() or not w.isascii() for w in words):
        raise PlacementError("invalid word for grid size")
    order = sorted(words, key=len, reverse=True)
    for attempt in range(max_tries):
        rng = random.Random(f"{seed}:{attempt}")
        grid = [[""] * size for _ in range(size)]
        placements = {}
        ok = True
        for w in order:
            cells = _try_place(grid, size, w, rng)
            if cells is None:
                ok = False
                break
            placements[w] = cells
        if not ok:
            continue
        for r in range(size):
            for c in range(size):
                if grid[r][c] == "":
                    grid[r][c] = rng.choice(string.ascii_uppercase)
        if all(count_occurrences(grid, size, w) == 1 for w in words):
            return {"grid": grid, "placements": placements, "seed_used": f"{seed}:{attempt}"}
    raise PlacementError("could not build puzzle")
