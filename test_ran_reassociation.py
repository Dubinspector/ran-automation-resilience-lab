from app.ran_engine import (
    build_baseline_sites,
    build_candidate_sites,
    compare_cell_kpis,
    evaluate_ran_state,
    find_cell,
)


# =========================================================
# TEST CONFIGURATION
# =========================================================

TARGET_CELL_ID = (
    "CELL-JES-A-N78"
)

CANDIDATE_TX_POWER_DBM = (
    30.0
)


# =========================================================
# BASELINE
# =========================================================

baseline_sites = (
    build_baseline_sites()
)


baseline_cell = (
    find_cell(
        baseline_sites,
        TARGET_CELL_ID
    )[
        "cell"
    ]
)


baseline_snapshot = (
    evaluate_ran_state(
        baseline_sites
    )
)


# =========================================================
# CANDIDATE
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


candidate_cell = (
    find_cell(
        candidate_sites,
        TARGET_CELL_ID
    )[
        "cell"
    ]
)


candidate_snapshot = (
    evaluate_ran_state(
        candidate_sites
    )
)


# =========================================================
# CONFIGURATION CHECK
# =========================================================

print()
print("=" * 100)
print("RAN UE REASSOCIATION TEST")
print("=" * 100)

print()

print(
    "Target cell:",
    TARGET_CELL_ID
)

print(
    "Baseline TX [dBm]:",
    baseline_cell[
        "tx_power_dbm"
    ]
)

print(
    "Candidate TX [dBm]:",
    candidate_cell[
        "tx_power_dbm"
    ]
)


# =========================================================
# GLOBAL SERVICE
# =========================================================

print()
print("=" * 100)
print("GLOBAL SERVICE")
print("=" * 100)

print()

print(
    "Baseline served UEs:",
    baseline_snapshot[
        "service"
    ][
        "served_active_ues"
    ]
)

print(
    "Candidate served UEs:",
    candidate_snapshot[
        "service"
    ][
        "served_active_ues"
    ]
)

print(
    "Baseline unserved UEs:",
    baseline_snapshot[
        "service"
    ][
        "unserved_active_ues"
    ]
)

print(
    "Candidate unserved UEs:",
    candidate_snapshot[
        "service"
    ][
        "unserved_active_ues"
    ]
)

print(
    "Baseline served ratio [%]:",
    baseline_snapshot[
        "service"
    ][
        "served_ratio_pct"
    ]
)

print(
    "Candidate served ratio [%]:",
    candidate_snapshot[
        "service"
    ][
        "served_ratio_pct"
    ]
)


# =========================================================
# TARGET CELL
# =========================================================

print()
print("=" * 100)
print("TARGET CELL BEFORE / AFTER")
print("=" * 100)

print()

print(
    "Baseline KPI:"
)

print(
    baseline_snapshot[
        "cells"
    ].get(
        TARGET_CELL_ID
    )
)

print()

print(
    "Candidate KPI:"
)

print(
    candidate_snapshot[
        "cells"
    ].get(
        TARGET_CELL_ID
    )
)


# =========================================================
# UE ASSIGNMENTS
# =========================================================

baseline_assignments = {

    item[
        "sample_id"
    ]:
        item

    for item
    in baseline_snapshot[
        "assignments"
    ]
}


candidate_assignments = {

    item[
        "sample_id"
    ]:
        item

    for item
    in candidate_snapshot[
        "assignments"
    ]
}


changed_assignments = []


for sample_id in sorted(
    baseline_assignments
):

    baseline = (
        baseline_assignments[
            sample_id
        ]
    )

    candidate = (
        candidate_assignments[
            sample_id
        ]
    )


    baseline_cell_id = (
        baseline.get(
            "primary_cell_id"
        )
    )

    candidate_cell_id = (
        candidate.get(
            "primary_cell_id"
        )
    )


    if (
        baseline_cell_id
        != candidate_cell_id
    ):

        changed_assignments.append({

            "sample_id":
                sample_id,

            "area_id":
                baseline[
                    "area_id"
                ],

            "active_ues":
                baseline[
                    "active_ues"
                ],

            "baseline_cell_id":
                baseline_cell_id,

            "candidate_cell_id":
                candidate_cell_id,

            "baseline_band":
                baseline.get(
                    "band"
                ),

            "candidate_band":
                candidate.get(
                    "band"
                ),

            "baseline_rsrp_dbm":
                baseline.get(
                    "rsrp_dbm"
                ),

            "candidate_rsrp_dbm":
                candidate.get(
                    "rsrp_dbm"
                ),

            "baseline_sinr_db":
                baseline.get(
                    "sinr_db"
                ),

            "candidate_sinr_db":
                candidate.get(
                    "sinr_db"
                ),

            "baseline_serviceability":
                baseline.get(
                    "serviceability"
                ),

            "candidate_serviceability":
                candidate.get(
                    "serviceability"
                )
        })


print()
print("=" * 100)
print("UE REASSOCIATIONS")
print("=" * 100)


if not changed_assignments:

    print()

    print(
        "No UE sample changed primary cell."
    )


for change in changed_assignments:

    print()

    print(
        change[
            "sample_id"
        ]
    )

    print(
        "  Area:",
        change[
            "area_id"
        ]
    )

    print(
        "  Active UEs represented:",
        change[
            "active_ues"
        ]
    )

    print(
        "  Before:",
        change[
            "baseline_cell_id"
        ],
        "/",
        change[
            "baseline_band"
        ]
    )

    print(
        "  After:",
        change[
            "candidate_cell_id"
        ],
        "/",
        change[
            "candidate_band"
        ]
    )

    print(
        "  Before RSRP [dBm]:",
        change[
            "baseline_rsrp_dbm"
        ]
    )

    print(
        "  After RSRP [dBm]:",
        change[
            "candidate_rsrp_dbm"
        ]
    )

    print(
        "  Before SINR [dB]:",
        change[
            "baseline_sinr_db"
        ]
    )

    print(
        "  After SINR [dB]:",
        change[
            "candidate_sinr_db"
        ]
    )

    print(
        "  Before serviceability:",
        change[
            "baseline_serviceability"
        ]
    )

    print(
        "  After serviceability:",
        change[
            "candidate_serviceability"
        ]
    )


moved_active_ues = sum(

    item[
        "active_ues"
    ]

    for item
    in changed_assignments
)


print()
print(
    "UE samples with changed association:",
    len(
        changed_assignments
    )
)

print(
    "Active UEs represented by changed samples:",
    moved_active_ues
)


# =========================================================
# CELL KPI COMPARISON
# =========================================================

comparison = (
    compare_cell_kpis(

        baseline_snapshot,
        candidate_snapshot
    )
)


print()
print("=" * 100)
print("SERVING-CELL KPI CHANGES")
print("=" * 100)


for (
    cell_id,
    result
) in comparison.items():


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


        if (

            delta[
                "active_users"
            ]
            == 0

            and

            delta[
                "prb_percentage_points"
            ]
            == 0

            and

            delta[
                "sinr_db"
            ]
            == 0

            and

            delta[
                "rsrp_db"
            ]
            == 0
        ):

            continue


        print()

        print(
            cell_id
        )

        print(
            "  Status: COMPARABLE"
        )

        print(
            "  Active-user delta:",
            delta[
                "active_users"
            ]
        )

        print(
            "  RSRP delta [dB]:",
            delta[
                "rsrp_db"
            ]
        )

        print(
            "  SINR delta [dB]:",
            delta[
                "sinr_db"
            ]
        )

        print(
            "  PRB delta [pp]:",
            delta[
                "prb_percentage_points"
            ]
        )


    elif (
        result[
            "status"
        ]
        == "NEW_SERVING_CELL"
    ):

        print()

        print(
            cell_id
        )

        print(
            "  Status: NEW_SERVING_CELL"
        )

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

        print()

        print(
            cell_id
        )

        print(
            "  Status: NO_LONGER_SERVING"
        )

        print(
            "  Baseline active users:",
            result[
                "baseline"
            ][
                "active_users"
            ]
        )


# =========================================================
# ACCOUNTING
# =========================================================

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


print()
print("=" * 100)
print("ACCOUNTING CHECK")
print("=" * 100)

print()

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
# RESULT
# =========================================================

print()
print("=" * 100)
print("TEST QUESTION")
print("=" * 100)

print(
    """
We deliberately reduced one n78 cell from 43 dBm to
30 dBm.

We are NOT declaring that configuration invalid merely
because the TX value is low.

We want to observe whether the physical degradation
causes:

- lower target-cell RSRP,
- different interference conditions,
- UE reassociation,
- traffic redistribution,
- active-user changes,
- PRB changes.

Only after observing these effects will the automation
layer define acceptance / rollback policy.
"""
)