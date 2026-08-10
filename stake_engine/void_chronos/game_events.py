"""Custom book events for VOID CHRONOS's unique mechanics (Portal Wild, Orb Collector)."""

PORTAL_WILD_INFO = "portalWildInfo"
ORB_COLLECTOR_INFO = "orbCollectorInfo"


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
    }
    gamestate.book.add_event(event)
