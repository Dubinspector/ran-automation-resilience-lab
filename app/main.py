"""
FastAPI boundary for the RAN Automation Delivery &
Resilience Lab.

Architecture:

HTTP / dashboard
        â†“
RanAutomationController
        â†“
RAN configuration engine
        â†“
RF model
        â†“
traffic / UE association
        â†“
guardrails
        â†“
BLOCK / PROMOTE / ROLLBACK / SELF-HEAL

The API deliberately does not calculate RF KPIs itself.

The RAN sites and cells are synthetic learning-lab
infrastructure anchored to real geography around
Jesenice u Prahy. They are not claimed to represent
real operator BTS locations.
"""

import os

from contextlib import asynccontextmanager
from urllib.error import URLError
from urllib.request import urlopen

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from app.dashboard import DASHBOARD_HTML

from app.optimization_evaluator import (
    PeriodicOptimizationEvaluator,
    inject_optimization_widget,
)

from app.jesenice_scenario import (
    SCENARIO_METADATA,
)

from app.ran_controller import (
    RanAutomationController,
)

from app.ran_engine import (
    ALLOWED_BANDWIDTHS_MHZ,
    MAX_ELECTRICAL_TILT_DEG,
    MAX_TX_POWER_DBM,
    MIN_ELECTRICAL_TILT_DEG,
    MIN_TX_POWER_DBM,
    build_baseline_sites,
    build_candidate_sites,
    build_configuration_inventory,
    compare_cell_kpis,
)

from app.ran_guardrails import (
    evaluate_ran_guardrails,
)


# =========================================================
# FASTAPI APPLICATION LIFESPAN
# =========================================================

@asynccontextmanager
async def application_lifespan(app_instance):

    # optimization_evaluator is created during module import below.
    # The name is resolved when the application actually starts.
    optimization_evaluator.start()

    try:
        yield

    finally:
        optimization_evaluator.stop()


# =========================================================
# FASTAPI APPLICATION
# =========================================================

app = FastAPI(

    title=
        "RAN Automation Delivery & Resilience Lab",

    version=
        "2.3.1",

    lifespan=
        application_lifespan
)


# =========================================================
# APPLICATION CONFIGURATION
# =========================================================

ENVIRONMENT_NAME = os.getenv(
    "ENVIRONMENT_NAME",
    "ENV-LOCAL"
)


APPLICATION_RELEASE = os.getenv(
    "APPLICATION_RELEASE",
    "APP-v2.3.1"
)


RAN_ADAPTER_URL = os.getenv(
    "RAN_ADAPTER_URL",
    "http://127.0.0.1:8000"
)


OPTIMIZATION_INTERVAL_SECONDS = max(
    10.0,
    float(
        os.getenv(
            "OPTIMIZATION_INTERVAL_SECONDS",
            "60"
        )
    )
)


# Synthetic normal-load calibration for the operator demo.
# This is deliberately explicit and is NOT claimed to be measured
# T-Mobile traffic. Focused engine/controller regression tests keep
# their legacy multiplier=1.0 unless they opt into this runtime value.
NORMAL_TRAFFIC_MULTIPLIER = float(
    os.getenv(
        "NORMAL_TRAFFIC_MULTIPLIER",
        "0.25"
    )
)


# =========================================================
# CONTROLLER
# =========================================================
#
# Important:
#
# This controller is intentionally in-memory.
#
# One application process therefore owns one controller
# state.
#
# If this application were scaled to multiple active
# replicas, configuration state would need to move to
# an external durable / coordinated state store.
# =========================================================

controller = (
    RanAutomationController(
        traffic_multiplier=
            NORMAL_TRAFFIC_MULTIPLIER,

        steering_mode=
            "LOAD_AWARE"
    )
)


optimization_evaluator = (
    PeriodicOptimizationEvaluator(
        controller=controller,
        interval_seconds=OPTIMIZATION_INTERVAL_SECONDS
    )
)


# =========================================================
# FACTORY CONFIGURATION INVENTORY
# =========================================================

FACTORY_CONFIGURATION = (
    build_configuration_inventory(

        build_baseline_sites()
    )
)


# =========================================================
# API REQUEST MODELS
# =========================================================

class CellConfigUpdate(BaseModel):

    tx_power_dbm: float | None = Field(

        default=None,

        ge=MIN_TX_POWER_DBM,

        le=MAX_TX_POWER_DBM
    )


    bandwidth_mhz: int | None = Field(

        default=None,

        ge=5,

        le=100
    )


class AntennaConfigUpdate(BaseModel):

    electrical_tilt_deg: float | None = Field(

        default=None,

        ge=MIN_ELECTRICAL_TILT_DEG,

        le=MAX_ELECTRICAL_TILT_DEG
    )


class CandidateConfigRequest(BaseModel):

    cells: dict[
        str,
        CellConfigUpdate
    ] = Field(
        default_factory=dict
    )


    antennas: dict[
        str,
        AntennaConfigUpdate
    ] = Field(
        default_factory=dict
    )


class RfFaultInjectionRequest(BaseModel):

    site_id: str = Field(
        default="SITE-JESENICE-01"
    )

    band: str = Field(
        default="n78"
    )

    tx_power_dbm: float = Field(
        default=30.0,
        ge=MIN_TX_POWER_DBM,
        le=MAX_TX_POWER_DBM
    )


class CapacitySpikeInjectionRequest(BaseModel):

    spike_factor: float = Field(
        default=8.0,
        gt=1.0,
        le=8.0
    )


# =========================================================
# REQUEST -> ENGINE UPDATE FORMAT
# =========================================================

def request_to_updates(
    request: CandidateConfigRequest
):

    cell_updates = {

        cell_id:
            update.model_dump(
                exclude_none=True
            )

        for (
            cell_id,
            update
        ) in request.cells.items()
    }


    antenna_updates = {

        antenna_id:
            update.model_dump(
                exclude_none=True
            )

        for (
            antenna_id,
            update
        ) in request.antennas.items()
    }


    return (
        cell_updates,
        antenna_updates
    )


# =========================================================
# DASHBOARD CONFIGURATION FORMAT
# =========================================================
#
# dashboard.py was originally written against:
#
# {
#     "version": ...,
#     "cells": {
#         CELL-ID: {...}
#     },
#     "antennas": {
#         ANT-ID: {...}
#     }
# }
#
# ran_engine.py internally uses normalized inventory lists.
#
# This adapter preserves the API boundary while keeping
# the new engine internally cleaner.
# =========================================================

def inventory_to_dashboard_config(
    inventory,
    version
):

    cells = {}


    for cell in inventory[
        "cells"
    ]:

        cells[
            cell[
                "cell_id"
            ]
        ] = {

            "technology":
                cell[
                    "technology"
                ],

            "band":
                cell[
                    "band"
                ],

            "antenna_group":
                cell[
                    "antenna_id"
                ],

            "site_id":
                cell[
                    "site_id"
                ],

            "sector_id":
                cell[
                    "sector_id"
                ],

            "tx_power_dbm":
                cell[
                    "tx_power_dbm"
                ],

            "bandwidth_mhz":
                cell[
                    "bandwidth_mhz"
                ],

            "carrier_frequency_mhz":
                cell[
                    "frequency_mhz"
                ],

            "enabled":
                cell[
                    "enabled"
                ]
        }


    antennas = {}


    for antenna in inventory[
        "antennas"
    ]:

        antennas[
            antenna[
                "antenna_id"
            ]
        ] = {

            "site_id":
                antenna[
                    "site_id"
                ],

            "sector_id":
                antenna[
                    "sector_id"
                ],

            "profile":
                antenna[
                    "profile"
                ],

            "azimuth_deg":
                antenna[
                    "azimuth_deg"
                ],

            "mechanical_tilt_deg":
                antenna[
                    "mechanical_tilt_deg"
                ],

            "electrical_tilt_deg":
                antenna[
                    "electrical_tilt_deg"
                ]
        }


    return {

        "version":
            version,

        "cells":
            cells,

        "antennas":
            antennas
    }


# =========================================================
# ACTIVE DASHBOARD CONFIGURATION
# =========================================================

def get_active_dashboard_config():

    state = (
        controller.get_active_state()
    )


    return (
        inventory_to_dashboard_config(

            state[
                "configuration"
            ],

            state[
                "active_version"
            ]
        )
    )


# =========================================================
# FACTORY DASHBOARD CONFIGURATION
# =========================================================

def get_factory_dashboard_config():

    return (
        inventory_to_dashboard_config(

            FACTORY_CONFIGURATION,

            "CONFIG-1.0"
        )
    )


# =========================================================
# TOPOLOGY VIEW
# =========================================================

def build_topology_view():

    antennas = {}


    cells_by_antenna = {}


    for cell in FACTORY_CONFIGURATION[
        "cells"
    ]:

        antenna_id = (
            cell[
                "antenna_id"
            ]
        )


        cells_by_antenna.setdefault(
            antenna_id,
            []
        ).append(
            cell[
                "cell_id"
            ]
        )


    for antenna in FACTORY_CONFIGURATION[
        "antennas"
    ]:

        antenna_id = (
            antenna[
                "antenna_id"
            ]
        )


        antennas[
            antenna_id
        ] = {

            "site_id":
                antenna[
                    "site_id"
                ],

            "sector":
                antenna[
                    "sector_id"
                ],

            "profile":
                antenna[
                    "profile"
                ],

            "azimuth_deg":
                antenna[
                    "azimuth_deg"
                ],

            "cells":
                sorted(

                    cells_by_antenna.get(
                        antenna_id,
                        []
                    )
                )
        }


    sites = sorted({

        cell[
            "site_id"
        ]

        for cell
        in FACTORY_CONFIGURATION[
            "cells"
        ]
    })


    return {

        # Compatibility with the previous single-site
        # dashboard field.
        "site_id":
            SCENARIO_METADATA[
                "scenario_id"
            ],

        "scenario_id":
            SCENARIO_METADATA[
                "scenario_id"
            ],

        "scenario_name":
            SCENARIO_METADATA[
                "name"
            ],

        "real_bts_locations":
            SCENARIO_METADATA[
                "real_bts_locations"
            ],

        "sites":
            sites,

        "antennas":
            antennas
    }


# =========================================================
# NORMALIZED KPI -> LEGACY DASHBOARD KPI
# =========================================================

def normalized_cell_to_dashboard(
    cell
):

    degraded_users = int(

        cell.get(
            "serviceability_ue_mix",
            {}
        ).get(
            "DEGRADED",
            0
        )
    )


    return {

        "cell_id":
            cell[
                "cell_id"
            ],

        "site_id":
            cell[
                "site_id"
            ],

        "sector_id":
            cell[
                "sector_id"
            ],

        "technology":
            cell[
                "technology"
            ],

        "band":
            cell[
                "band"
            ],

        "bandwidth_mhz":
            cell[
                "bandwidth_mhz"
            ],

        # Compatibility names used by the existing
        # dashboard.
        "prb_utilization":
            cell[
                "prb_utilization_pct"
            ],

        "sinr_db":
            cell[
                "sinr_db"
            ],

        "rsrp_dbm":
            cell[
                "rsrp_dbm"
            ],

        "active_users":
            cell[
                "active_users"
            ],

        "status":
            (
                "DEGRADED"

                if degraded_users > 0

                else "ACTIVE"
            ),

        # New richer fields.
        "traffic_mbps":
            cell[
                "traffic_mbps"
            ],

        "estimated_capacity_mbps":
            cell[
                "estimated_capacity_mbps"
            ],

        "serviceability_ue_mix":
            cell[
                "serviceability_ue_mix"
            ]
    }


def normalized_cells_to_dashboard(
    cells
):

    return [

        normalized_cell_to_dashboard(
            cells[
                cell_id
            ]
        )

        for cell_id
        in sorted(
            cells
        )
    ]


# =========================================================
# FAILED-CELL EXTRACTION
# =========================================================

def extract_failed_cells(
    guardrails
):

    failed_cells = set()


    for check in guardrails[
        "failed_checks"
    ]:

        for field_name in (
            "baseline",
            "candidate"
        ):

            value = check.get(
                field_name
            )


            if (
                isinstance(
                    value,
                    str
                )

                and

                value.startswith(
                    "CELL-"
                )
            ):

                failed_cells.add(
                    value
                )


            if isinstance(
                value,
                dict
            ):

                cell_id = value.get(
                    "cell_id"
                )


                if (
                    isinstance(
                        cell_id,
                        str
                    )

                    and

                    cell_id.startswith(
                        "CELL-"
                    )
                ):

                    failed_cells.add(
                        cell_id
                    )


    return sorted(
        failed_cells
    )


# =========================================================
# LEGACY PER-CELL VALIDATION VIEW
# =========================================================
#
# The authoritative decision is guardrails["verdict"].
#
# This per-cell structure exists so the existing dashboard
# can still display familiar baseline/current/delta fields.
# =========================================================

def build_cell_validation_rows(
    baseline_snapshot,
    candidate_cells,
    guardrails
):

    if (
        baseline_snapshot is None

        or

        candidate_cells is None
    ):

        return []


    comparison = (
        compare_cell_kpis(

            baseline_snapshot,

            {
                "cells":
                    candidate_cells
            }
        )
    )


    policy = (
        guardrails[
            "policy"
        ]
    )


    rows = []


    for cell_id in sorted(
        comparison
    ):

        result = comparison[
            cell_id
        ]


        if (
            result[
                "status"
            ]
            != "COMPARABLE"
        ):

            continue


        baseline = (
            result[
                "baseline"
            ]
        )


        candidate = (
            result[
                "candidate"
            ]
        )


        delta = (
            result[
                "delta"
            ]
        )


        prb_failed = (

            delta[
                "prb_percentage_points"
            ]

            > policy[
                "max_comparable_cell_prb_increase_pp"
            ]
        )


        sinr_failed = (

            delta[
                "sinr_db"
            ]

            < -policy[
                "max_comparable_cell_sinr_drop_db"
            ]
        )


        rsrp_failed = (

            delta[
                "rsrp_db"
            ]

            < -policy[
                "max_comparable_cell_rsrp_drop_db"
            ]
        )


        rows.append({

            "cell_id":
                cell_id,

            "baseline": {

                "prb_utilization":
                    baseline[
                        "prb_utilization_pct"
                    ],

                "sinr_db":
                    baseline[
                        "sinr_db"
                    ],

                "rsrp_dbm":
                    baseline[
                        "rsrp_dbm"
                    ],

                "active_users":
                    baseline[
                        "active_users"
                    ]
            },

            "current": {

                "prb_utilization":
                    candidate[
                        "prb_utilization_pct"
                    ],

                "sinr_db":
                    candidate[
                        "sinr_db"
                    ],

                "rsrp_dbm":
                    candidate[
                        "rsrp_dbm"
                    ],

                "active_users":
                    candidate[
                        "active_users"
                    ]
            },

            "delta": {

                "prb":
                    delta[
                        "prb_percentage_points"
                    ],

                "sinr":
                    delta[
                        "sinr_db"
                    ],

                "rsrp":
                    delta[
                        "rsrp_db"
                    ],

                "users":
                    delta[
                        "active_users"
                    ]
            },

            "thresholds": {

                "prb_change":
                    policy[
                        "max_comparable_cell_prb_increase_pp"
                    ],

                "sinr_drop":
                    policy[
                        "max_comparable_cell_sinr_drop_db"
                    ],

                "rsrp_drop":
                    policy[
                        "max_comparable_cell_rsrp_drop_db"
                    ],

                # UE movement is intentionally not a
                # direct failure threshold anymore.
                "user_change":
                    None
            },

            "checks": {

                "prb":
                    (
                        "FAIL"
                        if prb_failed
                        else "PASS"
                    ),

                "sinr":
                    (
                        "FAIL"
                        if sinr_failed
                        else "PASS"
                    ),

                "rsrp":
                    (
                        "FAIL"
                        if rsrp_failed
                        else "PASS"
                    ),

                "users":
                    "INFO"
            }
        })


    return rows


# =========================================================
# GUARDRAILS -> API VALIDATION VIEW
# =========================================================

def guardrails_to_validation(
    guardrails,
    baseline_snapshot=None,
    candidate_cells=None
):

    return {

        "status":
            guardrails[
                "verdict"
            ],

        "failed_cells":
            extract_failed_cells(
                guardrails
            ),

        "cells":
            build_cell_validation_rows(

                baseline_snapshot,
                candidate_cells,
                guardrails
            ),

        "checks":
            guardrails[
                "checks"
            ],

        "failed_checks":
            guardrails[
                "failed_checks"
            ],

        "summary":
            guardrails[
                "summary"
            ],

        "reassociation":
            guardrails[
                "reassociation"
            ]
    }


# =========================================================
# CURRENT KNOWN-GOOD VALIDATION
# =========================================================

def get_current_validation():
    """
    Return a fresh validation of the ACTIVE RAN under the
    current authoritative weather + traffic-clock context.

    This intentionally re-observes the active configuration
    before validating it. "Known-good configuration" does not
    imply that current traffic/load is still inside the safe
    operating envelope.
    """

    observation = controller.get_baseline_health()
    snapshot = controller.get_active_snapshot()

    return guardrails_to_validation(
        observation["baseline_health"]["guardrails"],
        baseline_snapshot=snapshot,
        candidate_cells=snapshot["cells"],
    )


# =========================================================
# DYNAMIC ALARMS
# =========================================================

def build_active_alarms():

    snapshot = (
        controller.get_active_snapshot()
    )


    alarms = []


    alarm_number = 1


    for cell_id in sorted(
        snapshot[
            "cells"
        ]
    ):

        cell = (
            snapshot[
                "cells"
            ][
                cell_id
            ]
        )


        degraded_users = int(

            cell.get(
                "serviceability_ue_mix",
                {}
            ).get(
                "DEGRADED",
                0
            )
        )


        if degraded_users > 0:

            alarms.append({

                "alarm_id":
                    (
                        f"ALARM-"
                        f"{alarm_number:03d}"
                    ),

                "cell_id":
                    cell_id,

                "severity":
                    "MINOR",

                "type":
                    "DEGRADED_SERVICE",

                "active":
                    True,

                "detail":
                    (
                        f"{degraded_users} active UE "
                        "represented in DEGRADED service"
                    )
            })


            alarm_number += 1


        if (
            cell[
                "prb_utilization_pct"
            ]
            >= 85.0
        ):

            alarms.append({

                "alarm_id":
                    (
                        f"ALARM-"
                        f"{alarm_number:03d}"
                    ),

                "cell_id":
                    cell_id,

                "severity":
                    "MAJOR",

                "type":
                    "HIGH_PRB_UTILIZATION",

                "active":
                    True,

                "detail":
                    (
                        "PRB utilization is "
                        f"{cell['prb_utilization_pct']} %"
                    )
            })


            alarm_number += 1


    return alarms


# =========================================================
# EXTERNAL PRECHECK
# =========================================================
#
# RAN_ADAPTER_URL remains intentionally configurable.
#
# This preserves the previous ConfigMap / integration
# failure exercise where the application process is healthy
# while its configured RAN adapter endpoint is unavailable.
# =========================================================

def run_precheck_data():

    ran_adapter_available = False


    adapter_url = (
        RAN_ADAPTER_URL.rstrip(
            "/"
        )
    )


    try:

        with urlopen(

            f"{adapter_url}/cells",

            timeout=2

        ) as response:

            ran_adapter_available = (
                response.status == 200
            )


    except (
        URLError,
        TimeoutError,
        OSError
    ):

        ran_adapter_available = False


    state = (
        controller.get_active_state()
    )


    checks = {

        "ran_adapter_available":
            ran_adapter_available,

        "cells_discovered":
            (
                len(
                    state[
                        "configuration"
                    ][
                        "cells"
                    ]
                )
                > 0
            ),

        "kpi_baseline_collected":
            (
                len(
                    state[
                        "cells"
                    ]
                )
                > 0
            )
    }


    return {

        "status":
            (
                "PASS"

                if all(
                    checks.values()
                )

                else "FAIL"
            ),

        "checks":
            checks,

        "ran_adapter_url":
            RAN_ADAPTER_URL
    }


# =========================================================
# SAFETY SCORE
# =========================================================
#
# This remains a learning-lab rollout readiness summary.
#
# It is not a production operator scoring algorithm.
# =========================================================

def get_safety_score_data():

    validation = (
        get_current_validation()
    )


    active_alarms = (
        build_active_alarms()
    )


    environment_health = 25


    kubernetes_capacity = 20


    ran_baseline_stable = (

        20

        if (
            validation[
                "status"
            ]
            == "PASS"
        )

        else 0
    )


    recent_alarms = (

        15

        if not active_alarms

        else 10
    )


    previous_config_health = 20


    total = (

        environment_health

        + kubernetes_capacity

        + ran_baseline_stable

        + recent_alarms

        + previous_config_health
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

        "previous_config_health":
            previous_config_health,

        "total":
            total,

        "rollout_allowed":
            total >= 80,

        "note":
            (
                "Learning-lab rollout readiness score; "
                "not a production operator policy."
            )
    }


# =========================================================
# DASHBOARD
# =========================================================

@app.get(
    "/",
    response_class=HTMLResponse
)
def dashboard():

    return inject_optimization_widget(
        DASHBOARD_HTML
    )


# =========================================================
# PERIODIC OPTIMIZATION EVALUATOR
# =========================================================

@app.get(
    "/optimization/status"
)
def get_optimization_status():
    """
    Return the latest read-only optimization recommendation and
    recent evaluator history. Automatic RAN actuation is disabled.
    """

    return optimization_evaluator.get_status()


@app.post(
    "/optimization/evaluate-now"
)
def evaluate_optimization_now():
    """
    Trigger one immediate read-only evaluation for demo / inspection.

    This endpoint does not call guarded_apply(), run_self_healing() or
    any other state-changing controller operation.
    """

    return optimization_evaluator.evaluate_now(
        trigger="MANUAL"
    )


# =========================================================
# STATUS
# =========================================================

@app.get(
    "/status"
)
def get_status():
    """
    Fresh operator-facing state summary.

    One controller baseline observation supplies the weather,
    traffic simulation timestamp, service state and baseline-health
    decision so the fields describe the same modelled context.
    """

    observation = controller.get_baseline_health()
    state = controller.get_active_state()

    baseline_health = observation["baseline_health"]

    return {
        "environment": ENVIRONMENT_NAME,
        "scenario": SCENARIO_METADATA["scenario_id"],
        "application_release": APPLICATION_RELEASE,
        "ran_config_version": state["active_version"],
        "rollout_state": state["rollout_state"],
        "last_action": state["last_action"],
        "application_health": "HEALTHY",

        # Compatibility field used by the current dashboard.
        "ran_validation": baseline_health["status"],

        "served_ratio_pct": observation[
            "service"
        ][
            "served_ratio_pct"
        ],

        # New authoritative live context.
        "weather": observation["weather"],
        "simulation_timestamp": observation[
            "simulation_timestamp"
        ],
        "baseline_health": baseline_health,
        "service": observation["service"],
        "self_healing": controller.get_self_healing_state(),
        "normal_traffic_multiplier": NORMAL_TRAFFIC_MULTIPLIER,
    }


# =========================================================
# SELF-HEALING STATE
# =========================================================

@app.get(
    "/self-healing/status"
)
def get_self_healing_status():
    """
    Return non-mutating recovery state.

    Normal guarded changes and recovery are intentionally separate:
    an unhealthy baseline blocks ordinary promotion, while an active
    injected learning-lab fault authorizes the recovery workflow.
    """

    return controller.get_self_healing_state()


@app.get(
    "/weather"
)
def get_weather():
    """
    Return the exact weather snapshot and traffic simulation clock
    used to re-evaluate the active RAN for this request.

    The dashboard must consume this endpoint (or /status)
    rather than fetching Open-Meteo independently. That keeps
    displayed weather and modelled RAN state consistent.
    """

    observation = controller.get_baseline_health()

    return {
        "active_version": observation["active_version"],
        "weather": observation["weather"],
        "simulation_timestamp": observation[
            "simulation_timestamp"
        ],
        "baseline_health": {
            "status": observation[
                "baseline_health"
            ][
                "status"
            ],
            "inside_safe_envelope": observation[
                "baseline_health"
            ][
                "inside_safe_envelope"
            ],
            "failed_check_count": observation[
                "baseline_health"
            ][
                "failed_check_count"
            ],
            "failed_checks": observation[
                "baseline_health"
            ][
                "failed_checks"
            ],
        },
        "service": observation["service"],
    }


@app.get(
    "/baseline-health"
)
def get_baseline_health():
    """
    Full active-RAN baseline health observation for operator
    troubleshooting.
    """

    return controller.get_baseline_health()


# =========================================================
# CELLS
# =========================================================

@app.get(
    "/cells"
)
def get_cells():

    snapshot = (
        controller.get_active_snapshot()
    )


    return (
        normalized_cells_to_dashboard(

            snapshot[
                "cells"
            ]
        )
    )


@app.get(
    "/cells/{cell_id}/kpis"
)
def get_cell_kpis(
    cell_id: str
):

    snapshot = (
        controller.get_active_snapshot()
    )


    cell = (
        snapshot[
            "cells"
        ].get(
            cell_id
        )
    )


    if cell is not None:

        return (
            normalized_cell_to_dashboard(
                cell
            )
        )


    # -----------------------------------------------------
    # The cell may still exist in RAN configuration but
    # currently have no assigned traffic.
    # -----------------------------------------------------

    for configured_cell in snapshot[
        "configuration"
    ][
        "cells"
    ]:

        if (
            configured_cell[
                "cell_id"
            ]
            == cell_id
        ):

            return {

                "cell_id":
                    cell_id,

                "site_id":
                    configured_cell[
                        "site_id"
                    ],

                "sector_id":
                    configured_cell[
                        "sector_id"
                    ],

                "technology":
                    configured_cell[
                        "technology"
                    ],

                "band":
                    configured_cell[
                        "band"
                    ],

                "bandwidth_mhz":
                    configured_cell[
                        "bandwidth_mhz"
                    ],

                "prb_utilization":
                    None,

                "sinr_db":
                    None,

                "rsrp_dbm":
                    None,

                "active_users":
                    0,

                "status":
                    "NOT_SERVING",

                "traffic_mbps":
                    0.0,

                "estimated_capacity_mbps":
                    None,

                "serviceability_ue_mix":
                    {}
            }


    raise HTTPException(

        status_code=404,

        detail=(
            f"Unknown cell_id: "
            f"{cell_id}"
        )
    )


# =========================================================
# ALARMS
# =========================================================

@app.get(
    "/alarms"
)
def get_alarms():

    return (
        build_active_alarms()
    )


# =========================================================
# EVENTS
# =========================================================

@app.get(
    "/events"
)
def get_events():

    events = (
        controller.get_events(
            limit=100
        )
    )


    # Compatibility alias:
    #
    # previous API used "type";
    # controller uses "event_type".

    return [

        {

            **event,

            "type":
                event[
                    "event_type"
                ]
        }

        for event
        in events
    ]


# =========================================================
# PRECHECK
# =========================================================

@app.get(
    "/precheck"
)
def run_precheck():

    return (
        run_precheck_data()
    )


# =========================================================
# SAFETY SCORE
# =========================================================

@app.get(
    "/safety-score"
)
def get_safety_score():

    return (
        get_safety_score_data()
    )


# =========================================================
# CURRENT VALIDATION
# =========================================================

@app.get(
    "/validation"
)
def validate_ran():

    return (
        get_current_validation()
    )


# =========================================================
# RAN CONFIGURATION
# =========================================================

@app.get(
    "/ran-config"
)
def get_ran_config():

    topology = (
        build_topology_view()
    )


    return {

        "site":
            SCENARIO_METADATA[
                "scenario_id"
            ],

        "scenario": {

            "scenario_id":
                SCENARIO_METADATA[
                    "scenario_id"
                ],

            "name":
                SCENARIO_METADATA[
                    "name"
                ],

            "real_bts_locations":
                SCENARIO_METADATA[
                    "real_bts_locations"
                ]
        },

        "active":
            get_active_dashboard_config(),

        "factory_baseline":
            get_factory_dashboard_config(),

        "topology":
            topology,

        "allowed_ranges": {

            "tx_power_dbm": {

                "min":
                    MIN_TX_POWER_DBM,

                "max":
                    MAX_TX_POWER_DBM
            },

            "electrical_tilt_deg": {

                "min":
                    MIN_ELECTRICAL_TILT_DEG,

                "max":
                    MAX_ELECTRICAL_TILT_DEG
            },

            # Compatibility key for the current UI.
            #
            # The new model is actually band-aware, so the
            # definitive values are in
            # bandwidth_mhz_by_band below.
            "5G_bandwidth_mhz":
                sorted(

                    ALLOWED_BANDWIDTHS_MHZ[
                        "n28"
                    ]

                    |

                    ALLOWED_BANDWIDTHS_MHZ[
                        "n78"
                    ]
                ),

            "4G_bandwidth_mhz":
                sorted(

                    ALLOWED_BANDWIDTHS_MHZ[
                        "B3"
                    ]
                ),

            "bandwidth_mhz_by_band": {

                band:
                    sorted(
                        values
                    )

                for (
                    band,
                    values
                ) in ALLOWED_BANDWIDTHS_MHZ.items()
            }
        }
    }


# =========================================================
# EVALUATE CANDIDATE
# =========================================================
#
# This endpoint performs:
#
# config
#   -> RF
#   -> interference
#   -> UE association
#   -> traffic
#   -> KPI
#   -> guardrails
#
# but does NOT change active known-good state.
# =========================================================

@app.post(
    "/ran-config/evaluate"
)
def evaluate_candidate(
    request: CandidateConfigRequest
):
    """
    Non-mutating candidate preview.

    The controller freezes one weather snapshot and one traffic
    simulation timestamp, re-observes the active baseline under that
    pair, evaluates the candidate under the same pair, and returns
    separate baseline-health and candidate-outcome decisions.
    """

    (
        cell_updates,
        antenna_updates
    ) = request_to_updates(
        request
    )

    try:
        result = controller.evaluate(
            cell_updates=cell_updates,
            antenna_updates=antenna_updates,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    # evaluate() refreshes the active observation but does not
    # change active configuration. Therefore this snapshot is
    # the same weather + traffic-clock baseline used by the
    # controller attempt.
    baseline_snapshot = controller.get_active_snapshot()

    validation = guardrails_to_validation(
        result["guardrails"],
        baseline_snapshot=baseline_snapshot,
        candidate_cells=result["candidate_cells"],
    )

    candidate_config = inventory_to_dashboard_config(
        result["candidate_configuration"],
        result["candidate_version"],
    )

    return {
        # Compatibility contract used by the current dashboard.
        "status": "EVALUATED",
        "candidate_version": result["candidate_version"],
        "active_version": result["active_version"],
        "candidate_config": candidate_config,
        "predicted_cells": normalized_cells_to_dashboard(
            result["candidate_cells"]
        ),
        "validation": validation,
        "would_be_accepted": result["would_be_accepted"],

        # Rich controller context.
        "decision": result["decision"],
        "attempt_id": result["attempt_id"],
        "baseline_version": result["baseline_version"],
        "weather": result["weather"],
        "simulation_timestamp": result[
            "simulation_timestamp"
        ],
        "baseline_health": result["baseline_health"],
        "baseline_service": result["baseline_service"],
        "candidate_service": result["candidate_service"],
        "guardrails": result["guardrails"],
        "reassociation": result[
            "guardrails"
        ][
            "reassociation"
        ],
    }


# =========================================================
# GUARDED APPLY
# =========================================================

@app.post(
    "/ran-config/guarded-apply"
)
def guarded_apply_candidate(
    request: CandidateConfigRequest
):
    """
    Guarded configuration apply.

    Order:
      1. external adapter pre-check,
      2. freeze one weather + traffic-clock context pair,
      3. capture the active same-context baseline,
      4. controller baseline-health pre-check,
      5. only if healthy: build/evaluate candidate,
      6. promote or rollback.

    An unhealthy baseline returns BLOCKED. No candidate RF
    evaluation occurs and no rollback is needed.
    """

    # -----------------------------------------------------
    # STEP 0 - EXTERNAL INTEGRATION PRECHECK
    # -----------------------------------------------------

    precheck = run_precheck_data()

    if precheck["status"] != "PASS":
        return {
            "status": "BLOCKED",
            "reason": "EXTERNAL_PRECHECK_FAILED",
            "active_version": controller.get_active_state()[
                "active_version"
            ],
            "candidate_evaluated": False,
            "configuration_changed": False,
            "steps": [
                {
                    "step": "External RAN adapter pre-check",
                    "status": "FAIL",
                }
            ],
            "precheck": precheck,
        }

    (
        cell_updates,
        antenna_updates
    ) = request_to_updates(
        request
    )

    # -----------------------------------------------------
    # FREEZE CURRENT CONTEXT FOR THIS API ATTEMPT
    # -----------------------------------------------------
    #
    # get_baseline_health() resolves the weather and traffic
    # simulation clock once and refreshes the active observation.
    # We then pass that exact pair into guarded_apply(), so the
    # API baseline and controller baseline/candidate comparison
    # are context-identical.
    # -----------------------------------------------------

    baseline_observation = controller.get_baseline_health()

    attempt_weather = baseline_observation[
        "weather"
    ]

    attempt_simulation_timestamp = baseline_observation[
        "simulation_timestamp"
    ]

    baseline_snapshot = controller.get_active_snapshot()
    baseline_sites = controller.get_active_sites()

    result = controller.guarded_apply(
        cell_updates=cell_updates,
        antenna_updates=antenna_updates,
        weather=attempt_weather,
        simulation_timestamp=attempt_simulation_timestamp,
    )

    steps = [
        {
            "step": "External RAN adapter pre-check",
            "status": "PASS",
        },
        *result["steps"],
    ]

    # -----------------------------------------------------
    # ACTIVE RAN ALREADY UNSAFE -> BLOCK
    # -----------------------------------------------------

    if result["status"] == "BLOCKED":
        return {
            "status": "BLOCKED",
            "reason": result["reason"],
            "attempt_id": result["attempt_id"],
            "previous_version": result["previous_version"],
            "candidate_version": result["candidate_version"],
            "active_version": result["active_version"],
            "weather": result["weather"],
            "simulation_timestamp": result[
                "simulation_timestamp"
            ],
            "baseline_health": result["baseline_health"],
            "baseline_service": result["baseline_service"],
            "active_service": result["active_service"],
            "candidate_evaluated": result[
                "candidate_evaluated"
            ],
            "configuration_changed": result[
                "configuration_changed"
            ],
            "steps": steps,
            "precheck": precheck,
            "candidate_config": None,
        }

    if result["status"] == "REJECTED":
        raise HTTPException(
            status_code=400,
            detail=result.get(
                "error",
                "Candidate rejected",
            ),
        )

    # -----------------------------------------------------
    # CONFIG-ONLY CANDIDATE VIEW
    # -----------------------------------------------------
    #
    # This runs only after the controller has passed baseline
    # health and accepted the candidate input shape. It does
    # not calculate RF in the API layer.
    # -----------------------------------------------------

    try:
        candidate_sites_preview = build_candidate_sites(
            base_sites=baseline_sites,
            cell_updates=cell_updates,
            antenna_updates=antenna_updates,
        )

        candidate_inventory_preview = (
            build_configuration_inventory(
                candidate_sites_preview
            )
        )

    except ValueError as exc:
        # Defensive only: the controller has already validated
        # the same candidate input.
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    candidate_config = inventory_to_dashboard_config(
        candidate_inventory_preview,
        result["candidate_version"],
    )

    # =====================================================
    # PASS -> ACTIVE CONFIGURATION CHANGED
    # =====================================================

    if result["status"] == "APPLIED":
        active_snapshot = controller.get_active_snapshot()

        validation = guardrails_to_validation(
            result["guardrails"],
            baseline_snapshot=baseline_snapshot,
            candidate_cells=active_snapshot["cells"],
        )

        return {
            "status": "APPLIED",
            "attempt_id": result["attempt_id"],
            "previous_version": result["previous_version"],
            "candidate_version": result["candidate_version"],
            "active_version": result["active_version"],
            "weather": result["weather"],
            "simulation_timestamp": result[
                "simulation_timestamp"
            ],
            "baseline_health": result["baseline_health"],
            "steps": steps,
            "precheck": precheck,
            "candidate_config": candidate_config,
            "active_config": get_active_dashboard_config(),
            "cells": normalized_cells_to_dashboard(
                active_snapshot["cells"]
            ),
            "validation": validation,
            "active_service": result["active_service"],
            "guardrails": result["guardrails"],
            "reassociation": result[
                "guardrails"
            ][
                "reassociation"
            ],
            "candidate_evaluated": True,
            "configuration_changed": True,
        }

    # =====================================================
    # FAIL -> PREVIOUS KNOWN-GOOD REMAINS ACTIVE
    # =====================================================

    restored_snapshot = controller.get_active_snapshot()

    failed_validation = guardrails_to_validation(
        result["guardrails"]
    )

    # Use the controller's same-context rollback verification.
    # Do NOT call get_current_validation() here because that
    # could resolve newer weather or a newer traffic clock and
    # contaminate the attempt evidence.
    post_rollback_validation = guardrails_to_validation(
        result["rollback_verification"],
        baseline_snapshot=baseline_snapshot,
        candidate_cells=restored_snapshot["cells"],
    )

    return {
        "status": "ROLLED_BACK",
        "attempt_id": result["attempt_id"],
        "previous_version": result["previous_version"],
        "candidate_version": result["candidate_version"],
        "active_version": result["active_version"],
        "weather": result["weather"],
        "simulation_timestamp": result[
            "simulation_timestamp"
        ],
        "baseline_health": result["baseline_health"],
        "steps": steps,
        "precheck": precheck,
        "candidate_config": candidate_config,

        # Candidate RF state is represented by authoritative
        # candidate guardrails. It was never promoted.
        "candidate_cells": [],
        "failed_validation": failed_validation,
        "post_rollback_validation": post_rollback_validation,
        "candidate_service": result["candidate_service"],
        "restored_service": result["restored_service"],
        "guardrails": result["guardrails"],
        "rollback_verification": result[
            "rollback_verification"
        ],
        "reassociation": result[
            "guardrails"
        ][
            "reassociation"
        ],
        "restored_cells": normalized_cells_to_dashboard(
            restored_snapshot["cells"]
        ),
        "candidate_evaluated": True,
        "configuration_changed": False,
    }


# =========================================================
# LEARNING-LAB RF FAULT INJECTION
# =========================================================
#
# Fault injection is deliberately separate from configuration
# promotion. It simulates an operational RF degradation without
# incrementing the accepted configuration revision.
# =========================================================

@app.post(
    "/self-healing/inject-rf-fault"
)
def inject_rf_fault(
    request: RfFaultInjectionRequest
):

    inventory = build_configuration_inventory(
        controller.get_active_sites()
    )

    cell_ids = [
        cell["cell_id"]
        for cell in inventory["cells"]
        if (
            cell["site_id"] == request.site_id
            and
            cell["band"] == request.band
            and
            cell.get("enabled", True)
        )
    ]

    if not cell_ids:
        raise HTTPException(
            status_code=400,
            detail=(
                "No enabled cells match fault-injection scope: "
                f"site={request.site_id}, band={request.band}"
            ),
        )

    try:
        result = controller.inject_rf_fault(
            cell_ids=cell_ids,
            tx_power_dbm=request.tx_power_dbm,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    snapshot = controller.get_active_snapshot()

    return {
        **result,
        "site_id": request.site_id,
        "band": request.band,
        "cell_ids": cell_ids,
        "active_config": get_active_dashboard_config(),
        "cells": normalized_cells_to_dashboard(
            snapshot["cells"]
        ),
        "self_healing": controller.get_self_healing_state(),
    }


# =========================================================
# LEARNING-LAB CAPACITY SPIKE INJECTION
# =========================================================
#
# This changes synthetic traffic demand, not accepted RAN
# configuration. The subsequent self-healing path must keep the
# elevated demand fixed and recover by changing traffic steering.
# =========================================================

@app.post(
    "/self-healing/inject-capacity-spike"
)
def inject_capacity_spike(
    request: CapacitySpikeInjectionRequest
):

    try:
        result = controller.inject_capacity_spike(
            spike_factor=request.spike_factor
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    snapshot = controller.get_active_snapshot()

    return {
        **result,
        "active_config": get_active_dashboard_config(),
        "cells": normalized_cells_to_dashboard(
            snapshot["cells"]
        ),
        "self_healing": controller.get_self_healing_state(),
    }


# =========================================================
# SELF-HEALING / RECOVERY
# =========================================================
#
# This is a separately authorized remediation path. It does not
# weaken guarded_apply(): normal configuration promotion remains
# fail-closed when the active baseline is already unhealthy.
#
# For a recovery attempt we freeze the same weather + traffic-clock
# context and restore the last intentionally accepted known-good
# configuration or apply capacity-recovery split steering for a capacity event.
# Capacity recovery keeps the elevated demand fixed during verification.
# =========================================================

@app.post(
    "/self-healing/run"
)
def run_self_healing():

    precheck = run_precheck_data()

    if precheck["status"] != "PASS":
        return {
            "status": "BLOCKED",
            "reason": "EXTERNAL_PRECHECK_FAILED",
            "active_version": controller.get_active_state()[
                "active_version"
            ],
            "configuration_changed": False,
            "configuration_revision_changed": False,
            "precheck": precheck,
            "steps": [
                {
                    "step": "External RAN adapter pre-check",
                    "status": "FAIL",
                }
            ],
        }

    # Freeze exactly one environment + traffic context pair for the
    # recovery attempt, just as guarded_apply() does.
    observation = controller.get_baseline_health()

    result = controller.run_self_healing(
        weather=observation["weather"],
        simulation_timestamp=observation[
            "simulation_timestamp"
        ],
    )

    snapshot = controller.get_active_snapshot()

    return {
        **result,
        "precheck": precheck,
        "steps": [
            {
                "step": "External RAN adapter pre-check",
                "status": "PASS",
            },
            *result.get("steps", []),
        ],
        "active_config": get_active_dashboard_config(),
        "cells": normalized_cells_to_dashboard(
            snapshot["cells"]
        ),
        "self_healing": controller.get_self_healing_state(),
    }


# =========================================================
# RESTORE FACTORY BASELINE
# =========================================================

@app.post(
    "/ran-config/restore-baseline"
)
def restore_factory_baseline():
    result = controller.restore_factory_baseline()
    snapshot = controller.get_active_snapshot()

    validation = guardrails_to_validation(
        result["baseline_health"]["guardrails"],
        baseline_snapshot=snapshot,
        candidate_cells=snapshot["cells"],
    )

    return {
        "status": result["status"],
        "previous_version": result["previous_version"],
        "active_version": result["active_version"],
        "weather": result["weather"],
        "simulation_timestamp": result[
            "simulation_timestamp"
        ],
        "baseline_health": result["baseline_health"],
        "active_config": get_active_dashboard_config(),
        "validation": validation,
        "service": result["service"],
    }


# =========================================================
# RETIRED LEGACY ENDPOINTS
# =========================================================
#
# The previous implementation allowed direct KPI mutation:
#
#   /configuration?mode=degraded
#   /rollback
#   /rollout
#
# That bypassed the RF model and therefore no longer fits
# the architecture.
#
# We keep explicit endpoints temporarily so callers receive
# a clear explanation instead of an ambiguous HTTP 404.
# =========================================================

@app.post(
    "/configuration"
)
def retired_configuration(
    mode: str
):

    raise HTTPException(

        status_code=410,

        detail=(
            "Legacy direct KPI injection has been removed. "
            "Use /ran-config/evaluate and "
            "/ran-config/guarded-apply."
        )
    )


@app.post(
    "/rollback"
)
def retired_manual_rollback():

    raise HTTPException(

        status_code=410,

        detail=(
            "Legacy manual KPI rollback has been removed. "
            "Guarded RAN configuration rollback is handled "
            "by RanAutomationController."
        )
    )


@app.post(
    "/rollout"
)
def retired_legacy_rollout():

    raise HTTPException(

        status_code=410,

        detail=(
            "Legacy hard-coded rollout regression has been "
            "removed. Use the physical RAN configuration "
            "guarded-apply workflow."
        )
    )
