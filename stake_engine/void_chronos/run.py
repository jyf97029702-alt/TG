"""Main file for generating results for VOID CHRONOS (Obsidian Play)."""

from gamestate import GameState
from game_config import GameConfig
from game_optimization import OptimizationSetup
from optimization_program.run_script import OptimizationExecution
from utils.game_analytics.run_analysis import create_stat_sheet
from utils.rgs_verification import execute_all_tests
from src.state.run_sims import create_books
from src.write_data.write_configs import generate_configs

if __name__ == "__main__":

    num_threads = 8
    rust_threads = 8
    batching_size = 1000
    compression = True
    profiling = False

    # NOTE: these counts are a fast sanity-check run, not a certification-grade
    # simulation. Real submission-quality math typically needs 1e5-1e6+ sims
    # per mode so the optimizer has enough diversity to hit RTP/volatility
    # targets precisely -- raise these once the pipeline is verified to work.
    num_sim_args = {
        "normal": int(2e3),
        "ante_bet": int(2e3),
        "surge": int(1e3),
        "standard_bonus": int(1e3),
        "void_gates": int(1e3),
        "chronos_storm": int(1e3),
    }

    run_conditions = {
        "run_sims": True,
        "run_optimization": True,
        "run_analysis": True,
        "run_format_checks": True,
    }
    target_modes = list(num_sim_args.keys())

    config = GameConfig()
    gamestate = GameState(config)
    if run_conditions["run_optimization"] or run_conditions["run_analysis"]:
        optimization_setup_class = OptimizationSetup(config)

    if run_conditions["run_sims"]:
        create_books(
            gamestate,
            config,
            num_sim_args,
            batching_size,
            num_threads,
            compression,
            profiling,
        )

    generate_configs(gamestate)

    if run_conditions["run_optimization"]:
        OptimizationExecution().run_all_modes(config, target_modes, rust_threads)
        generate_configs(gamestate)

    if run_conditions["run_analysis"]:
        custom_keys = [{"symbol": "scatter"}]
        create_stat_sheet(gamestate, custom_keys=custom_keys)

    if run_conditions["run_format_checks"]:
        execute_all_tests(config)
