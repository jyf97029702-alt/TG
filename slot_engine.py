"""
VOID CHRONOS - Slot Math Engine
Studio: Obsidian Play

Stateless scatter-pay + tumble (cascade) engine, built in the spirit of a
Stake Engine RGS math module. Every call to ``VoidChronosEngine.spin`` is
fully self-contained: no state is kept between calls, all randomness comes
from the RNG instance passed/created inside the call, and the full outcome
(grid, every cascade step, orb/collector events, free spins, final payout)
is returned as a JSON-serialisable dict.

Grid:        6 rows x 5 columns (30 cells)
Wins:        Scatter pays -> 8+ of the same symbol anywhere on the grid pays
Mechanic:    Cascade / Tumble -> winning symbols are removed, the grid
             collapses with gravity and refills from the top, repeating
             until no new win is formed.
Features:
  - Portal Wild:    a PORTAL symbol converts itself + 1-3 adjacent cells
                     (2-4 total) into WILDs before wins are evaluated.
  - Orb Collector:  ORB symbols (free spins only) carry a multiplier value.
                     A COLLECT symbol landing on the grid absorbs every ORB
                     value currently visible and adds the sum to the
                     permanent Global Multiplier for the rest of the bonus.
  - Free Spins:     4 scatters -> 10 spins, 5+ scatters -> 12 spins.
                     3+ scatters landing during a free spin retriggers +5
                     spins. The Global Multiplier persists across the whole
                     bonus and never resets until it ends.
  - Bonus Buy:      NORMAL / ANTE_BET / SURGE / STANDARD_BONUS /
                     VOID_GATES / CHRONOS_STORM, see MODES below.
  - Max win:        capped at 20,000x the base bet.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# GRID / SYMBOL CONSTANTS
# ---------------------------------------------------------------------------

ROWS = 6
COLS = 5
GRID_CELLS = ROWS * COLS

# Regular paying symbols
LOW_SYMBOLS = ["S1", "S2", "S3", "S4"]          # Cyan Shard, Teal Rune, Azure Gem, Gold Coin
HIGH_SYMBOLS = ["S5", "S6", "S7", "S8"]         # Void Eye, Portal Core, Chronos Gear, Obsidian Skull
PAYING_SYMBOLS = LOW_SYMBOLS + HIGH_SYMBOLS

WILD = "WILD"          # Void Wild - substitutes all paying symbols
SCATTER = "SCAT"        # Chronos Scatter - hourglass/void portal, pays + triggers Free Spins
PORTAL = "PORTAL"       # Portal symbol - converts nearby cells into Wilds
COLLECTOR = "COLLECT"   # Void Collector - absorbs Orb multipliers into the Global Multiplier
ORB = "ORB"             # Multiplier Orb - free spins only, carries a multiplier value

SYMBOL_NAMES = {
    "S1": "Cyan Shard",
    "S2": "Teal Rune",
    "S3": "Azure Gem",
    "S4": "Gold Coin",
    "S5": "Void Eye",
    "S6": "Portal Core",
    "S7": "Chronos Gear",
    "S8": "Obsidian Skull",
    "WILD": "Void Wild",
    "SCAT": "Chronos Scatter",
    "PORTAL": "Portal Rift",
    "COLLECT": "Void Collector",
    "ORB": "Multiplier Orb",
}

# Scatter-pay paytable, built from a shared tier curve x a per-symbol value factor.
# With an 8-of-30 "anywhere on grid" trigger the low tier (8-11 symbols) lands very
# often, so its payout must stay tiny; the payout only becomes serious from tier 15+,
# where landing that many of one symbol is a genuine (and, for 25+, extremely rare) event.
_TIER_CURVE: Dict[int, float] = {8: 0.00426, 10: 0.01277, 12: 0.03832, 15: 0.12774, 20: 0.63879, 25: 4.25681}
_VALUE_FACTOR: Dict[str, float] = {
    "S1": 1.0, "S2": 1.4, "S3": 2.0, "S4": 2.8,
    "S5": 5.0, "S6": 8.0, "S7": 13.0, "S8": 20.0,
    "WILD": 28.0, "SCAT": 25.0,
}

PAYTABLE: Dict[str, List[Tuple[int, float]]] = {
    sym: sorted(
        ((tier, round(mult * factor, 5)) for tier, mult in _TIER_CURVE.items()),
        key=lambda t: t[0],
        reverse=True,
    )
    for sym, factor in _VALUE_FACTOR.items()
}

# Orb multiplier catalogue
ORB_VALUES = [2, 5, 10, 25, 50, 100, 500, 1000]
ORB_WEIGHTS = [300, 240, 170, 110, 65, 30, 8, 2]

MAX_WIN_MULT = 20000.0  # cap, expressed as a multiple of the base bet

# Reel weights used for the base game (no ORB / COLLECT, they are Free Spins only).
# Weights are calibrated (see run_simulation) so that no single symbol dominates the
# 30-cell grid too heavily -- with a scatter-pays-anywhere mechanic on 30 cells, a
# skewed distribution makes 8+ matches far too likely and blows up the RTP.
BASE_WEIGHTS: Dict[str, int] = {
    "S1": 170, "S2": 155, "S3": 139, "S4": 124,
    "S5": 109, "S6": 93, "S7": 78, "S8": 62,
    "WILD": 35,
    "SCAT": 15,
    "PORTAL": 20,
}

# Reel weights used inside Free Spins (introduces ORB + COLLECT).
FREE_SPIN_WEIGHTS: Dict[str, int] = {
    "S1": 172, "S2": 155, "S3": 139, "S4": 123,
    "S5": 108, "S6": 92, "S7": 76, "S8": 59,
    "WILD": 40,
    "SCAT": 5,
    "PORTAL": 25,
    "ORB": 12,
    "COLLECT": 3,
}

# Safety valve: hard cap on cascade steps within a single spin sequence so a
# pathological RNG streak can never produce an unbounded loop.
MAX_CASCADE_STEPS = 40

NATURAL_FS_TABLE = {4: 10, 5: 12}  # scatter_count -> free spins awarded (5+ all award 12)
RETRIGGER_SCATTER_THRESHOLD = 3
RETRIGGER_SPINS = 5

# ---------------------------------------------------------------------------
# BONUS BUY MODES
# ---------------------------------------------------------------------------

MODES: Dict[str, Dict[str, Any]] = {
    "NORMAL": {
        "cost_multiplier": 1,
        "scatter_weight_mult": 1,
        "forces_free_spins": False,
    },
    "ANTE_BET": {
        "cost_multiplier": 3,
        "scatter_weight_mult": 3,   # triples the chance of landing 4+ scatters
        "forces_free_spins": False,
    },
    "SURGE": {
        "cost_multiplier": 50,
        "forces_free_spins": True,
        "fs_count": 8,
        "min_orb": 5,
        "start_global_mult": 1,
        "guaranteed_orbs": None,
    },
    "STANDARD_BONUS": {
        "cost_multiplier": 100,
        "forces_free_spins": True,
        "fs_count": 10,
        "min_orb": None,
        "start_global_mult": 1,
        "guaranteed_orbs": None,
    },
    "VOID_GATES": {
        "cost_multiplier": 500,
        "forces_free_spins": True,
        "fs_count": 10,
        "min_orb": 10,
        "start_global_mult": 1,
        # guarantees a couple of orbs (min value 10x, per the mode) on every free spin
        "guaranteed_orbs": {"count_range": (1, 2), "forced_values": [], "pool_min": 10},
    },
    "CHRONOS_STORM": {
        "cost_multiplier": 1000,
        "forces_free_spins": True,
        "fs_count": 12,
        "min_orb": None,
        "start_global_mult": 50,
        # Every free spin forces 3-5 high value orbs (always including a 500x and a 1000x
        # when count allows). This is the top-tier "jackpot hunting" buy: by spec design its
        # average return sits well above its cost -- players pay the 1000x premium expressly
        # to chase the 20,000x cap. See run_simulation(mode="CHRONOS_STORM") for its live stats.
        "guaranteed_orbs": {"count_range": (3, 5), "forced_values": [500, 1000], "pool_min": 50},
    },
}


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def _weighted_symbol(rng: random.Random, weights: Dict[str, int]) -> str:
    symbols = list(weights.keys())
    w = list(weights.values())
    return rng.choices(symbols, weights=w, k=1)[0]


def _roll_orb_value(rng: random.Random, min_orb: Optional[int] = None) -> int:
    values = ORB_VALUES
    weights = ORB_WEIGHTS
    if min_orb is not None:
        filtered = [(v, w) for v, w in zip(values, weights) if v >= min_orb]
        if filtered:
            values, weights = zip(*filtered)
    return rng.choices(list(values), weights=list(weights), k=1)[0]


def _pay_multiplier(symbol: str, count: int) -> float:
    tiers = PAYTABLE.get(symbol)
    if not tiers:
        return 0.0
    for min_count, mult in tiers:
        if count >= min_count:
            return mult
    return 0.0


def _idx(row: int, col: int) -> int:
    return row * COLS + col


def _rc(index: int) -> Tuple[int, int]:
    return divmod(index, COLS)


def _neighbors(index: int) -> List[int]:
    row, col = _rc(index)
    out = []
    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        r, c = row + dr, col + dc
        if 0 <= r < ROWS and 0 <= c < COLS:
            out.append(_idx(r, c))
    return out


# ---------------------------------------------------------------------------
# CORE DATA STRUCTURES
# ---------------------------------------------------------------------------

@dataclass
class Cell:
    symbol: str
    orb_value: Optional[int] = None

    def to_json(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"symbol": self.symbol}
        if self.orb_value is not None:
            d["value"] = self.orb_value
        return d


def _grid_to_json(grid: List[Optional[Cell]]) -> List[Dict[str, Any]]:
    return [c.to_json() if c is not None else None for c in grid]


# ---------------------------------------------------------------------------
# ENGINE
# ---------------------------------------------------------------------------

class VoidChronosEngine:
    """Stateless math engine for VOID CHRONOS.

    Every call to :meth:`spin` is fully self contained: pass a bet amount and
    a bonus-buy mode, get back a JSON-serialisable dict describing the whole
    outcome. No instance state is mutated or reused between calls.
    """

    def __init__(self, rows: int = ROWS, cols: int = COLS):
        self.rows = rows
        self.cols = cols

    # -- public API ---------------------------------------------------------

    def spin(self, bet_amount: float, mode: str = "NORMAL", rng_seed: Optional[int] = None) -> Dict[str, Any]:
        if mode not in MODES:
            raise ValueError(f"Unknown mode '{mode}'. Valid modes: {list(MODES.keys())}")
        if bet_amount <= 0:
            raise ValueError("bet_amount must be positive")

        rng = random.Random(rng_seed) if rng_seed is not None else random.Random()
        mode_cfg = MODES[mode]

        result: Dict[str, Any] = {
            "game": "VOID CHRONOS",
            "studio": "Obsidian Play",
            "bet_amount": bet_amount,
            "mode": mode,
            "buy_cost": round(bet_amount * mode_cfg["cost_multiplier"], 6),
            "base_game": None,
            "free_spins_triggered": False,
            "free_spins": None,
            "total_win": 0.0,
            "total_win_multiplier": 0.0,
            "max_win_capped": False,
        }

        running_total = 0.0
        cap_amount = bet_amount * MAX_WIN_MULT

        if mode_cfg["forces_free_spins"]:
            # Bonus-buy modes skip straight into the Free Spins bonus.
            fs_result, running_total = self._play_free_spins(
                rng=rng,
                bet_amount=bet_amount,
                fs_count=mode_cfg["fs_count"],
                start_global_mult=mode_cfg.get("start_global_mult", 1),
                min_orb=mode_cfg.get("min_orb"),
                guaranteed_orbs=mode_cfg.get("guaranteed_orbs"),
                running_total=running_total,
                cap_amount=cap_amount,
            )
            result["free_spins_triggered"] = True
            result["free_spins"] = fs_result
        else:
            initial_weights = dict(BASE_WEIGHTS)
            scat_mult = mode_cfg.get("scatter_weight_mult", 1)
            if scat_mult != 1:
                initial_weights["SCAT"] = initial_weights["SCAT"] * scat_mult

            base_seq = self._resolve_spin_sequence(
                rng=rng,
                weights=BASE_WEIGHTS,
                initial_weights=initial_weights,
                bet_amount=bet_amount,
                global_multiplier=1,
                min_orb=None,
                guaranteed_orbs=None,
                in_free_spins=False,
            )
            result["base_game"] = base_seq
            running_total += base_seq["spin_win"]

            scatter_count = base_seq["scatter_count"]
            fs_award = 0
            if scatter_count >= 5:
                fs_award = NATURAL_FS_TABLE[5]
            elif scatter_count == 4:
                fs_award = NATURAL_FS_TABLE[4]

            if fs_award > 0 and running_total < cap_amount:
                # "Los Free Spins naturales funcionan igual que STANDARD_BONUS"
                fs_result, running_total = self._play_free_spins(
                    rng=rng,
                    bet_amount=bet_amount,
                    fs_count=fs_award,
                    start_global_mult=1,
                    min_orb=None,
                    guaranteed_orbs=None,
                    running_total=running_total,
                    cap_amount=cap_amount,
                )
                result["free_spins_triggered"] = True
                result["free_spins"] = fs_result

        capped = running_total >= cap_amount
        final_total = min(running_total, cap_amount)

        result["total_win"] = round(final_total, 6)
        result["total_win_multiplier"] = round(final_total / bet_amount, 4) if bet_amount else 0.0
        result["max_win_capped"] = capped
        return result

    # -- free spins bonus ----------------------------------------------------

    def _play_free_spins(
        self,
        rng: random.Random,
        bet_amount: float,
        fs_count: int,
        start_global_mult: int,
        min_orb: Optional[int],
        guaranteed_orbs: Optional[Dict[str, Any]],
        running_total: float,
        cap_amount: float,
    ) -> Tuple[Dict[str, Any], float]:
        global_multiplier = start_global_mult
        spins_remaining = fs_count
        spins_played = 0
        total_retriggers = 0
        spin_log: List[Dict[str, Any]] = []
        total_fs_win = 0.0

        while spins_remaining > 0:
            if running_total >= cap_amount:
                break

            spins_remaining -= 1
            spins_played += 1

            seq = self._resolve_spin_sequence(
                rng=rng,
                weights=FREE_SPIN_WEIGHTS,
                bet_amount=bet_amount,
                global_multiplier=global_multiplier,
                min_orb=min_orb,
                guaranteed_orbs=guaranteed_orbs,
                in_free_spins=True,
            )
            # global_multiplier may have grown during the sequence (orb collector events)
            global_multiplier = seq["global_multiplier_end"]

            retrigger = seq["scatter_count"] >= RETRIGGER_SCATTER_THRESHOLD
            if retrigger:
                spins_remaining += RETRIGGER_SPINS
                total_retriggers += 1

            seq["spin_index"] = spins_played
            seq["retrigger"] = retrigger
            seq["spins_remaining_after"] = spins_remaining

            total_fs_win += seq["spin_win"]
            running_total += seq["spin_win"]
            spin_log.append(seq)

            if running_total >= cap_amount:
                break

        fs_result = {
            "initial_spins_awarded": fs_count,
            "spins_played": spins_played,
            "retriggers": total_retriggers,
            "global_multiplier_start": start_global_mult,
            "global_multiplier_final": global_multiplier,
            "total_free_spins_win": round(total_fs_win, 6),
            "spins": spin_log,
        }
        return fs_result, running_total

    # -- single spin sequence (base spin OR one free spin) ------------------

    def _resolve_spin_sequence(
        self,
        rng: random.Random,
        weights: Dict[str, int],
        bet_amount: float,
        global_multiplier: int,
        min_orb: Optional[int],
        guaranteed_orbs: Optional[Dict[str, Any]],
        in_free_spins: bool,
        initial_weights: Optional[Dict[str, int]] = None,
    ) -> Dict[str, Any]:
        # `initial_weights` (e.g. ANTE_BET's boosted scatter odds) only applies to the
        # fresh deal; cascade refills always use the standard `weights` table so a
        # modifier on the entry draw doesn't get non-linearly amplified by tumbling.
        grid = self._generate_grid(rng, initial_weights or weights, min_orb, guaranteed_orbs if in_free_spins else None)
        scatter_count = sum(1 for c in grid if c.symbol == SCATTER)

        cascades: List[Dict[str, Any]] = []
        spin_win = 0.0
        step = 0

        while True:
            step += 1
            if step > MAX_CASCADE_STEPS:
                break
            grid_before = _grid_to_json(grid)

            portal_events = self._apply_portal_wilds(rng, grid)

            wins, win_positions = self._evaluate_wins(grid)
            win_pay_raw = sum(w["pay_base"] for w in wins)

            orb_event = self._apply_orb_collector(grid)
            if orb_event is not None:
                global_multiplier += orb_event["collected_total"]

            win_pay = win_pay_raw * global_multiplier
            spin_win += win_pay
            for w in wins:
                w["pay"] = round(w["pay_base"] * global_multiplier, 6)

            remove_positions = sorted(set(win_positions) | (set(orb_event["positions"]) if orb_event else set()))

            cascade_entry = {
                "step": step,
                "grid_before": grid_before,
                "portal_events": portal_events,
                "wins": wins,
                "orb_collector_event": orb_event,
                "global_multiplier_after_step": global_multiplier,
                "removed_positions": remove_positions,
                "step_win": round(win_pay, 6),
            }

            if not remove_positions:
                cascade_entry["grid_after"] = _grid_to_json(grid)
                cascade_entry["new_symbols"] = []
                cascades.append(cascade_entry)
                break

            new_symbols = self._tumble(rng, grid, remove_positions, weights, min_orb)
            for pos in new_symbols:
                if grid[pos].symbol == SCATTER:
                    scatter_count += 1

            cascade_entry["grid_after"] = _grid_to_json(grid)
            cascade_entry["new_symbols"] = new_symbols
            cascades.append(cascade_entry)

        return {
            "initial_grid": _grid_to_json(self._grid_snapshot_from_cascades(cascades)),
            "cascades": cascades,
            "scatter_count": scatter_count,
            "spin_win": round(spin_win, 6),
            "global_multiplier_end": global_multiplier,
        }

    @staticmethod
    def _grid_snapshot_from_cascades(cascades: List[Dict[str, Any]]) -> List[Cell]:
        # first cascade's "grid_before" is the true initial grid; rebuild Cell objs for consistency
        raw = cascades[0]["grid_before"]
        return [Cell(symbol=c["symbol"], orb_value=c.get("value")) if c else None for c in raw]

    # -- grid generation ------------------------------------------------------

    def _generate_grid(
        self,
        rng: random.Random,
        weights: Dict[str, int],
        min_orb: Optional[int],
        guaranteed_orbs: Optional[Dict[str, Any]],
    ) -> List[Cell]:
        grid: List[Cell] = []
        for _ in range(GRID_CELLS):
            sym = _weighted_symbol(rng, weights)
            if sym == ORB:
                grid.append(Cell(symbol=ORB, orb_value=_roll_orb_value(rng, min_orb)))
            else:
                grid.append(Cell(symbol=sym))

        if guaranteed_orbs is not None:
            self._force_guaranteed_orbs(rng, grid, guaranteed_orbs)

        return grid

    @staticmethod
    def _force_guaranteed_orbs(rng: random.Random, grid: List[Cell], spec: Dict[str, Any]) -> None:
        lo, hi = spec["count_range"]
        count = rng.randint(lo, hi)
        positions = rng.sample(range(GRID_CELLS), k=count)
        forced_values = list(spec.get("forced_values", []))
        pool_min = spec.get("pool_min", 50)

        values: List[int] = []
        for i in range(count):
            if i < len(forced_values):
                values.append(forced_values[i])
            else:
                values.append(_roll_orb_value(rng, min_orb=pool_min))
        rng.shuffle(values)

        for pos, val in zip(positions, values):
            grid[pos] = Cell(symbol=ORB, orb_value=val)

    # -- portal wild ------------------------------------------------------

    @staticmethod
    def _apply_portal_wilds(rng: random.Random, grid: List[Cell]) -> List[Dict[str, Any]]:
        events = []
        portal_positions = [i for i, c in enumerate(grid) if c is not None and c.symbol == PORTAL]

        for p in portal_positions:
            candidates = [n for n in _neighbors(p) if grid[n] is not None and grid[n].symbol not in (SCATTER, PORTAL, COLLECTOR, ORB, WILD)]
            rng.shuffle(candidates)
            extra_count = rng.randint(1, min(3, max(1, len(candidates))))
            chosen = candidates[:extra_count]

            converted = [p] + chosen
            for pos in converted:
                grid[pos] = Cell(symbol=WILD)

            events.append({"portal_position": p, "converted_positions": converted})

        return events

    # -- orb collector ------------------------------------------------------

    @staticmethod
    def _apply_orb_collector(grid: List[Cell]) -> Optional[Dict[str, Any]]:
        collector_positions = [i for i, c in enumerate(grid) if c is not None and c.symbol == COLLECTOR]
        if not collector_positions:
            return None

        orb_positions = [i for i, c in enumerate(grid) if c is not None and c.symbol == ORB]
        collected_total = sum(grid[i].orb_value or 0 for i in orb_positions)

        return {
            "collector_positions": collector_positions,
            "orb_positions": orb_positions,
            "orb_values": [grid[i].orb_value for i in orb_positions],
            "collected_total": collected_total,
            "positions": collector_positions + orb_positions,
        }

    # -- win evaluation ------------------------------------------------------

    @staticmethod
    def _evaluate_wins(grid: List[Cell]) -> Tuple[List[Dict[str, Any]], List[int]]:
        wild_positions = [i for i, c in enumerate(grid) if c is not None and c.symbol == WILD]
        wins: List[Dict[str, Any]] = []
        all_win_positions: set = set()

        for sym in PAYING_SYMBOLS:
            sym_positions = [i for i, c in enumerate(grid) if c is not None and c.symbol == sym]
            total_count = len(sym_positions) + len(wild_positions)
            if total_count < 8:
                continue
            mult = _pay_multiplier(sym, total_count)
            if mult <= 0:
                continue
            positions = sorted(set(sym_positions) | set(wild_positions))
            wins.append({
                "symbol": sym,
                "count": total_count,
                "positions": positions,
                "pay_base": mult,
            })
            all_win_positions.update(positions)

        # A pure wild win (8+ wilds with no matching paying symbol requirement)
        if len(wild_positions) >= 8:
            mult = _pay_multiplier(WILD, len(wild_positions))
            if mult > 0:
                wins.append({
                    "symbol": WILD,
                    "count": len(wild_positions),
                    "positions": sorted(wild_positions),
                    "pay_base": mult,
                })
                all_win_positions.update(wild_positions)

        # Scatter pay (scatters do not accept wild substitution)
        scat_positions = [i for i, c in enumerate(grid) if c is not None and c.symbol == SCATTER]
        if len(scat_positions) >= 8:
            mult = _pay_multiplier(SCATTER, len(scat_positions))
            if mult > 0:
                wins.append({
                    "symbol": SCATTER,
                    "count": len(scat_positions),
                    "positions": sorted(scat_positions),
                    "pay_base": mult,
                })
                all_win_positions.update(scat_positions)

        return wins, sorted(all_win_positions)

    # -- tumble / cascade ------------------------------------------------------

    def _tumble(
        self,
        rng: random.Random,
        grid: List[Cell],
        remove_positions: List[int],
        weights: Dict[str, int],
        min_orb: Optional[int],
    ) -> List[int]:
        for pos in remove_positions:
            grid[pos] = None  # type: ignore[assignment]

        new_positions: List[int] = []

        for col in range(self.cols):
            col_cells = [grid[_idx(r, col)] for r in range(self.rows)]
            surviving = [c for c in col_cells if c is not None]
            missing = self.rows - len(surviving)

            fresh: List[Cell] = []
            for _ in range(missing):
                sym = _weighted_symbol(rng, weights)
                if sym == ORB:
                    fresh.append(Cell(symbol=ORB, orb_value=_roll_orb_value(rng, min_orb)))
                else:
                    fresh.append(Cell(symbol=sym))

            new_col = fresh + surviving  # new symbols drop in from the top
            for r in range(self.rows):
                idx = _idx(r, col)
                grid[idx] = new_col[r]
                if r < missing:
                    new_positions.append(idx)

        return new_positions

    # -- convenience: pretty JSON string -------------------------------------

    def spin_json(self, bet_amount: float, mode: str = "NORMAL", rng_seed: Optional[int] = None, indent: int = 2) -> str:
        return json.dumps(self.spin(bet_amount, mode, rng_seed), indent=indent)


# ---------------------------------------------------------------------------
# SIMULATION / RTP VALIDATION
# ---------------------------------------------------------------------------

def run_simulation(spins: int = 100_000, bet: float = 1.0, mode: str = "NORMAL", seed: Optional[int] = None) -> Dict[str, Any]:
    """Runs `spins` independent spin() calls and reports RTP / volatility stats.

    Useful to validate RTP (~96.2% target) and to sanity check the Free Spins /
    Super Bonus (CHRONOS_STORM) behaviour before wiring the engine to a
    front end or a Stake-Engine style RGS.
    """
    engine = VoidChronosEngine()
    rng = random.Random(seed)

    total_bet = 0.0
    total_win = 0.0
    max_win_seen = 0.0
    hits = 0
    fs_triggers = 0
    capped_hits = 0
    win_multiples: List[float] = []

    for _ in range(spins):
        result = engine.spin(bet_amount=bet, mode=mode, rng_seed=rng.randrange(1 << 30))
        total_bet += result["buy_cost"]  # buy_cost == bet_amount * cost_multiplier (1x for NORMAL)
        total_win += result["total_win"]
        win_multiples.append(result["total_win_multiplier"])

        if result["total_win"] > 0:
            hits += 1
        if result["free_spins_triggered"]:
            fs_triggers += 1
        if result["max_win_capped"]:
            capped_hits += 1
        max_win_seen = max(max_win_seen, result["total_win_multiplier"])

    win_multiples.sort()
    n = len(win_multiples)

    def percentile(p: float) -> float:
        if n == 0:
            return 0.0
        i = min(n - 1, int(p * n))
        return win_multiples[i]

    rtp = total_win / total_bet if total_bet else 0.0

    return {
        "mode": mode,
        "spins": spins,
        "rtp": round(rtp * 100, 4),
        "hit_frequency_pct": round(100 * hits / spins, 4),
        "free_spins_trigger_pct": round(100 * fs_triggers / spins, 4),
        "max_win_capped_count": capped_hits,
        "highest_win_multiplier": round(max_win_seen, 2),
        "median_win_multiplier": round(percentile(0.5), 4),
        "p99_win_multiplier": round(percentile(0.99), 4),
        "average_win_multiplier": round(sum(win_multiples) / n, 4) if n else 0.0,
    }


if __name__ == "__main__":
    print("VOID CHRONOS - Obsidian Play")
    print("Example single spin (NORMAL mode):")
    engine = VoidChronosEngine()
    print(engine.spin_json(bet_amount=1.0, mode="NORMAL", rng_seed=42))

    print("\nRunning RTP simulation (NORMAL mode, 20,000 spins)...")
    stats = run_simulation(spins=20_000, bet=1.0, mode="NORMAL", seed=1)
    print(json.dumps(stats, indent=2))
