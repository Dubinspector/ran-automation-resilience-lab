"""
Bounded AI-gated closed loop for the synthetic RAN learning lab.

Safety model
------------
The AI model never chooses RF values and never calls a state-changing RAN
method. The deterministic optimizer first computes the best safe candidate.
The AI returns only APPROVE / HOLD / ABSTAIN plus engineering interpretation.
A deterministic supervisor may then submit the exact optimizer candidate
through guarded_apply().

A change is not considered fully trusted immediately after guarded_apply().
The supervisor keeps the previous verified-healthy controller snapshot as a
safety checkpoint and verifies the applied change again on the next control
cycle. If the active RAN becomes unhealthy during that verification window,
the supervisor force-restores the checkpoint through the controller's
separately authorized safety rollback path.

Five consecutive AI-approved changes that produce a bad actuation outcome
open a circuit breaker. The fifth failure is rolled back like the previous
ones, automatic AI-gated actuation stops, and a manual reset is required.

Provider unavailability, timeout, malformed AI output, HOLD and ABSTAIN do
not count as bad AI instructions because no state-changing action is taken.
They fail closed for actuation while the deterministic optimizer remains
available for observation.
"""

from copy import deepcopy
from datetime import datetime, timezone
import time
from threading import Event, Lock, RLock, Thread

from app.ai_advisor import build_ai_advisor_input


AI_CONTROL_MODE = "AI_GATED_DETERMINISTIC_ACTUATION"
DIRECT_AI_ACTUATION = "DISABLED"
DEFAULT_INTERVAL_SECONDS = 60.0
DEFAULT_BAD_DECISION_THRESHOLD = 5
HISTORY_LIMIT = 25

_ALLOWED_PARAMETERS = {
    "tx_power_dbm",
    "electrical_tilt_deg",
}

_ALLOWED_ACTIONS = {
    "REDUCE_TX_POWER",
    "INCREASE_TX_POWER",
    "RESTORE_KNOWN_GOOD_TX_POWER",
    "INCREASE_ELECTRICAL_DOWNTILT",
    "REDUCE_ELECTRICAL_DOWNTILT",
}


def _utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


def _number(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _health_status(observation):
    observation = observation or {}
    return (
        observation.get("status")
        or (observation.get("baseline_health") or {}).get("status")
    )


class AIControlSupervisor:
    """Single-process, non-overlapping, safety-supervised AI control loop."""

    def __init__(
        self,
        controller,
        optimizer_evaluator,
        ai_advisor,
        alarm_provider=None,
        enabled=False,
        interval_seconds=DEFAULT_INTERVAL_SECONDS,
        bad_decision_threshold=DEFAULT_BAD_DECISION_THRESHOLD,
    ):
        self._controller = controller
        self._optimizer = optimizer_evaluator
        self._ai_advisor = ai_advisor
        self._alarm_provider = alarm_provider or (lambda: [])
        self._enabled = bool(enabled)
        self._interval_seconds = max(30.0, float(interval_seconds))
        self._bad_decision_threshold = max(1, int(bad_decision_threshold))

        self._state_lock = RLock()
        self._cycle_lock = Lock()
        self._stop_event = Event()
        self._thread = None
        self._running = False

        self._cycle_counter = 0
        self._history = []
        self._last_cycle = None
        self._last_verified_checkpoint = None
        self._pending_verification = None
        self._consecutive_bad_ai_outcomes = 0
        self._circuit_state = "CLOSED"
        self._circuit_reason = None

    @property
    def enabled(self):
        return self._enabled

    @property
    def interval_seconds(self):
        return self._interval_seconds

    def start(self):
        if not self._enabled:
            return

        with self._state_lock:
            if self._running:
                return
            self._stop_event.clear()
            self._running = True
            self._thread = Thread(
                target=self._worker,
                name="ran-ai-control-supervisor",
                daemon=True,
            )
            self._thread.start()

    def stop(self):
        with self._state_lock:
            self._running = False
            self._stop_event.set()
            thread = self._thread

        if thread and thread.is_alive():
            thread.join(timeout=2.0)

    def _worker(self):
        # Do not make a state-changing decision immediately at application
        # startup. First establish a baseline/checkpoint, then wait one full
        # configured observation interval before the first autonomous cycle.
        self._initialize_checkpoint_if_healthy()

        next_deadline = time.monotonic() + self._interval_seconds

        while True:
            wait_seconds = max(0.0, next_deadline - time.monotonic())
            if self._stop_event.wait(wait_seconds):
                break

            cycle_started = time.monotonic()
            self.run_cycle(trigger="PERIODIC")
            elapsed = time.monotonic() - cycle_started

            with self._state_lock:
                if self._last_cycle is not None:
                    self._last_cycle["duration_seconds"] = round(elapsed, 3)
                    self._last_cycle["interval_overrun"] = (
                        elapsed > self._interval_seconds
                    )

            if elapsed > self._interval_seconds:
                # Never overlap or launch a catch-up storm. A cycle that takes
                # longer than the configured period is itself evidence that
                # the observation interval should be increased.
                next_deadline = time.monotonic() + self._interval_seconds
            else:
                # Fixed start-to-start cadence: e.g. a 20 s cycle with a 60 s
                # period sleeps roughly 40 s before the next cycle.
                next_deadline += self._interval_seconds

    def _active_version(self):
        try:
            return self._controller.get_active_state().get("active_version")
        except Exception:
            return None

    def _capture_checkpoint(self, source):
        checkpoint = {
            "captured_at": _utc_now_iso(),
            "source": source,
            "active_version": self._active_version(),
            "sites": self._controller.get_active_sites(),
        }
        with self._state_lock:
            self._last_verified_checkpoint = deepcopy(checkpoint)
        return checkpoint

    def _initialize_checkpoint_if_healthy(self):
        try:
            health = self._controller.get_baseline_health()
        except Exception:
            return None

        if _health_status(health) == "PASS":
            return self._capture_checkpoint("STARTUP_HEALTHY_BASELINE")
        return None

    def _record_cycle(self, result):
        with self._state_lock:
            self._cycle_counter += 1
            enriched = {
                "cycle_id": f"AICTL-{self._cycle_counter:06d}",
                "timestamp": _utc_now_iso(),
                **deepcopy(result),
            }
            self._last_cycle = deepcopy(enriched)
            self._history.append(deepcopy(enriched))
            self._history = self._history[-HISTORY_LIMIT:]
            return deepcopy(enriched)

    def _open_circuit(self, reason):
        with self._state_lock:
            self._circuit_state = "OPEN"
            self._circuit_reason = str(reason)

    def _register_bad_ai_outcome(self, reason):
        with self._state_lock:
            self._consecutive_bad_ai_outcomes += 1
            count = self._consecutive_bad_ai_outcomes

        if count >= self._bad_decision_threshold:
            self._open_circuit(
                f"BAD_AI_OUTCOME_THRESHOLD_REACHED: {reason}"
            )
        return count

    def _register_verified_success(self):
        with self._state_lock:
            self._consecutive_bad_ai_outcomes = 0

    def _force_restore_checkpoint(self, reason):
        with self._state_lock:
            checkpoint = deepcopy(self._last_verified_checkpoint)

        if not checkpoint:
            self._open_circuit("NO_VERIFIED_HEALTHY_CHECKPOINT_AVAILABLE")
            return {
                "status": "ROLLBACK_UNAVAILABLE",
                "reason": reason,
                "rollback_verified": False,
            }

        restore = self._controller.restore_safety_checkpoint(
            checkpoint_sites=checkpoint["sites"],
            checkpoint_label=checkpoint.get("active_version"),
        )

        if not restore.get("rollback_verified"):
            self._open_circuit("SAFETY_ROLLBACK_DID_NOT_RESTORE_HEALTH")

        return {
            "status": "ROLLBACK_COMPLETED",
            "reason": reason,
            "checkpoint_version": checkpoint.get("active_version"),
            "restore": restore,
            "rollback_verified": bool(restore.get("rollback_verified")),
        }

    def _verify_pending_change(self):
        with self._state_lock:
            pending = deepcopy(self._pending_verification)

        if not pending:
            return None

        try:
            health = self._controller.get_baseline_health()
        except Exception as exc:
            rollback = self._force_restore_checkpoint(
                f"POST_CHANGE_VERIFICATION_ERROR:{type(exc).__name__}"
            )
            count = self._register_bad_ai_outcome(
                "post-change health verification errored"
            )
            with self._state_lock:
                self._pending_verification = None
            return {
                "verification": "ERROR",
                "bad_ai_outcome_count": count,
                "rollback": rollback,
                "error_type": type(exc).__name__,
            }

        if _health_status(health) == "PASS":
            self._capture_checkpoint("POST_CHANGE_VERIFIED_HEALTHY")
            self._register_verified_success()
            with self._state_lock:
                self._pending_verification = None
            return {
                "verification": "PASS",
                "verified_change": pending,
                "bad_ai_outcome_count": 0,
            }

        rollback = self._force_restore_checkpoint(
            "POST_CHANGE_RAN_UNHEALTHY"
        )
        count = self._register_bad_ai_outcome(
            "AI-approved change became unhealthy during observation window"
        )
        with self._state_lock:
            self._pending_verification = None

        return {
            "verification": "FAIL",
            "verified_change": pending,
            "health": deepcopy(health),
            "bad_ai_outcome_count": count,
            "rollback": rollback,
        }

    def _policy_gate(self, optimization, assessment):
        reasons = []

        if optimization.get("ran_state") != "HEALTHY":
            reasons.append("RAN_NOT_HEALTHY")
        if optimization.get("optimization_state") != "OPPORTUNITY_FOUND":
            reasons.append("NO_OPTIMIZATION_OPPORTUNITY")
        if optimization.get("guardrail_verdict") != "PASS":
            reasons.append("OPTIMIZER_GUARDRAIL_NOT_PASS")
        if optimization.get("parameter") not in _ALLOWED_PARAMETERS:
            reasons.append("ACTUATOR_NOT_AUTO_ALLOWED")
        if optimization.get("recommended_action") not in _ALLOWED_ACTIONS:
            reasons.append("ACTION_NOT_AUTO_ALLOWED")
        if optimization.get("target_cell") is None:
            reasons.append("TARGET_CELL_MISSING")
        if optimization.get("target_value") is None:
            reasons.append("TARGET_VALUE_MISSING")
        if _number(optimization.get("objective_gain"), 0.0) <= 0.0:
            reasons.append("NON_POSITIVE_OBJECTIVE_GAIN")

        if assessment.get("control_decision") != "APPROVE":
            reasons.append(
                f"AI_DECISION_{assessment.get('control_decision') or 'MISSING'}"
            )
        if assessment.get("risk_level") == "HIGH":
            reasons.append("AI_RISK_HIGH")
        if assessment.get("confidence") == "LOW":
            reasons.append("AI_CONFIDENCE_LOW")

        # Explicitly fail closed on critical alarms. The advisor sees the
        # alarm evidence too, but the deterministic supervisor enforces this
        # independently from model judgement.
        try:
            alarms = list(self._alarm_provider() or [])
        except Exception:
            alarms = []
        if any(str(a.get("severity", "")).upper() == "CRITICAL" for a in alarms):
            reasons.append("CRITICAL_ALARM_ACTIVE")

        return {
            "passed": not reasons,
            "reasons": reasons,
        }

    def _build_apply_updates(self, optimization):
        parameter = optimization.get("parameter")
        target_cell = optimization.get("target_cell")
        target_value = optimization.get("target_value")

        if parameter == "tx_power_dbm":
            return {
                "cell_updates": {
                    target_cell: {"tx_power_dbm": float(target_value)}
                },
                "antenna_updates": {},
            }

        if parameter == "electrical_tilt_deg":
            antenna_id = optimization.get("target_antenna")
            if not antenna_id:
                raise ValueError("Optimizer result is missing target_antenna")
            return {
                "cell_updates": {},
                "antenna_updates": {
                    antenna_id: {"electrical_tilt_deg": float(target_value)}
                },
            }

        raise ValueError(f"Unsupported automatic parameter: {parameter}")

    def run_cycle(self, trigger="MANUAL"):
        if not self._enabled:
            return self._record_cycle({
                "trigger": str(trigger).upper(),
                "status": "DISABLED",
                "actuation_performed": False,
            })

        if not self._cycle_lock.acquire(blocking=False):
            return self._record_cycle({
                "trigger": str(trigger).upper(),
                "status": "SKIPPED_OVERLAPPING_CYCLE",
                "actuation_performed": False,
            })

        started = time.monotonic()
        try:
            verification = self._verify_pending_change()

            if verification and verification.get("verification") in {"FAIL", "ERROR"}:
                result = {
                    "trigger": str(trigger).upper(),
                    "status": "POST_CHANGE_ROLLBACK",
                    "actuation_performed": False,
                    "post_change_verification": verification,
                    "circuit_state": self._circuit_state,
                }
                result["duration_seconds"] = round(time.monotonic() - started, 3)
                return self._record_cycle(result)

            with self._state_lock:
                circuit_state = self._circuit_state

            optimization = self._optimizer.evaluate_now(
                trigger=f"AI_CONTROL_{str(trigger).upper()}"
            )

            if circuit_state == "OPEN":
                result = {
                    "trigger": str(trigger).upper(),
                    "status": "CIRCUIT_OPEN_READ_ONLY",
                    "actuation_performed": False,
                    "post_change_verification": verification,
                    "optimization": optimization,
                    "circuit_state": "OPEN",
                }
                result["duration_seconds"] = round(time.monotonic() - started, 3)
                return self._record_cycle(result)

            # Never ask AI to approve a state-changing action when the
            # deterministic layer has no safe opportunity or the RAN is
            # already unhealthy. This is a deterministic pre-gate.
            if (
                optimization.get("ran_state") != "HEALTHY"
                or optimization.get("optimization_state") != "OPPORTUNITY_FOUND"
                or optimization.get("guardrail_verdict") != "PASS"
            ):
                result = {
                    "trigger": str(trigger).upper(),
                    "status": "NO_AUTO_ACTION_DETERMINISTIC_GATE",
                    "actuation_performed": False,
                    "post_change_verification": verification,
                    "optimization": optimization,
                    "circuit_state": self._circuit_state,
                }
                result["duration_seconds"] = round(time.monotonic() - started, 3)
                return self._record_cycle(result)

            advisor_input = build_ai_advisor_input(
                optimization,
                alarms=self._alarm_provider(),
            )
            ai_result = self._ai_advisor.analyze(
                advisor_input,
                force=True,
            )

            if ai_result.get("status") != "AVAILABLE":
                result = {
                    "trigger": str(trigger).upper(),
                    "status": "NO_AUTO_ACTION_AI_UNAVAILABLE",
                    "actuation_performed": False,
                    "post_change_verification": verification,
                    "optimization": optimization,
                    "ai_result": ai_result,
                    "circuit_state": self._circuit_state,
                }
                result["duration_seconds"] = round(time.monotonic() - started, 3)
                return self._record_cycle(result)

            assessment = deepcopy(ai_result.get("assessment") or {})
            gate = self._policy_gate(optimization, assessment)

            if not gate["passed"]:
                result = {
                    "trigger": str(trigger).upper(),
                    "status": "NO_AUTO_ACTION_POLICY_GATE",
                    "actuation_performed": False,
                    "post_change_verification": verification,
                    "optimization": optimization,
                    "ai_result": ai_result,
                    "policy_gate": gate,
                    "circuit_state": self._circuit_state,
                }
                result["duration_seconds"] = round(time.monotonic() - started, 3)
                return self._record_cycle(result)

            # Capture the exact currently verified healthy configuration as
            # rollback checkpoint before any state-changing call.
            current_health = self._controller.get_baseline_health()
            if _health_status(current_health) != "PASS":
                result = {
                    "trigger": str(trigger).upper(),
                    "status": "NO_AUTO_ACTION_BASELINE_CHANGED",
                    "actuation_performed": False,
                    "post_change_verification": verification,
                    "optimization": optimization,
                    "ai_result": ai_result,
                    "policy_gate": gate,
                    "current_health": current_health,
                    "circuit_state": self._circuit_state,
                }
                result["duration_seconds"] = round(time.monotonic() - started, 3)
                return self._record_cycle(result)

            checkpoint = self._capture_checkpoint(
                f"PRE_AI_APPLY:{optimization.get('evaluation_id')}"
            )

            try:
                updates = self._build_apply_updates(optimization)
            except Exception as exc:
                self._open_circuit(
                    f"CONTROL_MAPPING_ERROR:{type(exc).__name__}"
                )
                result = {
                    "trigger": str(trigger).upper(),
                    "status": "CONTROL_MAPPING_ERROR",
                    "actuation_performed": False,
                    "optimization": optimization,
                    "ai_result": ai_result,
                    "error_type": type(exc).__name__,
                    "circuit_state": self._circuit_state,
                }
                result["duration_seconds"] = round(time.monotonic() - started, 3)
                return self._record_cycle(result)

            context = optimization.get("context") or {}
            apply_result = self._controller.guarded_apply(
                cell_updates=updates["cell_updates"] or None,
                antenna_updates=updates["antenna_updates"] or None,
                weather=deepcopy(context.get("weather") or None),
                simulation_timestamp=context.get("simulation_timestamp"),
            )

            if apply_result.get("status") == "APPLIED":
                # Immediate verification catches gross failures without waiting
                # one full cycle; the next periodic cycle remains the actual
                # post-change observation-window acceptance point.
                immediate_health = self._controller.get_baseline_health()
                if _health_status(immediate_health) != "PASS":
                    rollback = self._force_restore_checkpoint(
                        "IMMEDIATE_POST_APPLY_UNHEALTHY"
                    )
                    count = self._register_bad_ai_outcome(
                        "AI-approved change failed immediate health verification"
                    )
                    result = {
                        "trigger": str(trigger).upper(),
                        "status": "IMMEDIATE_ROLLBACK",
                        "actuation_performed": True,
                        "optimization": optimization,
                        "ai_result": ai_result,
                        "policy_gate": gate,
                        "apply_result": apply_result,
                        "immediate_health": immediate_health,
                        "rollback": rollback,
                        "bad_ai_outcome_count": count,
                        "circuit_state": self._circuit_state,
                    }
                    result["duration_seconds"] = round(time.monotonic() - started, 3)
                    return self._record_cycle(result)

                pending = {
                    "source_evaluation_id": optimization.get("evaluation_id"),
                    "approved_at": _utc_now_iso(),
                    "previous_checkpoint_version": checkpoint.get("active_version"),
                    "applied_version": apply_result.get("active_version"),
                    "target_cell": optimization.get("target_cell"),
                    "target_antenna": optimization.get("target_antenna"),
                    "parameter": optimization.get("parameter"),
                    "current_value": optimization.get("current_value"),
                    "target_value": optimization.get("target_value"),
                    "recommended_action": optimization.get("recommended_action"),
                }
                with self._state_lock:
                    self._pending_verification = deepcopy(pending)

                result = {
                    "trigger": str(trigger).upper(),
                    "status": "APPLIED_PENDING_VERIFICATION",
                    "actuation_performed": True,
                    "optimization": optimization,
                    "ai_result": ai_result,
                    "policy_gate": gate,
                    "apply_result": apply_result,
                    "immediate_health": immediate_health,
                    "pending_verification": pending,
                    "circuit_state": self._circuit_state,
                }
                result["duration_seconds"] = round(time.monotonic() - started, 3)
                return self._record_cycle(result)

            if apply_result.get("status") == "ROLLED_BACK":
                count = self._register_bad_ai_outcome(
                    "AI-approved deterministic candidate failed guarded_apply"
                )
                result = {
                    "trigger": str(trigger).upper(),
                    "status": "GUARDED_APPLY_ROLLED_BACK",
                    "actuation_performed": False,
                    "optimization": optimization,
                    "ai_result": ai_result,
                    "policy_gate": gate,
                    "apply_result": apply_result,
                    "bad_ai_outcome_count": count,
                    "circuit_state": self._circuit_state,
                }
                result["duration_seconds"] = round(time.monotonic() - started, 3)
                return self._record_cycle(result)

            # BLOCKED means the current state changed or became unsafe before
            # actuation; do not blame the AI because the state-changing attempt
            # was never accepted. REJECTED/unexpected statuses indicate a
            # deterministic contract error and open the circuit immediately.
            if apply_result.get("status") == "BLOCKED":
                result = {
                    "trigger": str(trigger).upper(),
                    "status": "GUARDED_APPLY_BLOCKED",
                    "actuation_performed": False,
                    "optimization": optimization,
                    "ai_result": ai_result,
                    "policy_gate": gate,
                    "apply_result": apply_result,
                    "circuit_state": self._circuit_state,
                }
                result["duration_seconds"] = round(time.monotonic() - started, 3)
                return self._record_cycle(result)

            self._open_circuit(
                f"UNEXPECTED_GUARDED_APPLY_STATUS:{apply_result.get('status')}"
            )
            result = {
                "trigger": str(trigger).upper(),
                "status": "CONTROL_CONTRACT_ERROR",
                "actuation_performed": False,
                "optimization": optimization,
                "ai_result": ai_result,
                "policy_gate": gate,
                "apply_result": apply_result,
                "circuit_state": self._circuit_state,
            }
            result["duration_seconds"] = round(time.monotonic() - started, 3)
            return self._record_cycle(result)

        except Exception as exc:
            # Any unexpected control-path exception fails closed. It does not
            # count as a bad AI instruction unless an AI-approved actuation was
            # already classified through one of the explicit paths above.
            self._open_circuit(
                f"SUPERVISOR_ERROR:{type(exc).__name__}"
            )
            result = {
                "trigger": str(trigger).upper(),
                "status": "SUPERVISOR_ERROR_CIRCUIT_OPEN",
                "actuation_performed": False,
                "error_type": type(exc).__name__,
                "circuit_state": "OPEN",
            }
            result["duration_seconds"] = round(time.monotonic() - started, 3)
            return self._record_cycle(result)

        finally:
            self._cycle_lock.release()

    def reset_circuit_breaker(self):
        if not self._enabled:
            return {
                "status": "DISABLED",
                "circuit_state": self._circuit_state,
            }

        health = self._controller.get_baseline_health()
        if _health_status(health) != "PASS":
            return {
                "status": "RESET_BLOCKED_RAN_UNHEALTHY",
                "circuit_state": self._circuit_state,
                "health": health,
            }

        self._capture_checkpoint("MANUAL_CIRCUIT_RESET_HEALTHY_BASELINE")
        with self._state_lock:
            self._circuit_state = "CLOSED"
            self._circuit_reason = None
            self._consecutive_bad_ai_outcomes = 0
            self._pending_verification = None

        return {
            "status": "RESET",
            "circuit_state": "CLOSED",
            "health": health,
        }

    def get_status(self):
        with self._state_lock:
            thread_alive = bool(self._thread and self._thread.is_alive())
            checkpoint = deepcopy(self._last_verified_checkpoint)
            if checkpoint:
                checkpoint.pop("sites", None)

            return {
                "status": (
                    "RUNNING" if self._running
                    else "DISABLED" if not self._enabled
                    else "STOPPED"
                ),
                "enabled": self._enabled,
                "worker_alive": thread_alive,
                "mode": AI_CONTROL_MODE,
                "direct_ai_actuation": DIRECT_AI_ACTUATION,
                "interval_seconds": self._interval_seconds,
                "bad_decision_threshold": self._bad_decision_threshold,
                "consecutive_bad_ai_outcomes": self._consecutive_bad_ai_outcomes,
                "circuit_state": self._circuit_state,
                "circuit_reason": self._circuit_reason,
                "pending_verification": deepcopy(self._pending_verification),
                "last_verified_checkpoint": checkpoint,
                "last_cycle": deepcopy(self._last_cycle),
                "history": deepcopy(self._history[-10:]),
            }


# =========================================================
# DASHBOARD WIDGET
# =========================================================

_AI_CONTROL_STYLE = r"""
<style id="ai-control-style">
#ai-control {
    margin-bottom: 18px;
    padding: 18px;
    border: 1px solid #334155;
    border-radius: 10px;
    background: #111827;
}
#ai-control .ctl-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 10px;
}
#ai-control .ctl-card {
    min-height: 78px;
    padding: 12px;
    border: 1px solid #334155;
    border-radius: 8px;
    background: #1e293b;
}
#ai-control .ctl-label {
    color: #94a3b8;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: .06em;
}
#ai-control .ctl-value {
    margin-top: 6px;
    font-size: 15px;
    font-weight: 700;
    overflow-wrap: anywhere;
}
#ai-control .ctl-title { font-size: 20px; font-weight: 700; margin-bottom: 4px; }
#ai-control .ctl-subtitle { color: #94a3b8; font-size: 13px; margin-bottom: 14px; }
#ai-control .ctl-good { color: #86efac; }
#ai-control .ctl-warn { color: #fdba74; }
#ai-control .ctl-bad { color: #fca5a5; }
</style>
"""

_AI_CONTROL_HTML = r"""
<div id="ai-control">
    <div class="ctl-title">AI Control Safety Supervisor</div>
    <div class="ctl-subtitle">
        One bounded decision per cycle. Exact optimizer candidate only. Guarded apply, post-change verification,
        forced healthy-checkpoint rollback and 5-strike circuit breaker.
    </div>
    <div class="ctl-grid">
        <div class="ctl-card"><div class="ctl-label">Supervisor</div><div id="ctl-status" class="ctl-value">Loading...</div></div>
        <div class="ctl-card"><div class="ctl-label">Cycle interval</div><div id="ctl-interval" class="ctl-value">-</div></div>
        <div class="ctl-card"><div class="ctl-label">Circuit breaker</div><div id="ctl-circuit" class="ctl-value">-</div></div>
        <div class="ctl-card"><div class="ctl-label">Bad AI outcomes</div><div id="ctl-strikes" class="ctl-value">-</div></div>
        <div class="ctl-card"><div class="ctl-label">Pending verification</div><div id="ctl-pending" class="ctl-value">-</div></div>
        <div class="ctl-card"><div class="ctl-label">Last control result</div><div id="ctl-last" class="ctl-value">-</div></div>
        <div class="ctl-card"><div class="ctl-label">Direct AI actuation</div><div id="ctl-direct" class="ctl-value ctl-warn">DISABLED</div></div>
    </div>
</div>
"""

_AI_CONTROL_SCRIPT = r"""
<script id="ai-control-script">
function controlClass(value) {
    if (value === "RUNNING" || value === "CLOSED" || value === "PASS") return "ctl-good";
    if (value === "OPEN" || String(value).includes("ERROR") || String(value).includes("ROLLBACK")) return "ctl-bad";
    return "ctl-warn";
}

async function refreshAIControl() {
    try {
        const response = await fetch("/ai-control/status", { cache: "no-store" });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
        const status = document.getElementById("ctl-status");
        status.textContent = data.status || "-";
        status.className = `ctl-value ${controlClass(data.status)}`;
        document.getElementById("ctl-interval").textContent = `${data.interval_seconds || "-"} s`;
        const circuit = document.getElementById("ctl-circuit");
        circuit.textContent = data.circuit_state || "-";
        circuit.className = `ctl-value ${controlClass(data.circuit_state)}`;
        document.getElementById("ctl-strikes").textContent = `${data.consecutive_bad_ai_outcomes || 0} / ${data.bad_decision_threshold || "-"}`;
        document.getElementById("ctl-pending").textContent = data.pending_verification ? "YES" : "NO";
        document.getElementById("ctl-last").textContent = (data.last_cycle || {}).status || "-";
        document.getElementById("ctl-direct").textContent = data.direct_ai_actuation || "DISABLED";
    }
    catch (error) {
        const status = document.getElementById("ctl-status");
        if (status) {
            status.textContent = `UNAVAILABLE: ${error}`;
            status.className = "ctl-value ctl-bad";
        }
    }
}

refreshAIControl();
setInterval(refreshAIControl, 5000);
</script>
"""


def inject_ai_control_widget(dashboard_html):
    html = str(dashboard_html)
    if "ai-control-style" in html:
        return html

    html = html.replace("</head>", _AI_CONTROL_STYLE + "\n</head>", 1)

    marker = '<div id="ai-advisor">'
    if marker in html:
        html = html.replace(marker, _AI_CONTROL_HTML + "\n" + marker, 1)
    else:
        html = html.replace(
            '<div class="container">',
            '<div class="container">\n\n' + _AI_CONTROL_HTML,
            1,
        )

    html = html.replace("</body>", _AI_CONTROL_SCRIPT + "\n</body>", 1)
    return html
