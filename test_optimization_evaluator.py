"""Regression test for the v2.3 periodic read-only optimization evaluator.

The test deliberately verifies decision logic without starting a background
thread and without changing RAN state.
"""

from copy import deepcopy

from app.optimization_evaluator import (
    PeriodicOptimizationEvaluator,
    build_optimization_recommendation,
    inject_optimization_widget,
)
from app.ran_engine import (
    build_baseline_sites,
    build_candidate_sites,
)


TARGET = "CELL-JES-A-N78"


def make_cell(
    prb=40.0,
    rsrp=-85.0,
    sinr=15.0,
    users=50,
):
    return {
        "cell_id": TARGET,
        "site_id": "SITE-JESENICE-01",
        "sector_id": "SECTOR-A",
        "technology": "5G",
        "band": "n78",
        "bandwidth_mhz": 60,
        "prb_utilization_pct": prb,
        "rsrp_dbm": rsrp,
        "sinr_db": sinr,
        "active_users": users,
    }


def make_observation(
    cell,
    *,
    active_sites=None,
    recovery_sites=None,
    fault_state=None,
    steering_mode="LOAD_AWARE",
):
    if recovery_sites is None:
        recovery_sites = build_baseline_sites()

    if active_sites is None:
        active_sites = deepcopy(recovery_sites)

    return {
        "active_version": "CONFIG-1.0",
        "recovery_target_version": "CONFIG-1.0",
        "rollout_state": "STABLE",
        "last_action": "TEST",
        "fault_state": deepcopy(fault_state),
        "steering_mode": steering_mode,
        "snapshot": {
            "cells": {
                cell["cell_id"]: deepcopy(cell),
            }
        },
        "active_sites": deepcopy(active_sites),
        "recovery_target_sites": deepcopy(recovery_sites),
    }


def expect(label, condition):
    print(f"{label}: {'PASS' if condition else 'FAIL'}")
    assert condition, label


def main():
    print("=" * 92)
    print("V2.3 PERIODIC OPTIMIZATION EVALUATOR REGRESSION TEST")
    print("=" * 92)

    healthy = build_optimization_recommendation(
        make_observation(make_cell())
    )
    expect(
        "Healthy RAN returns NO_ACTION",
        healthy["ran_state"] == "HEALTHY"
        and healthy["recommended_action"] == "NO_ACTION",
    )

    capacity = build_optimization_recommendation(
        make_observation(make_cell(prb=96.0))
    )
    expect(
        "Capacity congestion selects cell-specific traffic steering",
        capacity["ran_state"] == "CAPACITY_CONGESTION"
        and capacity["target_cell"] == TARGET
        and capacity["recommended_action"] == "TRAFFIC_STEERING"
        and TARGET in capacity["proposed_change"]
        and "CAPACITY_RECOVERY" in capacity["proposed_change"],
    )

    recovery_sites = build_baseline_sites()
    active_sites = build_candidate_sites(
        base_sites=recovery_sites,
        cell_updates={
            TARGET: {
                "tx_power_dbm": 30.0,
            }
        },
    )

    rf_fault = build_optimization_recommendation(
        make_observation(
            make_cell(rsrp=-112.0, sinr=12.0, prb=35.0),
            active_sites=active_sites,
            recovery_sites=recovery_sites,
            fault_state={
                "active": True,
                "type": "TX_POWER_DROP",
                "cell_ids": [TARGET],
                "tx_power_dbm": 30.0,
            },
        )
    )
    expect(
        "Injected RF fault recommends exact known-good TX restore",
        rf_fault["ran_state"] == "RF_DEGRADATION"
        and rf_fault["target_cell"] == TARGET
        and rf_fault["recommended_action"]
        == "RESTORE_KNOWN_GOOD_TX_POWER"
        and rf_fault["current_value"] == 30.0
        and rf_fault["target_value"] > rf_fault["current_value"],
    )

    coverage = build_optimization_recommendation(
        make_observation(
            make_cell(rsrp=-110.0, sinr=12.0, prb=42.0)
        )
    )
    expect(
        "Weak coverage recommends a guarded +3 dB TX candidate",
        coverage["ran_state"] == "RF_COVERAGE_DEGRADATION"
        and coverage["recommended_action"] == "INCREASE_TX_POWER"
        and coverage["delta"] == 3.0,
    )

    interference = build_optimization_recommendation(
        make_observation(
            make_cell(rsrp=-80.0, sinr=0.0, prb=45.0)
        )
    )
    expect(
        "Strong RSRP plus poor SINR recommends tilt evaluation only",
        interference["ran_state"] == "RF_INTERFERENCE_SUSPECTED"
        and interference["recommended_action"]
        == "EVALUATE_ELECTRICAL_DOWNTILT"
        and interference["review"]
        == "ENGINEERING_VALIDATION_REQUIRED",
    )

    class ReadOnlyFakeController:
        def __init__(self, observation):
            self.observation = deepcopy(observation)
            self.read_count = 0

        def get_optimization_observation(self):
            self.read_count += 1
            return deepcopy(self.observation)

    fake = ReadOnlyFakeController(
        make_observation(make_cell(prb=96.0))
    )
    evaluator = PeriodicOptimizationEvaluator(
        fake,
        interval_seconds=60,
    )
    one_shot = evaluator.evaluate_now(trigger="TEST")
    expect(
        "One-shot evaluator is read-only and automatic actuation is disabled",
        fake.read_count == 1
        and one_shot["evaluation_mode"] == "READ_ONLY"
        and one_shot["automatic_actuation"] == "DISABLED"
        and one_shot["actuation_performed"] is False,
    )

    html = inject_optimization_widget(
        '<html><head></head><body><div class="container"></div></body></html>'
    )
    expect(
        "Dashboard widget injects status card and API script",
        "Periodic Optimization Evaluator" in html
        and "/optimization/status" in html
        and "/optimization/evaluate-now" in html,
    )
    # Startup compatibility: the app uses FastAPI lifespan rather than
    # the removed/deprecated add_event_handler path. Importing main must
    # therefore succeed before deployment.
    import app.main as main_module
    expect(
        "FastAPI application imports with lifespan-based evaluator startup",
        main_module.app is not None
        and main_module.optimization_evaluator is not None,
    )

    print("\nOVERALL V2.3.1 OPTIMIZATION EVALUATOR TEST: PASS")


if __name__ == "__main__":
    main()
