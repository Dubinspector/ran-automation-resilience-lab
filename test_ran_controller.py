from copy import deepcopy
from unittest.mock import patch

from app.ran_controller import (
    RanAutomationController,
)

from app.ran_engine import (
    DEFAULT_WEATHER,
)


# =========================================================
# FIXED REGRESSION ENVIRONMENT
# =========================================================
#
# Regression tests must not depend on:
#
# - current clock time,
# - live Open-Meteo data,
# - current traffic activity profile.
#
# Weather observation time and traffic simulation time are
# intentionally different in this regression.
#
# The environmental snapshot is marked 12:40, while the traffic
# simulation clock is fixed at 00:40. The result must therefore
# remain the deterministic NIGHT profile with 274 active UEs.
#
# This explicitly proves that weather observation validity no longer
# selects the traffic activity profile. Live behaviour is tested
# separately.
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


# =========================================================
# HELPERS
# =========================================================

def find_inventory_cell(
    state,
    cell_id,
):

    for cell in state[
        "configuration"
    ][
        "cells"
    ]:

        if (
            cell[
                "cell_id"
            ]
            == cell_id
        ):

            return cell

    raise ValueError(
        f"Cell not found in state: {cell_id}"
    )


def print_state(
    title,
    controller,
    target_cell_id,
):

    state = (
        controller.get_active_state()
    )

    target = (
        find_inventory_cell(
            state,
            target_cell_id,
        )
    )

    print()
    print("=" * 110)
    print(title)
    print("=" * 110)
    print()

    print(
        "Active version:",
        state[
            "active_version"
        ],
    )

    print(
        "Rollout state:",
        state[
            "rollout_state"
        ],
    )

    print(
        "Last action:",
        state[
            "last_action"
        ],
    )

    print(
        "Weather timestamp:",
        state[
            "weather"
        ][
            "timestamp"
        ],
    )

    print(
        "Weather source:",
        state[
            "weather"
        ].get(
            "source",
            "-",
        ),
    )

    print(
        "Simulation timestamp:",
        state[
            "simulation_timestamp"
        ],
    )

    print(
        "Target cell:",
        target_cell_id,
    )

    print(
        "Target TX [dBm]:",
        target[
            "tx_power_dbm"
        ],
    )

    print(
        "Requested active UEs:",
        state[
            "service"
        ][
            "requested_active_ues"
        ],
    )

    print(
        "Served UEs:",
        state[
            "service"
        ][
            "served_active_ues"
        ],
    )

    print(
        "Unserved UEs:",
        state[
            "service"
        ][
            "unserved_active_ues"
        ],
    )

    print(
        "Served ratio [%]:",
        state[
            "service"
        ][
            "served_ratio_pct"
        ],
    )

    return state


# =========================================================
# TEST CONFIGURATION
# =========================================================

TARGET_CELL_ID = (
    "CELL-JES-A-N78"
)


SAFE_CELL_UPDATES = {

    TARGET_CELL_ID: {

        "tx_power_dbm":
            48.0,
    },
}


HARMFUL_CELL_UPDATES = {

    "CELL-JES-A-N28": {
        "tx_power_dbm": 30.0,
    },

    "CELL-JES-A-B3": {
        "tx_power_dbm": 30.0,
    },

    "CELL-JES-A-N78": {
        "tx_power_dbm": 30.0,
    },

    "CELL-JES-B-N28": {
        "tx_power_dbm": 30.0,
    },

    "CELL-JES-B-B3": {
        "tx_power_dbm": 30.0,
    },

    "CELL-JES-B-N78": {
        "tx_power_dbm": 30.0,
    },

    "CELL-JES-C-N28": {
        "tx_power_dbm": 30.0,
    },

    "CELL-JES-C-B3": {
        "tx_power_dbm": 30.0,
    },

    "CELL-JES-C-N78": {
        "tx_power_dbm": 30.0,
    },
}


HARMFUL_ANTENNA_UPDATES = {

    "ANT-JES-A-LOWMID": {
        "electrical_tilt_deg": 12.0,
    },

    "ANT-JES-A-N78": {
        "electrical_tilt_deg": 12.0,
    },

    "ANT-JES-B-LOWMID": {
        "electrical_tilt_deg": 12.0,
    },

    "ANT-JES-B-N78": {
        "electrical_tilt_deg": 12.0,
    },

    "ANT-JES-C-LOWMID": {
        "electrical_tilt_deg": 12.0,
    },

    "ANT-JES-C-N78": {
        "electrical_tilt_deg": 12.0,
    },
}


# =========================================================
# INITIALIZE CONTROLLER
# =========================================================
#
# RanAutomationController normally resolves live weather
# during construction.
#
# For this regression test only, patch the imported weather
# provider so initial state is deterministic as well.
# =========================================================

print()
print("=" * 110)
print("RAN AUTOMATION CONTROLLER TEST")
print("=" * 110)

print()
print(
    "Regression weather:",
    TEST_WEATHER[
        "timestamp"
    ],
)

print(
    "Regression weather mode:",
    TEST_WEATHER[
        "source_status"
    ],
)

print(
    "Regression traffic clock:",
    TEST_SIMULATION_TIMESTAMP,
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


initial_state = print_state(

    "1 - INITIAL KNOWN-GOOD STATE",

    controller,

    TARGET_CELL_ID,
)


# =========================================================
# INITIAL DETERMINISM CHECK
# =========================================================

initial_weather_check = (

    initial_state[
        "weather"
    ][
        "timestamp"
    ]
    == TEST_WEATHER[
        "timestamp"
    ]
)


initial_simulation_time_check = (

    initial_state[
        "simulation_timestamp"
    ]
    == TEST_SIMULATION_TIMESTAMP
)


initial_traffic_check = (

    initial_state[
        "service"
    ][
        "requested_active_ues"
    ]
    == 274
)


traffic_clock_decoupled_check = (

    TEST_WEATHER[
        "timestamp"
    ]
    != TEST_SIMULATION_TIMESTAMP

    and

    initial_simulation_time_check

    and

    initial_traffic_check
)


print()
print(
    "Fixed weather applied:",
    (
        "PASS"
        if initial_weather_check
        else "FAIL"
    ),
)

print(
    "Fixed traffic simulation timestamp:",
    (
        "PASS"
        if initial_simulation_time_check
        else "FAIL"
    ),
)

print(
    "Weather time decoupled from NIGHT traffic:",
    (
        "PASS"
        if traffic_clock_decoupled_check
        else "FAIL"
    ),
)

print(
    "Deterministic NIGHT traffic:",
    (
        "PASS"
        if initial_traffic_check
        else "FAIL"
    ),
)


# =========================================================
# EVALUATE SAFE CANDIDATE
# =========================================================
#
# evaluate() must:
#
# - use the fixed environment,
# - leave active configuration unchanged,
# - return PASS for the known safe candidate.
# =========================================================

evaluation = (
    controller.evaluate(

        cell_updates=
            SAFE_CELL_UPDATES,

        weather=
            deepcopy(
                TEST_WEATHER
            ),

        simulation_timestamp=
            TEST_SIMULATION_TIMESTAMP,
    )
)


print()
print("=" * 110)
print("2 - SAFE CANDIDATE EVALUATE ONLY")
print("=" * 110)
print()

print(
    "Operation:",
    evaluation[
        "operation"
    ],
)

print(
    "Attempt ID:",
    evaluation[
        "attempt_id"
    ],
)

print(
    "Baseline version:",
    evaluation[
        "baseline_version"
    ],
)

print(
    "Candidate version:",
    evaluation[
        "candidate_version"
    ],
)

print(
    "Active version after evaluate:",
    evaluation[
        "active_version"
    ],
)

print(
    "Weather:",
    evaluation[
        "weather"
    ][
        "timestamp"
    ],
)

print(
    "Simulation timestamp:",
    evaluation[
        "simulation_timestamp"
    ],
)

print(
    "Would be accepted:",
    evaluation[
        "would_be_accepted"
    ],
)

print(
    "Guardrail verdict:",
    evaluation[
        "guardrails"
    ][
        "verdict"
    ],
)

print(
    "Failed checks:",
    evaluation[
        "guardrails"
    ][
        "failed_check_count"
    ],
)

print(
    "Candidate service:",
    evaluation[
        "candidate_service"
    ],
)


# =========================================================
# ACTIVE STATE AFTER EVALUATE
# =========================================================

state_after_evaluate = print_state(

    "3 - ACTIVE STATE AFTER EVALUATE",

    controller,

    TARGET_CELL_ID,
)


# =========================================================
# SAFE GUARDED APPLY
# =========================================================

safe_apply = (
    controller.guarded_apply(

        cell_updates=
            SAFE_CELL_UPDATES,

        weather=
            deepcopy(
                TEST_WEATHER
            ),

        simulation_timestamp=
            TEST_SIMULATION_TIMESTAMP,
    )
)


print()
print("=" * 110)
print("4 - SAFE GUARDED APPLY")
print("=" * 110)
print()

print(
    "Status:",
    safe_apply[
        "status"
    ],
)

print(
    "Attempt ID:",
    safe_apply[
        "attempt_id"
    ],
)

print(
    "Previous version:",
    safe_apply.get(
        "previous_version"
    ),
)

print(
    "Candidate version:",
    safe_apply[
        "candidate_version"
    ],
)

print(
    "Active version:",
    safe_apply[
        "active_version"
    ],
)

print(
    "Weather:",
    safe_apply[
        "weather"
    ][
        "timestamp"
    ],
)

print(
    "Simulation timestamp:",
    safe_apply[
        "simulation_timestamp"
    ],
)

print(
    "Guardrail verdict:",
    safe_apply[
        "guardrails"
    ][
        "verdict"
    ],
)

print()
print(
    "Steps:"
)

for step in safe_apply[
    "steps"
]:

    print(
        " ",
        step[
            "status"
        ],
        "|",
        step[
            "step"
        ],
    )


state_after_safe_apply = print_state(

    "5 - ACTIVE STATE AFTER SAFE PROMOTION",

    controller,

    TARGET_CELL_ID,
)


# =========================================================
# CAPTURE KNOWN-GOOD STATE
# =========================================================

known_good_before_failure = (
    controller.get_active_state()
)


known_good_target = (
    find_inventory_cell(

        known_good_before_failure,

        TARGET_CELL_ID,
    )
)


known_good_version = (
    known_good_before_failure[
        "active_version"
    ]
)


known_good_tx = (
    known_good_target[
        "tx_power_dbm"
    ]
)


# =========================================================
# HARMFUL GUARDED APPLY
# =========================================================

harmful_apply = (
    controller.guarded_apply(

        cell_updates=
            HARMFUL_CELL_UPDATES,

        antenna_updates=
            HARMFUL_ANTENNA_UPDATES,

        weather=
            deepcopy(
                TEST_WEATHER
            ),

        simulation_timestamp=
            TEST_SIMULATION_TIMESTAMP,
    )
)


print()
print("=" * 110)
print("6 - HARMFUL GUARDED APPLY")
print("=" * 110)
print()

print(
    "Status:",
    harmful_apply[
        "status"
    ],
)

print(
    "Attempt ID:",
    harmful_apply[
        "attempt_id"
    ],
)

print(
    "Candidate version:",
    harmful_apply[
        "candidate_version"
    ],
)

print(
    "Active version:",
    harmful_apply[
        "active_version"
    ],
)

print(
    "Weather:",
    harmful_apply[
        "weather"
    ][
        "timestamp"
    ],
)

print(
    "Simulation timestamp:",
    harmful_apply[
        "simulation_timestamp"
    ],
)

print(
    "Guardrail verdict:",
    harmful_apply[
        "guardrails"
    ][
        "verdict"
    ],
)

print(
    "Failed checks:",
    harmful_apply[
        "guardrails"
    ][
        "failed_check_count"
    ],
)


print()
print(
    "Failed guardrails:"
)


for check in harmful_apply[
    "guardrails"
][
    "failed_checks"
]:

    print(
        " ",
        check[
            "name"
        ],
        "| delta:",
        check[
            "delta"
        ],
        "| limit:",
        check[
            "limit"
        ],
    )


print()
print(
    "Steps:"
)


for step in harmful_apply[
    "steps"
]:

    print(
        " ",
        step[
            "status"
        ],
        "|",
        step[
            "step"
        ],
    )


print()

print(
    "Rollback verification verdict:",
    harmful_apply[
        "rollback_verification"
    ][
        "verdict"
    ],
)


# =========================================================
# VERIFY RESTORED KNOWN-GOOD
# =========================================================

restored_state = print_state(

    "7 - ACTIVE STATE AFTER FAILED CANDIDATE",

    controller,

    TARGET_CELL_ID,
)


restored_target = (
    find_inventory_cell(

        restored_state,

        TARGET_CELL_ID,
    )
)


restored_version = (
    restored_state[
        "active_version"
    ]
)


restored_tx = (
    restored_target[
        "tx_power_dbm"
    ]
)


print()
print("=" * 110)
print("8 - KNOWN-GOOD RESTORE CHECK")
print("=" * 110)
print()

print(
    "Known-good version before failure:",
    known_good_version,
)

print(
    "Version after rollback:",
    restored_version,
)

print(
    "Known-good target TX [dBm]:",
    known_good_tx,
)

print(
    "Target TX after rollback [dBm]:",
    restored_tx,
)


version_restored = (

    restored_version
    == known_good_version
)


tx_restored = (

    restored_tx
    == known_good_tx
)


print()

print(
    "Version restore:",
    (
        "PASS"
        if version_restored
        else "FAIL"
    ),
)

print(
    "Configuration restore:",
    (
        "PASS"
        if tx_restored
        else "FAIL"
    ),
)


# =========================================================
# STATE MACHINE CHECK
# =========================================================

safe_evaluate_check = (

    evaluation[
        "active_version"
    ]
    == "CONFIG-1.0"

    and

    evaluation[
        "would_be_accepted"
    ]
    is True

    and

    evaluation[
        "guardrails"
    ][
        "verdict"
    ]
    == "PASS"

    and

    evaluation[
        "guardrails"
    ][
        "failed_check_count"
    ]
    == 0
)


safe_apply_check = (

    safe_apply[
        "status"
    ]
    == "APPLIED"

    and

    safe_apply[
        "active_version"
    ]
    == "CONFIG-1.1"

    and

    safe_apply[
        "guardrails"
    ][
        "verdict"
    ]
    == "PASS"
)


harmful_rollback_check = (

    harmful_apply[
        "status"
    ]
    == "ROLLED_BACK"

    and

    harmful_apply[
        "active_version"
    ]
    == "CONFIG-1.1"

    and

    harmful_apply[
        "guardrails"
    ][
        "verdict"
    ]
    == "FAIL"

    and

    harmful_apply[
        "rollback_verification"
    ][
        "verdict"
    ]
    == "PASS"
)


operation_weather_check = (

    evaluation[
        "weather"
    ][
        "timestamp"
    ]
    == TEST_WEATHER[
        "timestamp"
    ]

    and

    safe_apply[
        "weather"
    ][
        "timestamp"
    ]
    == TEST_WEATHER[
        "timestamp"
    ]

    and

    harmful_apply[
        "weather"
    ][
        "timestamp"
    ]
    == TEST_WEATHER[
        "timestamp"
    ]
)


operation_simulation_time_check = (

    evaluation[
        "simulation_timestamp"
    ]
    == TEST_SIMULATION_TIMESTAMP

    and

    safe_apply[
        "simulation_timestamp"
    ]
    == TEST_SIMULATION_TIMESTAMP

    and

    harmful_apply[
        "simulation_timestamp"
    ]
    == TEST_SIMULATION_TIMESTAMP
)


overall_check = all(
    [

        initial_weather_check,

        initial_simulation_time_check,

        traffic_clock_decoupled_check,

        initial_traffic_check,

        safe_evaluate_check,

        safe_apply_check,

        harmful_rollback_check,

        version_restored,

        tx_restored,

        operation_weather_check,

        operation_simulation_time_check,
    ]
)


print()
print("=" * 110)
print("9 - STATE MACHINE VERIFICATION")
print("=" * 110)
print()

print(
    "Fixed regression weather:",
    (
        "PASS"
        if initial_weather_check
        else "FAIL"
    ),
)

print(
    "Traffic clock independent from weather timestamp:",
    (
        "PASS"
        if traffic_clock_decoupled_check
        else "FAIL"
    ),
)

print(
    "Deterministic NIGHT traffic = 274 UE:",
    (
        "PASS"
        if initial_traffic_check
        else "FAIL"
    ),
)

print(
    "Evaluate does not promote and candidate passes:",
    (
        "PASS"
        if safe_evaluate_check
        else "FAIL"
    ),
)

print(
    "Safe candidate promotes CONFIG-1.1:",
    (
        "PASS"
        if safe_apply_check
        else "FAIL"
    ),
)

print(
    "Harmful candidate rolls back:",
    (
        "PASS"
        if harmful_rollback_check
        else "FAIL"
    ),
)

print(
    "Known-good version preserved:",
    (
        "PASS"
        if version_restored
        else "FAIL"
    ),
)

print(
    "Known-good configuration preserved:",
    (
        "PASS"
        if tx_restored
        else "FAIL"
    ),
)

print(
    "All operations use fixed weather timestamp:",
    (
        "PASS"
        if operation_weather_check
        else "FAIL"
    ),
)

print(
    "All operations use fixed traffic simulation timestamp:",
    (
        "PASS"
        if operation_simulation_time_check
        else "FAIL"
    ),
)

print()

print(
    "OVERALL CONTROLLER TEST:",
    (
        "PASS"
        if overall_check
        else "FAIL"
    ),
)


# =========================================================
# EVENT TIMELINE
# =========================================================

print()
print("=" * 110)
print("10 - CONTROLLER EVENT TIMELINE")
print("=" * 110)


for event in controller.get_events():

    print()

    print(
        event[
            "timestamp"
        ]
    )

    print(
        " ",
        event[
            "event_type"
        ],
        "|",
        event[
            "status"
        ],
    )

    print(
        " ",
        event[
            "message"
        ],
    )

    print(
        "  Details:",
        event[
            "details"
        ],
    )


# =========================================================
# FINAL INTERPRETATION
# =========================================================

print()
print("=" * 110)
print("EXPECTED CONTROL LOOP")
print("=" * 110)

print(
    """
Regression environment:

fixed environmental observation
2026-08-28 12:40 +02:00
        |
        |  independent input
        v
fixed traffic simulation clock
2026-08-28 00:40 +02:00
        |
        v
deterministic NIGHT traffic
274 active UE

State transition:

CONFIG-1.0
    |
    | evaluate safe candidate
    | same fixed weather + traffic-clock context
    v
CONFIG-1.0
    |
    | guarded apply + guardrails PASS
    v
CONFIG-1.1   <-- new known-good
    |
    | harmful candidate evaluated
    | guardrails FAIL
    v
candidate rejected
    |
    | restore / verify previous known-good
    | same fixed weather + traffic-clock context
    v
CONFIG-1.1

The failed candidate must NOT increment the active
configuration revision.

The rollback must restore CONFIG-1.1, not the original
factory CONFIG-1.0.

The weather observation timestamp intentionally differs from the
traffic simulation timestamp. This proves that the two clocks are
separate inputs.

This regression test intentionally does NOT test current live traffic
or current live weather. Those belong to the runtime / integration
path.
"""
)
