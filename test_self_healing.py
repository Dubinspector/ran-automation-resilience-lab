from copy import deepcopy
from unittest.mock import patch

from app.ran_controller import (
    RanAutomationController,
)

from app.ran_engine import (
    DEFAULT_WEATHER,
)


# =========================================================
# FIXED REGRESSION CONTEXT
# =========================================================
#
# Environmental observation time and traffic simulation time are
# deliberately different. Every before/after comparison in one
# self-healing operation still uses the same pair.
# =========================================================

TEST_WEATHER = deepcopy(
    DEFAULT_WEATHER
)

TEST_WEATHER[
    "source"
] = "TEST_FIXED"

TEST_WEATHER[
    "source_status"
] = "FIXED"

TEST_WEATHER[
    "timestamp"
] = "2026-08-28T12:40:00+02:00"


TEST_SIMULATION_TIMESTAMP = (
    "2026-08-28T00:40:00+02:00"
)


TARGET_SITE_ID = (
    "SITE-JESENICE-01"
)

TARGET_BAND = (
    "n78"
)

FAULT_TX_POWER_DBM = (
    30.0
)


# =========================================================
# HELPERS
# =========================================================

def target_cells(
    state
):

    return [
        cell
        for cell in state[
            "configuration"
        ][
            "cells"
        ]
        if (
            cell[
                "site_id"
            ]
            == TARGET_SITE_ID
            and
            cell[
                "band"
            ]
            == TARGET_BAND
            and
            cell.get(
                "enabled",
                True
            )
        )
    ]


def powers_by_cell(
    state
):

    return {
        cell[
            "cell_id"
        ]:
            float(
                cell[
                    "tx_power_dbm"
                ]
            )
        for cell in target_cells(
            state
        )
    }


def print_scope(
    title,
    scope
):

    print()
    print("=" * 100)
    print(title)
    print("=" * 100)
    print()

    print(
        "Configured cells:",
        scope.get(
            "configured_cells"
        )
    )

    print(
        "Serving cells:",
        scope.get(
            "serving_cells"
        )
    )

    print(
        "Active UE:",
        scope.get(
            "active_users"
        )
    )

    print(
        "Mean RSRP [dBm]:",
        scope.get(
            "mean_rsrp_dbm"
        )
    )

    print(
        "Mean SINR [dB]:",
        scope.get(
            "mean_sinr_db"
        )
    )

    print(
        "Max PRB [%]:",
        scope.get(
            "max_prb_utilization_pct"
        )
    )


# =========================================================
# INITIALIZE DETERMINISTIC CONTROLLER
# =========================================================

print()
print("=" * 100)
print("SELF-HEALING REGRESSION TEST")
print("=" * 100)
print()

print(
    "Weather timestamp:",
    TEST_WEATHER[
        "timestamp"
    ]
)

print(
    "Traffic simulation timestamp:",
    TEST_SIMULATION_TIMESTAMP
)


with patch(
    "app.ran_controller.get_weather_snapshot",
    return_value=
        deepcopy(
            TEST_WEATHER
        ),
):

    controller = (
        RanAutomationController(
            simulation_timestamp=
                TEST_SIMULATION_TIMESTAMP
        )
    )


initial_state = (
    controller.get_active_state()
)

initial_version = (
    initial_state[
        "active_version"
    ]
)

initial_powers = (
    powers_by_cell(
        initial_state
    )
)

cell_ids = sorted(
    initial_powers
)


assert cell_ids, (
    "No target n78 cells found for self-healing test."
)


print()
print(
    "Target cells:",
    cell_ids
)

print(
    "Initial TX powers:",
    initial_powers
)

print(
    "Initial version:",
    initial_version
)


# =========================================================
# INJECT RF FAULT
# =========================================================

fault = (
    controller.inject_rf_fault(
        cell_ids=
            cell_ids,
        tx_power_dbm=
            FAULT_TX_POWER_DBM,
        weather=
            deepcopy(
                TEST_WEATHER
            ),
        simulation_timestamp=
            TEST_SIMULATION_TIMESTAMP,
    )
)


faulted_state = (
    controller.get_active_state()
)

faulted_powers = (
    powers_by_cell(
        faulted_state
    )
)


print_scope(
    "1 - BEFORE FAULT SCOPE",
    fault[
        "before_scope"
    ]
)

print_scope(
    "2 - AFTER FAULT SCOPE",
    fault[
        "after_scope"
    ]
)


print()
print(
    "Fault status:",
    fault[
        "status"
    ]
)

print(
    "Version after fault:",
    faulted_state[
        "active_version"
    ]
)

print(
    "Faulted TX powers:",
    faulted_powers
)


fault_status_check = (
    fault[
        "status"
    ]
    == "FAULT_INJECTED"
)

version_unchanged_after_fault = (
    faulted_state[
        "active_version"
    ]
    == initial_version
)

all_fault_powers_applied = all(
    power
    == FAULT_TX_POWER_DBM
    for power in faulted_powers.values()
)

fault_state_active = (
    controller.get_self_healing_state()[
        "fault_active"
    ]
    is True
)

fault_context_check = (
    fault[
        "weather"
    ][
        "timestamp"
    ]
    == TEST_WEATHER[
        "timestamp"
    ]
    and
    fault[
        "simulation_timestamp"
    ]
    == TEST_SIMULATION_TIMESTAMP
)


# =========================================================
# RUN SELF-HEALING
# =========================================================

recovery = (
    controller.run_self_healing(
        weather=
            deepcopy(
                TEST_WEATHER
            ),
        simulation_timestamp=
            TEST_SIMULATION_TIMESTAMP,
    )
)


recovered_state = (
    controller.get_active_state()
)

recovered_powers = (
    powers_by_cell(
        recovered_state
    )
)


print_scope(
    "3 - SELF-HEAL BEFORE SCOPE",
    recovery[
        "before_scope"
    ]
)

print_scope(
    "4 - SELF-HEAL AFTER SCOPE",
    recovery[
        "after_scope"
    ]
)


print()
print(
    "Recovery status:",
    recovery[
        "status"
    ]
)

print(
    "Recovery reason:",
    recovery[
        "reason"
    ]
)

print(
    "Version after recovery:",
    recovered_state[
        "active_version"
    ]
)

print(
    "Recovered TX powers:",
    recovered_powers
)

print(
    "Full safe envelope restored:",
    recovery[
        "full_safe_envelope_restored"
    ]
)

print(
    "Remaining failed checks:",
    recovery[
        "remaining_failed_checks"
    ]
)


recovery_status_check = (
    recovery[
        "status"
    ]
    == "RECOVERED"
)

configuration_restored_check = (
    recovery[
        "configuration_restored"
    ]
    is True
)

powers_restored_check = (
    recovered_powers
    == initial_powers
)

version_unchanged_after_recovery = (
    recovered_state[
        "active_version"
    ]
    == initial_version
)

fault_cleared_check = (
    controller.get_self_healing_state()[
        "fault_active"
    ]
    is False
)

recovery_context_check = (
    recovery[
        "weather"
    ][
        "timestamp"
    ]
    == TEST_WEATHER[
        "timestamp"
    ]
    and
    recovery[
        "simulation_timestamp"
    ]
    == TEST_SIMULATION_TIMESTAMP
)

revision_semantics_check = (
    fault[
        "configuration_revision_changed"
    ]
    is False
    and
    recovery[
        "configuration_revision_changed"
    ]
    is False
)


# =========================================================
# NO-ACTION SAFETY CHECK
# =========================================================
#
# A second recovery call without an active injected fault must not
# mutate configuration or pretend that a generic capacity problem was
# automatically repaired.
# =========================================================

no_action = (
    controller.run_self_healing(
        weather=
            deepcopy(
                TEST_WEATHER
            ),
        simulation_timestamp=
            TEST_SIMULATION_TIMESTAMP,
    )
)

no_action_check = (
    no_action[
        "status"
    ]
    == "NO_ACTION"
    and
    no_action[
        "reason"
    ]
    == "NO_ACTIVE_INJECTED_FAULT"
    and
    no_action[
        "configuration_changed"
    ]
    is False
)


# =========================================================
# FINAL VERIFICATION
# =========================================================

checks = {
    "RF fault injection accepted":
        fault_status_check,

    "Accepted config revision unchanged by fault":
        version_unchanged_after_fault,

    "Fault TX power applied to all target cells":
        all_fault_powers_applied,

    "Self-healing trigger active after fault":
        fault_state_active,

    "Fault uses fixed weather + traffic context":
        fault_context_check,

    "Self-healing returns RECOVERED":
        recovery_status_check,

    "Known-good configuration restored":
        configuration_restored_check,

    "Target TX powers restored":
        powers_restored_check,

    "Accepted config revision unchanged by recovery":
        version_unchanged_after_recovery,

    "Injected fault cleared":
        fault_cleared_check,

    "Recovery uses fixed weather + traffic context":
        recovery_context_check,

    "Fault/recovery do not create config revision":
        revision_semantics_check,

    "Recovery without authorized fault is NO_ACTION":
        no_action_check,
}


print()
print("=" * 100)
print("5 - SELF-HEALING STATE MACHINE VERIFICATION")
print("=" * 100)
print()

for name, passed in checks.items():

    print(
        f"{name}:",
        "PASS" if passed else "FAIL"
    )


all_passed = all(
    checks.values()
)


print()
print(
    "OVERALL SELF-HEALING TEST:",
    "PASS" if all_passed else "FAIL"
)


if not all_passed:
    raise SystemExit(1)
