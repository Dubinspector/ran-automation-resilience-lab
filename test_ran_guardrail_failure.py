from app.ran_engine import (
    build_baseline_sites,
    build_candidate_sites,
    evaluate_ran_state,
)

from app.ran_guardrails import (
    evaluate_ran_guardrails,
)


# =========================================================
# DELIBERATELY HARMFUL CONFIGURATION
# =========================================================
#
# We simulate a bad configuration rollout affecting the
# whole synthetic Jesenice site.
#
# This is NOT a hardware outage.
#
# All carriers remain enabled, but:
#
# - TX power is reduced to the lower lab limit
# - electrical tilt is increased to the upper lab limit
#
# Whether this configuration FAILS must be determined by
# RF / service / traffic outcomes, not by parameter values.
# =========================================================

CELL_UPDATES = {

    "CELL-JES-A-N28": {
        "tx_power_dbm": 30.0
    },

    "CELL-JES-A-B3": {
        "tx_power_dbm": 30.0
    },

    "CELL-JES-A-N78": {
        "tx_power_dbm": 30.0
    },


    "CELL-JES-B-N28": {
        "tx_power_dbm": 30.0
    },

    "CELL-JES-B-B3": {
        "tx_power_dbm": 30.0
    },

    "CELL-JES-B-N78": {
        "tx_power_dbm": 30.0
    },


    "CELL-JES-C-N28": {
        "tx_power_dbm": 30.0
    },

    "CELL-JES-C-B3": {
        "tx_power_dbm": 30.0
    },

    "CELL-JES-C-N78": {
        "tx_power_dbm": 30.0
    }
}


ANTENNA_UPDATES = {

    "ANT-JES-A-LOWMID": {
        "electrical_tilt_deg": 12.0
    },

    "ANT-JES-A-N78": {
        "electrical_tilt_deg": 12.0
    },


    "ANT-JES-B-LOWMID": {
        "electrical_tilt_deg": 12.0
    },

    "ANT-JES-B-N78": {
        "electrical_tilt_deg": 12.0
    },


    "ANT-JES-C-LOWMID": {
        "electrical_tilt_deg": 12.0
    },

    "ANT-JES-C-N78": {
        "electrical_tilt_deg": 12.0
    }
}


# =========================================================
# BASELINE
# =========================================================

print()
print("=" * 110)
print("RAN GUARDRAIL FAILURE TEST")
print("=" * 110)


baseline_sites = (
    build_baseline_sites()
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

        cell_updates=
            CELL_UPDATES,

        antenna_updates=
            ANTENNA_UPDATES
    )
)


candidate_snapshot = (
    evaluate_ran_state(
        candidate_sites
    )
)


# =========================================================
# GUARDRAILS
# =========================================================

result = (
    evaluate_ran_guardrails(

        baseline_snapshot,
        candidate_snapshot
    )
)


# =========================================================
# CONFIGURATION SUMMARY
# =========================================================

print()
print("=" * 110)
print("CANDIDATE CONFIGURATION")
print("=" * 110)

print()

print(
    "Affected site:",
    "SITE-JESENICE-01"
)

print(
    "Cells with TX reduction:",
    len(
        CELL_UPDATES
    )
)

print(
    "Antennas with tilt change:",
    len(
        ANTENNA_UPDATES
    )
)

print(
    "Candidate TX [dBm]:",
    30.0
)

print(
    "Candidate electrical tilt [deg]:",
    12.0
)


# =========================================================
# GLOBAL SERVICE
# =========================================================

print()
print("=" * 110)
print("GLOBAL SERVICE")
print("=" * 110)

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
# FINAL VERDICT
# =========================================================

print()
print("=" * 110)
print("FINAL VERDICT")
print("=" * 110)

print()

print(
    "Verdict:",
    result[
        "verdict"
    ]
)

print(
    "Failed check count:",
    result[
        "failed_check_count"
    ]
)


# =========================================================
# ALL GUARDRAIL CHECKS
# =========================================================

print()
print("=" * 110)
print("GUARDRAIL CHECKS")
print("=" * 110)


for check in result[
    "checks"
]:

    print()

    print(
        check[
            "name"
        ]
    )

    print(
        "  Status:",
        check[
            "status"
        ]
    )

    print(
        "  Baseline:",
        check[
            "baseline"
        ]
    )

    print(
        "  Candidate:",
        check[
            "candidate"
        ]
    )

    print(
        "  Delta:",
        check[
            "delta"
        ]
    )

    print(
        "  Limit:",
        check[
            "limit"
        ]
    )


# =========================================================
# FAILED CHECKS
# =========================================================

print()
print("=" * 110)
print("FAILED CHECKS ONLY")
print("=" * 110)


if not result[
    "failed_checks"
]:

    print()

    print(
        "No failed guardrail checks."
    )


for check in result[
    "failed_checks"
]:

    print()

    print(
        check[
            "name"
        ]
    )

    print(
        "  Baseline:",
        check[
            "baseline"
        ]
    )

    print(
        "  Candidate:",
        check[
            "candidate"
        ]
    )

    print(
        "  Delta:",
        check[
            "delta"
        ]
    )

    print(
        "  Limit:",
        check[
            "limit"
        ]
    )


# =========================================================
# KPI SUMMARY
# =========================================================

summary = (
    result[
        "summary"
    ]
)


print()
print("=" * 110)
print("SERVICE / KPI SUMMARY")
print("=" * 110)

print()

print(
    "Baseline degraded UEs:",
    summary[
        "baseline_degraded_ues"
    ]
)

print(
    "Candidate degraded UEs:",
    summary[
        "candidate_degraded_ues"
    ]
)

print(
    "Baseline weighted SINR [dB]:",
    summary[
        "baseline_weighted_sinr_db"
    ]
)

print(
    "Candidate weighted SINR [dB]:",
    summary[
        "candidate_weighted_sinr_db"
    ]
)

print(
    "Baseline weighted RSRP [dBm]:",
    summary[
        "baseline_weighted_rsrp_dbm"
    ]
)

print(
    "Candidate weighted RSRP [dBm]:",
    summary[
        "candidate_weighted_rsrp_dbm"
    ]
)

print(
    "Maximum candidate PRB:",
    summary[
        "max_candidate_prb"
    ]
)


# =========================================================
# REASSOCIATION
# =========================================================

reassociation = (
    result[
        "reassociation"
    ]
)


print()
print("=" * 110)
print("UE REASSOCIATION")
print("=" * 110)

print()

print(
    "Changed UE samples:",
    reassociation[
        "changed_sample_count"
    ]
)

print(
    "Reassociated active UEs:",
    reassociation[
        "reassociated_active_ues"
    ]
)


for change in reassociation[
    "changes"
]:

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
        ],
        "/",
        change[
            "baseline_serviceability"
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
        ],
        "/",
        change[
            "candidate_serviceability"
        ]
    )


# =========================================================
# JESENICE ASSIGNMENTS
# =========================================================

print()
print("=" * 110)
print("CANDIDATE JESENICE UE STATE")
print("=" * 110)


for assignment in candidate_snapshot[
    "assignments"
]:

    if (
        assignment[
            "area_id"
        ]
        != "UE-JESENICE"
    ):

        continue


    print()

    print(
        assignment[
            "sample_id"
        ]
    )

    print(
        "  Active UEs:",
        assignment[
            "active_ues"
        ]
    )

    print(
        "  Status:",
        assignment[
            "status"
        ]
    )

    print(
        "  Primary cell:",
        assignment.get(
            "primary_cell_id"
        )
    )

    print(
        "  Band:",
        assignment.get(
            "band"
        )
    )

    print(
        "  RSRP [dBm]:",
        assignment.get(
            "rsrp_dbm"
        )
    )

    print(
        "  SINR [dB]:",
        assignment.get(
            "sinr_db"
        )
    )

    print(
        "  Serviceability:",
        assignment.get(
            "serviceability"
        )
    )


# =========================================================
# ACCOUNTING CHECK
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
print("=" * 110)
print("ACCOUNTING CHECK")
print("=" * 110)

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
# INTERPRETATION
# =========================================================

print()
print("=" * 110)
print("INTERPRETATION")
print("=" * 110)

print(
    """
This candidate represents a site-wide configuration
mistake, not a simulated hardware failure.

All Jesenice cells remain logically enabled.

The RF model must determine the consequences of:

- reduced transmit power,
- aggressive electrical downtilt,
- changed received signal strength,
- changed interference,
- UE reassociation,
- possible service loss,
- possible load redistribution.

We expect this to be substantially more disruptive than
changing one cell.

However, the test does NOT hard-code an expected FAIL.

If the guardrails still return PASS, we will inspect the
evidence rather than changing thresholds merely to force
a red result.
"""
)