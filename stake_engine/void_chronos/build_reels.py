"""
Generates the reel-strip CSV files used by GameConfig from the same symbol-weight
ratios that were used to calibrate the standalone prototype (slot_engine.py /
index.html). Re-run this script any time the weight tables below change.

Reels produced:
    BR0  - base game, normal odds
    FR0  - free spins, normal odds (introduces ORB/COLLECT)
    FRW  - free spins, "wincap" biased odds (heavy ORB/COLLECT density), used only
           by the wincap-forcing distribution bucket of the bonus-buy modes so that
           a max-win outcome can be found in a reasonable number of simulations.
"""

import csv
import os
import random

REEL_LEN = 300
NUM_REELS = 5  # columns
random.seed(20260810)

BASE_WEIGHTS = {
    "S1": 170, "S2": 155, "S3": 139, "S4": 124,
    "S5": 109, "S6": 93, "S7": 78, "S8": 62,
    "W": 35, "SC": 15, "P": 20,
}
FREE_WEIGHTS = {
    "S1": 172, "S2": 155, "S3": 139, "S4": 123,
    "S5": 108, "S6": 92, "S7": 76, "S8": 59,
    "W": 40, "SC": 5, "P": 25, "O": 12, "C": 3,
}
WINCAP_WEIGHTS = {
    "S1": 60, "S2": 55, "S3": 48, "S4": 42,
    "S5": 60, "S6": 55, "S7": 48, "S8": 42,
    "W": 60, "SC": 4, "P": 20, "O": 140, "C": 40,
}


# SCATTER must never appear twice within one 6-row viewing window on the same
# reel -- the sdk's board-forcing (force_special_board) places exactly one
# scatter per reel and assumes the reel strip can't hand it a second one "for
# free" in the same window, or the forced count would silently be wrong. Wild
# and the other special symbols aren't forced this way, so they don't need the
# same guarantee.
SPECIAL_SYMBOLS = {"SC"}
MIN_GAP = 12  # comfortably > num_rows (6) + top/bottom padding, so no two scatters
              # can ever land in the same visible (+padding) window


def symbol_counts(weights: dict, length: int) -> dict:
    """Largest-remainder rounding so counts sum exactly to `length`."""
    total = sum(weights.values())
    raw = {sym: w * length / total for sym, w in weights.items()}
    floors = {sym: int(v) for sym, v in raw.items()}
    remainder = length - sum(floors.values())
    fracs = sorted(raw.items(), key=lambda kv: kv[1] - floors[kv[0]], reverse=True)
    for sym, _ in fracs[:remainder]:
        floors[sym] += 1
    return floors


def weights_to_strip(weights: dict, length: int) -> list:
    """
    Build one reel strip: special symbols are placed first with a minimum
    circular gap between same-type occurrences, then the remaining slots are
    filled with the (shuffled) paying symbols.
    """
    counts = symbol_counts(weights, length)
    strip = [None] * length

    for sym in SPECIAL_SYMBOLS:
        count = counts.get(sym, 0)
        placed = []
        attempts = 0
        while len(placed) < count and attempts < length * 50:
            attempts += 1
            pos = random.randrange(length)
            if strip[pos] is not None:
                continue
            ok = all(min(abs(pos - p), length - abs(pos - p)) >= MIN_GAP for p in placed)
            if ok:
                strip[pos] = sym
                placed.append(pos)
        if len(placed) < count:
            raise RuntimeError(
                f"Could not place {count} '{sym}' symbols with min gap {MIN_GAP} on a strip of length {length}."
            )

    filler = []
    for sym, count in counts.items():
        if sym not in SPECIAL_SYMBOLS:
            filler.extend([sym] * count)
    random.shuffle(filler)

    fi = 0
    for i in range(length):
        if strip[i] is None:
            strip[i] = filler[fi]
            fi += 1
    assert fi == len(filler), "filler/empty-slot count mismatch"
    return strip


def write_reel_csv(path: str, weights: dict, num_reels: int = NUM_REELS, length: int = REEL_LEN):
    columns = [weights_to_strip(weights, length) for _ in range(num_reels)]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for row in range(length):
            writer.writerow([columns[c][row] for c in range(num_reels)])


if __name__ == "__main__":
    out_dir = os.path.join(os.path.dirname(__file__), "reels")
    os.makedirs(out_dir, exist_ok=True)
    write_reel_csv(os.path.join(out_dir, "BR0.csv"), BASE_WEIGHTS)
    write_reel_csv(os.path.join(out_dir, "FR0.csv"), FREE_WEIGHTS)
    write_reel_csv(os.path.join(out_dir, "FRW.csv"), WINCAP_WEIGHTS)
    print("Reel strips written to", out_dir)
