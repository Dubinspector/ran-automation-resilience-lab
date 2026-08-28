import os
from copy import deepcopy
from datetime import datetime, timezone
from urllib.error import URLError
from urllib.request import urlopen

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from app.dashboard import DASHBOARD_HTML


app = FastAPI()


# ---------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------

ENVIRONMENT_NAME = os.getenv(
    "ENVIRONMENT_NAME",
    "ENV-LOCAL"
)

PRB_THRESHOLD = int(
    os.getenv("PRB_THRESHOLD", "20")
)

SINR_THRESHOLD = int(
    os.getenv("SINR_THRESHOLD", "5")
)

RSRP_THRESHOLD = int(
    os.getenv("RSRP_THRESHOLD", "15")
)

USER_THRESHOLD = int(
    os.getenv("USER_THRESHOLD", "40")
)

RAN_ADAPTER_URL = os.getenv(
    "RAN_ADAPTER_URL",
    "http://127.0.0.1:8000"
)


# ---------------------------------------------------------
# SYNTHETIC RAN ENVIRONMENT
# ---------------------------------------------------------

environment = {
    "environment_id": ENVIRONMENT_NAME,
    "release": "v1.0.0",
    "rollout_state": "STABLE",

    "cells": [
        {
            "cell_id": "CELL-001",
            "technology": "5G",
            "prb_utilization": 54,
            "sinr_db": 18,
            "rsrp_dbm": -82,
            "active_users": 82,
            "status": "ACTIVE"
        },
        {
            "cell_id": "CELL-002",
            "technology": "5G",
            "prb_utilization": 68,
            "sinr_db": 8,
            "rsrp_dbm": -94,
            "active_users": 103,
            "status": "ACTIVE"
        },
        {
            "cell_id": "CELL-003",
            "technology": "4G",
            "prb_utilization": 45,
            "sinr_db": 25,
            "rsrp_dbm": -78,
            "active_users": 17,
            "status": "ACTIVE"
        }
    ],

    "alarms": [
        {
            "alarm_id": "ALARM-001",
            "cell_id": "CELL-002",
            "severity": "MAJOR",
            "type": "LOW_SINR",
            "active": True
        }
    ]
}


# Baseline is the known-good RAN state.
baseline_cells = deepcopy(
    environment["cells"]
)


# Operational event timeline.
event_log = []


# ---------------------------------------------------------
# EVENT LOG
# ---------------------------------------------------------

def add_event(
    event_type,
    status,
    message
):
    event_log.append({
        "timestamp":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "type":
            event_type,

        "status":
            status,

        "message":
            message
    })

    # Keep only the newest 50 events.
    if len(event_log) > 50:
        del event_log[:-50]


# ---------------------------------------------------------
# PRECHECK
# ---------------------------------------------------------

def run_precheck_data():

    ran_adapter_available = False

    try:

        with urlopen(
            f"{RAN_ADAPTER_URL}/cells",
            timeout=2
        ) as response:

            ran_adapter_available = (
                response.status == 200
            )

    except (
        URLError,
        TimeoutError
    ):
        ran_adapter_available = False


    checks = {

        "ran_adapter_available":
            ran_adapter_available,

        "cells_discovered":
            len(environment["cells"]) > 0,

        "kpi_baseline_collected":
            all(
                "prb_utilization" in cell
                and "sinr_db" in cell
                and "rsrp_dbm" in cell
                and "active_users" in cell
                for cell
                in environment["cells"]
            )
    }


    overall_pass = all(
        checks.values()
    )


    return {
        "status":
            "PASS"
            if overall_pass
            else "FAIL",

        "checks":
            checks
    }


# ---------------------------------------------------------
# SAFETY SCORE
# ---------------------------------------------------------

def get_safety_score_data():

    active_alarms = [
        alarm
        for alarm
        in environment["alarms"]
        if alarm["active"]
    ]


    environment_health = 25

    kubernetes_capacity = 20

    ran_baseline_stable = 20

    recent_alarms = (
        15
        if len(active_alarms) == 0
        else 10
    )

    previous_release_health = 20


    total = (
        environment_health
        + kubernetes_capacity
        + ran_baseline_stable
        + recent_alarms
        + previous_release_health
    )


    return {
        "environment_health":
            environment_health,

        "kubernetes_capacity":
            kubernetes_capacity,

        "ran_baseline_stable":
            ran_baseline_stable,

        "recent_alarms":
            recent_alarms,

        "previous_release_health":
            previous_release_health,

        "total":
            total,

        "rollout_allowed":
            total >= 80
    }


# ---------------------------------------------------------
# RAN KPI VALIDATION
# ---------------------------------------------------------

def check_ran_validation():

    failed_cells = []

    cell_results = []


    for cell in environment["cells"]:

        baseline = next(
            baseline_cell
            for baseline_cell
            in baseline_cells
            if baseline_cell["cell_id"]
            == cell["cell_id"]
        )


        # KPI deltas.
        prb_delta = (
            cell["prb_utilization"]
            - baseline["prb_utilization"]
        )

        sinr_delta = (
            cell["sinr_db"]
            - baseline["sinr_db"]
        )

        rsrp_delta = (
            cell["rsrp_dbm"]
            - baseline["rsrp_dbm"]
        )

        user_delta = (
            cell["active_users"]
            - baseline["active_users"]
        )


        # Threshold evaluation.
        #
        # PRB:
        # large increase or decrease is considered abnormal.
        prb_failed = (
            abs(prb_delta)
            > PRB_THRESHOLD
        )

        # SINR:
        # negative delta means degradation.
        sinr_failed = (
            sinr_delta
            < -SINR_THRESHOLD
        )

        # RSRP:
        # more negative value means weaker signal.
        rsrp_failed = (
            rsrp_delta
            < -RSRP_THRESHOLD
        )

        # Users:
        # large increase or decrease can indicate
        # traffic imbalance or session loss.
        users_failed = (
            abs(user_delta)
            > USER_THRESHOLD
        )


        if (
            prb_failed
            or sinr_failed
            or rsrp_failed
            or users_failed
        ):
            failed_cells.append(
                cell["cell_id"]
            )


        cell_results.append({

            "cell_id":
                cell["cell_id"],


            "baseline": {

                "prb_utilization":
                    baseline["prb_utilization"],

                "sinr_db":
                    baseline["sinr_db"],

                "rsrp_dbm":
                    baseline["rsrp_dbm"],

                "active_users":
                    baseline["active_users"]
            },


            "current": {

                "prb_utilization":
                    cell["prb_utilization"],

                "sinr_db":
                    cell["sinr_db"],

                "rsrp_dbm":
                    cell["rsrp_dbm"],

                "active_users":
                    cell["active_users"]
            },


            "delta": {

                "prb":
                    prb_delta,

                "sinr":
                    sinr_delta,

                "rsrp":
                    rsrp_delta,

                "users":
                    user_delta
            },


            "thresholds": {

                "prb_change":
                    PRB_THRESHOLD,

                "sinr_drop":
                    SINR_THRESHOLD,

                "rsrp_drop":
                    RSRP_THRESHOLD,

                "user_change":
                    USER_THRESHOLD
            },


            "checks": {

                "prb":
                    "FAIL"
                    if prb_failed
                    else "PASS",

                "sinr":
                    "FAIL"
                    if sinr_failed
                    else "PASS",

                "rsrp":
                    "FAIL"
                    if rsrp_failed
                    else "PASS",

                "users":
                    "FAIL"
                    if users_failed
                    else "PASS"
            }
        })


    return {

        "status":
            "FAIL"
            if failed_cells
            else "PASS",

        "failed_cells":
            failed_cells,

        "cells":
            cell_results
    }


# ---------------------------------------------------------
# WEB DASHBOARD
# ---------------------------------------------------------

@app.get(
    "/",
    response_class=HTMLResponse
)
def dashboard():

    return DASHBOARD_HTML


# ---------------------------------------------------------
# PLATFORM / RAN STATUS
# ---------------------------------------------------------

@app.get("/status")
def get_status():

    validation = (
        check_ran_validation()
    )

    return {

        "environment":
            environment[
                "environment_id"
            ],

        "active_release":
            environment["release"],

        "rollout_state":
            environment[
                "rollout_state"
            ],

        "application_health":
            "HEALTHY",

        "ran_validation":
            validation["status"]
    }


# ---------------------------------------------------------
# CELLS
# ---------------------------------------------------------

@app.get("/cells")
def get_cells():

    return environment["cells"]


@app.get(
    "/cells/{cell_id}/kpis"
)
def get_cell_kpis(
    cell_id: str
):

    for cell in environment["cells"]:

        if (
            cell["cell_id"]
            == cell_id
        ):

            return {

                "cell_id":
                    cell["cell_id"],

                "prb_utilization":
                    cell[
                        "prb_utilization"
                    ],

                "sinr_db":
                    cell["sinr_db"],

                "rsrp_dbm":
                    cell["rsrp_dbm"],

                "active_users":
                    cell[
                        "active_users"
                    ],

                "status":
                    cell["status"]
            }


    raise HTTPException(
        status_code=404,
        detail="Cell not found"
    )


# ---------------------------------------------------------
# ALARMS
# ---------------------------------------------------------

@app.get("/alarms")
def get_alarms():

    return environment["alarms"]


# ---------------------------------------------------------
# EVENT TIMELINE
# ---------------------------------------------------------

@app.get("/events")
def get_events():

    return event_log


# ---------------------------------------------------------
# PRECHECK ENDPOINT
# ---------------------------------------------------------

@app.get("/precheck")
def run_precheck():

    return run_precheck_data()


# ---------------------------------------------------------
# SAFETY SCORE ENDPOINT
# ---------------------------------------------------------

@app.get("/safety-score")
def get_safety_score():

    return get_safety_score_data()


# ---------------------------------------------------------
# CONFIGURATION / INCIDENT INJECTION
# ---------------------------------------------------------

@app.post("/configuration")
def apply_configuration(
    mode: str
):

    # -----------------------------------------------------
    # DEGRADED MODE
    # -----------------------------------------------------

    if mode == "degraded":

        # CELL-001:
        #
        # Simulated overload:
        #
        # PRB   54 -> 94 %
        # SINR  18 -> 2 dB
        # RSRP -82 -> -113 dBm
        # users 82 -> 151

        environment["cells"][0][
            "prb_utilization"
        ] = 94

        environment["cells"][0][
            "sinr_db"
        ] = 2

        environment["cells"][0][
            "rsrp_dbm"
        ] = -113

        environment["cells"][0][
            "active_users"
        ] = 151


        # CELL-002:
        #
        # Simulated severe coverage degradation
        # and user/session loss:
        #
        # PRB   68 -> 29 %
        # SINR   8 -> -3 dB
        # RSRP -94 -> -121 dBm
        # users 103 -> 31

        environment["cells"][1][
            "prb_utilization"
        ] = 29

        environment["cells"][1][
            "sinr_db"
        ] = -3

        environment["cells"][1][
            "rsrp_dbm"
        ] = -121

        environment["cells"][1][
            "active_users"
        ] = 31


        environment[
            "rollout_state"
        ] = "REGRESSION"


        add_event(
            "KPI",
            "FAIL",
            "Major RAN regression injected: "
            "CELL-001 overload and "
            "CELL-002 coverage/user loss"
        )


        return {

            "status":
                "APPLIED",

            "mode":
                "degraded",

            "validation":
                check_ran_validation()
        }


    # -----------------------------------------------------
    # HEALTHY MODE
    # -----------------------------------------------------

    if mode == "healthy":

        environment["cells"] = (
            deepcopy(
                baseline_cells
            )
        )

        environment[
            "rollout_state"
        ] = "STABLE"


        add_event(
            "CONFIGURATION",
            "PASS",
            "Healthy RAN baseline "
            "configuration restored"
        )


        return {

            "status":
                "APPLIED",

            "mode":
                "healthy",

            "validation":
                check_ran_validation()
        }


    raise HTTPException(
        status_code=400,
        detail="Unknown configuration mode"
    )


# ---------------------------------------------------------
# VALIDATION
# ---------------------------------------------------------

@app.get("/validation")
def validate_ran():

    return (
        check_ran_validation()
    )


# ---------------------------------------------------------
# MANUAL APPLICATION-LEVEL ROLLBACK
# ---------------------------------------------------------

@app.post("/rollback")
def rollback():

    previous_release = (
        environment["release"]
    )


    environment["cells"] = (
        deepcopy(
            baseline_cells
        )
    )

    environment["release"] = (
        "v1.0.0"
    )

    environment[
        "rollout_state"
    ] = "ROLLED_BACK"


    add_event(
        "ROLLBACK",
        "PASS",
        f"Release {previous_release} "
        "rolled back to v1.0.0"
    )


    validation = (
        check_ran_validation()
    )


    add_event(
        "VALIDATION",
        validation["status"],
        "Post-rollback RAN "
        "validation "
        f"{validation['status']}"
    )


    return {

        "status":
            "ROLLED_BACK",

        "active_release":
            environment["release"],

        "validation":
            validation
    }


# ---------------------------------------------------------
# GUARDED RAN-AWARE ROLLOUT
# ---------------------------------------------------------

@app.post("/rollout")
def rollout():

    steps = []

    attempted_release = (
        "v1.1.0"
    )


    # -----------------------------------------------------
    # STEP 1
    # PRECHECK
    # -----------------------------------------------------

    precheck = (
        run_precheck_data()
    )


    steps.append({

        "step":
            "Pre-check",

        "status":
            precheck["status"]
    })


    add_event(
        "PRECHECK",
        precheck["status"],
        "RAN integration pre-check "
        f"{precheck['status']}"
    )


    if (
        precheck["status"]
        != "PASS"
    ):

        environment[
            "rollout_state"
        ] = "BLOCKED"


        return {

            "status":
                "BLOCKED",

            "reason":
                "Pre-check failed",

            "steps":
                steps,

            "precheck":
                precheck
        }


    # -----------------------------------------------------
    # STEP 2
    # SAFETY SCORE
    # -----------------------------------------------------

    safety = (
        get_safety_score_data()
    )


    safety_status = (
        "PASS"
        if safety[
            "rollout_allowed"
        ]
        else "FAIL"
    )


    steps.append({

        "step":
            "Safety score",

        "status":
            safety_status,

        "detail":
            f"{safety['total']}/100"
    })


    add_event(
        "SAFETY",
        safety_status,
        f"Safety score "
        f"{safety['total']}/100"
    )


    if not safety[
        "rollout_allowed"
    ]:

        environment[
            "rollout_state"
        ] = "BLOCKED"


        return {

            "status":
                "BLOCKED",

            "reason":
                "Safety score "
                "below threshold",

            "steps":
                steps,

            "safety_score":
                safety
        }


    # -----------------------------------------------------
    # STEP 3
    # RELEASE ACTIVATION
    # -----------------------------------------------------

    environment["release"] = (
        attempted_release
    )

    environment[
        "rollout_state"
    ] = "DEPLOYING"


    steps.append({

        "step":
            f"Activate release "
            f"{attempted_release}",

        "status":
            "PASS"
    })


    add_event(
        "RELEASE",
        "PASS",
        f"Release "
        f"{attempted_release} "
        "activated"
    )


    # -----------------------------------------------------
    # STEP 4
    # SIMULATED POST-CHANGE RAN REGRESSION
    # -----------------------------------------------------

    # CELL-001 overload.

    environment["cells"][0][
        "prb_utilization"
    ] = 94

    environment["cells"][0][
        "sinr_db"
    ] = 2

    environment["cells"][0][
        "rsrp_dbm"
    ] = -113

    environment["cells"][0][
        "active_users"
    ] = 151


    # CELL-002 coverage degradation.

    environment["cells"][1][
        "prb_utilization"
    ] = 29

    environment["cells"][1][
        "sinr_db"
    ] = -3

    environment["cells"][1][
        "rsrp_dbm"
    ] = -121

    environment["cells"][1][
        "active_users"
    ] = 31


    # Preserve the failed KPI state
    # before automatic rollback.

    regression_snapshot = (
        deepcopy(
            environment["cells"]
        )
    )


    steps.append({

        "step":
            "Post-change KPI collection",

        "status":
            "PASS"
    })


    add_event(
        "KPI",
        "FAIL",
        "RAN regression: "
        "CELL-001 PRB 54->94, "
        "SINR 18->2, "
        "RSRP -82->-113, "
        "users 82->151; "
        "CELL-002 PRB 68->29, "
        "SINR 8->-3, "
        "RSRP -94->-121, "
        "users 103->31"
    )


    # -----------------------------------------------------
    # STEP 5
    # RAN KPI VALIDATION
    # -----------------------------------------------------

    validation = (
        check_ran_validation()
    )


    steps.append({

        "step":
            "RAN KPI validation",

        "status":
            validation["status"]
    })


    add_event(
        "VALIDATION",
        validation["status"],
        "Post-change RAN "
        "validation "
        f"{validation['status']}"
    )


    # -----------------------------------------------------
    # STEP 6
    # AUTOMATIC APPLICATION-LEVEL ROLLBACK
    # -----------------------------------------------------

    if (
        validation["status"]
        == "FAIL"
    ):

        failed_release = (
            environment["release"]
        )


        steps.append({

            "step":
                "Automatic rollback "
                "triggered",

            "status":
                "PASS"
        })


        add_event(
            "ROLLBACK",
            "PASS",
            "Regression detected. "
            f"Rolling back "
            f"{failed_release}"
        )


        # Restore known-good RAN baseline.

        environment["cells"] = (
            deepcopy(
                baseline_cells
            )
        )

        # Restore known-good release.

        environment["release"] = (
            "v1.0.0"
        )

        environment[
            "rollout_state"
        ] = "ROLLED_BACK"


        post_rollback_validation = (
            check_ran_validation()
        )


        steps.append({

            "step":
                "Restore release v1.0.0",

            "status":
                "PASS"
        })


        steps.append({

            "step":
                "Post-rollback validation",

            "status":
                post_rollback_validation[
                    "status"
                ]
        })


        add_event(
            "RELEASE",
            "PASS",
            "Previous release "
            "v1.0.0 restored"
        )


        add_event(
            "VALIDATION",
            post_rollback_validation[
                "status"
            ],
            "Post-rollback RAN "
            "validation "
            f"{post_rollback_validation['status']}"
        )


        return {

            "status":
                "ROLLED_BACK",

            "attempted_release":
                attempted_release,

            "active_release":
                environment["release"],

            "steps":
                steps,

            "regression_snapshot":
                regression_snapshot,

            "failed_validation":
                validation,

            "post_rollback_validation":
                post_rollback_validation
        }


    # -----------------------------------------------------
    # SUCCESS PATH
    # -----------------------------------------------------

    environment[
        "rollout_state"
    ] = "STABLE"


    steps.append({

        "step":
            "Rollout completed",

        "status":
            "PASS"
    })


    return {

        "status":
            "DEPLOYED",

        "active_release":
            environment["release"],

        "steps":
            steps,

        "validation":
            validation
    }