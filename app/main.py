import os
from copy import deepcopy
from urllib.request import urlopen
from urllib.error import URLError

from fastapi import FastAPI, HTTPException


app = FastAPI()

ENVIRONMENT_NAME = os.getenv("ENVIRONMENT_NAME", "ENV-LOCAL")
PRB_THRESHOLD = int(os.getenv("PRB_THRESHOLD", "20"))
SINR_THRESHOLD = int(os.getenv("SINR_THRESHOLD", "5"))

RAN_ADAPTER_URL = os.getenv(
    "RAN_ADAPTER_URL",
    "http://127.0.0.1:8000"
)

environment = {
    "environment_id": ENVIRONMENT_NAME,
    "release": "v1.0.0",

    "cells": [
        {
            "cell_id": "CELL-001",
            "technology": "5G",
            "prb_utilization": 54,
            "sinr_db": 18,
            "active_users": 82,
            "status": "ACTIVE"
        },
        {
            "cell_id": "CELL-002",
            "technology": "5G",
            "prb_utilization": 68,
            "sinr_db": 8,
            "active_users": 103,
            "status": "ACTIVE"
        },
        {
            "cell_id": "CELL-003",
            "technology": "4G",
            "prb_utilization": 45,
            "sinr_db": 25,
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


baseline_cells = deepcopy(environment["cells"])


@app.get("/cells")
def get_cells():
    return environment["cells"]


@app.get("/cells/{cell_id}/kpis")
def get_cell_kpis(cell_id: str):
    for cell in environment["cells"]:
        if cell["cell_id"] == cell_id:
            return {
                "cell_id": cell["cell_id"],
                "prb_utilization": cell["prb_utilization"],
                "sinr_db": cell["sinr_db"],
                "active_users": cell["active_users"],
                "status": cell["status"]
            }

    raise HTTPException(status_code=404, detail="Cell not found")


@app.get("/alarms")
def get_alarms():
    return environment["alarms"]


@app.get("/precheck")
def run_precheck():
    ran_adapter_available = False

    try:
        with urlopen(
            f"{RAN_ADAPTER_URL}/cells",
            timeout=2
        ) as response:
            ran_adapter_available = response.status == 200
    except (URLError, TimeoutError):
        ran_adapter_available = False

    checks = {
        "ran_adapter_available": ran_adapter_available,
        "cells_discovered": len(environment["cells"]) > 0,
        "kpi_baseline_collected": all(
            "prb_utilization" in cell
            and "sinr_db" in cell
            and "active_users" in cell
            for cell in environment["cells"]
        )
    }

    overall_pass = all(checks.values())

    return {
        "status": "PASS" if overall_pass else "FAIL",
        "checks": checks
    }

@app.get("/safety-score")
def get_safety_score():
    active_alarms = [
        alarm
        for alarm in environment["alarms"]
        if alarm["active"]
    ]

    environment_health = 25
    kubernetes_capacity = 20
    ran_baseline_stable = 20
    recent_alarms = 15 if len(active_alarms) == 0 else 10
    previous_release_health = 20

    total = (
        environment_health
        + kubernetes_capacity
        + ran_baseline_stable
        + recent_alarms
        + previous_release_health
    )

    return {
        "environment_health": environment_health,
        "kubernetes_capacity": kubernetes_capacity,
        "ran_baseline_stable": ran_baseline_stable,
        "recent_alarms": recent_alarms,
        "previous_release_health": previous_release_health,
        "total": total,
        "rollout_allowed": total >= 80
    }


@app.post("/configuration")
def apply_configuration(mode: str):
    if mode == "degraded":
        environment["cells"][0]["prb_utilization"] = 91
        environment["cells"][0]["sinr_db"] = 11

        return {
            "status": "APPLIED",
            "mode": "degraded"
        }

    if mode == "healthy":
        environment["cells"][0]["prb_utilization"] = 54
        environment["cells"][0]["sinr_db"] = 18

        return {
            "status": "APPLIED",
            "mode": "healthy"
        }

    raise HTTPException(
        status_code=400,
        detail="Unknown configuration mode"
    )


def check_ran_validation():
    failed_cells = []

    for cell in environment["cells"]:
        baseline = next(
            b
            for b in baseline_cells
            if b["cell_id"] == cell["cell_id"]
        )

        prb_increase = (
            cell["prb_utilization"]
            - baseline["prb_utilization"]
        )

        sinr_drop = (
            baseline["sinr_db"]
            - cell["sinr_db"]
        )

        if (
            prb_increase > PRB_THRESHOLD
            or sinr_drop > SINR_THRESHOLD
        ):
            failed_cells.append(cell["cell_id"])

    return {
        "status": "FAIL" if failed_cells else "PASS",
        "failed_cells": failed_cells
    }


@app.get("/validation")
def validate_ran():
    return check_ran_validation()


@app.post("/rollback")
def rollback():
    environment["cells"] = deepcopy(baseline_cells)

    return {
        "status": "ROLLED_BACK",
        "release": environment["release"]
    }


@app.post("/rollout")
def rollout():
    attempted_release = "v1.1.0"

    # Simulate deployment of the new release
    environment["release"] = attempted_release

    # Simulate RAN regression after deployment
    environment["cells"][0]["prb_utilization"] = 91
    environment["cells"][0]["sinr_db"] = 11

    # Post-change validation
    validation = check_ran_validation()

    if validation["status"] == "FAIL":
        # Automatic rollback
        environment["cells"] = deepcopy(baseline_cells)
        environment["release"] = "v1.0.0"

        return {
            "status": "ROLLED_BACK",
            "attempted_release": attempted_release,
            "active_release": environment["release"],
            "validation": validation
        }

    return {
        "status": "DEPLOYED",
        "active_release": environment["release"],
        "validation": validation
    }