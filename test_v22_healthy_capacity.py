from copy import deepcopy
from unittest.mock import patch

from app.ran_controller import RanAutomationController
from app.ran_engine import DEFAULT_WEATHER


FIXED_WEATHER = deepcopy(DEFAULT_WEATHER)
FIXED_WEATHER.update({
    "timestamp": "2026-08-29T12:40:00+02:00",
    "source": "TEST_FIXED",
    "source_status": "FIXED",
})

NORMAL_TRAFFIC_MULTIPLIER = 0.25

# The runtime uses the current Europe/Prague traffic clock. A healthy
# factory/demo baseline therefore must not depend on which activity
# profile happens to be active when the interviewer opens the UI.
PROFILE_TIMESTAMPS = (
    ("NIGHT", "2026-08-29T01:40:00+02:00"),
    ("EARLY_MORNING", "2026-08-29T06:00:00+02:00"),
    ("MORNING_COMMUTE", "2026-08-29T08:00:00+02:00"),
    ("DAYTIME", "2026-08-29T12:40:00+02:00"),
    ("EVENING_BUSY_HOUR", "2026-08-29T18:00:00+02:00"),
    ("EVENING", "2026-08-29T21:00:00+02:00"),
    ("LATE_EVENING", "2026-08-29T23:30:00+02:00"),
)

DAYTIME_SIMULATION_TIMESTAMP = "2026-08-29T12:40:00+02:00"


def max_prb(health):
    item = health["guardrails"]["summary"].get("max_candidate_prb") or {}
    return item.get("prb_utilization_pct")


with patch(
    "app.ran_controller.get_weather_snapshot",
    return_value=deepcopy(FIXED_WEATHER),
):
    print("=" * 92)
    print("V2.2 ALL-DAY HEALTHY DEFAULT + CAPACITY SELF-HEAL TEST")
    print("=" * 92)

    # ---------------------------------------------------------
    # ALL-DAY DEFAULT-HEALTH REGRESSION
    # ---------------------------------------------------------
    for expected_profile, simulation_timestamp in PROFILE_TIMESTAMPS:
        profile_controller = RanAutomationController(
            simulation_timestamp=simulation_timestamp,
            traffic_multiplier=NORMAL_TRAFFIC_MULTIPLIER,
            steering_mode="LOAD_AWARE",
        )

        observation = profile_controller.get_baseline_health(
            weather=FIXED_WEATHER,
            simulation_timestamp=simulation_timestamp,
        )

        # get_baseline_health() intentionally returns the compact health/service
        # observation used by the API. The full population/traffic metadata
        # remains available through get_active_state(), which now represents
        # the exact same freshly observed simulation context.
        active_state = profile_controller.get_active_state()
        actual_profile = active_state["population_model"]["activity_profile"]
        health = observation["baseline_health"]

        print()
        print(
            expected_profile,
            "| actual=", actual_profile,
            "| requested_ue=", observation["service"]["requested_active_ues"],
            "| max_prb=", max_prb(health),
            "| health=", health["status"],
        )

        assert actual_profile["name"] == expected_profile
        assert health["status"] == "PASS", (
            f"v2.2 default baseline must be safe in {expected_profile}; "
            f"failed={health['failed_checks']}"
        )

    # ---------------------------------------------------------
    # DAYTIME CAPACITY FAULT + RECOVERY
    # ---------------------------------------------------------
    controller = RanAutomationController(
        simulation_timestamp=DAYTIME_SIMULATION_TIMESTAMP,
        traffic_multiplier=NORMAL_TRAFFIC_MULTIPLIER,
        steering_mode="LOAD_AWARE",
    )

    baseline = controller.get_baseline_health(
        weather=FIXED_WEATHER,
        simulation_timestamp=DAYTIME_SIMULATION_TIMESTAMP,
    )

    print()
    print("DAYTIME capacity scenario baseline:")
    print("Baseline status:", baseline["baseline_health"]["status"])
    print("Requested UE:", baseline["service"]["requested_active_ues"])
    print("Max PRB:", max_prb(baseline["baseline_health"]))
    print("Traffic context:", controller.get_self_healing_state())

    assert baseline["baseline_health"]["status"] == "PASS"

    revision_before = controller.active_version

    fault = controller.inject_capacity_spike(
        spike_factor=8.0,
        weather=FIXED_WEATHER,
        simulation_timestamp=DAYTIME_SIMULATION_TIMESTAMP,
    )

    print()
    print("Capacity fault status:", fault["status"])
    print("Requested spike:", fault.get("requested_spike_factor"))
    print("Hotspot area:", fault.get("hotspot_area_id"))
    print("Applied spike:", fault.get("applied_spike_factor"))
    print("Max PRB before:", fault.get("max_prb_before"))
    print("Max PRB after:", fault.get("max_prb_after"))
    print("Recovery preview safe:", fault.get("recovery_preview_safe"))

    assert fault["status"] == "FAULT_INJECTED"
    assert controller.active_version == revision_before
    assert fault["configuration_revision_changed"] is False
    assert fault["baseline_health_before"]["status"] == "PASS"
    assert fault["baseline_health_after"]["status"] == "FAIL", (
        "capacity injection must create an observable unsafe PRB state"
    )
    assert fault["recovery_preview_safe"] is True, (
        "capacity spike must be auto-calibrated to a recoverable demo point"
    )

    elevated_multiplier = fault["traffic_multiplier_after"]
    elevated_area_multipliers = deepcopy(
        fault["area_traffic_multipliers_after"]
    )

    assert fault["hotspot_area_id"] in elevated_area_multipliers
    assert fault["steering_mode_after"] == "LOAD_AWARE"

    healed = controller.run_self_healing(
        weather=FIXED_WEATHER,
        simulation_timestamp=DAYTIME_SIMULATION_TIMESTAMP,
    )

    print()
    print("Self-heal status:", healed["status"])
    print("Reason:", healed["reason"])
    print("Traffic multiplier remains:", healed.get("traffic_multiplier"))
    print(
        "Steering:",
        healed.get("steering_mode_before"),
        "->",
        healed.get("steering_mode_after"),
    )
    print("Max PRB:", healed.get("max_prb_before"), "->", healed.get("max_prb_after"))
    print("Full safe envelope:", healed.get("full_safe_envelope_restored"))

    assert healed["status"] == "RECOVERED"
    assert healed["full_safe_envelope_restored"] is True
    assert healed["traffic_multiplier"] == elevated_multiplier, (
        "capacity remediation must keep the global traffic scale fixed"
    )
    assert healed["area_traffic_multipliers"] == elevated_area_multipliers, (
        "capacity remediation must keep the local hotspot demand fixed"
    )
    assert healed["hotspot_area_id"] == fault["hotspot_area_id"]
    assert healed["steering_mode_before"] == "LOAD_AWARE"
    assert healed["steering_mode_after"] == "CAPACITY_RECOVERY"
    assert controller.active_version == revision_before
    assert controller.get_self_healing_state()["fault_active"] is False

    restored = controller.restore_factory_baseline(
        weather=FIXED_WEATHER,
        simulation_timestamp=DAYTIME_SIMULATION_TIMESTAMP,
    )

    assert restored["baseline_health"]["status"] == "PASS"
    final_state = controller.get_self_healing_state()
    assert final_state["traffic_multiplier"] == NORMAL_TRAFFIC_MULTIPLIER
    assert final_state["area_traffic_multipliers"] == {}
    assert final_state["steering_mode"] == "LOAD_AWARE"

print()
print("OVERALL V2.2 HEALTHY/CAPACITY TEST: PASS")
