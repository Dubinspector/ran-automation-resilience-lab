from app.ran_engine import (
    build_baseline_sites,
    build_candidate_sites,
    evaluate_ran_state,
)

from app.ran_guardrails import (
    evaluate_ran_guardrails,
)


# =========================================================
# TEST TARGET
# =========================================================

TARGET_CELL_ID = (
    "CELL-JES-A-N78"
)


TEST_CASES = [

    {
        "name":
            "HIGHER_TX",

        "candidate_tx_power_dbm":
            48.0
    },

    {
        "name":
            "LOWER_TX_WITH_REASSOCIATION",

        "candidate_tx_power_dbm":
            30.0
    }
]


# =========================================================
# BASELINE
# =========================================================

print()
print("=" * 110)
print("RAN GUARDRAIL TEST")
print("=" * 110)


baseline_sites = (
    build_baseline_sites()
)


baseline_snapshot = (
    evaluate_ran_state(
        baseline_sites
    )
)


print()

print(
    "Baseline served ratio [%]:",
    baseline_snapshot[
        "service"
    ][
        "served_ratio_pct"
    ]
)

print(
    "Baseline served UEs:",
    baseline_snapshot[
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


# =========================================================
# TEST EACH CANDIDATE
# =========================================================

for test_case in TEST_CASES:

    test_name = (
        test_case[
            "name"
        ]
    )


    candidate_tx = (
        test_case[
            "candidate_tx_power_dbm"
        ]
    )


    print()
    print()
    print("#" * 110)
    print(
        f"TEST CASE: {test_name}"
    )
    print("#" * 110)


    # =====================================================
    # BUILD CANDIDATE CONFIGURATION
    # =====================================================

    candidate_sites = (
        build_candidate_sites(

            base_sites=
                baseline_sites,

            cell_updates={

                TARGET_CELL_ID: {

                    "tx_power_dbm":
                        candidate_tx
                }
            }
        )
    )


    # =====================================================
    # RF + TRAFFIC SNAPSHOT
    # =====================================================

    candidate_snapshot = (
        evaluate_ran_state(
            candidate_sites
        )
    )


    # =====================================================
    # GUARDRAILS
    # =====================================================

    result = (
        evaluate_ran_guardrails(

            baseline_snapshot,
            candidate_snapshot
        )
    )


    # =====================================================
    # CONFIGURATION
    # =====================================================

    print()
    print("=" * 110)
    print("CONFIGURATION")
    print("=" * 110)

    print()

    print(
        "Target cell:",
        TARGET_CELL_ID
    )

    print(
        "Baseline TX [dBm]:",
        43.0
    )

    print(
        "Candidate TX [dBm]:",
        candidate_tx
    )


    # =====================================================
    # VERDICT
    # =====================================================

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
        "Failed checks:",
        result[
            "failed_check_count"
        ]
    )


    # =====================================================
    # CHECKS
    # =====================================================

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

        print(
            "  Explanation:",
            check[
                "explanation"
            ]
        )


    # =====================================================
    # SERVICE SUMMARY
    # =====================================================

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
        "Baseline served ratio [%]:",
        summary[
            "baseline_served_ratio_pct"
        ]
    )

    print(
        "Candidate served ratio [%]:",
        summary[
            "candidate_served_ratio_pct"
        ]
    )

    print(
        "Baseline unserved UEs:",
        summary[
            "baseline_unserved_ues"
        ]
    )

    print(
        "Candidate unserved UEs:",
        summary[
            "candidate_unserved_ues"
        ]
    )

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


    # =====================================================
    # REASSOCIATION
    # =====================================================

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
            "  Active UEs:",
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


    # =====================================================
    # FAILED CHECKS ONLY
    # =====================================================

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


    else:

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
# INTERPRETATION
# =========================================================

print()
print()
print("=" * 110)
print("INTERPRETATION")
print("=" * 110)

print(
    """
The automation policy evaluates the RESULT of each RAN
configuration rather than rejecting a parameter value
directly.

Important examples:

- Increasing TX power can improve the target cell while
  increasing co-channel interference elsewhere.

- Reducing TX power can cause UE reassociation without
  causing service loss.

- A cell disappearing from the active serving-cell KPI
  set is not automatically a failure.

- Reassociation is informational unless the resulting
  service, radio quality or load violates a guardrail.

The next step is to create a deliberately harmful
candidate and verify that the same policy produces FAIL.
"""
)