"""Fast calibration harness: runs GameState.run_spin() directly (no multiprocessing,
no optimizer) sampling criteria by their quota, to get a quick blended RTP read
without paying the cost of the full run.py pipeline on every iteration."""
import sys
import random
sys.path.insert(0, ".")
from gamestate import GameState
from game_config import GameConfig
from src.wins.win_manager import WinManager

config = GameConfig()

MODE_QUOTAS = {
    "normal": [("0", 0.55), ("basegame", 0.40), ("freegame", 0.0499), ("wincap", 0.0001)],
}

def run(mode, n=3000, seed=1):
    quotas = MODE_QUOTAS[mode]
    names = [q[0] for q in quotas]
    weights = [q[1] for q in quotas]
    rng = random.Random(seed)
    gs = GameState(config)
    gs.betmode = mode
    gs.win_manager = WinManager(config.basegame_type, config.freegame_type, config.wincap)
    total_win = 0.0
    hits = 0
    for sim in range(n):
        gs.criteria = rng.choices(names, weights=weights, k=1)[0]
        gs.run_spin(sim + rng.randrange(10**7))
        total_win += gs.final_win
        if gs.final_win > 0:
            hits += 1
    rtp = total_win / n
    print(f"{mode}: n={n} blended_rtp={rtp*100:.2f}% hit_freq={100*hits/n:.2f}%")

def run_single_criteria(mode, criteria, n=1000, seed=1):
    rng = random.Random(seed)
    gs = GameState(config)
    gs.betmode = mode
    gs.win_manager = WinManager(config.basegame_type, config.freegame_type, config.wincap)
    total_win = 0.0
    for sim in range(n):
        gs.criteria = criteria
        gs.run_spin(sim + rng.randrange(10**7))
        total_win += gs.final_win
    avg = total_win / n
    print(f"{mode}/{criteria}: n={n} avg_win_multiplier={avg:.3f}")
    return avg

if __name__ == "__main__":
    run_single_criteria("normal", "basegame", n=2000)
    run_single_criteria("normal", "freegame", n=300)
    run("normal", n=4000)
