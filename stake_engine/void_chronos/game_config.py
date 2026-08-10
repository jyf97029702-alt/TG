"""
VOID CHRONOS - Obsidian Play
GameConfig: symbols, paytable, reels and bet-mode (incl. bonus-buy) definitions.

Ported from the standalone prototype (slot_engine.py / index.html) onto the
Stake Engine math-sdk framework. One notable adaptation versus the prototype:
SCATTER no longer carries its own paytable entry (the sdk's built-in Scatter.
get_scatterpay_wins() lets Wilds substitute for every symbol that IS in the
paytable, including scatter, which would break "wild does not substitute
scatter"). Excluding SCATTER from the paytable makes it a pure feature-trigger
symbol, matching the sdk's own sample games -- a common, deliberate design
choice in real scatter-pay slots.
"""

import os
from src.config.config import Config
from src.config.distributions import Distribution
from src.config.betmode import BetMode


# Shared pay-curve x per-symbol value factor. NOTE this differs from the
# standalone prototype's _TIER_CURVE: Stake's RGS rejects any non-zero payout
# below 0.10x ("Minimum non-zero payout is 10 (RGS accepts 'cents' increments)"
# -- see utils/rgs_verification.py), which the prototype's 8-of-30 tier (as low
# as 0.00387x) violates outright. The minimum winning count is raised from 8 to
# 10 here (cutting into the tier that hit most often) and the lowest tier is
# set exactly at the 0.10x floor for the lowest-value symbol (S1); every other
# symbol/tier sits above it by construction (higher value_factor). This is a
# real platform constraint, not a preference -- re-tune _TIER_CURVE against
# actual run.py RTP output rather than reverting the floor.
_TIER_CURVE = {10: 0.10, 12: 0.22, 15: 0.55, 20: 2.20, 25: 14.0}
_VALUE_FACTOR = {
    "S1": 1.0, "S2": 1.4, "S3": 2.0, "S4": 2.8,
    "S5": 5.0, "S6": 8.0, "S7": 13.0, "S8": 20.0,
    "W": 28.0,
}
_TIER_RANGES = [(10, 11), (12, 14), (15, 19), (20, 24), (25, 30)]


class GameConfig(Config):
    """Load all game specific parameters and elements."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        super().__init__()
        self.game_id = "void_chronos"
        self.game_name = "void_chronos"
        self.provider_number = 0
        self.working_name = "VOID CHRONOS"
        self.wincap = 20000.0
        self.win_type = "scatter"
        self.rtp = 0.962
        self.construct_paths()

        # ---- Board dimensions: 6 rows x 5 columns (30 cells) -------------------
        self.num_reels = 5
        self.num_rows = [6] * self.num_reels

        # ---- Paytable ------------------------------------------------------
        pay_group = {}
        for sym, factor in _VALUE_FACTOR.items():
            for tier_min, tier_max in _TIER_RANGES:
                pay_group[((tier_min, tier_max), sym)] = round(_TIER_CURVE[tier_min] * factor, 5)
        self.paytable = self.convert_range_table(pay_group)

        self.include_padding = True
        self.special_symbols = {
            "wild": ["W"],
            "scatter": ["SC"],
            "multiplier": ["O"],       # Multiplier Orb reuses the sdk's built-in multiplier attribute
            "portal": ["P"],           # Portal Rift - custom mechanic, see game_executables.py
            "collector": ["C"],        # Void Collector - custom mechanic, see game_executables.py
        }

        # 4 scatters -> 10 free spins, 5+ scatters -> 12 free spins (natural trigger).
        # Free-game retrigger is a flat +5 for 3+ scatters landing during a free spin.
        # Both dicts are populated for every plausible count (not just the two/three
        # "designed" thresholds): tumbling can keep drawing fresh symbols from the
        # continuing reel-strip position after a forced or natural scatter count is
        # set, so the *actual* count seen at trigger-check time can organically end
        # up higher than what was originally forced/expected -- every count needs a
        # mapping or update_freespin_amount()/update_fs_retrigger_amt() KeyErrors.
        max_syms = self.num_reels * self.num_rows[0]
        self.freespin_triggers = {
            self.basegame_type: {4: 10, **{n: 12 for n in range(5, max_syms + 1)}},
            self.freegame_type: {n: 5 for n in range(3, max_syms + 1)},
        }
        self.anticipation_triggers = {
            self.basegame_type: min(self.freespin_triggers[self.basegame_type].keys()) - 1,
            self.freegame_type: min(self.freespin_triggers[self.freegame_type].keys()) - 1,
        }

        # ---- Reels -----------------------------------------------------------
        reels = {"BR0": "BR0.csv", "FR0": "FR0.csv", "FRW": "FRW.csv"}
        self.reels = {}
        for r, f in reels.items():
            self.reels[r] = self.read_reels_csv(os.path.join(self.reels_path, f))

        self.padding_reels[self.basegame_type] = self.reels["BR0"]
        self.padding_reels[self.freegame_type] = self.reels["FR0"]

        # ---- Orb multiplier value catalogue (mirrors slot_engine.py ORB_VALUES) ----
        # Keyed to the "multiplier" attribute assigned to ORB ("O") symbols.
        self.orb_values = {2: 300, 5: 240, 10: 170, 25: 110, 50: 65, 100: 30, 500: 8, 1000: 2}

        # Fixed free-spin counts used by the bonus-buy modes (bypasses the natural
        # scatter-count -> freespin_triggers lookup, see game_override.py).
        self.buy_mode_fs_count = {
            "surge": 8,
            "standard_bonus": 10,
            "void_gates": 10,
            "chronos_storm": 12,
        }
        self.buy_mode_min_orb = {"surge": 5, "void_gates": 10}
        self.buy_mode_start_global_mult = {"chronos_storm": 50}

        # ---- Bet modes (incl. Bonus Buy) --------------------------------------
        self.bet_modes = [
            BetMode(
                name="normal",
                cost=1.0,
                rtp=self.rtp,
                max_win=self.wincap,
                auto_close_disabled=False,
                is_feature=True,
                is_buybonus=False,
                distributions=[
                    Distribution(
                        criteria="0",
                        quota=0.55,
                        win_criteria=0.0,
                        conditions={
                            "reel_weights": {self.basegame_type: {"BR0": 1}},
                            "force_freegame": False,
                        },
                    ),
                    Distribution(
                        criteria="basegame",
                        quota=0.40,
                        conditions={
                            "reel_weights": {self.basegame_type: {"BR0": 1}},
                            "force_freegame": False,
                        },
                    ),
                    Distribution(
                        criteria="freegame",
                        quota=0.0499,
                        conditions={
                            "reel_weights": {self.basegame_type: {"BR0": 1}, self.freegame_type: {"FR0": 1}},
                            "scatter_triggers": {4: 5, 5: 1},
                            "force_freegame": True,
                        },
                    ),
                    Distribution(
                        criteria="wincap",
                        quota=0.0001,
                        win_criteria=self.wincap,
                        conditions={
                            "reel_weights": {self.basegame_type: {"BR0": 1}, self.freegame_type: {"FRW": 1}},
                            "scatter_triggers": {5: 1},
                            "guaranteed_orbs": {"count_range": (3, 5), "forced_values": [500, 1000], "pool_min": 50},
                            "force_freegame": True,
                            "force_wincap": True,
                        },
                    ),
                ],
            ),
            BetMode(
                name="ante_bet",
                cost=3.0,
                rtp=self.rtp,
                max_win=self.wincap,
                auto_close_disabled=False,
                is_feature=True,
                is_buybonus=False,
                distributions=[
                    Distribution(
                        criteria="0",
                        quota=0.45,
                        win_criteria=0.0,
                        conditions={
                            "reel_weights": {self.basegame_type: {"BR0": 1}},
                            "force_freegame": False,
                        },
                    ),
                    Distribution(
                        criteria="basegame",
                        quota=0.40,
                        conditions={
                            "reel_weights": {self.basegame_type: {"BR0": 1}},
                            "force_freegame": False,
                        },
                    ),
                    Distribution(
                        criteria="freegame",
                        quota=0.1499,
                        conditions={
                            "reel_weights": {self.basegame_type: {"BR0": 1}, self.freegame_type: {"FR0": 1}},
                            "scatter_triggers": {4: 5, 5: 1},
                            "force_freegame": True,
                        },
                    ),
                    Distribution(
                        criteria="wincap",
                        quota=0.0001,
                        win_criteria=self.wincap,
                        conditions={
                            "reel_weights": {self.basegame_type: {"BR0": 1}, self.freegame_type: {"FRW": 1}},
                            "scatter_triggers": {5: 1},
                            "guaranteed_orbs": {"count_range": (3, 5), "forced_values": [500, 1000], "pool_min": 50},
                            "force_freegame": True,
                            "force_wincap": True,
                        },
                    ),
                ],
            ),
            BetMode(
                name="surge",
                cost=50.0,
                rtp=self.rtp,
                max_win=self.wincap,
                auto_close_disabled=False,
                is_feature=False,
                is_buybonus=True,
                distributions=[
                    Distribution(
                        criteria="freegame",
                        quota=0.999,
                        conditions={
                            "reel_weights": {self.basegame_type: {"BR0": 1}, self.freegame_type: {"FR0": 1}},
                            "scatter_triggers": {4: 1},
                            "min_orb": 5,
                            "force_freegame": True,
                        },
                    ),
                    Distribution(
                        criteria="wincap",
                        quota=0.001,
                        win_criteria=self.wincap,
                        conditions={
                            "reel_weights": {self.basegame_type: {"BR0": 1}, self.freegame_type: {"FRW": 1}},
                            "scatter_triggers": {4: 1},
                            "min_orb": 5,
                            "guaranteed_orbs": {"count_range": (3, 5), "forced_values": [500, 1000], "pool_min": 50},
                            "force_freegame": True,
                            "force_wincap": True,
                        },
                    ),
                ],
            ),
            BetMode(
                name="standard_bonus",
                cost=100.0,
                rtp=self.rtp,
                max_win=self.wincap,
                auto_close_disabled=False,
                is_feature=False,
                is_buybonus=True,
                distributions=[
                    Distribution(
                        criteria="freegame",
                        quota=0.999,
                        conditions={
                            "reel_weights": {self.basegame_type: {"BR0": 1}, self.freegame_type: {"FR0": 1}},
                            "scatter_triggers": {4: 1},
                            "force_freegame": True,
                        },
                    ),
                    Distribution(
                        criteria="wincap",
                        quota=0.001,
                        win_criteria=self.wincap,
                        conditions={
                            "reel_weights": {self.basegame_type: {"BR0": 1}, self.freegame_type: {"FRW": 1}},
                            "scatter_triggers": {4: 1},
                            "guaranteed_orbs": {"count_range": (3, 5), "forced_values": [500, 1000], "pool_min": 50},
                            "force_freegame": True,
                            "force_wincap": True,
                        },
                    ),
                ],
            ),
            BetMode(
                name="void_gates",
                cost=500.0,
                rtp=self.rtp,
                max_win=self.wincap,
                auto_close_disabled=False,
                is_feature=False,
                is_buybonus=True,
                distributions=[
                    Distribution(
                        criteria="freegame",
                        quota=0.999,
                        conditions={
                            "reel_weights": {self.basegame_type: {"BR0": 1}, self.freegame_type: {"FR0": 1}},
                            "scatter_triggers": {4: 1},
                            "min_orb": 10,
                            "guaranteed_orbs": {"count_range": (1, 2), "forced_values": [], "pool_min": 10},
                            "force_freegame": True,
                        },
                    ),
                    Distribution(
                        criteria="wincap",
                        quota=0.001,
                        win_criteria=self.wincap,
                        conditions={
                            "reel_weights": {self.basegame_type: {"BR0": 1}, self.freegame_type: {"FRW": 1}},
                            "scatter_triggers": {4: 1},
                            "min_orb": 10,
                            "guaranteed_orbs": {"count_range": (3, 5), "forced_values": [500, 1000], "pool_min": 50},
                            "force_freegame": True,
                            "force_wincap": True,
                        },
                    ),
                ],
            ),
            BetMode(
                name="chronos_storm",
                cost=1000.0,
                rtp=self.rtp,
                max_win=self.wincap,
                auto_close_disabled=False,
                is_feature=False,
                is_buybonus=True,
                distributions=[
                    Distribution(
                        criteria="freegame",
                        quota=0.995,
                        conditions={
                            "reel_weights": {self.basegame_type: {"BR0": 1}, self.freegame_type: {"FR0": 1}},
                            "scatter_triggers": {4: 1},
                            "start_global_mult": 50,
                            "guaranteed_orbs": {"count_range": (3, 5), "forced_values": [500, 1000], "pool_min": 50},
                            "force_freegame": True,
                        },
                    ),
                    Distribution(
                        criteria="wincap",
                        quota=0.005,
                        win_criteria=self.wincap,
                        conditions={
                            "reel_weights": {self.basegame_type: {"BR0": 1}, self.freegame_type: {"FRW": 1}},
                            "scatter_triggers": {4: 1},
                            "start_global_mult": 50,
                            "guaranteed_orbs": {"count_range": (3, 5), "forced_values": [1000, 1000]},
                            "force_freegame": True,
                            "force_wincap": True,
                        },
                    ),
                ],
            ),
        ]
