"""VOID CHRONOS executables: spin-sequence building blocks used by gamestate.py."""

from copy import copy

from game_calculations import GameCalculations
from src.calculations.scatter import Scatter
from src.events.events import (
    set_win_event,
    set_total_event,
    fs_trigger_event,
    update_freespin_event,
)


class GameExecutables(GameCalculations):
    """Game specific executable functions. Used for grouping commonly used/repeated applications."""

    def get_scatterpays_update_wins(self) -> None:
        """Evaluate scatter-pay wins on the current board (self.board is modified in-place)."""
        self.win_data = Scatter.get_scatterpay_wins(self.config, self.board, global_multiplier=self.global_multiplier)
        # Round every win to the nearest 0.10x at the source. The RGS lookup-table
        # format requires every payout to be an exact multiple of 0.10x (its
        # verify_lookup_format() enforces `payout % 10 == 0` on the *100 "cents"
        # value). basegame_wins/freegame_wins/running_bet_win are running sums of
        # these per-win values, so rounding here guarantees every downstream sum
        # (and the sdk's own round-then-compare assertions in update_final_win())
        # lands on that same 0.10x grid instead of accumulating finer fractions.
        for w in self.win_data["wins"]:
            w["win"] = round(w["win"] * 10) / 10
        self.win_data["totalWin"] = round(sum(w["win"] for w in self.win_data["wins"]) * 10) / 10
        Scatter.record_scatter_wins(self)
        self.win_manager.tumble_win = self.win_data["totalWin"]
        self.win_manager.update_spinwin(self.win_data["totalWin"])

    def set_end_tumble_event(self) -> None:
        if self.win_manager.spin_win > 0:
            set_win_event(self)
        set_total_event(self)

    def update_freespin_amount(self, scatter_key: str = "scatter") -> None:
        """
        Natural trigger (NORMAL / ANTE_BET): free spins awarded from freespin_triggers,
        keyed by scatter count. Bonus-buy modes (is_buybonus) use a fixed spin count
        instead, defined in config.buy_mode_fs_count.
        """
        betmode = self.get_current_betmode()
        if betmode.get_buybonus():
            self.tot_fs = self.config.buy_mode_fs_count[self.betmode]
        else:
            self.tot_fs = self.config.freespin_triggers[self.gametype][self.count_special_symbols(scatter_key)]

        basegame_trigger = self.gametype == self.config.basegame_type
        fs_trigger_event(self, basegame_trigger=basegame_trigger, freegame_trigger=not basegame_trigger)

    def update_fs_retrigger_amt(self, scatter_key: str = "scatter") -> None:
        """Flat +5 free spins for 3+ scatters landing during a free spin."""
        self.tot_fs += self.config.freespin_triggers[self.gametype][self.count_special_symbols(scatter_key)]
        fs_trigger_event(self, freegame_trigger=True, basegame_trigger=False)

    def update_freespin(self) -> None:
        """Called before every free spin reveal. Global multiplier is intentionally
        NOT reset here -- it persists for the whole bonus (reset only once, in
        reset_fs_spin, at bonus entry)."""
        update_freespin_event(self)
        self.fs += 1
        self.win_manager.reset_spin_win()
        self.win_data = {}
