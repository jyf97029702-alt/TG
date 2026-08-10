"""VOID CHRONOS game-specific calculations: Portal Wild, Orb Collector, Orb values."""

import random

from src.executables.executables import Executables
from game_events import send_portal_wild_event, send_orb_collector_event

_EXCLUDED_FROM_PORTAL_TARGET = ("scatter", "portal", "collector", "multiplier", "wild")


class GameCalculations(Executables):
    """Game specific calculations for VOID CHRONOS."""

    # ---- Orb multiplier value roll -----------------------------------------

    def roll_orb_value(self, min_orb: int = None) -> int:
        """Weighted-random orb multiplier value, optionally floored at `min_orb`."""
        items = list(self.config.orb_values.items())
        if min_orb is not None:
            filtered = [(v, w) for v, w in items if v >= min_orb]
            if filtered:
                items = filtered
        values = [v for v, _ in items]
        weights = [w for _, w in items]
        return random.choices(values, weights=weights, k=1)[0]

    def assign_orb_property(self, symbol) -> None:
        """Assign a rolled multiplier value to a freshly drawn ORB ('O') symbol."""
        min_orb = self.get_current_distribution_conditions().get("min_orb")
        value = self.roll_orb_value(min_orb)
        symbol.assign_attribute({"multiplier": value})

    def apply_guaranteed_orbs(self) -> None:
        """
        Force a handful of high-value ORB symbols onto the board (used by
        VOID_GATES / CHRONOS_STORM and the wincap-forcing buckets). Must be
        called after draw_board(emit_event=False) and before the reveal event
        is emitted, so the forced orbs are visible in the book's board state.
        """
        spec = self.get_current_distribution_conditions().get("guaranteed_orbs")
        if not spec:
            return

        lo, hi = spec["count_range"]
        count = random.randint(lo, hi)
        forced_values = list(spec.get("forced_values", []))
        pool_min = spec.get("pool_min")

        # Eligible cells: anything that isn't already a scatter (keep the forced
        # trigger count intact) or an existing orb.
        eligible = []
        for reel in range(self.config.num_reels):
            for row in range(self.config.num_rows[reel]):
                sym = self.board[reel][row]
                if not sym.check_attribute("scatter") and not sym.check_attribute("multiplier"):
                    eligible.append((reel, row))
        random.shuffle(eligible)
        chosen = eligible[:count]

        values = []
        for i in range(len(chosen)):
            if i < len(forced_values):
                values.append(forced_values[i])
            else:
                values.append(self.roll_orb_value(pool_min))
        random.shuffle(values)

        for (reel, row), value in zip(chosen, values):
            sym = self.create_symbol("O")
            sym.assign_attribute({"multiplier": value})
            self.board[reel][row] = sym

        self.get_special_symbols_on_board()

    # ---- Portal Wild ---------------------------------------------------------

    def _neighbors(self, reel: int, row: int) -> list:
        candidates = []
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            r, c = reel + dr, row + dc
            if 0 <= r < self.config.num_reels and 0 <= c < self.config.num_rows[r]:
                candidates.append((r, c))
        return candidates

    def apply_portal_wilds(self) -> bool:
        """
        Convert every Portal ('P') symbol currently on the board, plus 1-3 random
        adjacent non-special neighbours (2-4 cells total), into Wilds. Must run
        after every reveal/tumble and before win evaluation so the new Wilds can
        contribute to that step's wins. Returns True if any conversion happened.
        """
        portal_positions = list(self.special_syms_on_board.get("portal", []))
        if not portal_positions:
            return False

        conversions = []
        for pos in portal_positions:
            reel, row = pos["reel"], pos["row"]
            candidates = [
                (r, c) for r, c in self._neighbors(reel, row)
                if not any(self.board[r][c].check_attribute(a) for a in _EXCLUDED_FROM_PORTAL_TARGET)
            ]
            random.shuffle(candidates)
            extra_n = random.randint(1, min(3, max(1, len(candidates))))
            chosen = candidates[:extra_n]

            converted_positions = [{"reel": reel, "row": row}] + [{"reel": r, "row": c} for r, c in chosen]
            for p in converted_positions:
                self.board[p["reel"]][p["row"]] = self.create_symbol("W")

            conversions.append({"portal": {"reel": reel, "row": row}, "converted": converted_positions})

        self.get_special_symbols_on_board()
        send_portal_wild_event(self, conversions)
        return True

    # ---- Orb Collector ---------------------------------------------------------

    def apply_orb_collector(self) -> bool:
        """
        If a Collector ('C') symbol is present, sum every visible ORB multiplier
        value and add it to the persistent global multiplier, then mark the
        collector + orb symbols to explode (removed on the next tumble). Only
        meaningful during free spins, where ORB/COLLECT symbols can appear.
        Returns True if a collection happened.
        """
        collector_positions = list(self.special_syms_on_board.get("collector", []))
        if not collector_positions:
            return False

        orb_positions = list(self.special_syms_on_board.get("multiplier", []))
        orb_values = [self.board[p["reel"]][p["row"]].get_attribute("multiplier") for p in orb_positions]
        collected_total = sum(orb_values)

        self.global_multiplier += collected_total
        from src.events.events import update_global_mult_event
        update_global_mult_event(self)

        for p in orb_positions + collector_positions:
            self.board[p["reel"]][p["row"]].explode = True

        send_orb_collector_event(self, orb_positions, orb_values, collector_positions, collected_total, self.global_multiplier)
        return True
