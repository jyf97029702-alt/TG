# VOID CHRONOS (Obsidian Play)

#### Summary:

* A 5-reel, 6-row pay-anywhere (scatter-pays) tumbling/cascading game.
* 8 paying symbols (4 high, 4 low) + Wild.
* Scatter ("SC") is a pure feature-trigger symbol (no direct payout -- see notes).
* Two custom mechanics: Portal Wild ("P") and Orb Collector ("O" orb / "C" collector).

#### Basegame:
4 Scatters trigger 10 free spins, 5+ Scatters trigger 12 free spins.

#### Portal Wild
Every "P" symbol on the board, on reveal or after any tumble, converts itself plus
1-3 random adjacent (orthogonal) non-special neighbours into Wilds (2-4 cells total)
before wins are evaluated for that step.

#### Orb Collector (Free Spins only)
"O" (Orb) symbols carry a multiplier value (reuses the sdk's built-in `multiplier`
symbol attribute: 2x/5x/10x/25x/50x/100x/500x/1000x). When a "C" (Collector) symbol
is on the board, every visible Orb value is summed and added to the persistent
Global Multiplier, then the Orb + Collector symbols are removed (tumble). The Global
Multiplier is applied to every win as it happens and is reset only once, at the start
of the bonus (never per-spin) -- it holds for the whole free spin round.

#### Free spins rules
3+ Scatters landing during a free spin retrigger +5 free spins (flat, not scaled by
count). CHRONOS_STORM starts the Global Multiplier at 50x and forces 3-5 high-value
Orbs (always including a 500x and a 1000x, when the forced count allows) onto every
free spin's board. VOID_GATES forces 1-2 Orbs (min value 10x) onto every free spin.

#### Bonus Buy modes (bet_modes)
| name            | cost   | notes                                                   |
|-----------------|-------:|----------------------------------------------------------|
| normal          |    1x  | base game, natural free-spin trigger                     |
| ante_bet        |    3x  | same as normal, ~3x the natural free-spin trigger odds    |
| surge           |   50x  | 8 free spins, orb minimum 5x                              |
| standard_bonus  |  100x  | 10 free spins                                             |
| void_gates      |  500x  | 10 free spins, orb minimum 10x, 1-2 orbs guaranteed/spin  |
| chronos_storm   | 1000x  | 12 free spins, global mult starts 50x, 3-5 high orbs/spin |

Max win is capped at 20,000x (`config.wincap`).

#### Adaptations vs. the standalone prototype (slot_engine.py / index.html)
* SCATTER no longer has its own paytable entry. The sdk's built-in
  `Scatter.get_scatterpay_wins()` lets Wilds substitute for every symbol present
  in `config.paytable`; keeping Scatter out of the paytable is what keeps "Wild
  does not substitute Scatter" true, and matches the sdk's own sample games
  (their scatter symbol has no payout either) -- a common, deliberate choice in
  real scatter-pay slots, not a math-sdk limitation being worked around badly.
* Reel-strip based RNG (drawn from `reels/BR0.csv` / `FR0.csv` / `FRW.csv`, see
  `build_reels.py`) replaces the prototype's independent per-cell weighted draw.
  This is the standard, more authentic approach for a certifiable math model.
* Minimum winning count raised from 8 to 10, and the lowest paytable tier is
  fixed at exactly 0.10x (for the lowest-value symbol, S1). Stake's own RGS
  format check (`utils/rgs_verification.py: verify_lookup_format`) rejects any
  non-zero payout below 0.10x, and requires every payout to land on an exact
  0.10x increment -- both hard platform constraints the prototype's much finer
  (0.00387x-precision) curve violated outright. Every win amount is rounded to
  the nearest 0.10x at the point it's computed (game_executables.py) so every
  downstream sum lands on that grid.

#### Event descriptions (book events, in addition to the sdk's standard set)
"portalWildInfo" - Portal Wild conversions for a given step (portal position +
                    converted positions).
"orbCollectorInfo" - Orb Collector absorption for a given step (orb positions/values,
                      collector positions, amount added, resulting Global Multiplier).

#### Status
This folder runs end-to-end (`python3 run.py`) against a *small* simulation count
for pipeline validation. It is a first working port, not certification-grade math --
see run.py and game_optimization.py for what to scale up before treating the RTP as
final. The frontend (web-sdk / Svelte) integration is a separate, not-yet-started
stage; the existing single-file HTML/Pixi.js demo does not consume these book events.
