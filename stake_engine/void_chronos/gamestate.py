from game_override import GameStateOverride
from src.events.events import reveal_event


class GameState(GameStateOverride):
    """Gamestate for a single VOID CHRONOS spin."""

    def run_spin(self, sim: int, simulation_seed=None):
        self.reset_seed(sim)
        self.repeat = True
        while self.repeat:
            self.reset_book()
            self.draw_board()
            self.apply_portal_wilds()

            self.get_scatterpays_update_wins()
            self.emit_tumble_win_events()

            while self.win_data["totalWin"] > 0 and not self.wincap_triggered:
                self.tumble_game_board()
                self.apply_portal_wilds()
                self.get_scatterpays_update_wins()
                self.emit_tumble_win_events()

            self.set_end_tumble_event()
            self.win_manager.update_gametype_wins(self.gametype)

            if self.check_fs_condition() and self.check_freespin_entry():
                self.run_freespin_from_base()

            self.evaluate_finalwin()
            self.check_repeat()

        self.imprint_wins()

    def run_freespin(self):
        self.reset_fs_spin()
        while self.fs < self.tot_fs and not self.wincap_triggered:
            self.update_freespin()

            # Draw without emitting yet: guaranteed-orb forcing (Void Gates / Chronos
            # Storm / wincap bucket) must land on the board before the reveal event
            # is recorded, so the frontend book shows the true starting grid.
            self.draw_board(emit_event=False)
            self.apply_guaranteed_orbs()
            reveal_event(self)

            self.apply_portal_wilds()
            orb_triggered = self.apply_orb_collector()
            self.get_scatterpays_update_wins()
            self.emit_tumble_win_events()

            while (self.win_data["totalWin"] > 0 or orb_triggered) and not self.wincap_triggered:
                self.tumble_game_board()
                self.apply_portal_wilds()
                orb_triggered = self.apply_orb_collector()
                self.get_scatterpays_update_wins()
                self.emit_tumble_win_events()

            self.set_end_tumble_event()
            self.win_manager.update_gametype_wins(self.gametype)

            if self.check_fs_condition():
                self.update_fs_retrigger_amt()

        self.end_freespin()
