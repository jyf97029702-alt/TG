"""
Optimization targets per bet-mode / criteria bucket.

NOTE: the per-criteria `rtp` values below are a starting point, not a certified
split. Each mode's bucket RTPs are chosen to sum exactly to that mode's overall
target (0.962, matching the standalone slot_engine.py prototype) -- required by
verify_optimization_input(). The actual post-optimization RTP still depends on
how well the raw simulation batch (num_sim_args in run.py) covers each bucket;
re-run with a much larger simulation count and, if needed, adjust these splits
before treating the output as certification-grade.
"""

from optimization_program.optimization_config import (
    ConstructScaling,
    ConstructParameters,
    ConstructFenceBias,
    ConstructConditions,
    verify_optimization_input,
)


def _params(num_show=3000, num_per_fence=6000, test_spins=None, test_weights=None):
    return ConstructParameters(
        num_show=num_show,
        num_per_fence=num_per_fence,
        min_m2m=4,
        max_m2m=8,
        pmb_rtp=1.0,
        sim_trials=3000,
        test_spins=test_spins or [10, 50, 100],
        test_weights=test_weights or [0.4, 0.4, 0.2],
        score_type="rtp",
        max_trial_dist=15,
    ).return_dict()


class OptimizationSetup:
    """Handle all game mode optimization parameters."""

    def __init__(self, game_config):
        self.game_config = game_config
        wincap = game_config.wincap

        self.game_config.opt_params = {
            "normal": {
                "conditions": {
                    "0": ConstructConditions(rtp=0, av_win=0, search_conditions=0).return_dict(),
                    "basegame": ConstructConditions(rtp=0.450, hr=2.2).return_dict(),
                    "freegame": ConstructConditions(rtp=0.500, hr=120).return_dict(),
                    "wincap": ConstructConditions(rtp=0.012, av_win=wincap, search_conditions=wincap).return_dict(),
                },
                "scaling": ConstructScaling(
                    [
                        {"criteria": "basegame", "scale_factor": 1.2, "win_range": (1, 3), "probability": 1.0},
                        {"criteria": "freegame", "scale_factor": 1.2, "win_range": (5000, wincap), "probability": 1.0},
                    ]
                ).return_dict(),
                "parameters": _params(),
                "distribution_bias": ConstructFenceBias(
                    applied_criteria=["basegame"], bias_ranges=[(1.0, 3.0)], bias_weights=[0.4]
                ).return_dict(),
            },
            "ante_bet": {
                "conditions": {
                    "0": ConstructConditions(rtp=0, av_win=0, search_conditions=0).return_dict(),
                    "basegame": ConstructConditions(rtp=0.450, hr=2.2).return_dict(),
                    "freegame": ConstructConditions(rtp=0.500, hr=40).return_dict(),
                    "wincap": ConstructConditions(rtp=0.012, av_win=wincap, search_conditions=wincap).return_dict(),
                },
                "scaling": ConstructScaling(
                    [
                        {"criteria": "basegame", "scale_factor": 1.2, "win_range": (1, 3), "probability": 1.0},
                        {"criteria": "freegame", "scale_factor": 1.2, "win_range": (5000, wincap), "probability": 1.0},
                    ]
                ).return_dict(),
                "parameters": _params(),
                "distribution_bias": ConstructFenceBias(
                    applied_criteria=["basegame"], bias_ranges=[(1.0, 3.0)], bias_weights=[0.4]
                ).return_dict(),
            },
            "surge": {
                "conditions": {
                    "freegame": ConstructConditions(rtp=0.950, hr="x").return_dict(),
                    "wincap": ConstructConditions(rtp=0.012, av_win=wincap, search_conditions=wincap).return_dict(),
                },
                "scaling": ConstructScaling(
                    [{"criteria": "freegame", "scale_factor": 1.1, "win_range": (100, 2000), "probability": 1.0}]
                ).return_dict(),
                "parameters": _params(test_spins=[8, 20], test_weights=[0.6, 0.4]),
                "distribution_bias": ConstructFenceBias(
                    applied_criteria=["freegame"], bias_ranges=[(30.0, 80.0)], bias_weights=[0.3]
                ).return_dict(),
            },
            "standard_bonus": {
                "conditions": {
                    "freegame": ConstructConditions(rtp=0.950, hr="x").return_dict(),
                    "wincap": ConstructConditions(rtp=0.012, av_win=wincap, search_conditions=wincap).return_dict(),
                },
                "scaling": ConstructScaling(
                    [{"criteria": "freegame", "scale_factor": 1.1, "win_range": (100, 2000), "probability": 1.0}]
                ).return_dict(),
                "parameters": _params(test_spins=[10, 25], test_weights=[0.6, 0.4]),
                "distribution_bias": ConstructFenceBias(
                    applied_criteria=["freegame"], bias_ranges=[(30.0, 80.0)], bias_weights=[0.3]
                ).return_dict(),
            },
            "void_gates": {
                "conditions": {
                    "freegame": ConstructConditions(rtp=0.950, hr="x").return_dict(),
                    "wincap": ConstructConditions(rtp=0.012, av_win=wincap, search_conditions=wincap).return_dict(),
                },
                "scaling": ConstructScaling(
                    [{"criteria": "freegame", "scale_factor": 1.1, "win_range": (500, 5000), "probability": 1.0}]
                ).return_dict(),
                "parameters": _params(test_spins=[10, 25], test_weights=[0.6, 0.4]),
                "distribution_bias": ConstructFenceBias(
                    applied_criteria=["freegame"], bias_ranges=[(80.0, 200.0)], bias_weights=[0.3]
                ).return_dict(),
            },
            "chronos_storm": {
                "conditions": {
                    "freegame": ConstructConditions(rtp=0.900, hr="x").return_dict(),
                    "wincap": ConstructConditions(rtp=0.062, av_win=wincap, search_conditions=wincap).return_dict(),
                },
                "scaling": ConstructScaling(
                    [{"criteria": "freegame", "scale_factor": 1.1, "win_range": (2000, wincap), "probability": 1.0}]
                ).return_dict(),
                "parameters": _params(test_spins=[12, 30], test_weights=[0.6, 0.4]),
                "distribution_bias": ConstructFenceBias(
                    applied_criteria=["freegame"], bias_ranges=[(500.0, 2000.0)], bias_weights=[0.4]
                ).return_dict(),
            },
        }

        verify_optimization_input(self.game_config, self.game_config.opt_params)
