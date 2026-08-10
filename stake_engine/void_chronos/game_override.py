"""Overrides/extensions of the universal GeneralGameState functions for VOID CHRONOS."""

from game_executables import *


class GameStateOverride(GameExecutables):
    """Game specific overrides. e.g. custom book properties to reset."""

    def assign_special_sym_function(self):
        self.special_symbol_functions = {"O": [self.assign_orb_property]}

    def reset_fs_spin(self) -> None:
        """Global multiplier starts at 1, except CHRONOS_STORM which starts at
        50x per spec. Only resets once per bonus -- persists across every free
        spin within that bonus (see update_freespin in game_executables.py)."""
        super().reset_fs_spin()
        try:
            self.global_multiplier = self.get_current_distribution_conditions().get("start_global_mult", 1)
        except Exception:
            self.global_multiplier = 1
