"""
RAN configuration simulation engine.

This module connects:

synthetic RAN configuration
        â†“
RF model
        â†“
traffic / UE association model
        â†“
normalized KPI snapshot

It deliberately contains no FastAPI code and no rollout /
rollback state machine.

That separation allows the automation layer in main.py to
treat the RF simulator as an external RAN adapter would be
treated in a real automation platform.
"""

from copy import deepcopy

from app.jesenice_scenario import (
    ANTENNA_PROFILES,
    SYNTHETIC_SITES,
)

from app.traffic_model import (
    build_traffic_snapshot,
)


# =========================================================
# DEFAULT WEATHER SNAPSHOT
# =========================================================
#
# Recorded dry baseline used by the current learning lab.
#
# Later this can be injected dynamically through the API.
# =========================================================

DEFAULT_WEATHER = {

    "timestamp":
        "2026-08-28T00:40:00+02:00",

    "temperature_c":
        20.5,

    "pressure_hpa":
        1014.1,

    "relative_humidity_pct":
        58.9,

    "rain_rate_mm_per_h":
        0.0
}


# =========================================================
# CONFIGURATION LIMITS
# =========================================================
#
# These are simulator input validation limits.
#
# They are NOT claims about universal operator or vendor
# limits.
# =========================================================

MIN_TX_POWER_DBM = 30.0
MAX_TX_POWER_DBM = 49.0

MIN_ELECTRICAL_TILT_DEG = 0.0
MAX_ELECTRICAL_TILT_DEG = 12.0


ALLOWED_BANDWIDTHS_MHZ = {

    "n78":
        {
            40,
            50,
            60,
            80,
            100
        },

    "n28":
        {
            5,
            10,
            15,
            20
        },

    "B3":
        {
            5,
            10,
            15,
            20
        }
}


# =========================================================
# BASELINE CONFIGURATION
# =========================================================

def build_baseline_sites():

    return deepcopy(
        SYNTHETIC_SITES
    )


# =========================================================
# TOPOLOGY ITERATORS
# =========================================================

def iter_antennas(
    sites
):

    for (
        site_id,
        site
    ) in sites.items():

        for (
            sector_key,
            sector
        ) in site[
            "sectors"
        ].items():

            for (
                antenna_id,
                antenna
            ) in sector[
                "antenna_systems"
            ].items():

                yield {

                    "site_id":
                        site_id,

                    "site":
                        site,

                    "sector_key":
                        sector_key,

                    "sector":
                        sector,

                    "antenna_id":
                        antenna_id,

                    "antenna":
                        antenna
                }


def iter_cells(
    sites
):

    for antenna_record in iter_antennas(
        sites
    ):

        antenna = (
            antenna_record[
                "antenna"
            ]
        )

        for cell in antenna[
            "cells"
        ]:

            yield {

                **antenna_record,

                "cell":
                    cell
            }


# =========================================================
# LOOKUPS
# =========================================================

def find_cell(
    sites,
    cell_id
):

    for record in iter_cells(
        sites
    ):

        if (
            record[
                "cell"
            ][
                "cell_id"
            ]
            == cell_id
        ):

            return record


    raise ValueError(
        f"Unknown cell_id: {cell_id}"
    )


def find_antenna(
    sites,
    antenna_id
):

    for record in iter_antennas(
        sites
    ):

        if (
            record[
                "antenna_id"
            ]
            == antenna_id
        ):

            return record


    raise ValueError(
        f"Unknown antenna_id: {antenna_id}"
    )


# =========================================================
# VALIDATION
# =========================================================

def validate_tx_power(
    value
):

    value = float(
        value
    )


    if not (
        MIN_TX_POWER_DBM
        <= value
        <= MAX_TX_POWER_DBM
    ):

        raise ValueError(

            "TX power must be between "

            f"{MIN_TX_POWER_DBM} and "
            f"{MAX_TX_POWER_DBM} dBm"
        )


    return value


def validate_tilt(
    value
):

    value = float(
        value
    )


    if not (
        MIN_ELECTRICAL_TILT_DEG
        <= value
        <= MAX_ELECTRICAL_TILT_DEG
    ):

        raise ValueError(

            "Electrical tilt must be between "

            f"{MIN_ELECTRICAL_TILT_DEG} and "
            f"{MAX_ELECTRICAL_TILT_DEG} degrees"
        )


    return value


def validate_bandwidth(
    band,
    bandwidth_mhz
):

    bandwidth_mhz = int(
        bandwidth_mhz
    )


    allowed = (
        ALLOWED_BANDWIDTHS_MHZ.get(
            band
        )
    )


    if allowed is None:

        raise ValueError(
            f"No bandwidth policy for band {band}"
        )


    if bandwidth_mhz not in allowed:

        raise ValueError(

            f"Bandwidth {bandwidth_mhz} MHz "

            f"is not allowed for band {band}. "

            f"Allowed values: "
            f"{sorted(allowed)}"
        )


    return bandwidth_mhz


# =========================================================
# APPLY CELL CONFIGURATION
# =========================================================

def apply_cell_update(
    sites,
    cell_id,
    tx_power_dbm=None,
    bandwidth_mhz=None
):

    record = find_cell(
        sites,
        cell_id
    )


    cell = record[
        "cell"
    ]


    if tx_power_dbm is not None:

        cell[
            "tx_power_dbm"
        ] = validate_tx_power(
            tx_power_dbm
        )


    if bandwidth_mhz is not None:

        cell[
            "bandwidth_mhz"
        ] = validate_bandwidth(

            cell[
                "band"
            ],

            bandwidth_mhz
        )


    return cell


# =========================================================
# APPLY ANTENNA CONFIGURATION
# =========================================================

def apply_antenna_update(
    sites,
    antenna_id,
    electrical_tilt_deg=None
):

    record = find_antenna(
        sites,
        antenna_id
    )


    antenna = record[
        "antenna"
    ]


    if electrical_tilt_deg is not None:

        antenna[
            "electrical_tilt_deg"
        ] = validate_tilt(
            electrical_tilt_deg
        )


    return antenna


# =========================================================
# BUILD CANDIDATE TOPOLOGY
# =========================================================

def build_candidate_sites(
    base_sites=None,
    cell_updates=None,
    antenna_updates=None
):

    if base_sites is None:

        candidate = (
            build_baseline_sites()
        )

    else:

        candidate = deepcopy(
            base_sites
        )


    if cell_updates is None:

        cell_updates = {}


    if antenna_updates is None:

        antenna_updates = {}


    for (
        cell_id,
        update
    ) in cell_updates.items():

        apply_cell_update(

            candidate,

            cell_id,

            tx_power_dbm=
                update.get(
                    "tx_power_dbm"
                ),

            bandwidth_mhz=
                update.get(
                    "bandwidth_mhz"
                )
        )


    for (
        antenna_id,
        update
    ) in antenna_updates.items():

        apply_antenna_update(

            candidate,

            antenna_id,

            electrical_tilt_deg=
                update.get(
                    "electrical_tilt_deg"
                )
        )


    return candidate


# =========================================================
# CONFIGURATION INVENTORY
# =========================================================

def build_configuration_inventory(
    sites
):

    antennas = []

    cells = []


    for record in iter_antennas(
        sites
    ):

        antenna = (
            record[
                "antenna"
            ]
        )


        antennas.append({

            "site_id":
                record[
                    "site_id"
                ],

            "sector_id":
                record[
                    "sector"
                ][
                    "sector_id"
                ],

            "antenna_id":
                record[
                    "antenna_id"
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
        })


    for record in iter_cells(
        sites
    ):

        cell = (
            record[
                "cell"
            ]
        )


        cells.append({

            "site_id":
                record[
                    "site_id"
                ],

            "sector_id":
                record[
                    "sector"
                ][
                    "sector_id"
                ],

            "antenna_id":
                record[
                    "antenna_id"
                ],

            "cell_id":
                cell[
                    "cell_id"
                ],

            "technology":
                cell[
                    "technology"
                ],

            "band":
                cell[
                    "band"
                ],

            "frequency_mhz":
                cell[
                    "downlink_center_frequency_mhz"
                ],

            "bandwidth_mhz":
                cell[
                    "bandwidth_mhz"
                ],

            "tx_power_dbm":
                cell[
                    "tx_power_dbm"
                ],

            "enabled":
                cell[
                    "enabled"
                ]
        })


    return {

        "antennas":
            antennas,

        "cells":
            cells
    }


# =========================================================
# NORMALIZED KPI VIEW
# =========================================================

def normalize_cell_kpis(
    traffic_snapshot
):

    normalized = {}


    for cell in traffic_snapshot[
        "cells"
    ]:

        normalized[
            cell[
                "cell_id"
            ]
        ] = {

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

            "prb_utilization_pct":
                cell[
                    "prb_utilization_pct"
                ],

            "sinr_db":
                cell[
                    "weighted_mean_sinr_db"
                ],

            "rsrp_dbm":
                cell[
                    "weighted_mean_rsrp_dbm"
                ],

            "active_users":
                cell[
                    "active_users"
                ],

            "traffic_mbps":
                cell[
                    "traffic_mbps"
                ],

            "estimated_capacity_mbps":
                cell[
                    "estimated_capacity_mbps"
                ],

            "serviceability_ue_mix":
                deepcopy(
                    cell[
                        "serviceability_ue_mix"
                    ]
                )
        }


    return normalized


# =========================================================
# RUN ONE RAN SNAPSHOT
# =========================================================

def evaluate_ran_state(
    sites=None,
    weather=None,
    simulation_timestamp=None
):

    if sites is None:

        sites = (
            build_baseline_sites()
        )


    if weather is None:

        weather = deepcopy(
            DEFAULT_WEATHER
        )


    # -----------------------------------------------------
    # TRAFFIC CLOCK
    # -----------------------------------------------------
    #
    # Keep environmental observation time separate from the
    # traffic/activity clock.
    #
    # The controller supplies an explicit runtime timestamp.
    # The fallback preserves deterministic behaviour for older
    # direct engine callers and existing focused unit tests.
    # -----------------------------------------------------

    if simulation_timestamp is None:

        simulation_timestamp = (
            weather[
                "timestamp"
            ]
        )


    traffic_snapshot = (
        build_traffic_snapshot(

            weather,

            sites=sites,

            antenna_profiles=
                ANTENNA_PROFILES,

            simulation_timestamp=
                simulation_timestamp
        )
    )


    return {

        "weather":
            deepcopy(
                weather
            ),

        "simulation_timestamp":
            traffic_snapshot[
                "simulation_timestamp"
            ],

        "configuration":
            build_configuration_inventory(
                sites
            ),

        "population_model":
            deepcopy(
                traffic_snapshot[
                    "population_model"
                ]
            ),

        "service":
            deepcopy(
                traffic_snapshot[
                    "service"
                ]
            ),

        "radio_model_range":
            deepcopy(
                traffic_snapshot[
                    "radio_model_range"
                ]
            ),

        "cells":
            normalize_cell_kpis(
                traffic_snapshot
            ),

        "assignments":
            deepcopy(
                traffic_snapshot[
                    "assignments"
                ]
            )
    }


# =========================================================
# BASELINE -> CANDIDATE COMPARISON
# =========================================================

def compare_cell_kpis(
    baseline_snapshot,
    candidate_snapshot
):

    baseline_cells = (
        baseline_snapshot[
            "cells"
        ]
    )


    candidate_cells = (
        candidate_snapshot[
            "cells"
        ]
    )


    cell_ids = sorted(

        set(
            baseline_cells
        )

        | set(
            candidate_cells
        )
    )


    comparison = {}


    for cell_id in cell_ids:

        baseline = (
            baseline_cells.get(
                cell_id
            )
        )

        candidate = (
            candidate_cells.get(
                cell_id
            )
        )


        # A serving cell may appear or disappear because UE
        # association changed.
        #
        # We intentionally retain that as an observable
        # automation event rather than inventing KPI values
        # for a cell with no assigned traffic.

        if baseline is None:

            comparison[
                cell_id
            ] = {

                "status":
                    "NEW_SERVING_CELL",

                "baseline":
                    None,

                "candidate":
                    candidate
            }

            continue


        if candidate is None:

            comparison[
                cell_id
            ] = {

                "status":
                    "NO_LONGER_SERVING",

                "baseline":
                    baseline,

                "candidate":
                    None
            }

            continue


        comparison[
            cell_id
        ] = {

            "status":
                "COMPARABLE",

            "baseline":
                baseline,

            "candidate":
                candidate,

            "delta": {

                "prb_percentage_points":
                    round(

                        candidate[
                            "prb_utilization_pct"
                        ]

                        - baseline[
                            "prb_utilization_pct"
                        ],

                        2
                    ),

                "sinr_db":
                    round(

                        candidate[
                            "sinr_db"
                        ]

                        - baseline[
                            "sinr_db"
                        ],

                        2
                    ),

                "rsrp_db":
                    round(

                        candidate[
                            "rsrp_dbm"
                        ]

                        - baseline[
                            "rsrp_dbm"
                        ],

                        2
                    ),

                "active_users":
                    (

                        candidate[
                            "active_users"
                        ]

                        - baseline[
                            "active_users"
                        ]
                    )
            }
        }


    return comparison
