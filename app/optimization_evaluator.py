"""
Network-wide, read-only RAN optimization evaluator for the learning lab.

v2.4 purpose
------------
The evaluator now distinguishes two questions:

1. Is the active RAN inside the configured safe envelope?
2. Even if it is safe, is there a demonstrably better configuration under
   the same synthetic RF / UE / traffic / weather context?

Every cycle therefore:

- captures one consistent read-only controller observation,
- re-evaluates the complete active network under one frozen context,
- scans every configured cell for optimization pressure,
- shortlists only the most relevant cells so the search remains bounded,
- evaluates a limited set of concrete TX-power / electrical-tilt / traffic-
  steering alternatives through the existing physics-inspired RAN engine,
- rejects candidates that fail the existing guardrails,
- ranks the remaining candidates by a transparent network-wide objective,
- returns one concrete cell-level recommendation with predicted KPI impact.

The search does NOT select a previous value merely because it was previous.
Factory / recovery values are used only as useful candidate seeds. A value is
recommended only if the simulated candidate is safe and scores better than
current active state under the same context.

Safety boundary
---------------
The evaluator NEVER applies RAN changes. Automatic actuation is intentionally
DISABLED. Existing guarded-apply and self-healing workflows remain the only
state-changing paths.

Search boundary
---------------
All configured cells are screened every cycle, but the evaluator deliberately
does not brute-force every possible multi-cell configuration. It performs a
bounded single-actuator search on the highest-priority opportunities. This
keeps the learning-lab loop explainable and avoids combinatorial explosion.

The implementation is still single-process / in-memory learning-lab code, not
production SMO / RIC software.
"""

from copy import deepcopy
from datetime import datetime, timezone
from threading import Event, Lock, RLock, Thread

from app.ran_engine import (
    MAX_ELECTRICAL_TILT_DEG,
    MAX_TX_POWER_DBM,
    MIN_ELECTRICAL_TILT_DEG,
    MIN_TX_POWER_DBM,
    build_baseline_sites,
    build_candidate_sites,
    build_configuration_inventory,
    evaluate_ran_state,
)
from app.ran_guardrails import evaluate_ran_guardrails


# =========================================================
# SEARCH POLICY - LEARNING LAB, NOT OPERATOR POLICY
# =========================================================

PRB_CONGESTION_THRESHOLD_PCT = 85.0
PRB_SCREEN_THRESHOLD_PCT = 80.0
WEAK_RSRP_SCREEN_DBM = -105.0
POOR_SINR_SCREEN_DB = 5.0

TX_SEARCH_STEPS_DB = (-3.0, -1.0, 1.0, 3.0)
TILT_SEARCH_STEPS_DEG = (-2.0, -1.0, 1.0, 2.0)

DEFAULT_MAX_TARGET_CELLS = 3
DEFAULT_MAX_CANDIDATE_EVALUATIONS = 18
HISTORY_LIMIT = 20

# A small positive threshold suppresses recommendations caused only by
# numerical noise in the synthetic model.
MIN_MEANINGFUL_OBJECTIVE_GAIN = 0.25

# Transparent scalarization weights. Hard safety constraints are NOT encoded
# here: candidates first have to PASS the existing RAN guardrails.
OBJECTIVE_WEIGHTS = {
    "served_ratio_pp": 12.0,
    "unserved_ue_reduction": 3.0,
    "degraded_ue_reduction": 0.35,
    "weighted_sinr_db": 4.0,
    "mean_cell_sinr_db": 2.0,
    "weighted_rsrp_db": 0.35,
    "max_prb_reduction_pp": 0.55,
    "p95_prb_reduction_pp": 0.20,
    "aggregate_prb_reduction_pp": 0.18,
    "change_magnitude_penalty": 0.03,
}


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


def _round_or_none(value, digits=3):
    if value is None:
        return None
    return round(float(value), digits)


def _percentile(values, percentile):
    values = sorted(float(value) for value in values)
    if not values:
        return None
    if len(values) == 1:
        return values[0]

    position = (len(values) - 1) * float(percentile)
    lower = int(position)
    upper = min(lower + 1, len(values) - 1)
    fraction = position - lower

    return values[lower] + (values[upper] - values[lower]) * fraction


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

    return inventory, cells, antennas


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
        "prb_utilization_pct": _round_or_none(
            cell.get("prb_utilization_pct"), 1
        ),
        "rsrp_dbm": _round_or_none(cell.get("rsrp_dbm"), 1),
        "sinr_db": _round_or_none(cell.get("sinr_db"), 1),
        "active_users": int(_number(cell.get("active_users"), 0)),
    }


def _active_cells(snapshot):
    return [
        cell
        for cell in snapshot.get("cells", {}).values()
        if int(_number(cell.get("active_users"), 0)) > 0
    ]


def _max_prb_cell(snapshot):
    cells = _active_cells(snapshot)
    if not cells:
        return None
    return max(
        cells,
        key=lambda cell: _number(cell.get("prb_utilization_pct"), 0.0),
    )


# =========================================================
# NETWORK SUMMARY / OBJECTIVE
# =========================================================

def summarize_network(snapshot):
    """Build a compact network-wide KPI summary from one RAN snapshot."""

    cells = list(snapshot.get("cells", {}).values())
    active = [
        cell
        for cell in cells
        if int(_number(cell.get("active_users"), 0)) > 0
    ]

    total_active_users = sum(
        int(_number(cell.get("active_users"), 0))
        for cell in active
    )

    def weighted_metric(metric):
        weighted_sum = 0.0
        weight_sum = 0.0

        for cell in active:
            value = cell.get(metric)
            users = int(_number(cell.get("active_users"), 0))
            if value is None or users <= 0:
                continue
            weighted_sum += float(value) * users
            weight_sum += users

        if weight_sum <= 0:
            return None

        return weighted_sum / weight_sum

    prb_values = [
        _number(cell.get("prb_utilization_pct"), 0.0)
        for cell in active
    ]

    degraded_ues = sum(
        int(
            _number(
                cell.get("serviceability_ue_mix", {}).get("DEGRADED", 0),
                0,
            )
        )
        for cell in active
    )

    service = snapshot.get("service", {})

    return {
        "configured_cells": len(cells),
        "serving_cells": len(active),
        "active_users": total_active_users,
        "requested_active_ues": int(
            _number(service.get("requested_active_ues"), total_active_users)
        ),
        "served_active_ues": int(
            _number(service.get("served_active_ues"), total_active_users)
        ),
        "unserved_active_ues": int(
            _number(service.get("unserved_active_ues"), 0)
        ),
        "served_ratio_pct": _round_or_none(
            service.get("served_ratio_pct"), 3
        ),
        "degraded_active_ues": degraded_ues,
        "weighted_sinr_db": _round_or_none(weighted_metric("sinr_db"), 3),
        "mean_cell_sinr_db": _round_or_none(
            sum(_number(cell.get("sinr_db"), 0.0) for cell in active) / len(active),
            3,
        ) if active else None,
        "weighted_rsrp_dbm": _round_or_none(weighted_metric("rsrp_dbm"), 3),
        "mean_cell_rsrp_dbm": _round_or_none(
            sum(_number(cell.get("rsrp_dbm"), 0.0) for cell in active) / len(active),
            3,
        ) if active else None,
        "aggregate_prb_pct_points": _round_or_none(sum(prb_values), 3)
        if prb_values
        else None,
        "max_prb_pct": _round_or_none(max(prb_values), 3)
        if prb_values
        else None,
        "p95_prb_pct": _round_or_none(_percentile(prb_values, 0.95), 3),
        "cells_at_or_above_85_prb": sum(
            1 for value in prb_values if value >= PRB_CONGESTION_THRESHOLD_PCT
        ),
    }


def build_network_delta(baseline_summary, candidate_summary):
    """Candidate minus baseline for quality, baseline minus candidate for load."""

    def delta(key):
        before = baseline_summary.get(key)
        after = candidate_summary.get(key)
        if before is None or after is None:
            return None
        return float(after) - float(before)

    max_prb_before = baseline_summary.get("max_prb_pct")
    max_prb_after = candidate_summary.get("max_prb_pct")
    p95_before = baseline_summary.get("p95_prb_pct")
    p95_after = candidate_summary.get("p95_prb_pct")

    return {
        "served_ratio_pp": _round_or_none(delta("served_ratio_pct"), 3),
        "unserved_ue_change": int(
            candidate_summary.get("unserved_active_ues", 0)
            - baseline_summary.get("unserved_active_ues", 0)
        ),
        "degraded_ue_change": int(
            candidate_summary.get("degraded_active_ues", 0)
            - baseline_summary.get("degraded_active_ues", 0)
        ),
        "weighted_sinr_db": _round_or_none(delta("weighted_sinr_db"), 3),
        "mean_cell_sinr_db": _round_or_none(delta("mean_cell_sinr_db"), 3),
        "weighted_rsrp_db": _round_or_none(delta("weighted_rsrp_dbm"), 3),
        "aggregate_prb_pp": _round_or_none(
            delta("aggregate_prb_pct_points"),
            3,
        ),
        "max_prb_pp": _round_or_none(
            None
            if max_prb_before is None or max_prb_after is None
            else float(max_prb_after) - float(max_prb_before),
            3,
        ),
        "p95_prb_pp": _round_or_none(
            None
            if p95_before is None or p95_after is None
            else float(p95_after) - float(p95_before),
            3,
        ),
    }


def objective_gain(delta, change_magnitude=0.0):
    """
    Return transparent scalarized gain relative to current active network.

    Positive = predicted improvement. Safety is evaluated separately by the
    existing guardrails before this score is used for ranking.
    """

    served_ratio = _number(delta.get("served_ratio_pp"), 0.0)
    unserved_reduction = -_number(delta.get("unserved_ue_change"), 0.0)
    degraded_reduction = -_number(delta.get("degraded_ue_change"), 0.0)
    sinr_gain = _number(delta.get("weighted_sinr_db"), 0.0)
    mean_cell_sinr_gain = _number(delta.get("mean_cell_sinr_db"), 0.0)
    rsrp_gain = _number(delta.get("weighted_rsrp_db"), 0.0)
    max_prb_reduction = -_number(delta.get("max_prb_pp"), 0.0)
    p95_prb_reduction = -_number(delta.get("p95_prb_pp"), 0.0)
    aggregate_prb_reduction = -_number(delta.get("aggregate_prb_pp"), 0.0)

    components = {
        "served_ratio": served_ratio * OBJECTIVE_WEIGHTS["served_ratio_pp"],
        "unserved_ues": (
            unserved_reduction * OBJECTIVE_WEIGHTS["unserved_ue_reduction"]
        ),
        "degraded_ues": (
            degraded_reduction * OBJECTIVE_WEIGHTS["degraded_ue_reduction"]
        ),
        "weighted_sinr": (
            sinr_gain * OBJECTIVE_WEIGHTS["weighted_sinr_db"]
        ),
        "mean_cell_sinr": (
            mean_cell_sinr_gain * OBJECTIVE_WEIGHTS["mean_cell_sinr_db"]
        ),
        "weighted_rsrp": (
            rsrp_gain * OBJECTIVE_WEIGHTS["weighted_rsrp_db"]
        ),
        "max_prb": (
            max_prb_reduction * OBJECTIVE_WEIGHTS["max_prb_reduction_pp"]
        ),
        "p95_prb": (
            p95_prb_reduction * OBJECTIVE_WEIGHTS["p95_prb_reduction_pp"]
        ),
        "aggregate_prb": (
            aggregate_prb_reduction
            * OBJECTIVE_WEIGHTS["aggregate_prb_reduction_pp"]
        ),
        "change_penalty": (
            -abs(float(change_magnitude))
            * OBJECTIVE_WEIGHTS["change_magnitude_penalty"]
        ),
    }

    score = sum(components.values())

    return round(score, 4), {
        key: round(value, 4)
        for key, value in components.items()
    }


def _meaningful_gain(candidate):
    if candidate.get("guardrail_verdict") != "PASS":
        return False

    gain = _number(candidate.get("objective_gain"), 0.0)
    delta = candidate.get("network_delta", {})

    served_drop = _number(delta.get("served_ratio_pp"), 0.0) < -0.001
    unserved_increase = int(delta.get("unserved_ue_change") or 0) > 0

    if served_drop or unserved_increase:
        return False

    if gain < MIN_MEANINGFUL_OBJECTIVE_GAIN:
        return False

    # At least one interpretable KPI must improve beyond rounding noise.
    interpretable_improvement = any(
        (
            _number(delta.get("weighted_sinr_db"), 0.0) >= 0.05,
            _number(delta.get("mean_cell_sinr_db"), 0.0) >= 0.03,
            _number(delta.get("weighted_rsrp_db"), 0.0) >= 0.20,
            _number(delta.get("aggregate_prb_pp"), 0.0) <= -0.50,
            _number(delta.get("max_prb_pp"), 0.0) <= -0.50,
            _number(delta.get("p95_prb_pp"), 0.0) <= -0.50,
            int(delta.get("degraded_ue_change") or 0) < 0,
        )
    )

    return interpretable_improvement


# =========================================================
# PER-CELL NETWORK IMPACT
# =========================================================

def _cell_impact_rows(baseline_snapshot, candidate_snapshot):
    baseline_cells = baseline_snapshot.get("cells", {})
    candidate_cells = candidate_snapshot.get("cells", {})

    rows = []

    for cell_id in sorted(set(baseline_cells) | set(candidate_cells)):
        before = baseline_cells.get(cell_id)
        after = candidate_cells.get(cell_id)
        if before is None or after is None:
            continue

        row = {
            "cell_id": cell_id,
            "sinr_delta_db": _round_or_none(
                _number(after.get("sinr_db"), 0.0)
                - _number(before.get("sinr_db"), 0.0),
                3,
            ),
            "rsrp_delta_db": _round_or_none(
                _number(after.get("rsrp_dbm"), 0.0)
                - _number(before.get("rsrp_dbm"), 0.0),
                3,
            ),
            "prb_delta_pp": _round_or_none(
                _number(after.get("prb_utilization_pct"), 0.0)
                - _number(before.get("prb_utilization_pct"), 0.0),
                3,
            ),
            "active_ue_delta": int(
                _number(after.get("active_users"), 0)
                - _number(before.get("active_users"), 0)
            ),
        }

        magnitude = (
            abs(_number(row["sinr_delta_db"], 0.0))
            + 0.35 * abs(_number(row["rsrp_delta_db"], 0.0))
            + 0.20 * abs(_number(row["prb_delta_pp"], 0.0))
            + 0.02 * abs(_number(row["active_ue_delta"], 0.0))
        )

        if magnitude >= 0.05:
            row["impact_magnitude"] = round(magnitude, 3)
            rows.append(row)

    rows.sort(key=lambda row: row["impact_magnitude"], reverse=True)
    return rows[:8]


# =========================================================
# NETWORK-WIDE SCREENING
# =========================================================

def _screen_cells(observation, baseline_snapshot):
    active_sites = observation.get("active_sites", {})
    recovery_sites = observation.get("recovery_target_sites", {})
    factory_sites = build_baseline_sites()

    _, active_cfg, active_antennas = _inventory_indexes(active_sites)
    _, recovery_cfg, recovery_antennas = _inventory_indexes(recovery_sites)
    _, factory_cfg, factory_antennas = _inventory_indexes(factory_sites)

    kpis = baseline_snapshot.get("cells", {})
    fault = observation.get("fault_state") or {}
    fault_type = str(fault.get("type", "")).upper()
    fault_cells = set(fault.get("cell_ids", []) or [])

    rows = []

    for cell_id, config in active_cfg.items():
        kpi = kpis.get(cell_id, {})
        reasons = []
        priority = 0.0

        current_tx = _number(config.get("tx_power_dbm"), 0.0)
        factory_tx = _number(
            factory_cfg.get(cell_id, {}).get("tx_power_dbm"),
            current_tx,
        )
        recovery_tx = _number(
            recovery_cfg.get(cell_id, {}).get("tx_power_dbm"),
            current_tx,
        )

        if abs(current_tx - factory_tx) >= 0.1:
            priority += 100.0 + abs(current_tx - factory_tx) * 5.0
            reasons.append(
                f"TX differs from factory seed ({factory_tx:.1f} dBm)"
            )

        if cell_id in fault_cells and fault_type == "TX_POWER_DROP":
            priority += 500.0
            reasons.append("explicit TX-power fault scope")

        prb = _number(kpi.get("prb_utilization_pct"), 0.0)
        rsrp = _number(kpi.get("rsrp_dbm"), -999.0)
        sinr = _number(kpi.get("sinr_db"), 999.0)

        if prb >= PRB_SCREEN_THRESHOLD_PCT:
            priority += 60.0 + (prb - PRB_SCREEN_THRESHOLD_PCT) * 3.0
            reasons.append(f"high PRB {prb:.1f}%")

        if rsrp <= WEAK_RSRP_SCREEN_DBM:
            priority += 40.0 + (WEAK_RSRP_SCREEN_DBM - rsrp) * 2.0
            reasons.append(f"weak RSRP {rsrp:.1f} dBm")

        if sinr <= POOR_SINR_SCREEN_DB:
            priority += 50.0 + (POOR_SINR_SCREEN_DB - sinr) * 4.0
            reasons.append(f"poor SINR {sinr:.1f} dB")

        antenna_id = config.get("antenna_id")
        active_tilt = _number(
            active_antennas.get(antenna_id, {}).get("electrical_tilt_deg"),
            0.0,
        )
        factory_tilt = _number(
            factory_antennas.get(antenna_id, {}).get("electrical_tilt_deg"),
            active_tilt,
        )
        recovery_tilt = _number(
            recovery_antennas.get(antenna_id, {}).get("electrical_tilt_deg"),
            active_tilt,
        )

        if abs(active_tilt - factory_tilt) >= 0.1:
            priority += 80.0 + abs(active_tilt - factory_tilt) * 4.0
            reasons.append(
                f"antenna tilt differs from factory seed ({factory_tilt:.1f} deg)"
            )

        if reasons:
            rows.append({
                "cell_id": cell_id,
                "site_id": config.get("site_id"),
                "sector_id": config.get("sector_id"),
                "antenna_id": antenna_id,
                "band": config.get("band"),
                "priority": round(priority, 3),
                "reasons": reasons,
                "current_tx_dbm": current_tx,
                "factory_tx_dbm": factory_tx,
                "recovery_tx_dbm": recovery_tx,
                "current_tilt_deg": active_tilt,
                "factory_tilt_deg": factory_tilt,
                "recovery_tilt_deg": recovery_tilt,
                "evidence": _cell_evidence(kpi),
            })

    # Capacity spike may not point at a configured cell directly. Make sure
    # the current max-PRB cell is included in the shortlist candidates.
    max_prb = _max_prb_cell(baseline_snapshot)
    if max_prb and (
        str(fault_type) == "CAPACITY_SPIKE"
        or _number(max_prb.get("prb_utilization_pct"), 0.0)
        >= PRB_SCREEN_THRESHOLD_PCT
    ):
        max_id = max_prb.get("cell_id")
        if max_id in active_cfg and not any(row["cell_id"] == max_id for row in rows):
            config = active_cfg[max_id]
            antenna_id = config.get("antenna_id")
            rows.append({
                "cell_id": max_id,
                "site_id": config.get("site_id"),
                "sector_id": config.get("sector_id"),
                "antenna_id": antenna_id,
                "band": config.get("band"),
                "priority": 450.0 if fault_type == "CAPACITY_SPIKE" else 90.0,
                "reasons": ["capacity hotspot / high PRB source"],
                "current_tx_dbm": _number(config.get("tx_power_dbm"), 0.0),
                "factory_tx_dbm": _number(
                    factory_cfg.get(max_id, {}).get("tx_power_dbm"),
                    config.get("tx_power_dbm"),
                ),
                "recovery_tx_dbm": _number(
                    recovery_cfg.get(max_id, {}).get("tx_power_dbm"),
                    config.get("tx_power_dbm"),
                ),
                "current_tilt_deg": _number(
                    active_antennas.get(antenna_id, {}).get("electrical_tilt_deg"),
                    0.0,
                ),
                "factory_tilt_deg": _number(
                    factory_antennas.get(antenna_id, {}).get("electrical_tilt_deg"),
                    0.0,
                ),
                "recovery_tilt_deg": _number(
                    recovery_antennas.get(antenna_id, {}).get("electrical_tilt_deg"),
                    0.0,
                ),
                "evidence": _cell_evidence(max_prb),
            })

    rows.sort(key=lambda row: row["priority"], reverse=True)

    return {
        "configured_cells_scanned": len(active_cfg),
        "serving_cells_scanned": len(_active_cells(baseline_snapshot)),
        "opportunity_cells_identified": len(rows),
        "rows": rows,
    }


# =========================================================
# BOUNDED CANDIDATE GENERATION
# =========================================================

def _unique_values(values, current, minimum, maximum):
    result = []
    seen = set()

    for value in values:
        value = round(min(max(float(value), minimum), maximum), 3)
        if abs(value - float(current)) < 0.001:
            continue
        if value in seen:
            continue
        seen.add(value)
        result.append(value)

    return result


def _candidate_specs(observation, screening, max_target_cells):
    rows = screening["rows"][:max_target_cells]
    specs = []
    seen_tilt = set()

    fault = observation.get("fault_state") or {}
    fault_type = str(fault.get("type", "")).upper()

    for row in rows:
        cell_id = row["cell_id"]
        current_tx = row["current_tx_dbm"]

        tx_values = []

        # Recovery and factory values are candidate SEEDS only. They are not
        # automatically preferred by the final objective.
        if fault_type == "TX_POWER_DROP":
            tx_values.append(row["recovery_tx_dbm"])

        tx_values.append(row["factory_tx_dbm"])
        tx_values.extend(current_tx + step for step in TX_SEARCH_STEPS_DB)

        for target_tx in _unique_values(
            tx_values,
            current_tx,
            MIN_TX_POWER_DBM,
            MAX_TX_POWER_DBM,
        ):
            specs.append({
                "kind": "CELL_TX_POWER",
                "target_cell": cell_id,
                "target_antenna": row["antenna_id"],
                "parameter": "tx_power_dbm",
                "current_value": current_tx,
                "target_value": target_tx,
                "delta": round(target_tx - current_tx, 3),
                "cell_updates": {
                    cell_id: {"tx_power_dbm": target_tx}
                },
                "antenna_updates": {},
                "steering_mode": observation.get("steering_mode", "LOAD_AWARE"),
                "screening_reasons": deepcopy(row["reasons"]),
            })

        # Tilt search is useful when the antenna itself changed or the cell
        # has a poor-SINR symptom. Dedupe because several carriers can share
        # the same antenna system.
        evidence = row.get("evidence", {})
        needs_tilt_search = (
            abs(row["current_tilt_deg"] - row["factory_tilt_deg"]) >= 0.1
            or _number(evidence.get("sinr_db"), 999.0) <= POOR_SINR_SCREEN_DB
        )

        if needs_tilt_search and row["antenna_id"]:
            antenna_id = row["antenna_id"]
            current_tilt = row["current_tilt_deg"]
            tilt_values = [row["factory_tilt_deg"]]
            tilt_values.extend(
                current_tilt + step
                for step in TILT_SEARCH_STEPS_DEG
            )

            for target_tilt in _unique_values(
                tilt_values,
                current_tilt,
                MIN_ELECTRICAL_TILT_DEG,
                MAX_ELECTRICAL_TILT_DEG,
            ):
                dedupe_key = (antenna_id, target_tilt)
                if dedupe_key in seen_tilt:
                    continue
                seen_tilt.add(dedupe_key)

                specs.append({
                    "kind": "ANTENNA_TILT",
                    "target_cell": cell_id,
                    "target_antenna": antenna_id,
                    "parameter": "electrical_tilt_deg",
                    "current_value": current_tilt,
                    "target_value": target_tilt,
                    "delta": round(target_tilt - current_tilt, 3),
                    "cell_updates": {},
                    "antenna_updates": {
                        antenna_id: {"electrical_tilt_deg": target_tilt}
                    },
                    "steering_mode": observation.get("steering_mode", "LOAD_AWARE"),
                    "screening_reasons": deepcopy(row["reasons"]),
                })

    # Capacity steering is a separate actuator and is evaluated through the
    # same RF/traffic/guardrail pipeline. It does not change RF configuration.
    max_prb = _max_prb_cell(observation.get("snapshot", {}))
    current_steering = str(observation.get("steering_mode", "LOAD_AWARE"))
    if (
        max_prb
        and current_steering.upper() != "CAPACITY_RECOVERY"
        and (
            _number(max_prb.get("prb_utilization_pct"), 0.0)
            >= PRB_SCREEN_THRESHOLD_PCT
            or fault_type == "CAPACITY_SPIKE"
        )
    ):
        specs.insert(0, {
            "kind": "TRAFFIC_STEERING",
            "target_cell": max_prb.get("cell_id"),
            "target_antenna": None,
            "parameter": "steering_mode",
            "current_value": current_steering,
            "target_value": "CAPACITY_RECOVERY",
            "delta": None,
            "cell_updates": {},
            "antenna_updates": {},
            "steering_mode": "CAPACITY_RECOVERY",
            "screening_reasons": ["capacity hotspot / high PRB source"],
        })

    return specs


# =========================================================
# PHYSICS / TRAFFIC CANDIDATE EVALUATION
# =========================================================

def _evaluate_candidate_spec(observation, baseline_snapshot, baseline_summary, spec):
    active_sites = observation.get("active_sites", {})

    candidate_sites = build_candidate_sites(
        base_sites=active_sites,
        cell_updates=spec.get("cell_updates") or None,
        antenna_updates=spec.get("antenna_updates") or None,
    )

    candidate_snapshot = evaluate_ran_state(
        candidate_sites,
        weather=deepcopy(observation.get("weather")),
        simulation_timestamp=observation.get("simulation_timestamp"),
        traffic_multiplier=_number(observation.get("traffic_multiplier"), 1.0),
        steering_mode=spec.get(
            "steering_mode",
            observation.get("steering_mode", "LOAD_AWARE"),
        ),
        area_traffic_multipliers=deepcopy(
            observation.get("area_traffic_multipliers") or {}
        ),
    )

    guardrails = evaluate_ran_guardrails(
        baseline_snapshot,
        candidate_snapshot,
    )

    candidate_summary = summarize_network(candidate_snapshot)
    delta = build_network_delta(baseline_summary, candidate_summary)

    change_magnitude = 0.0
    if spec.get("delta") is not None:
        change_magnitude = abs(_number(spec.get("delta"), 0.0))
    elif spec.get("kind") == "TRAFFIC_STEERING":
        change_magnitude = 1.0

    gain, components = objective_gain(delta, change_magnitude)

    return {
        **deepcopy(spec),
        "guardrail_verdict": guardrails.get("verdict"),
        "failed_guardrails": deepcopy(guardrails.get("failed_checks", [])),
        "objective_gain": gain,
        "objective_components": components,
        "network_delta": delta,
        "candidate_summary": candidate_summary,
        "cell_impact": _cell_impact_rows(
            baseline_snapshot,
            candidate_snapshot,
        ),
        "meaningful_gain": False,  # populated below
    }


# =========================================================
# FINAL RECOMMENDATION FORMATTING
# =========================================================

def _action_from_candidate(candidate, observation):
    kind = candidate.get("kind")
    current = candidate.get("current_value")
    target = candidate.get("target_value")

    if kind == "TRAFFIC_STEERING":
        return "TRAFFIC_STEERING"

    if kind == "ANTENNA_TILT":
        if _number(target) > _number(current):
            return "INCREASE_ELECTRICAL_DOWNTILT"
        return "REDUCE_ELECTRICAL_DOWNTILT"

    if kind == "CELL_TX_POWER":
        fault = observation.get("fault_state") or {}
        recovery_sites = observation.get("recovery_target_sites", {})
        _, recovery_cells, _ = _inventory_indexes(recovery_sites)
        target_id = candidate.get("target_cell")
        recovery_tx = recovery_cells.get(target_id, {}).get("tx_power_dbm")

        if (
            str(fault.get("type", "")).upper() == "TX_POWER_DROP"
            and target_id in set(fault.get("cell_ids", []) or [])
            and recovery_tx is not None
            and abs(_number(target) - _number(recovery_tx)) < 0.01
        ):
            return "RESTORE_KNOWN_GOOD_TX_POWER"

        if _number(target) < _number(current):
            return "REDUCE_TX_POWER"
        return "INCREASE_TX_POWER"

    return "REVIEW_CANDIDATE"


def _proposed_change(candidate):
    target_cell = candidate.get("target_cell") or "NETWORK"
    current = candidate.get("current_value")
    target = candidate.get("target_value")
    delta = candidate.get("delta")

    if candidate.get("kind") == "TRAFFIC_STEERING":
        return (
            f"{target_cell}: steering {current} -> {target} "
            "(split/load redistribution)"
        )

    if candidate.get("kind") == "ANTENNA_TILT":
        antenna = candidate.get("target_antenna")
        return (
            f"{target_cell} / {antenna}: electrical downtilt "
            f"{_number(current):.1f} -> {_number(target):.1f} deg "
            f"({_number(delta):+.1f} deg)"
        )

    return (
        f"{target_cell}: TX {_number(current):.1f} -> "
        f"{_number(target):.1f} dBm ({_number(delta):+.1f} dB)"
    )


def _candidate_reason(candidate):
    delta = candidate.get("network_delta", {})

    parts = [
        "Best safe candidate in the bounded physics-based search",
        f"objective gain {candidate.get('objective_gain'):+.3f}",
    ]

    if delta.get("weighted_sinr_db") is not None:
        parts.append(
            f"weighted SINR {delta['weighted_sinr_db']:+.3f} dB"
        )

    if delta.get("weighted_rsrp_db") is not None:
        parts.append(
            f"weighted RSRP {delta['weighted_rsrp_db']:+.3f} dB"
        )

    if delta.get("aggregate_prb_pp") is not None:
        parts.append(
            f"aggregate serving-cell PRB {delta['aggregate_prb_pp']:+.3f} pp"
        )

    if delta.get("max_prb_pp") is not None:
        parts.append(
            f"max PRB {delta['max_prb_pp']:+.3f} pp"
        )

    if delta.get("served_ratio_pp") is not None:
        parts.append(
            f"served ratio {delta['served_ratio_pp']:+.3f} pp"
        )

    return "; ".join(parts) + "."


# =========================================================
# NETWORK-WIDE OPTIMIZATION SEARCH
# =========================================================

def run_network_optimization_search(
    observation,
    max_target_cells=DEFAULT_MAX_TARGET_CELLS,
    max_candidate_evaluations=DEFAULT_MAX_CANDIDATE_EVALUATIONS,
):
    """
    Screen the complete network, then physically evaluate a bounded set of
    single-actuator candidates against one frozen weather / UE / traffic
    context.
    """

    active_sites = observation.get("active_sites", {})

    baseline_snapshot = evaluate_ran_state(
        active_sites,
        weather=deepcopy(observation.get("weather")),
        simulation_timestamp=observation.get("simulation_timestamp"),
        traffic_multiplier=_number(observation.get("traffic_multiplier"), 1.0),
        steering_mode=observation.get("steering_mode", "LOAD_AWARE"),
        area_traffic_multipliers=deepcopy(
            observation.get("area_traffic_multipliers") or {}
        ),
    )

    # Keep the observation snapshot equal to the exact baseline used by the
    # search so later helpers and output evidence all refer to one context.
    local_observation = deepcopy(observation)
    local_observation["snapshot"] = deepcopy(baseline_snapshot)

    baseline_summary = summarize_network(baseline_snapshot)
    baseline_guardrails = evaluate_ran_guardrails(
        baseline_snapshot,
        baseline_snapshot,
    )

    screening = _screen_cells(local_observation, baseline_snapshot)
    shortlist = screening["rows"][: max(1, int(max_target_cells))]

    specs = _candidate_specs(
        local_observation,
        screening,
        max_target_cells=max(1, int(max_target_cells)),
    )

    evaluated = []
    evaluation_errors = []

    for spec in specs[: max(1, int(max_candidate_evaluations))]:
        try:
            candidate = _evaluate_candidate_spec(
                local_observation,
                baseline_snapshot,
                baseline_summary,
                spec,
            )
            candidate["meaningful_gain"] = _meaningful_gain(candidate)
            evaluated.append(candidate)

        except Exception as exc:
            evaluation_errors.append({
                "kind": spec.get("kind"),
                "target_cell": spec.get("target_cell"),
                "parameter": spec.get("parameter"),
                "target_value": spec.get("target_value"),
                "error": str(exc),
            })

    safe_candidates = [
        candidate
        for candidate in evaluated
        if candidate.get("guardrail_verdict") == "PASS"
    ]

    meaningful = [
        candidate
        for candidate in safe_candidates
        if candidate.get("meaningful_gain")
    ]

    meaningful.sort(
        key=lambda candidate: _number(candidate.get("objective_gain"), 0.0),
        reverse=True,
    )

    safe_ranked = sorted(
        safe_candidates,
        key=lambda candidate: _number(candidate.get("objective_gain"), 0.0),
        reverse=True,
    )

    best = meaningful[0] if meaningful else None
    max_prb = _max_prb_cell(baseline_snapshot)

    ran_state = "HEALTHY"
    if baseline_guardrails.get("verdict") != "PASS":
        ran_state = "OUTSIDE_SAFE_ENVELOPE"
    if max_prb and _number(max_prb.get("prb_utilization_pct"), 0.0) >= PRB_CONGESTION_THRESHOLD_PCT:
        ran_state = "CAPACITY_CONGESTION"

    fault = local_observation.get("fault_state") or {}
    if bool(fault.get("active")) and str(fault.get("type", "")).upper() == "TX_POWER_DROP":
        ran_state = "RF_DEGRADATION"

    search_summary = {
        "method": "NETWORK_WIDE_SCREEN_THEN_BOUNDED_PHYSICS_SEARCH",
        "configured_cells_scanned": screening["configured_cells_scanned"],
        "serving_cells_scanned": screening["serving_cells_scanned"],
        "opportunity_cells_identified": screening["opportunity_cells_identified"],
        "shortlisted_cells": [row["cell_id"] for row in shortlist],
        "candidate_budget": int(max_candidate_evaluations),
        "candidates_generated": len(specs),
        "candidates_evaluated": len(evaluated),
        "safe_candidates": len(safe_candidates),
        "meaningful_candidates": len(meaningful),
        "evaluation_errors": evaluation_errors,
        "bandwidth_search": "NOT_EVALUATED_SPECTRUM_CAPABILITY_UNKNOWN",
    }

    context = {
        "source_active_version": local_observation.get("active_version"),
        "weather": deepcopy(local_observation.get("weather") or {}),
        "weather_timestamp": (
            (local_observation.get("weather") or {}).get("timestamp")
        ),
        "weather_source": (
            (local_observation.get("weather") or {}).get("source")
        ),
        "simulation_timestamp": local_observation.get("simulation_timestamp"),
        "traffic_multiplier": local_observation.get("traffic_multiplier"),
        "steering_mode": local_observation.get("steering_mode"),
        "context_policy": "ONE_FROZEN_CONTEXT_FOR_BASELINE_AND_ALL_CANDIDATES",
    }

    ranking_preview = [
        {
            "target_cell": candidate.get("target_cell"),
            "target_antenna": candidate.get("target_antenna"),
            "parameter": candidate.get("parameter"),
            "current_value": candidate.get("current_value"),
            "target_value": candidate.get("target_value"),
            "objective_gain": candidate.get("objective_gain"),
            "guardrail_verdict": candidate.get("guardrail_verdict"),
            "network_delta": deepcopy(candidate.get("network_delta")),
        }
        for candidate in safe_ranked[:5]
    ]

    if best is None:
        evidence = _cell_evidence(max_prb)
        if not evidence and shortlist:
            evidence = deepcopy(shortlist[0].get("evidence") or {})

        return {
            "ran_state": ran_state,
            "optimization_state": "NO_MEANINGFUL_GAIN",
            "target_cell": evidence.get("cell_id") if evidence else None,
            "target_antenna": None,
            "scope_cells": [],
            "evidence": evidence,
            "recommended_action": "NO_ACTION",
            "proposed_change": "No safe candidate produced a meaningful network-wide gain",
            "parameter": None,
            "current_value": None,
            "target_value": None,
            "delta": None,
            "objective_gain": 0.0,
            "objective_weights": deepcopy(OBJECTIVE_WEIGHTS),
            "baseline_summary": baseline_summary,
            "predicted_network_effect": {},
            "cell_impact": [],
            "reason": (
                "The complete configured-cell inventory was screened. "
                "No bounded candidate both passed guardrails and improved "
                "the transparent network-wide objective beyond the noise threshold."
            ),
            "review": "NONE",
            "search_summary": search_summary,
            "context": context,
            "candidate_ranking": ranking_preview,
            "active_version": local_observation.get("active_version"),
            "recovery_target_version": local_observation.get("recovery_target_version"),
        }

    action = _action_from_candidate(best, local_observation)

    return {
        "ran_state": ran_state,
        "optimization_state": "OPPORTUNITY_FOUND",
        "target_cell": best.get("target_cell"),
        "target_antenna": best.get("target_antenna"),
        "scope_cells": [best.get("target_cell")]
        if best.get("target_cell")
        else [],
        "evidence": _cell_evidence(
            baseline_snapshot.get("cells", {}).get(best.get("target_cell"))
        ),
        "recommended_action": action,
        "proposed_change": _proposed_change(best),
        "parameter": best.get("parameter"),
        "current_value": best.get("current_value"),
        "target_value": best.get("target_value"),
        "delta": best.get("delta"),
        "objective_gain": best.get("objective_gain"),
        "objective_components": deepcopy(best.get("objective_components")),
        "objective_weights": deepcopy(OBJECTIVE_WEIGHTS),
        "baseline_summary": baseline_summary,
        "predicted_network_effect": deepcopy(best.get("network_delta")),
        "candidate_summary": deepcopy(best.get("candidate_summary")),
        "cell_impact": deepcopy(best.get("cell_impact")),
        "guardrail_verdict": best.get("guardrail_verdict"),
        "failed_guardrails": deepcopy(best.get("failed_guardrails")),
        "reason": (
            _candidate_reason(best)
            + " The value was selected by simulated network outcome, not by rollback history."
        ),
        "review": "GUARDED_APPLY_REQUIRED"
        if action != "TRAFFIC_STEERING"
        else "AUTHORIZED_RECOVERY_OR_POLICY_ACTION_REQUIRED",
        "search_summary": search_summary,
        "context": context,
        "candidate_ranking": ranking_preview,
        "active_version": local_observation.get("active_version"),
        "recovery_target_version": local_observation.get("recovery_target_version"),
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

    def __init__(
        self,
        controller,
        interval_seconds=60.0,
        max_target_cells=DEFAULT_MAX_TARGET_CELLS,
        max_candidate_evaluations=DEFAULT_MAX_CANDIDATE_EVALUATIONS,
        background_enabled=True,
    ):
        self._controller = controller
        self._interval_seconds = max(10.0, float(interval_seconds))
        self._max_target_cells = max(1, int(max_target_cells))
        self._max_candidate_evaluations = max(
            1, int(max_candidate_evaluations)
        )
        self._background_enabled = bool(background_enabled)
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
            if not self._background_enabled:
                return
            if self._running:
                return

            self._stop_event.clear()
            self._running = True
            self._thread = Thread(
                target=self._worker,
                name="ran-network-optimization-evaluator",
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
        self.evaluate_now(trigger="STARTUP")

        while not self._stop_event.wait(self._interval_seconds):
            self.evaluate_now(trigger="PERIODIC")

    def evaluate_now(self, trigger="MANUAL"):
        with self._evaluation_lock:
            try:
                observation = self._controller.get_optimization_observation()

                recommendation = run_network_optimization_search(
                    observation,
                    max_target_cells=self._max_target_cells,
                    max_candidate_evaluations=self._max_candidate_evaluations,
                )

                with self._state_lock:
                    self._evaluation_counter += 1
                    evaluation_id = f"OPT-{self._evaluation_counter:06d}"

                result = {
                    "evaluation_id": evaluation_id,
                    "timestamp": _utc_now_iso(),
                    "trigger": str(trigger).upper(),
                    "evaluation_mode": "READ_ONLY_NETWORK_SEARCH",
                    "automatic_actuation": "DISABLED",
                    "actuation_performed": False,
                    **recommendation,
                }

            except Exception as exc:
                with self._state_lock:
                    self._evaluation_counter += 1
                    evaluation_id = f"OPT-{self._evaluation_counter:06d}"

                result = {
                    "evaluation_id": evaluation_id,
                    "timestamp": _utc_now_iso(),
                    "trigger": str(trigger).upper(),
                    "evaluation_mode": "READ_ONLY_NETWORK_SEARCH",
                    "automatic_actuation": "DISABLED",
                    "actuation_performed": False,
                    "ran_state": "EVALUATION_ERROR",
                    "optimization_state": "EVALUATION_ERROR",
                    "target_cell": None,
                    "target_antenna": None,
                    "scope_cells": [],
                    "evidence": {},
                    "recommended_action": "NO_ACTION",
                    "proposed_change": "No change - network optimization evaluation failed",
                    "parameter": None,
                    "current_value": None,
                    "target_value": None,
                    "delta": None,
                    "objective_gain": None,
                    "predicted_network_effect": {},
                    "cell_impact": [],
                    "search_summary": {},
                    "context": {},
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
            thread_alive = bool(self._thread and self._thread.is_alive())

            return {
                "status": (
                    "RUNNING" if self._running
                    else "MANUAL_ONLY" if not self._background_enabled
                    else "STOPPED"
                ),
                "worker_alive": thread_alive,
                "background_enabled": self._background_enabled,
                "interval_seconds": self._interval_seconds,
                "evaluation_mode": "READ_ONLY_NETWORK_SEARCH",
                "automatic_actuation": "DISABLED",
                "max_target_cells": self._max_target_cells,
                "max_candidate_evaluations": self._max_candidate_evaluations,
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
#optimization-loop .opt-button:hover { background: #334155; }
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
            <div class="opt-title">Network-wide Optimization Evaluator</div>
            <div class="opt-subtitle">
                Every 60 s: scan all configured cells, shortlist opportunities,
                simulate bounded physics/UE/weather candidates, validate guardrails,
                and recommend the best safe network-wide result. Automatic actuation is disabled.
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
            <div class="opt-label">RAN guardrail state</div>
            <div id="opt-ran-state" class="opt-value">-</div>
        </div>
        <div class="opt-card">
            <div class="opt-label">Optimization state</div>
            <div id="opt-optimization-state" class="opt-value">-</div>
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
            <div class="opt-label">Objective gain</div>
            <div id="opt-objective-gain" class="opt-value">-</div>
        </div>
        <div class="opt-card">
            <div class="opt-label">Search coverage</div>
            <div id="opt-search-coverage" class="opt-value">-</div>
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
        <div id="opt-effect" class="opt-evidence">Predicted network effect: -</div>
        <div id="opt-reason" class="opt-subtitle" style="margin-top:10px">-</div>
    </div>
</div>
"""


_OPTIMIZATION_SCRIPT = r"""
<script id="optimization-loop-script">
function optimizationStateClass(state) {
    if (state === "HEALTHY" || state === "NO_MEANINGFUL_GAIN") return "opt-good";
    if (state === "EVALUATION_ERROR") return "opt-bad";
    return "opt-warn";
}

function formatOptimizationEvidence(evidence) {
    if (!evidence || Object.keys(evidence).length === 0) return "Evidence: -";
    const parts = [];
    if (evidence.prb_utilization_pct !== undefined && evidence.prb_utilization_pct !== null) parts.push(`PRB ${evidence.prb_utilization_pct}%`);
    if (evidence.rsrp_dbm !== undefined && evidence.rsrp_dbm !== null) parts.push(`RSRP ${evidence.rsrp_dbm} dBm`);
    if (evidence.sinr_db !== undefined && evidence.sinr_db !== null) parts.push(`SINR ${evidence.sinr_db} dB`);
    if (evidence.active_users !== undefined) parts.push(`Active UE ${evidence.active_users}`);
    if (evidence.band) parts.push(`Band ${evidence.band}`);
    return `Current evidence: ${parts.join(" | ")}`;
}

function formatNetworkEffect(effect) {
    if (!effect || Object.keys(effect).length === 0) return "Predicted network effect: -";
    const parts = [];
    if (effect.weighted_sinr_db !== undefined && effect.weighted_sinr_db !== null) parts.push(`weighted SINR ${Number(effect.weighted_sinr_db).toFixed(3)} dB`);
    if (effect.weighted_rsrp_db !== undefined && effect.weighted_rsrp_db !== null) parts.push(`weighted RSRP ${Number(effect.weighted_rsrp_db).toFixed(3)} dB`);
    if (effect.aggregate_prb_pp !== undefined && effect.aggregate_prb_pp !== null) parts.push(`aggregate PRB ${Number(effect.aggregate_prb_pp).toFixed(3)} pp`);
    if (effect.max_prb_pp !== undefined && effect.max_prb_pp !== null) parts.push(`max PRB ${Number(effect.max_prb_pp).toFixed(3)} pp`);
    if (effect.served_ratio_pp !== undefined && effect.served_ratio_pp !== null) parts.push(`served ratio ${Number(effect.served_ratio_pp).toFixed(3)} pp`);
    if (effect.degraded_ue_change !== undefined && effect.degraded_ue_change !== null) parts.push(`degraded UE ${effect.degraded_ue_change >= 0 ? "+" : ""}${effect.degraded_ue_change}`);
    return `Predicted network effect: ${parts.join(" | ")}`;
}

async function refreshOptimizationLoop() {
    try {
        const response = await fetch("/optimization/status", { cache: "no-store" });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const data = await response.json();
        const last = data.last_evaluation || {};
        const search = last.search_summary || {};

        const loop = document.getElementById("opt-loop-status");
        const lastTime = document.getElementById("opt-last-evaluation");
        const ranState = document.getElementById("opt-ran-state");
        const optimizationState = document.getElementById("opt-optimization-state");
        const target = document.getElementById("opt-target-cell");
        const action = document.getElementById("opt-recommended-action");
        const objective = document.getElementById("opt-objective-gain");
        const coverage = document.getElementById("opt-search-coverage");
        const auto = document.getElementById("opt-auto-actuation");
        const proposed = document.getElementById("opt-proposed-change");
        const evidence = document.getElementById("opt-evidence");
        const effect = document.getElementById("opt-effect");
        const reason = document.getElementById("opt-reason");

        loop.textContent = `${data.status} / ${data.interval_seconds}s`;
        loop.className = `opt-value ${data.status === "RUNNING" ? "opt-good" : "opt-bad"}`;

        lastTime.textContent = last.timestamp ? new Date(last.timestamp).toLocaleTimeString() : "waiting";

        ranState.textContent = last.ran_state || "waiting";
        ranState.className = `opt-value ${optimizationStateClass(last.ran_state)}`;

        optimizationState.textContent = last.optimization_state || "waiting";
        optimizationState.className = `opt-value ${optimizationStateClass(last.optimization_state)}`;

        target.textContent = last.target_cell || "-";
        action.textContent = last.recommended_action || "-";
        objective.textContent = last.objective_gain !== undefined && last.objective_gain !== null
            ? `${Number(last.objective_gain).toFixed(3)}`
            : "-";
        coverage.textContent = search.configured_cells_scanned !== undefined
            ? `${search.configured_cells_scanned} cells / ${search.candidates_evaluated || 0} candidates`
            : "-";
        auto.textContent = data.automatic_actuation || "DISABLED";
        proposed.textContent = last.proposed_change || "-";
        evidence.textContent = formatOptimizationEvidence(last.evidence);
        effect.textContent = formatNetworkEffect(last.predicted_network_effect);
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
    """Inject the network-wide evaluator card into the existing dashboard."""

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
