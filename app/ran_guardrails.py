"""
RAN automation guardrails.

This module evaluates the operational outcome of a
candidate RAN configuration.

It does NOT decide whether a radio parameter value is
"inherently good" or "inherently bad".

The workflow is:

configuration
    ->
RF model
    ->
UE association
    ->
traffic / KPI snapshot
    ->
guardrails
    ->
PASS / FAIL

All thresholds below are explicit learning-lab automation
policy values.

They are NOT claimed to be production T-Mobile thresholds,
3GPP requirements, or universal operator rules.
"""

from copy import deepcopy

from app.ran_engine import (
    compare_cell_kpis,
)


# =========================================================
# DEFAULT AUTOMATION POLICY
# =========================================================

DEFAULT_GUARDRAIL_POLICY = {

    # -----------------------------------------------------
    # SERVICE AVAILABILITY
    # -----------------------------------------------------

    "max_served_ratio_drop_pp":
        1.0,

    "max_unserved_ue_increase":
        5,


    # -----------------------------------------------------
    # SERVICE QUALITY
    # -----------------------------------------------------

    "max_degraded_ue_increase":
        25,

    "max_weighted_sinr_drop_db":
        3.0,

    "max_weighted_rsrp_drop_db":
        6.0,


    # -----------------------------------------------------
    # INDIVIDUAL SERVING-CELL REGRESSION
    # -----------------------------------------------------

    "max_comparable_cell_sinr_drop_db":
        6.0,

    "max_comparable_cell_rsrp_drop_db":
        10.0,


    # -----------------------------------------------------
    # LOAD / CAPACITY
    # -----------------------------------------------------

    "max_candidate_cell_prb_pct":
        85.0,

    "max_comparable_cell_prb_increase_pp":
        25.0
}


# =========================================================
# HELPERS
# =========================================================

def get_cells(
    snapshot
):

    return snapshot.get(
        "cells",
        {}
    )


def get_assignments(
    snapshot
):

    return snapshot.get(
        "assignments",
        []
    )


# =========================================================
# USER-WEIGHTED KPI
# =========================================================

def weighted_cell_metric(
    snapshot,
    metric_name
):

    cells = get_cells(
        snapshot
    )


    weighted_sum = 0.0

    total_users = 0


    for cell in cells.values():

        active_users = int(

            cell.get(
                "active_users",
                0
            )
        )


        if active_users <= 0:

            continue


        metric_value = cell.get(
            metric_name
        )


        if metric_value is None:

            continue


        weighted_sum += (

            float(
                metric_value
            )

            * active_users
        )


        total_users += (
            active_users
        )


    if total_users == 0:

        return None


    return (

        weighted_sum
        / total_users
    )


# =========================================================
# DEGRADED UE COUNT
# =========================================================

def count_degraded_ues(
    snapshot
):

    total = 0


    for cell in get_cells(
        snapshot
    ).values():


        mix = cell.get(

            "serviceability_ue_mix",

            {}
        )


        total += int(

            mix.get(
                "DEGRADED",
                0
            )
        )


    return total


# =========================================================
# MAXIMUM PRB
# =========================================================

def find_max_prb_cell(
    snapshot
):

    cells = get_cells(
        snapshot
    )


    if not cells:

        return {

            "cell_id":
                None,

            "prb_utilization_pct":
                0.0
        }


    cell_id, cell = max(

        cells.items(),

        key=lambda item:
            item[
                1
            ].get(
                "prb_utilization_pct",
                0.0
            )
    )


    return {

        "cell_id":
            cell_id,

        "prb_utilization_pct":
            float(

                cell.get(
                    "prb_utilization_pct",
                    0.0
                )
            )
    }


# =========================================================
# REASSOCIATION SUMMARY
# =========================================================

def build_reassociation_summary(
    baseline_snapshot,
    candidate_snapshot
):

    baseline = {

        item[
            "sample_id"
        ]:
            item

        for item
        in get_assignments(
            baseline_snapshot
        )
    }


    candidate = {

        item[
            "sample_id"
        ]:
            item

        for item
        in get_assignments(
            candidate_snapshot
        )
    }


    sample_ids = sorted(

        set(
            baseline
        )

        | set(
            candidate
        )
    )


    changes = []


    for sample_id in sample_ids:

        before = baseline.get(
            sample_id
        )

        after = candidate.get(
            sample_id
        )


        if (
            before is None
            or after is None
        ):

            continue


        before_cell = (
            before.get(
                "primary_cell_id"
            )
        )


        after_cell = (
            after.get(
                "primary_cell_id"
            )
        )


        if (
            before_cell
            == after_cell
        ):

            continue


        changes.append({

            "sample_id":
                sample_id,

            "area_id":
                before.get(
                    "area_id"
                ),

            "active_ues":
                int(

                    before.get(
                        "active_ues",
                        0
                    )
                ),

            "baseline_cell_id":
                before_cell,

            "candidate_cell_id":
                after_cell,

            "baseline_band":
                before.get(
                    "band"
                ),

            "candidate_band":
                after.get(
                    "band"
                ),

            "baseline_serviceability":
                before.get(
                    "serviceability"
                ),

            "candidate_serviceability":
                after.get(
                    "serviceability"
                )
        })


    return {

        "changed_sample_count":
            len(
                changes
            ),

        "reassociated_active_ues":
            sum(

                item[
                    "active_ues"
                ]

                for item
                in changes
            ),

        "changes":
            changes
    }


# =========================================================
# WORST COMPARABLE CELL DELTAS
# =========================================================

def find_worst_comparable_deltas(
    baseline_snapshot,
    candidate_snapshot
):

    comparison = compare_cell_kpis(

        baseline_snapshot,
        candidate_snapshot
    )


    worst_sinr = {

        "cell_id":
            None,

        "delta_db":
            0.0
    }


    worst_rsrp = {

        "cell_id":
            None,

        "delta_db":
            0.0
    }


    worst_prb = {

        "cell_id":
            None,

        "delta_pp":
            0.0
    }


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

            continue


        delta = result[
            "delta"
        ]


        sinr_delta = float(

            delta[
                "sinr_db"
            ]
        )


        rsrp_delta = float(

            delta[
                "rsrp_db"
            ]
        )


        prb_delta = float(

            delta[
                "prb_percentage_points"
            ]
        )


        if (
            sinr_delta
            < worst_sinr[
                "delta_db"
            ]
        ):

            worst_sinr = {

                "cell_id":
                    cell_id,

                "delta_db":
                    sinr_delta
            }


        if (
            rsrp_delta
            < worst_rsrp[
                "delta_db"
            ]
        ):

            worst_rsrp = {

                "cell_id":
                    cell_id,

                "delta_db":
                    rsrp_delta
            }


        if (
            prb_delta
            > worst_prb[
                "delta_pp"
            ]
        ):

            worst_prb = {

                "cell_id":
                    cell_id,

                "delta_pp":
                    prb_delta
            }


    return {

        "comparison":
            comparison,

        "worst_sinr":
            worst_sinr,

        "worst_rsrp":
            worst_rsrp,

        "worst_prb":
            worst_prb
    }


# =========================================================
# CHECK BUILDER
# =========================================================

def make_check(
    name,
    passed,
    baseline,
    candidate,
    delta,
    limit,
    explanation
):

    return {

        "name":
            name,

        "status":
            (
                "PASS"
                if passed
                else "FAIL"
            ),

        "baseline":
            baseline,

        "candidate":
            candidate,

        "delta":
            delta,

        "limit":
            limit,

        "explanation":
            explanation
    }


# =========================================================
# EVALUATE GUARDRAILS
# =========================================================

def evaluate_ran_guardrails(
    baseline_snapshot,
    candidate_snapshot,
    policy=None
):

    if policy is None:

        policy = deepcopy(
            DEFAULT_GUARDRAIL_POLICY
        )

    else:

        policy = deepcopy(
            policy
        )


    checks = []


    # =====================================================
    # GLOBAL SERVICE
    # =====================================================

    baseline_service = (
        baseline_snapshot[
            "service"
        ]
    )


    candidate_service = (
        candidate_snapshot[
            "service"
        ]
    )


    baseline_served_ratio = float(

        baseline_service[
            "served_ratio_pct"
        ]
    )


    candidate_served_ratio = float(

        candidate_service[
            "served_ratio_pct"
        ]
    )


    served_ratio_drop = (

        baseline_served_ratio

        - candidate_served_ratio
    )


    checks.append(

        make_check(

            name=
                "SERVED_RATIO_DROP",

            passed=
                (
                    served_ratio_drop

                    <= policy[
                        "max_served_ratio_drop_pp"
                    ]
                ),

            baseline=
                baseline_served_ratio,

            candidate=
                candidate_served_ratio,

            delta=
                round(
                    -served_ratio_drop,
                    3
                ),

            limit=
                (
                    -policy[
                        "max_served_ratio_drop_pp"
                    ]
                ),

            explanation=
                (
                    "Candidate must not reduce the "
                    "served-user ratio beyond the "
                    "configured lab tolerance."
                )
        )
    )


    baseline_unserved = int(

        baseline_service[
            "unserved_active_ues"
        ]
    )


    candidate_unserved = int(

        candidate_service[
            "unserved_active_ues"
        ]
    )


    unserved_increase = (

        candidate_unserved

        - baseline_unserved
    )


    checks.append(

        make_check(

            name=
                "UNSERVED_UE_INCREASE",

            passed=
                (
                    unserved_increase

                    <= policy[
                        "max_unserved_ue_increase"
                    ]
                ),

            baseline=
                baseline_unserved,

            candidate=
                candidate_unserved,

            delta=
                unserved_increase,

            limit=
                policy[
                    "max_unserved_ue_increase"
                ],

            explanation=
                (
                    "Candidate must not create too many "
                    "additional unserved active UEs."
                )
        )
    )


    # =====================================================
    # SERVICEABILITY MIX
    # =====================================================

    baseline_degraded = (
        count_degraded_ues(
            baseline_snapshot
        )
    )


    candidate_degraded = (
        count_degraded_ues(
            candidate_snapshot
        )
    )


    degraded_increase = (

        candidate_degraded

        - baseline_degraded
    )


    checks.append(

        make_check(

            name=
                "DEGRADED_UE_INCREASE",

            passed=
                (
                    degraded_increase

                    <= policy[
                        "max_degraded_ue_increase"
                    ]
                ),

            baseline=
                baseline_degraded,

            candidate=
                candidate_degraded,

            delta=
                degraded_increase,

            limit=
                policy[
                    "max_degraded_ue_increase"
                ],

            explanation=
                (
                    "Reassociation is allowed, but the "
                    "candidate must not move excessive "
                    "traffic into DEGRADED service."
                )
        )
    )


    # =====================================================
    # USER-WEIGHTED RADIO KPI
    # =====================================================

    baseline_weighted_sinr = (
        weighted_cell_metric(

            baseline_snapshot,

            "sinr_db"
        )
    )


    candidate_weighted_sinr = (
        weighted_cell_metric(

            candidate_snapshot,

            "sinr_db"
        )
    )


    if (

        baseline_weighted_sinr
        is not None

        and

        candidate_weighted_sinr
        is not None
    ):

        weighted_sinr_drop = (

            baseline_weighted_sinr

            - candidate_weighted_sinr
        )

    else:

        weighted_sinr_drop = 0.0


    checks.append(

        make_check(

            name=
                "WEIGHTED_SINR_DROP",

            passed=
                (
                    weighted_sinr_drop

                    <= policy[
                        "max_weighted_sinr_drop_db"
                    ]
                ),

            baseline=
                (
                    None
                    if baseline_weighted_sinr is None
                    else round(
                        baseline_weighted_sinr,
                        3
                    )
                ),

            candidate=
                (
                    None
                    if candidate_weighted_sinr is None
                    else round(
                        candidate_weighted_sinr,
                        3
                    )
                ),

            delta=
                round(
                    -weighted_sinr_drop,
                    3
                ),

            limit=
                (
                    -policy[
                        "max_weighted_sinr_drop_db"
                    ]
                ),

            explanation=
                (
                    "User-weighted serving-cell SINR "
                    "must not regress beyond the lab "
                    "tolerance."
                )
        )
    )


    baseline_weighted_rsrp = (
        weighted_cell_metric(

            baseline_snapshot,

            "rsrp_dbm"
        )
    )


    candidate_weighted_rsrp = (
        weighted_cell_metric(

            candidate_snapshot,

            "rsrp_dbm"
        )
    )


    if (

        baseline_weighted_rsrp
        is not None

        and

        candidate_weighted_rsrp
        is not None
    ):

        weighted_rsrp_drop = (

            baseline_weighted_rsrp

            - candidate_weighted_rsrp
        )

    else:

        weighted_rsrp_drop = 0.0


    checks.append(

        make_check(

            name=
                "WEIGHTED_RSRP_DROP",

            passed=
                (
                    weighted_rsrp_drop

                    <= policy[
                        "max_weighted_rsrp_drop_db"
                    ]
                ),

            baseline=
                (
                    None
                    if baseline_weighted_rsrp is None
                    else round(
                        baseline_weighted_rsrp,
                        3
                    )
                ),

            candidate=
                (
                    None
                    if candidate_weighted_rsrp is None
                    else round(
                        candidate_weighted_rsrp,
                        3
                    )
                ),

            delta=
                round(
                    -weighted_rsrp_drop,
                    3
                ),

            limit=
                (
                    -policy[
                        "max_weighted_rsrp_drop_db"
                    ]
                ),

            explanation=
                (
                    "User-weighted serving RSRP must "
                    "not regress beyond the configured "
                    "lab tolerance."
                )
        )
    )


    # =====================================================
    # INDIVIDUAL COMPARABLE CELLS
    # =====================================================

    worst = (
        find_worst_comparable_deltas(

            baseline_snapshot,
            candidate_snapshot
        )
    )


    worst_sinr_drop = (

        -worst[
            "worst_sinr"
        ][
            "delta_db"
        ]
    )


    checks.append(

        make_check(

            name=
                "WORST_CELL_SINR_DROP",

            passed=
                (
                    worst_sinr_drop

                    <= policy[
                        "max_comparable_cell_sinr_drop_db"
                    ]
                ),

            baseline=
                worst[
                    "worst_sinr"
                ][
                    "cell_id"
                ],

            candidate=
                worst[
                    "worst_sinr"
                ][
                    "cell_id"
                ],

            delta=
                worst[
                    "worst_sinr"
                ][
                    "delta_db"
                ],

            limit=
                (
                    -policy[
                        "max_comparable_cell_sinr_drop_db"
                    ]
                ),

            explanation=
                (
                    "A still-serving comparable cell "
                    "must not suffer an excessive SINR "
                    "regression."
                )
        )
    )


    worst_rsrp_drop = (

        -worst[
            "worst_rsrp"
        ][
            "delta_db"
        ]
    )


    checks.append(

        make_check(

            name=
                "WORST_CELL_RSRP_DROP",

            passed=
                (
                    worst_rsrp_drop

                    <= policy[
                        "max_comparable_cell_rsrp_drop_db"
                    ]
                ),

            baseline=
                worst[
                    "worst_rsrp"
                ][
                    "cell_id"
                ],

            candidate=
                worst[
                    "worst_rsrp"
                ][
                    "cell_id"
                ],

            delta=
                worst[
                    "worst_rsrp"
                ][
                    "delta_db"
                ],

            limit=
                (
                    -policy[
                        "max_comparable_cell_rsrp_drop_db"
                    ]
                ),

            explanation=
                (
                    "A still-serving comparable cell "
                    "must not suffer an excessive RSRP "
                    "regression."
                )
        )
    )


    # =====================================================
    # LOAD
    # =====================================================

    max_candidate_prb = (
        find_max_prb_cell(
            candidate_snapshot
        )
    )


    checks.append(

        make_check(

            name=
                "MAX_CANDIDATE_PRB",

            passed=
                (
                    max_candidate_prb[
                        "prb_utilization_pct"
                    ]

                    <= policy[
                        "max_candidate_cell_prb_pct"
                    ]
                ),

            baseline=
                None,

            candidate={
                "cell_id":
                    max_candidate_prb[
                        "cell_id"
                    ],

                "prb_utilization_pct":
                    round(

                        max_candidate_prb[
                            "prb_utilization_pct"
                        ],

                        3
                    )
            },

            delta=
                None,

            limit=
                policy[
                    "max_candidate_cell_prb_pct"
                ],

            explanation=
                (
                    "No active serving cell in the "
                    "candidate may exceed the configured "
                    "PRB ceiling."
                )
        )
    )


    checks.append(

        make_check(

            name=
                "WORST_CELL_PRB_INCREASE",

            passed=
                (
                    worst[
                        "worst_prb"
                    ][
                        "delta_pp"
                    ]

                    <= policy[
                        "max_comparable_cell_prb_increase_pp"
                    ]
                ),

            baseline=
                worst[
                    "worst_prb"
                ][
                    "cell_id"
                ],

            candidate=
                worst[
                    "worst_prb"
                ][
                    "cell_id"
                ],

            delta=
                worst[
                    "worst_prb"
                ][
                    "delta_pp"
                ],

            limit=
                policy[
                    "max_comparable_cell_prb_increase_pp"
                ],

            explanation=
                (
                    "A comparable active cell must not "
                    "experience an excessive PRB load "
                    "increase."
                )
        )
    )


    # =====================================================
    # REASSOCIATION
    # =====================================================
    #
    # Important:
    #
    # This is deliberately informational.
    #
    # A UE changing primary cell or band is not itself a
    # failure if the resulting service remains acceptable.
    # =====================================================

    reassociation = (
        build_reassociation_summary(

            baseline_snapshot,
            candidate_snapshot
        )
    )


    # =====================================================
    # FINAL VERDICT
    # =====================================================

    failed_checks = [

        check

        for check
        in checks

        if check[
            "status"
        ]
        == "FAIL"
    ]


    verdict = (

        "PASS"

        if not failed_checks

        else "FAIL"
    )


    return {

        "verdict":
            verdict,

        "policy":
            policy,

        "checks":
            checks,

        "failed_check_count":
            len(
                failed_checks
            ),

        "failed_checks":
            deepcopy(
                failed_checks
            ),

        "reassociation":
            reassociation,

        "summary": {

            "baseline_served_ratio_pct":
                baseline_served_ratio,

            "candidate_served_ratio_pct":
                candidate_served_ratio,

            "baseline_unserved_ues":
                baseline_unserved,

            "candidate_unserved_ues":
                candidate_unserved,

            "baseline_degraded_ues":
                baseline_degraded,

            "candidate_degraded_ues":
                candidate_degraded,

            "baseline_weighted_sinr_db":
                (
                    None
                    if baseline_weighted_sinr is None
                    else round(
                        baseline_weighted_sinr,
                        3
                    )
                ),

            "candidate_weighted_sinr_db":
                (
                    None
                    if candidate_weighted_sinr is None
                    else round(
                        candidate_weighted_sinr,
                        3
                    )
                ),

            "baseline_weighted_rsrp_dbm":
                (
                    None
                    if baseline_weighted_rsrp is None
                    else round(
                        baseline_weighted_rsrp,
                        3
                    )
                ),

            "candidate_weighted_rsrp_dbm":
                (
                    None
                    if candidate_weighted_rsrp is None
                    else round(
                        candidate_weighted_rsrp,
                        3
                    )
                ),

            "max_candidate_prb":
                max_candidate_prb
        }
    }