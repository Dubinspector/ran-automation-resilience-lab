from app.ran_engine import (
    build_baseline_sites,
    build_candidate_sites,
    compare_cell_kpis,
    evaluate_ran_state,
    find_cell,
)


# =========================================================
# TEST TARGET
# =========================================================

TARGET_CELL_ID = (
    "CELL-JES-A-N78"
)

CANDIDATE_TX_POWER_DBM = (
    48.0
)


# =========================================================
# BASELINE CONFIGURATION
# =========================================================

baseline_sites = (
    build_baseline_sites()
)


baseline_cell_record = (
    find_cell(
        baseline_sites,
        TARGET_CELL_ID
    )
)


baseline_cell_config = (
    baseline_cell_record[
        "cell"
    ]
)


print()
print("=" * 100)
print("RAN ENGINE INTEGRATION TEST")
print("=" * 100)

print()

print(
    "Target cell:",
    TARGET_CELL_ID
)

print(
    "Baseline TX power [dBm]:",
    baseline_cell_config[
        "tx_power_dbm"
    ]
)

print(
    "Candidate TX power [dBm]:",
    CANDIDATE_TX_POWER_DBM
)


# =========================================================
# BASELINE RF + TRAFFIC SNAPSHOT
# =========================================================

print()
print("=" * 100)
print("BUILDING BASELINE SNAPSHOT")
print("=" * 100)


baseline_snapshot = (
    evaluate_ran_state(
        baseline_sites
    )
)


print()

print(
    "Requested active UEs:",
    baseline_snapshot[
        "service"
    ][
        "requested_active_ues"
    ]
)

print(
    "Served active UEs:",
    baseline_snapshot[
        "service"
    ][
        "served_active_ues"
    ]
)

print(
    "Unserved active UEs:",
    baseline_snapshot[
        "service"
    ][
        "unserved_active_ues"
    ]
)

print(
    "Served ratio [%]:",
    baseline_snapshot[
        "service"
    ][
        "served_ratio_pct"
    ]
)


# =========================================================
# BUILD CANDIDATE CONFIGURATION
# =========================================================

candidate_sites = (
    build_candidate_sites(

        base_sites=
            baseline_sites,

        cell_updates={

            TARGET_CELL_ID: {

                "tx_power_dbm":
                    CANDIDATE_TX_POWER_DBM
            }
        }
    )
)


candidate_cell_record = (
    find_cell(
        candidate_sites,
        TARGET_CELL_ID
    )
)


candidate_cell_config = (
    candidate_cell_record[
        "cell"
    ]
)


print()
print("=" * 100)
print("CANDIDATE CONFIGURATION")
print("=" * 100)

print()

print(
    "Target cell:",
    TARGET_CELL_ID
)

print(
    "Applied candidate TX power [dBm]:",
    candidate_cell_config[
        "tx_power_dbm"
    ]
)


# =========================================================
# VERIFY BASELINE WAS NOT MUTATED
# =========================================================

print()
print("=" * 100)
print("COPY ISOLATION CHECK")
print("=" * 100)

print()

print(
    "Baseline object TX [dBm]:",
    baseline_cell_config[
        "tx_power_dbm"
    ]
)

print(
    "Candidate object TX [dBm]:",
    candidate_cell_config[
        "tx_power_dbm"
    ]
)


if (
    baseline_cell_config[
        "tx_power_dbm"
    ]
    != candidate_cell_config[
        "tx_power_dbm"
    ]
):

    print(
        "Baseline/candidate isolation: PASS"
    )

else:

    print(
        "Baseline/candidate isolation: FAIL"
    )


# =========================================================
# CANDIDATE RF + TRAFFIC SNAPSHOT
# =========================================================

print()
print("=" * 100)
print("BUILDING CANDIDATE SNAPSHOT")
print("=" * 100)


candidate_snapshot = (
    evaluate_ran_state(
        candidate_sites
    )
)


print()

print(
    "Requested active UEs:",
    candidate_snapshot[
        "service"
    ][
        "requested_active_ues"
    ]
)

print(
    "Served active UEs:",
    candidate_snapshot[
        "service"
    ][
        "served_active_ues"
    ]
)

print(
    "Unserved active UEs:",
    candidate_snapshot[
        "service"
    ][
        "unserved_active_ues"
    ]
)

print(
    "Served ratio [%]:",
    candidate_snapshot[
        "service"
    ][
        "served_ratio_pct"
    ]
)


# =========================================================
# TARGET CELL KPI
# =========================================================

print()
print("=" * 100)
print("TARGET CELL KPI")
print("=" * 100)


baseline_target_kpi = (
    baseline_snapshot[
        "cells"
    ].get(
        TARGET_CELL_ID
    )
)


candidate_target_kpi = (
    candidate_snapshot[
        "cells"
    ].get(
        TARGET_CELL_ID
    )
)


print()

print(
    "Baseline:"
)

print(
    baseline_target_kpi
)


print()

print(
    "Candidate:"
)

print(
    candidate_target_kpi
)


# =========================================================
# KPI COMPARISON
# =========================================================

comparison = (
    compare_cell_kpis(

        baseline_snapshot,
        candidate_snapshot
    )
)


print()
print("=" * 100)
print("TARGET CELL DELTA")
print("=" * 100)

print()

print(
    comparison.get(
        TARGET_CELL_ID
    )
)


# =========================================================
# ALL CHANGED SERVING CELLS
# =========================================================

print()
print("=" * 100)
print("ALL OBSERVED SERVING-CELL CHANGES")
print("=" * 100)


changed_cells = []


for (
    cell_id,
    result
) in comparison.items():


    if (
        result[
            "status"
        ]
        != "COMPARABLE"
    ):

        changed_cells.append(

            (
                cell_id,
                result
            )
        )

        continue


    delta = (
        result[
            "delta"
        ]
    )


    if (

        delta[
            "prb_percentage_points"
        ]
        != 0

        or

        delta[
            "sinr_db"
        ]
        != 0

        or

        delta[
            "rsrp_db"
        ]
        != 0

        or

        delta[
            "active_users"
        ]
        != 0
    ):

        changed_cells.append(

            (
                cell_id,
                result
            )
        )


if not changed_cells:

    print()

    print(
        "No serving-cell KPI changes detected."
    )


for (
    cell_id,
    result
) in changed_cells:


    print()

    print(
        cell_id
    )

    print(
        "  Status:",
        result[
            "status"
        ]
    )


    if (
        result[
            "status"
        ]
        == "COMPARABLE"
    ):

        delta = (
            result[
                "delta"
            ]
        )


        print(
            "  PRB delta [pp]:",
            delta[
                "prb_percentage_points"
            ]
        )

        print(
            "  SINR delta [dB]:",
            delta[
                "sinr_db"
            ]
        )

        print(
            "  RSRP delta [dB]:",
            delta[
                "rsrp_db"
            ]
        )

        print(
            "  Active-user delta:",
            delta[
                "active_users"
            ]
        )


    elif (
        result[
            "status"
        ]
        == "NEW_SERVING_CELL"
    ):

        print(
            "  Candidate active users:",
            result[
                "candidate"
            ][
                "active_users"
            ]
        )


    elif (
        result[
            "status"
        ]
        == "NO_LONGER_SERVING"
    ):

        print(
            "  Baseline active users:",
            result[
                "baseline"
            ][
                "active_users"
            ]
        )


# =========================================================
# LARGEST SINR CHANGES
# =========================================================

comparable_changes = [

    (
        cell_id,
        result
    )

    for (
        cell_id,
        result
    ) in comparison.items()

    if (
        result[
            "status"
        ]
        == "COMPARABLE"
    )
]


largest_sinr_changes = sorted(

    comparable_changes,

    key=lambda item:
        abs(
            item[
                1
            ][
                "delta"
            ][
                "sinr_db"
            ]
        ),

    reverse=True
)


print()
print("=" * 100)
print("TOP 10 ABSOLUTE SINR CHANGES")
print("=" * 100)


for (
    index,
    (
        cell_id,
        result
    )
) in enumerate(

    largest_sinr_changes[
        :10
    ],

    start=1
):


    delta = (
        result[
            "delta"
        ]
    )


    print(

        f"{index:>2}.",

        cell_id,

        "| SINR:",

        delta[
            "sinr_db"
        ],

        "dB",

        "| RSRP:",

        delta[
            "rsrp_db"
        ],

        "dB",

        "| PRB:",

        delta[
            "prb_percentage_points"
        ],

        "pp",

        "| users:",

        delta[
            "active_users"
        ]
    )


# =========================================================
# ACCOUNTING CHECK
# =========================================================

print()
print("=" * 100)
print("CANDIDATE ACCOUNTING CHECK")
print("=" * 100)

print()


candidate_users_on_cells = sum(

    cell[
        "active_users"
    ]

    for cell
    in candidate_snapshot[
        "cells"
    ].values()
)


candidate_unserved = (

    candidate_snapshot[
        "service"
    ][
        "unserved_active_ues"
    ]
)


candidate_requested = (

    candidate_snapshot[
        "service"
    ][
        "requested_active_ues"
    ]
)


print(
    "Requested active UEs:",
    candidate_requested
)

print(
    "Users on serving cells:",
    candidate_users_on_cells
)

print(
    "Unserved active UEs:",
    candidate_unserved
)

print(
    "Assigned + unserved:",
    (
        candidate_users_on_cells
        + candidate_unserved
    )
)


if (
    candidate_users_on_cells
    + candidate_unserved
    == candidate_requested
):

    print(
        "Accounting check: PASS"
    )

else:

    print(
        "Accounting check: FAIL"
    )


# =========================================================
# INTERPRETATION
# =========================================================

print()
print("=" * 100)
print("INTERPRETATION")
print("=" * 100)

print(
    """
This test does NOT assume that increasing TX power is
automatically good or bad.

The important question is whether the configuration
change propagates through the physical model:

TX configuration
    ->
received signal and co-channel interference
    ->
SINR / RSRP
    ->
UE association
    ->
traffic distribution
    ->
cell KPI changes

We will inspect the resulting evidence before defining
automation guardrails.
"""
)