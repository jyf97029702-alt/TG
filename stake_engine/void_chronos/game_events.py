"""Custom book events for VOID CHRONOS's unique mechanics (Portal Wild, Orb Collector)."""

from src.events.events import json_ready_sym

PORTAL_WILD_INFO = "portalWildInfo"
ORB_COLLECTOR_INFO = "orbCollectorInfo"


def _serialize_board(gamestate) -> list:
    """Same shape/padding-index convention as the sdk's own reveal_event, so the
    frontend can treat these custom events as a full board 'settle' rather than
    having to patch individual cells in place."""
    special_attributes = list(gamestate.config.special_symbols.keys())
    board = []
    for reel, _ in enumerate(gamestate.board):
        board.append([json_ready_sym(gamestate.board[reel][row], special_attributes) for row in range(len(gamestate.board[reel]))])
    return board


def send_portal_wild_event(gamestate, conversions: list) -> None:
    """
    conversions: list of {"portal": {"reel","row"}, "converted": [{"reel","row"}, ...]}
    """
    payload = []
    for c in conversions:
        entry = {
            "portal": {"reel": c["portal"]["reel"], "row": c["portal"]["row"] + 1},
            "converted": [{"reel": p["reel"], "row": p["row"] + 1} for p in c["converted"]],
        }
        payload.append(entry)
    event = {
        "index": len(gamestate.book.events),
        "type": PORTAL_WILD_INFO,
        "conversions": payload,
        "board": _serialize_board(gamestate),
    }
    gamestate.book.add_event(event)


def send_orb_collector_event(gamestate, orb_positions: list, orb_values: list, collector_positions: list, collected_total: int, new_global_mult: int) -> None:
    event = {
        "index": len(gamestate.book.events),
        "type": ORB_COLLECTOR_INFO,
        "orbPositions": [{"reel": p["reel"], "row": p["row"] + 1} for p in orb_positions],
        "orbValues": orb_values,
        "collectorPositions": [{"reel": p["reel"], "row": p["row"] + 1} for p in collector_positions],
        "collectedTotal": int(collected_total),
        "globalMultiplier": int(new_global_mult),
        "board": _serialize_board(gamestate),
    }
    gamestate.book.add_event(event)
