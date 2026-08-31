"""
Periodic read-only RAN optimization evaluator for the learning lab.

Purpose
-------
This module adds a small continuous observe/evaluate loop without adding
fully autonomous state-changing actuation.

Every configured interval the evaluator reads one consistent controller
observation and produces a concrete, cell-level recommendation such as:

- NO_ACTION for a healthy RAN,
- restore known-good TX power for an explicitly injected RF fault,
- switch the overloaded source cell from LOAD_AWARE to
  CAPACITY_RECOVERY steering for capacity congestion,
- evaluate a +3 dB TX-power candidate for weak coverage when SINR and
  capacity headroom remain acceptable,
- evaluate additional electrical downtilt when a strong-serving-signal /
  very-low-SINR pattern suggests interference investigation.

Important safety boundary
-------------------------
The evaluator NEVER applies RAN changes. Automatic actuation is
intentionally disabled. Existing guarded-apply and self-healing workflows
remain the only state-changing paths.

The implementation is intentionally single-process and in-memory for the
learning lab. A production state-changing controller would require durable
state, distributed coordination / leader election, authorization, audit,
idempotency and explicit rollout policies before autonomous actuation.
"""

from copy import deepcopy
from datetime import datetime, timezone
from threading import Event, Lock, RLock, Thread

from app.ran_engine import build_configuration_inventory


PRB_CONGESTION_THRESHOLD_PCT = 85.0
WEAK_RSRP_THRESHOLD_DBM = -105.0
MIN_SINR_FOR_POWER_CANDIDATE_DB = 8.0
STRONG_RSRP_THRESHOLD_DBM = -90.0
POOR_SINR_THRESHOLD_DB = 3.0
TX_POWER_STEP_DB = 3.0
TILT_STEP_DEG = 2.0
MAX_TX_POWER_DBM = 49.0
MAX_ELECTRICAL_TILT_DEG = 12.0
HISTORY_LIMIT = 20


# =========================================================
# SMALL HELPERS
# =========================================================

def _utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


def _number(value, default=0.0):
    try:
        if value is None:
            return float(default)
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _cell_evidence(cell):
    if not cell:
        return {}

    return {
        "cell_id": cell.get("cell_id"),
        "site_id": cell.get("site_id"),
        "sector_id": cell.get("sector_id"),
        "technology": cell.get("technology"),
        "band": cell.get("band"),
        "bandwidth_mhz": cell.get("bandwidth_mhz"),
        "prb_utilization_pct": round(
            _number(cell.get("prb_utilization_pct")),
            1,
        ),
        "rsrp_dbm": round(
            _number(cell.get("rsrp_dbm")),
            1,
        ),
        "sinr_db": round(
            _number(cell.get("sinr_db")),
            1,
        ),
        "active_users": int(
            _number(cell.get("active_users"), 0)
        ),
    }


def _inventory_indexes(sites):
    inventory = build_configuration_inventory(sites)

    cells = {
        item["cell_id"]: item
        for item in inventory.get("cells", [])
    }

    antennas = {
        item["antenna_id"]: item
        for item in inventory.get("antennas", [])
    }

    return cells, antennas


def _active_serving_cells(snapshot):
    return [
        cell
        for cell in snapshot.get("cells", {}).values()
        if int(_number(cell.get("active_users"), 0)) > 0
    ]


def _max_prb_cell(cells):
    if not cells:
        return None

    return max(
        cells,
        key=lambda cell: _number(
            cell.get("prb_utilization_pct"),
            0.0,
        ),
    )


def _worst_rsrp_cell(cells):
    if not cells:
        return None

    return min(
        cells,
        key=lambda cell: _number(
            cell.get("rsrp_dbm"),
            0.0,
        ),
    )


def _interference_candidate(cells):
    candidates = [
        cell
        for cell in cells
        if (
            _number(cell.get("rsrp_dbm"), -999.0)
            >= STRONG_RSRP_THRESHOLD_DBM
            and
            _number(cell.get("sinr_db"), 999.0)
            <= POOR_SINR_THRESHOLD_DB
        )
    ]

    if not candidates:
        return None

    return min(
        candidates,
        key=lambda cell: _number(cell.get("sinr_db"), 999.0),
    )


def _coverage_candidate(cells):
    candidates = [
        cell
        for cell in cells
        if (
            _number(cell.get("rsrp_dbm"), 0.0)
            <= WEAK_RSRP_THRESHOLD_DBM
            and
            _number(cell.get("sinr_db"), -999.0)
            >= MIN_SINR_FOR_POWER_CANDIDATE_DB
            and
            _number(cell.get("prb_utilization_pct"), 100.0)
            < PRB_CONGESTION_THRESHOLD_PCT
        )
    ]

    return _worst_rsrp_cell(candidates)


# =========================================================
# PURE DECISION FUNCTION
# =========================================================

def build_optimization_recommendation(observation):
    """
    Build one read-only recommendation from one consistent observation.

    The function does not modify controller state and does not call any
    state-changing RAN operation.
    """

    snapshot = observation.get("snapshot", {})
    cells_by_id = snapshot.get("cells", {})
    serving_cells = _active_serving_cells(snapshot)
    max_prb = _max_prb_cell(serving_cells)

    active_sites = observation.get("active_sites", {})
    recovery_sites = observation.get("recovery_target_sites", {})

    active_cells, active_antennas = _inventory_indexes(active_sites)
    recovery_cells, _ = _inventory_indexes(recovery_sites)

    fault = observation.get("fault_state") or {}
    fault_active = bool(fault.get("active"))
    fault_type = str(fault.get("type", "")).upper()

    active_version = observation.get("active_version")
    recovery_target_version = observation.get("recovery_target_version")
    steering_mode = str(
        observation.get("steering_mode", "UNKNOWN")
    ).upper()

    # -----------------------------------------------------
    # 1) EXPLICITLY INJECTED RF FAULT
    # -----------------------------------------------------
    # This is the strongest signal because the controller already knows
    # that a separately authorized recovery target exists.
    # -----------------------------------------------------
    if fault_active and fault_type == "TX_POWER_DROP":
        scoped_ids = [
            cell_id
            for cell_id in fault.get("cell_ids", [])
            if cell_id in cells_by_id
        ]

        scoped_cells = [
            cells_by_id[cell_id]
            for cell_id in scoped_ids
        ]

        target = _worst_rsrp_cell(scoped_cells)

        if target is None and scoped_ids:
            target = cells_by_id.get(scoped_ids[0])

        target_id = target.get("cell_id") if target else None
        active_cfg = active_cells.get(target_id, {})
        recovery_cfg = recovery_cells.get(target_id, {})

        current_tx = _number(
            active_cfg.get("tx_power_dbm"),
            fault.get("tx_power_dbm", 0.0),
        )
        known_good_tx = _number(
            recovery_cfg.get("tx_power_dbm"),
            current_tx,
        )
        delta = known_good_tx - current_tx

        proposed = (
            f"{target_id}: TX {current_tx:.1f} -> "
            f"{known_good_tx:.1f} dBm ({delta:+.1f} dB)"
            if target_id
            else "Restore RF TX power to the last accepted known-good state"
        )

        return {
            "ran_state": "RF_DEGRADATION",
            "target_cell": target_id,
            "scope_cells": scoped_ids,
            "evidence": _cell_evidence(target),
            "recommended_action": "RESTORE_KNOWN_GOOD_TX_POWER",
            "proposed_change": proposed,
            "parameter": "tx_power_dbm",
            "current_value": round(current_tx, 1),
            "target_value": round(known_good_tx, 1),
            "delta": round(delta, 1),
            "reason": (
                "The controller has an explicitly injected TX-power fault. "
                "The safest recommendation is to restore the last accepted "
                "known-good RF value instead of inventing a new optimization."
            ),
            "review": "AUTHORIZED_RECOVERY_PATH_AVAILABLE",
            "active_version": active_version,
            "recovery_target_version": recovery_target_version,
        }

    # -----------------------------------------------------
    # 2) CAPACITY CONGESTION
    # -----------------------------------------------------
    capacity_fault = fault_active and fault_type == "CAPACITY_SPIKE"
    capacity_threshold_crossed = bool(
        max_prb
        and
        _number(max_prb.get("prb_utilization_pct"), 0.0)
        >= PRB_CONGESTION_THRESHOLD_PCT
    )

    if capacity_fault or capacity_threshold_crossed:
        target_id = max_prb.get("cell_id") if max_prb else None
        hotspot = fault.get("hotspot_area_id")

        proposed = (
            f"{target_id}: {steering_mode} -> CAPACITY_RECOVERY "
            "split steering"
            if target_id
            else f"{steering_mode} -> CAPACITY_RECOVERY split steering"
        )

        return {
            "ran_state": "CAPACITY_CONGESTION",
            "target_cell": target_id,
            "scope_cells": [target_id] if target_id else [],
            "hotspot_area_id": hotspot,
            "evidence": _cell_evidence(max_prb),
            "recommended_action": "TRAFFIC_STEERING",
            "proposed_change": proposed,
            "parameter": "steering_mode",
            "current_value": steering_mode,
            "target_value": "CAPACITY_RECOVERY",
            "delta": None,
            "reason": (
                "PRB utilization is at or above the learning-lab 85% "
                "capacity ceiling. RF power is not used as the default "
                "capacity actuator; the recommendation is load redistribution."
            ),
            "review": "OPERATOR_REVIEW_REQUIRED",
            "active_version": active_version,
            "recovery_target_version": recovery_target_version,
        }

    # -----------------------------------------------------
    # 3) STRONG RSRP + VERY LOW SINR
    # -----------------------------------------------------
    # This pattern can indicate an interference problem. Aggregate cell
    # KPIs alone are not sufficient to prove the interferer, so the output
    # is deliberately an evaluation candidate, not an automatic action.
    # -----------------------------------------------------
    interference = _interference_candidate(serving_cells)

    if interference is not None:
        target_id = interference.get("cell_id")
        cell_cfg = active_cells.get(target_id, {})
        antenna_id = cell_cfg.get("antenna_id")
        antenna_cfg = active_antennas.get(antenna_id, {})
        current_tilt = _number(
            antenna_cfg.get("electrical_tilt_deg"),
            0.0,
        )
        target_tilt = min(
            MAX_ELECTRICAL_TILT_DEG,
            current_tilt + TILT_STEP_DEG,
        )
        delta = target_tilt - current_tilt

        proposed = (
            f"{target_id} / {antenna_id}: electrical downtilt "
            f"{current_tilt:.1f} -> {target_tilt:.1f} deg "
            f"({delta:+.1f} deg) - evaluate candidate only"
        )

        return {
            "ran_state": "RF_INTERFERENCE_SUSPECTED",
            "target_cell": target_id,
            "scope_cells": [target_id],
            "evidence": _cell_evidence(interference),
            "recommended_action": "EVALUATE_ELECTRICAL_DOWNTILT",
            "proposed_change": proposed,
            "parameter": "electrical_tilt_deg",
            "current_value": round(current_tilt, 1),
            "target_value": round(target_tilt, 1),
            "delta": round(delta, 1),
            "reason": (
                "Serving RSRP is strong while SINR is very low. This can "
                "indicate interference, but neighbor/interferer evidence must "
                "be checked before applying an antenna change."
            ),
            "review": "ENGINEERING_VALIDATION_REQUIRED",
            "active_version": active_version,
            "recovery_target_version": recovery_target_version,
        }

    # -----------------------------------------------------
    # 4) WEAK COVERAGE WITH ACCEPTABLE SINR + CAPACITY HEADROOM
    # -----------------------------------------------------
    coverage = _coverage_candidate(serving_cells)

    if coverage is not None:
        target_id = coverage.get("cell_id")
        cell_cfg = active_cells.get(target_id, {})
        current_tx = _number(cell_cfg.get("tx_power_dbm"), 0.0)
        target_tx = min(
            MAX_TX_POWER_DBM,
            current_tx + TX_POWER_STEP_DB,
        )
        delta = target_tx - current_tx

        proposed = (
            f"{target_id}: TX {current_tx:.1f} -> "
            f"{target_tx:.1f} dBm ({delta:+.1f} dB) - evaluate candidate only"
        )

        return {
            "ran_state": "RF_COVERAGE_DEGRADATION",
            "target_cell": target_id,
            "scope_cells": [target_id],
            "evidence": _cell_evidence(coverage),
            "recommended_action": "INCREASE_TX_POWER",
            "proposed_change": proposed,
            "parameter": "tx_power_dbm",
            "current_value": round(current_tx, 1),
            "target_value": round(target_tx, 1),
            "delta": round(delta, 1),
            "reason": (
                "Serving RSRP is weak, while SINR remains acceptable and "
                "PRB utilization still has headroom. A small +3 dB TX-power "
                "candidate is reasonable to evaluate through the existing "
                "guarded-apply workflow."
            ),
            "review": "GUARDED_APPLY_REQUIRED",
            "active_version": active_version,
            "recovery_target_version": recovery_target_version,
        }

    # -----------------------------------------------------
    # 5) HEALTHY / NO ACTION
    # -----------------------------------------------------
    evidence_cell = max_prb or _worst_rsrp_cell(serving_cells)

    return {
        "ran_state": "HEALTHY",
        "target_cell": evidence_cell.get("cell_id") if evidence_cell else None,
        "scope_cells": [],
        "evidence": _cell_evidence(evidence_cell),
        "recommended_action": "NO_ACTION",
        "proposed_change": "No RAN parameter change recommended",
        "parameter": None,
        "current_value": None,
        "target_value": None,
        "delta": None,
        "reason": (
            "No active cell currently matches the evaluator's capacity, "
            "coverage or interference recommendation conditions."
        ),
        "review": "NONE",
        "active_version": active_version,
        "recovery_target_version": recovery_target_version,
    }


# =========================================================
# PERIODIC SERVICE
# =========================================================

class PeriodicOptimizationEvaluator:
    """
    Single-process periodic read-only evaluator.

    The worker produces recommendations only. It never calls guarded_apply,
    run_self_healing or any other state-changing controller method.
    """

    def __init__(self, controller, interval_seconds=60.0):
        self._controller = controller
        self._interval_seconds = max(
            10.0,
            float(interval_seconds),
        )
        self._state_lock = RLock()
        self._evaluation_lock = Lock()
        self._stop_event = Event()
        self._thread = None
        self._running = False
        self._evaluation_counter = 0
        self._history = []
        self._last_evaluation = None

    @property
    def interval_seconds(self):
        return self._interval_seconds

    def start(self):
        with self._state_lock:
            if self._running:
                return

            self._stop_event.clear()
            self._running = True
            self._thread = Thread(
                target=self._worker,
                name="ran-optimization-evaluator",
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
        # Evaluate immediately at application startup so the dashboard does
        # not have to wait one full interval for the first recommendation.
        self.evaluate_now(trigger="STARTUP")

        while not self._stop_event.wait(self._interval_seconds):
            self.evaluate_now(trigger="PERIODIC")

    def evaluate_now(self, trigger="MANUAL"):
        with self._evaluation_lock:
            try:
                observation = (
                    self._controller.get_optimization_observation()
                )

                recommendation = build_optimization_recommendation(
                    observation
                )

                with self._state_lock:
                    self._evaluation_counter += 1
                    evaluation_id = (
                        f"OPT-{self._evaluation_counter:06d}"
                    )

                result = {
                    "evaluation_id": evaluation_id,
                    "timestamp": _utc_now_iso(),
                    "trigger": str(trigger).upper(),
                    "evaluation_mode": "READ_ONLY",
                    "automatic_actuation": "DISABLED",
                    "actuation_performed": False,
                    **recommendation,
                }

            except Exception as exc:
                with self._state_lock:
                    self._evaluation_counter += 1
                    evaluation_id = (
                        f"OPT-{self._evaluation_counter:06d}"
                    )

                result = {
                    "evaluation_id": evaluation_id,
                    "timestamp": _utc_now_iso(),
                    "trigger": str(trigger).upper(),
                    "evaluation_mode": "READ_ONLY",
                    "automatic_actuation": "DISABLED",
                    "actuation_performed": False,
                    "ran_state": "EVALUATION_ERROR",
                    "target_cell": None,
                    "scope_cells": [],
                    "evidence": {},
                    "recommended_action": "NO_ACTION",
                    "proposed_change": "No change - evaluation failed",
                    "parameter": None,
                    "current_value": None,
                    "target_value": None,
                    "delta": None,
                    "reason": f"Optimization evaluation error: {exc}",
                    "review": "TROUBLESHOOT_EVALUATOR",
                    "active_version": None,
                    "recovery_target_version": None,
                }

            with self._state_lock:
                self._last_evaluation = deepcopy(result)
                self._history.append(deepcopy(result))
                self._history = self._history[-HISTORY_LIMIT:]

            return deepcopy(result)

    def get_status(self):
        with self._state_lock:
            thread_alive = bool(
                self._thread
                and
                self._thread.is_alive()
            )

            return {
                "status": "RUNNING" if self._running else "STOPPED",
                "worker_alive": thread_alive,
                "interval_seconds": self._interval_seconds,
                "evaluation_mode": "READ_ONLY",
                "automatic_actuation": "DISABLED",
                "evaluation_count": self._evaluation_counter,
                "last_evaluation": deepcopy(self._last_evaluation),
                "history": deepcopy(self._history[-10:]),
            }


# =========================================================
# DASHBOARD WIDGET INJECTION
# =========================================================

_OPTIMIZATION_STYLE = r"""
<style id="optimization-loop-style">
#optimization-loop {
    margin-bottom: 18px;
    padding: 18px;
    border: 1px solid #334155;
    border-radius: 10px;
    background: #111827;
}
#optimization-loop .opt-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    flex-wrap: wrap;
    margin-bottom: 14px;
}
#optimization-loop .opt-title {
    font-size: 20px;
    font-weight: 700;
}
#optimization-loop .opt-subtitle {
    margin-top: 4px;
    color: #94a3b8;
    font-size: 13px;
}
#optimization-loop .opt-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 10px;
}
#optimization-loop .opt-card {
    min-height: 84px;
    padding: 12px;
    border: 1px solid #334155;
    border-radius: 8px;
    background: #1e293b;
}
#optimization-loop .opt-label {
    color: #94a3b8;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}
#optimization-loop .opt-value {
    margin-top: 6px;
    font-size: 15px;
    font-weight: 700;
    overflow-wrap: anywhere;
}
#optimization-loop .opt-detail {
    margin-top: 12px;
    padding: 12px;
    border: 1px solid #334155;
    border-radius: 8px;
    background: #0f172a;
    line-height: 1.5;
}
#optimization-loop .opt-evidence {
    margin-top: 8px;
    color: #cbd5e1;
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    font-size: 12px;
    white-space: pre-wrap;
}
#optimization-loop .opt-button {
    border: 1px solid #475569;
    border-radius: 8px;
    padding: 9px 13px;
    background: #1e293b;
    color: #e2e8f0;
    cursor: pointer;
    font-weight: 700;
}
#optimization-loop .opt-button:hover {
    background: #334155;
}
#optimization-loop .opt-good { color: #86efac; }
#optimization-loop .opt-warn { color: #fdba74; }
#optimization-loop .opt-bad { color: #fca5a5; }
#optimization-loop .opt-muted { color: #94a3b8; }
</style>
"""


_OPTIMIZATION_HTML = r"""
<div id="optimization-loop">
    <div class="opt-head">
        <div>
            <div class="opt-title">Periodic Optimization Evaluator</div>
            <div class="opt-subtitle">
                Read-only observe/evaluate loop. Recommendations are generated every 60 seconds;
                automatic RAN actuation is intentionally disabled.
            </div>
        </div>
        <button class="opt-button" onclick="runOptimizationEvaluationNow()">
            Evaluate now
        </button>
    </div>

    <div class="opt-grid">
        <div class="opt-card">
            <div class="opt-label">Automation loop</div>
            <div id="opt-loop-status" class="opt-value">Loading...</div>
        </div>
        <div class="opt-card">
            <div class="opt-label">Last evaluation</div>
            <div id="opt-last-evaluation" class="opt-value">-</div>
        </div>
        <div class="opt-card">
            <div class="opt-label">RAN state</div>
            <div id="opt-ran-state" class="opt-value">-</div>
        </div>
        <div class="opt-card">
            <div class="opt-label">Target cell</div>
            <div id="opt-target-cell" class="opt-value">-</div>
        </div>
        <div class="opt-card">
            <div class="opt-label">Recommended action</div>
            <div id="opt-recommended-action" class="opt-value">-</div>
        </div>
        <div class="opt-card">
            <div class="opt-label">Automatic actuation</div>
            <div id="opt-auto-actuation" class="opt-value opt-warn">DISABLED</div>
        </div>
    </div>

    <div class="opt-detail">
        <div class="opt-label">Proposed change</div>
        <div id="opt-proposed-change" class="opt-value">-</div>
        <div id="opt-evidence" class="opt-evidence">Evidence: -</div>
        <div id="opt-reason" class="opt-subtitle" style="margin-top:10px">-</div>
    </div>
</div>
"""


_OPTIMIZATION_SCRIPT = r"""
<script id="optimization-loop-script">
function optimizationStateClass(state) {
    if (state === "HEALTHY") return "opt-good";
    if (state === "EVALUATION_ERROR") return "opt-bad";
    return "opt-warn";
}

function formatOptimizationEvidence(evidence) {
    if (!evidence || Object.keys(evidence).length === 0) {
        return "Evidence: -";
    }

    const parts = [];
    if (evidence.prb_utilization_pct !== undefined) {
        parts.push(`PRB ${evidence.prb_utilization_pct}%`);
    }
    if (evidence.rsrp_dbm !== undefined) {
        parts.push(`RSRP ${evidence.rsrp_dbm} dBm`);
    }
    if (evidence.sinr_db !== undefined) {
        parts.push(`SINR ${evidence.sinr_db} dB`);
    }
    if (evidence.active_users !== undefined) {
        parts.push(`Active UE ${evidence.active_users}`);
    }
    if (evidence.band) {
        parts.push(`Band ${evidence.band}`);
    }

    return `Evidence: ${parts.join(" | ")}`;
}

async function refreshOptimizationLoop() {
    try {
        const response = await fetch("/optimization/status", { cache: "no-store" });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const data = await response.json();
        const last = data.last_evaluation || {};

        const loop = document.getElementById("opt-loop-status");
        const lastTime = document.getElementById("opt-last-evaluation");
        const ranState = document.getElementById("opt-ran-state");
        const target = document.getElementById("opt-target-cell");
        const action = document.getElementById("opt-recommended-action");
        const auto = document.getElementById("opt-auto-actuation");
        const proposed = document.getElementById("opt-proposed-change");
        const evidence = document.getElementById("opt-evidence");
        const reason = document.getElementById("opt-reason");

        loop.textContent = `${data.status} / ${data.interval_seconds}s`;
        loop.className = `opt-value ${data.status === "RUNNING" ? "opt-good" : "opt-bad"}`;

        lastTime.textContent = last.timestamp
            ? new Date(last.timestamp).toLocaleTimeString()
            : "waiting";

        ranState.textContent = last.ran_state || "waiting";
        ranState.className = `opt-value ${optimizationStateClass(last.ran_state)}`;

        target.textContent = last.target_cell || "-";
        action.textContent = last.recommended_action || "-";
        auto.textContent = data.automatic_actuation || "DISABLED";
        proposed.textContent = last.proposed_change || "-";
        evidence.textContent = formatOptimizationEvidence(last.evidence);
        reason.textContent = last.reason || "-";
    }
    catch (error) {
        const loop = document.getElementById("opt-loop-status");
        if (loop) {
            loop.textContent = `UNAVAILABLE: ${error}`;
            loop.className = "opt-value opt-bad";
        }
    }
}

async function runOptimizationEvaluationNow() {
    try {
        const response = await fetch(
            "/optimization/evaluate-now",
            { method: "POST" }
        );

        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        await response.json();
        await refreshOptimizationLoop();
    }
    catch (error) {
        const loop = document.getElementById("opt-loop-status");
        if (loop) {
            loop.textContent = `EVALUATION ERROR: ${error}`;
            loop.className = "opt-value opt-bad";
        }
    }
}

refreshOptimizationLoop();
setInterval(refreshOptimizationLoop, 5000);
</script>
"""


def inject_optimization_widget(dashboard_html):
    """Inject the evaluator card into the existing dashboard HTML."""

    html = str(dashboard_html)

    if "optimization-loop-style" in html:
        return html

    html = html.replace(
        "</head>",
        _OPTIMIZATION_STYLE + "\n</head>",
        1,
    )

    html = html.replace(
        '<div class="container">',
        '<div class="container">\n\n' + _OPTIMIZATION_HTML,
        1,
    )

    html = html.replace(
        "</body>",
        _OPTIMIZATION_SCRIPT + "\n</body>",
        1,
    )

    return html
