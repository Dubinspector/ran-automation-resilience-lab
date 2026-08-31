"""Regression and acceptance tests for the v2.4 network-wide optimizer.

The key acceptance scenario mirrors the dashboard experiment:
CELL-JES-B-N28 is intentionally promoted from 40 to 45 dBm. The optimizer
must not simply compare history; it has to physically re-evaluate bounded
alternatives under one frozen context and recommend a lower TX value only if
that candidate is safe and improves the network-wide objective.
"""

from copy import deepcopy

from app.optimization_evaluator import (
    OBJECTIVE_WEIGHTS,
    PeriodicOptimizationEvaluator,
    build_network_delta,
    inject_optimization_widget,
    objective_gain,
    run_network_optimization_search,
    summarize_network,
)
from app.ran_controller import RanAutomationController
from app.ran_engine import DEFAULT_WEATHER


TARGET = "CELL-JES-B-N28"
SIMULATION_TIMESTAMP = "2026-08-28T12:40:00+02:00"


def expect(label, condition):
    print(f"{label}: {'PASS' if condition else 'FAIL'}")
    assert condition, label


def mini_snapshot(sinr=10.0, rsrp=-90.0, prb=50.0, served=100.0):
    return {
        "service": {
            "requested_active_ues": 100,
            "served_active_ues": int(served),
            "unserved_active_ues": 100 - int(served),
            "served_ratio_pct": served,
        },
        "cells": {
            "CELL-A": {
                "cell_id": "CELL-A",
                "site_id": "SITE-A",
                "sector_id": "SECTOR-A",
                "technology": "5G",
                "band": "n78",
                "bandwidth_mhz": 60,
                "prb_utilization_pct": prb,
                "sinr_db": sinr,
                "rsrp_dbm": rsrp,
                "active_users": int(served),
                "serviceability_ue_mix": {
                    "HEALTHY": int(served),
                    "DEGRADED": 0,
                    "UNSERVED": 100 - int(served),
                },
            }
        },
    }


def main():
    print("=" * 100)
    print("V2.4 NETWORK-WIDE READ-ONLY OPTIMIZATION REGRESSION / ACCEPTANCE TEST")
    print("=" * 100)

    baseline = summarize_network(
        mini_snapshot(sinr=10.0, rsrp=-90.0, prb=50.0)
    )
    improved = summarize_network(
        mini_snapshot(sinr=10.5, rsrp=-89.8, prb=47.0)
    )
    delta = build_network_delta(baseline, improved)
    gain, components = objective_gain(delta, change_magnitude=1.0)

    expect(
        "Network summary exposes weighted RF and load KPIs",
        baseline["weighted_sinr_db"] == 10.0
        and baseline["weighted_rsrp_dbm"] == -90.0
        and baseline["max_prb_pct"] == 50.0,
    )

    expect(
        "Transparent objective rewards safer network-wide improvement",
        gain > 0.0
        and components["weighted_sinr"] > 0.0
        and components["max_prb"] > 0.0
        and OBJECTIVE_WEIGHTS["weighted_sinr_db"] > 0.0,
    )

    # -----------------------------------------------------
    # REAL LAB ACCEPTANCE SCENARIO
    # -----------------------------------------------------
    controller = RanAutomationController(
        simulation_timestamp=SIMULATION_TIMESTAMP,
        traffic_multiplier=0.25,
        steering_mode="LOAD_AWARE",
    )

    before_version = controller.active_version

    apply_result = controller.guarded_apply(
        cell_updates={
            TARGET: {
                "tx_power_dbm": 45.0,
            }
        },
        weather=deepcopy(DEFAULT_WEATHER),
        simulation_timestamp=SIMULATION_TIMESTAMP,
    )

    expect(
        "Intentional CELL-JES-B-N28 40 -> 45 dBm change is accepted by guardrails",
        apply_result.get("status") == "APPLIED"
        and controller.active_version != before_version,
    )

    observation = controller.get_optimization_observation(
        weather=deepcopy(DEFAULT_WEATHER),
        simulation_timestamp=SIMULATION_TIMESTAMP,
    )

    expect(
        "Optimization observation is fresh, versioned and uses one frozen context",
        observation.get("active_version") == controller.active_version
        and observation.get("simulation_timestamp") == SIMULATION_TIMESTAMP
        and observation.get("traffic_multiplier") == 0.25
        and observation.get("steering_mode") == "LOAD_AWARE",
    )

    recommendation = run_network_optimization_search(
        observation,
        max_target_cells=3,
        max_candidate_evaluations=18,
    )

    search = recommendation.get("search_summary", {})

    print("\n--- v2.4 acceptance result ---")
    print("RAN state:", recommendation.get("ran_state"))
    print("Optimization state:", recommendation.get("optimization_state"))
    print("Target:", recommendation.get("target_cell"))
    print("Action:", recommendation.get("recommended_action"))
    print("Proposed change:", recommendation.get("proposed_change"))
    print("Objective gain:", recommendation.get("objective_gain"))
    print("Predicted effect:", recommendation.get("predicted_network_effect"))
    print("Search summary:", search)

    expect(
        "Complete configured-cell inventory is screened before bounded candidate search",
        search.get("configured_cells_scanned", 0) >= 54
        and search.get("candidates_evaluated", 0) > 0,
    )

    expect(
        "45 dBm safe-but-suboptimal state produces a model-based optimization opportunity",
        recommendation.get("optimization_state") == "OPPORTUNITY_FOUND"
        and recommendation.get("target_cell") == TARGET
        and recommendation.get("parameter") == "tx_power_dbm"
        and float(recommendation.get("current_value")) == 45.0
        and float(recommendation.get("target_value")) < 45.0
        and float(recommendation.get("objective_gain")) > 0.0,
    )

    expect(
        "Recommendation is justified by network simulation rather than rollback history",
        "selected by simulated network outcome" in recommendation.get("reason", "")
        and recommendation.get("guardrail_verdict") == "PASS"
        and bool(recommendation.get("predicted_network_effect")),
    )

    class FixedObservationController:
        def __init__(self, fixed_observation):
            self.fixed_observation = deepcopy(fixed_observation)
            self.read_count = 0

        def get_optimization_observation(self):
            self.read_count += 1
            return deepcopy(self.fixed_observation)

    fake = FixedObservationController(observation)
    evaluator = PeriodicOptimizationEvaluator(
        fake,
        interval_seconds=60,
        max_target_cells=3,
        max_candidate_evaluations=18,
    )
    one_shot = evaluator.evaluate_now(trigger="TEST")

    expect(
        "Periodic evaluator remains read-only and automatic actuation stays disabled",
        fake.read_count == 1
        and one_shot.get("evaluation_mode") == "READ_ONLY_NETWORK_SEARCH"
        and one_shot.get("automatic_actuation") == "DISABLED"
        and one_shot.get("actuation_performed") is False,
    )

    html = inject_optimization_widget(
        '<html><head></head><body><div class="container"></div></body></html>'
    )
    expect(
        "Dashboard exposes optimization state, objective gain and search coverage",
        "Network-wide Optimization Evaluator" in html
        and "Optimization state" in html
        and "Objective gain" in html
        and "Search coverage" in html
        and "/optimization/evaluate-now" in html,
    )

    import app.main as main_module
    expect(
        "FastAPI v2.4 imports with lifespan-based optimizer startup",
        main_module.app is not None
        and main_module.optimization_evaluator is not None,
    )

    print("\nOVERALL V2.4 NETWORK OPTIMIZATION TEST: PASS")


if __name__ == "__main__":
    main()
