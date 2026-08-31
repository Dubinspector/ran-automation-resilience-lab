"""Focused regression tests for the v2.6 AI-gated control safety supervisor."""

from copy import deepcopy

from app.ai_control_loop import AIControlSupervisor


def expect(label, condition):
    print(f"{label}: {'PASS' if condition else 'FAIL'}")
    assert condition, label


def opportunity_result(parameter="tx_power_dbm", action="REDUCE_TX_POWER"):
    return {
        "evaluation_id": "OPT-TEST",
        "timestamp": "2026-08-31T10:00:00+00:00",
        "evaluation_mode": "READ_ONLY_NETWORK_SEARCH",
        "automatic_actuation": "DISABLED",
        "actuation_performed": False,
        "ran_state": "HEALTHY",
        "optimization_state": "OPPORTUNITY_FOUND",
        "active_version": "CONFIG-1.0",
        "target_cell": "CELL-JES-B-N28",
        "target_antenna": "ANT-JES-B",
        "recommended_action": action,
        "proposed_change": "synthetic test change",
        "parameter": parameter,
        "current_value": 45.0 if parameter == "tx_power_dbm" else 4.0,
        "target_value": 40.0 if parameter == "tx_power_dbm" else 5.0,
        "delta": -5.0 if parameter == "tx_power_dbm" else 1.0,
        "objective_gain": 4.2,
        "guardrail_verdict": "PASS",
        "review": "GUARDED_APPLY_REQUIRED",
        "evidence": {
            "cell_id": "CELL-JES-B-N28",
            "sinr_db": 12.0,
            "prb_utilization_pct": 50.0,
        },
        "baseline_summary": {"served_ratio_pct": 100.0},
        "predicted_network_effect": {
            "weighted_sinr_db": 0.5,
            "aggregate_prb_pp": -1.2,
            "served_ratio_pp": 0.0,
        },
        "cell_impact": [],
        "candidate_ranking": [],
        "search_summary": {
            "configured_cells_scanned": 54,
            "candidates_evaluated": 8,
        },
        "context": {
            "weather": {
                "timestamp": "2026-08-31T10:00:00+00:00",
                "source": "TEST",
            },
            "simulation_timestamp": "2026-08-31T12:00:00+02:00",
            "traffic_multiplier": 0.25,
            "steering_mode": "LOAD_AWARE",
        },
    }


def no_action_result():
    result = opportunity_result()
    result.update({
        "optimization_state": "NO_MEANINGFUL_GAIN",
        "recommended_action": "NO_ACTION",
        "parameter": None,
        "target_value": None,
        "objective_gain": 0.0,
        "guardrail_verdict": None,
    })
    return result


class FakeOptimizer:
    def __init__(self, results):
        self.results = [deepcopy(r) for r in results]
        self.calls = 0

    def evaluate_now(self, trigger="MANUAL"):
        self.calls += 1
        if len(self.results) > 1:
            result = self.results.pop(0)
        else:
            result = self.results[0]
        result = deepcopy(result)
        result["evaluation_id"] = f"OPT-{self.calls:06d}"
        result["trigger"] = trigger
        return result


class FakeAdvisor:
    def __init__(self, decision="APPROVE", status="AVAILABLE", risk="LOW", confidence="HIGH"):
        self.decision = decision
        self.status = status
        self.risk = risk
        self.confidence = confidence
        self.calls = 0

    def analyze(self, advisor_input, force=False):
        self.calls += 1
        if self.status != "AVAILABLE":
            return {
                "status": self.status,
                "assessment": None,
                "optimizer_decision": deepcopy(advisor_input.get("candidate_result") or {}),
            }
        return {
            "status": "AVAILABLE",
            "assessment": {
                "control_decision": self.decision,
                "risk_level": self.risk,
                "confidence": self.confidence,
                "decision_reason": "synthetic test decision",
            },
            "optimizer_decision": deepcopy(advisor_input.get("candidate_result") or {}),
        }


class FakeController:
    def __init__(self, apply_status="APPLIED"):
        self.health_status = "PASS"
        self.apply_status = apply_status
        self.apply_calls = 0
        self.restore_calls = 0
        self.version = 0
        self.sites = {"SITE": {"value": 1}}

    def get_active_state(self):
        return {"active_version": f"CONFIG-1.{self.version}"}

    def get_active_sites(self):
        return deepcopy(self.sites)

    def get_baseline_health(self):
        return {
            "status": self.health_status,
            "baseline_health": {
                "status": self.health_status,
                "guardrails": {"verdict": "PASS" if self.health_status == "PASS" else "FAIL"},
            },
        }

    def guarded_apply(self, cell_updates=None, antenna_updates=None, weather=None, simulation_timestamp=None):
        self.apply_calls += 1
        if self.apply_status == "APPLIED":
            previous = f"CONFIG-1.{self.version}"
            self.version += 1
            self.sites = {
                "SITE": {
                    "value": self.version + 1,
                    "cell_updates": deepcopy(cell_updates),
                    "antenna_updates": deepcopy(antenna_updates),
                }
            }
            return {
                "status": "APPLIED",
                "previous_version": previous,
                "active_version": f"CONFIG-1.{self.version}",
            }
        if self.apply_status == "ROLLED_BACK":
            return {
                "status": "ROLLED_BACK",
                "active_version": f"CONFIG-1.{self.version}",
                "guardrails": {"verdict": "FAIL"},
            }
        if self.apply_status == "BLOCKED":
            return {"status": "BLOCKED"}
        return {"status": self.apply_status}

    def restore_safety_checkpoint(self, checkpoint_sites, checkpoint_label=None, weather=None, simulation_timestamp=None):
        self.restore_calls += 1
        self.version += 1
        self.sites = deepcopy(checkpoint_sites)
        return {
            "status": "RESTORED",
            "active_version": f"CONFIG-1.{self.version}",
            "checkpoint_label": checkpoint_label,
            "rollback_verified": True,
        }


def supervisor(controller, optimizer, advisor, threshold=5):
    return AIControlSupervisor(
        controller=controller,
        optimizer_evaluator=optimizer,
        ai_advisor=advisor,
        alarm_provider=lambda: [],
        enabled=True,
        interval_seconds=60,
        bad_decision_threshold=threshold,
    )


def main():
    print("=" * 96)
    print("V2.6 AI-GATED CONTROL SAFETY SUPERVISOR REGRESSION / ACCEPTANCE TEST")
    print("=" * 96)

    # 1. Happy path: exact candidate applied, then accepted only after the
    # next observation cycle remains healthy.
    ctl = FakeController()
    sup = supervisor(
        ctl,
        FakeOptimizer([opportunity_result(), no_action_result()]),
        FakeAdvisor(decision="APPROVE"),
    )
    first = sup.run_cycle()
    expect(
        "AI APPROVE can only reach deterministic guarded_apply",
        first["status"] == "APPLIED_PENDING_VERIFICATION"
        and ctl.apply_calls == 1
        and first["pending_verification"]["target_value"] == 40.0,
    )
    second = sup.run_cycle()
    expect(
        "Applied change must survive the next observation window before becoming the new healthy checkpoint",
        second["post_change_verification"]["verification"] == "PASS"
        and sup.get_status()["consecutive_bad_ai_outcomes"] == 0
        and sup.get_status()["pending_verification"] is None,
    )

    # 2. Provider unavailable: fail closed for actuation.
    ctl = FakeController()
    sup = supervisor(
        ctl,
        FakeOptimizer([opportunity_result()]),
        FakeAdvisor(status="UNAVAILABLE"),
    )
    result = sup.run_cycle()
    expect(
        "AI provider failure causes no state-changing action",
        result["status"] == "NO_AUTO_ACTION_AI_UNAVAILABLE"
        and ctl.apply_calls == 0,
    )

    # 3. HOLD and high-risk/low-confidence approvals are deterministic no-actuation outcomes.
    ctl = FakeController()
    sup = supervisor(
        ctl,
        FakeOptimizer([opportunity_result()]),
        FakeAdvisor(decision="HOLD"),
    )
    result = sup.run_cycle()
    expect(
        "AI HOLD cannot actuate",
        result["status"] == "NO_AUTO_ACTION_POLICY_GATE"
        and ctl.apply_calls == 0,
    )

    ctl = FakeController()
    sup = supervisor(
        ctl,
        FakeOptimizer([opportunity_result()]),
        FakeAdvisor(decision="APPROVE", risk="HIGH", confidence="HIGH"),
    )
    result = sup.run_cycle()
    expect(
        "Deterministic policy gate blocks APPROVE with HIGH AI risk",
        result["status"] == "NO_AUTO_ACTION_POLICY_GATE"
        and "AI_RISK_HIGH" in result["policy_gate"]["reasons"]
        and ctl.apply_calls == 0,
    )

    # 4. Traffic steering is deliberately not in the v2.6 automatic actuator allowlist.
    ctl = FakeController()
    steering = opportunity_result(parameter="steering_mode", action="TRAFFIC_STEERING")
    steering["current_value"] = "LOAD_AWARE"
    steering["target_value"] = "CAPACITY_RECOVERY"
    sup = supervisor(
        ctl,
        FakeOptimizer([steering]),
        FakeAdvisor(decision="APPROVE"),
    )
    result = sup.run_cycle()
    expect(
        "Automatic v2.6 actuation is restricted to bounded RF configuration parameters",
        result["status"] == "NO_AUTO_ACTION_POLICY_GATE"
        and "ACTUATOR_NOT_AUTO_ALLOWED" in result["policy_gate"]["reasons"]
        and ctl.apply_calls == 0,
    )

    # 5. A change that is healthy immediately but unhealthy at the next cycle
    # is force-rolled back to the pre-change verified checkpoint.
    ctl = FakeController()
    sup = supervisor(
        ctl,
        FakeOptimizer([opportunity_result()]),
        FakeAdvisor(decision="APPROVE"),
    )
    first = sup.run_cycle()
    expect("Pending verification created", first["status"] == "APPLIED_PENDING_VERIFICATION")
    ctl.health_status = "FAIL"
    second = sup.run_cycle()
    expect(
        "Unhealthy post-change observation forces checkpoint rollback and one bad-AI strike",
        second["status"] == "POST_CHANGE_ROLLBACK"
        and ctl.restore_calls == 1
        and sup.get_status()["consecutive_bad_ai_outcomes"] == 1,
    )

    # 6. Five consecutive AI-approved candidates that fail guarded_apply open
    # the circuit breaker. Each bad outcome is already rolled back by guarded_apply.
    ctl = FakeController(apply_status="ROLLED_BACK")
    sup = supervisor(
        ctl,
        FakeOptimizer([opportunity_result()]),
        FakeAdvisor(decision="APPROVE"),
        threshold=5,
    )
    for _ in range(5):
        result = sup.run_cycle()
    status = sup.get_status()
    expect(
        "Five consecutive bad AI-approved outcomes open the circuit breaker",
        result["status"] == "GUARDED_APPLY_ROLLED_BACK"
        and status["consecutive_bad_ai_outcomes"] == 5
        and status["circuit_state"] == "OPEN",
    )
    before = ctl.apply_calls
    blocked = sup.run_cycle()
    expect(
        "Open circuit keeps optimizer observable but disables further AI-gated actuation",
        blocked["status"] == "CIRCUIT_OPEN_READ_ONLY"
        and ctl.apply_calls == before,
    )

    # 7. Manual circuit reset is only accepted from a healthy current RAN.
    ctl.health_status = "FAIL"
    reset = sup.reset_circuit_breaker()
    expect(
        "Circuit reset is blocked while RAN is unhealthy",
        reset["status"] == "RESET_BLOCKED_RAN_UNHEALTHY"
        and sup.get_status()["circuit_state"] == "OPEN",
    )
    ctl.health_status = "PASS"
    reset = sup.reset_circuit_breaker()
    expect(
        "Healthy manual reset closes circuit and clears strike count",
        reset["status"] == "RESET"
        and sup.get_status()["circuit_state"] == "CLOSED"
        and sup.get_status()["consecutive_bad_ai_outcomes"] == 0,
    )

    print("\nOVERALL V2.6 AI CONTROL SUPERVISOR TEST: PASS")


if __name__ == "__main__":
    main()
