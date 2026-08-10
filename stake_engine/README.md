# VOID CHRONOS — Stake Engine math-sdk port

This is a port of the game's mechanics (`slot_engine.py` / `index.html` at the repo
root) into [Stake Engine's math-sdk](https://github.com/StakeEngine/math-sdk)
framework — the format actually required to submit a game to Stake, as opposed to
the standalone Python/JS prototype, which computes outcomes live and isn't a format
their platform accepts.

## How to run it

Stake's math-sdk is its own repository, not a dependency you `pip install` — you
check it out and drop your game's folder inside `games/`.

```bash
git clone https://github.com/StakeEngine/math-sdk.git
cd math-sdk
cp -r /path/to/this/TG/stake_engine/void_chronos games/void_chronos

# math-sdk needs Python >= 3.12 (some of its own files use 3.12-only f-string syntax)
python3.12 -m venv venv && source venv/bin/activate
pip install -r requirements.txt   # drop the first line (the -e git+... self-install) if it errors

python3 games/void_chronos/build_reels.py   # (re)generates reels/*.csv from the weight tables inside it
PYTHONPATH=. python3 games/void_chronos/run.py
```

`run.py` runs simulations for all 6 bet modes, writes `games/void_chronos/library/`
(books, lookup tables, configs), runs Stake's Rust optimizer, and runs their format
verification. See `void_chronos/readme.txt` for the game's mechanics, symbol
reference, and event list.

## Status — read before treating this as submission-ready

**The pipeline runs end-to-end without errors and produces structurally valid
output** (books, lookup tables, `config.json`/`config_fe.json`, `index.json`, and
`utils/rgs_verification.py`'s format checks all pass). That in itself took real
debugging: this port hit and fixed several real platform constraints along the way
(minimum win 0.10x, payouts must land on exact 0.10x increments, scatter symbols
must never appear twice within one viewing window on the same reel, a rounding
edge-case in the sdk's own win-accounting assertion, a couple of gamestate ordering
bugs around the wincap / free-spin loop). Those are documented inline in the code
and in `void_chronos/readme.txt`.

**RTP is not calibrated.** Even after generating 40,000 raw simulations for the
`normal` mode and running Stake's own Rust optimizer against it, the resulting
lookup table's actual RTP is still roughly 90x too high (a `~9350%` weighted
average against the 96.2% target), with the mismatch concentrated almost entirely
in the `freegame` and `wincap` distribution buckets — `basegame` alone lands only
about 2x off. That points at the optimizer not finding enough low-value variety to
reweight toward inside those buckets, and/or `game_optimization.py`'s
`scaling`/`distribution_bias`/`min_m2m`/`max_m2m` parameters needing real tuning
against this game's specific win-shape — not something to brute-force by guessing
different numbers. Real studios have a dedicated math/RTP-tuning pass for exactly
this step; it's a distinct skill from wiring up the mechanics, and it's the
recommended next piece of work here, in order:

1. Re-run with much larger simulation counts per mode (Stake's own docs recommend
   100k-1M+ for production; `run.py` currently uses 1k-2k for fast iteration).
2. Inspect `library/lookup_tables/lookUpTableSegmented_<mode>.csv` (which
   simulation landed in which criteria bucket) joined against
   `library/publish_files/lookUpTable_<mode>_0.csv` (the optimizer's final
   weights) to see exactly where each bucket's RTP contribution lands versus its
   `game_optimization.py` target — the same join used to produce the 90x figure
   above.
3. Iterate `game_optimization.py`'s `scaling` / `distribution_bias` /
   `ConstructParameters` values (or the `Distribution` `quota`s in
   `game_config.py`) against that read-out.
4. `calibrate.py` (included) runs `GameState.run_spin()` directly in a loop,
   without the multiprocessing/optimizer overhead — useful for quickly sanity
   checking a single bucket's raw average win before paying for a full
   `run.py` cycle.

## Not started: the frontend (web-sdk)

Stake's actual frontend framework is a separate repo (`web-sdk`): a TurboRepo
monorepo using Svelte + PixiJS + Storybook, which consumes the book `events` this
math-sdk produces. The existing single-file `index.html` at the repo root does not
consume this format — it has its own client-side JS re-implementation of the game
math for a standalone demo. Porting the frontend to `web-sdk` is a separate,
similarly-sized stage of work that hasn't been started.
