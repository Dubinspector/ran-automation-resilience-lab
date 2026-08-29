"""
Jesenice u Prahy synthetic RAN scenario.

IMPORTANT
---------

This file intentionally separates:

1. public / real geographic reference data,
2. synthetic RAN infrastructure,
3. RF model configuration.

The site and cell locations defined here are NOT claimed
to be real T-Mobile or other operator BTS locations.

They are synthetic scenario anchors placed around real
localities so that the lab can use realistic geography
without pretending to know a production RAN topology.

RF propagation calculations are performed elsewhere.
This file contains topology and model inputs only.
"""


# =========================================================
# SCENARIO METADATA
# =========================================================

SCENARIO_METADATA = {

    "scenario_id":
        "JESENICE-RAN-01",

    "name":
        "Jesenice u Prahy Synthetic RAN",

    "country":
        "CZ",

    "region":
        "Praha-zapad / south-east Prague edge",

    "center": {
        "latitude": 49.96876,
        "longitude": 14.51581,
        "elevation_m": 351
    },

    "operator_profile":
        "T-Mobile-CZ-inspired-spectrum",

    "real_bts_locations":
        False,

    "description":
        (
            "Synthetic multi-site RAN scenario anchored "
            "to real geography around Jesenice u Prahy. "
            "Exact BTS positions, sectors, antenna "
            "parameters and traffic are lab assumptions."
        )
}


# =========================================================
# REAL GEOGRAPHIC REFERENCE POINTS
# =========================================================

REFERENCE_LOCALITIES = {

    "JESENICE": {

        "name":
            "Jesenice",

        "latitude":
            49.96876,

        "longitude":
            14.51581,

        "elevation_m":
            351,

        "scenario_environment":
            "SUBURBAN_MIXED"
    },


    "ZDIMERICE": {

        "name":
            "Zdiměřice",

        "latitude":
            49.97889,

        "longitude":
            14.53089,

        "elevation_m":
            333,

        "scenario_environment":
            "SUBURBAN_RESIDENTIAL"
    },


    "OSNICE": {

        "name":
            "Osnice",

        "latitude":
            49.96934,

        "longitude":
            14.55142,

        "elevation_m":
            347,

        "scenario_environment":
            "SUBURBAN_OPEN"
    },


    "KOCANDA": {

        "name":
            "Kocanda",

        "latitude":
            49.97097,

        "longitude":
            14.54058,

        "elevation_m":
            343,

        "scenario_environment":
            "SUBURBAN_RESIDENTIAL"
    },


    "VESTEC": {

        "name":
            "Vestec",

        "latitude":
            49.98076,

        "longitude":
            14.50696,

        "elevation_m":
            327,

        "scenario_environment":
            "SUBURBAN_MIXED"
    },


    "DOLNI_JIRCANY": {

        "name":
            "Dolní Jirčany",

        "latitude":
            49.94847,

        "longitude":
            14.52142,

        "elevation_m":
            411,

        "scenario_environment":
            "ROLLING_SUBURBAN"
    },


    "PRUHONICE": {

        "name":
            "Průhonice",

        "latitude":
            50.00178,

        "longitude":
            14.56064,

        "elevation_m":
            296,

        "scenario_environment":
            "SUBURBAN_MIXED"
    },


    "HERINK": {

        "name":
            "Herink",

        "latitude":
            49.96706,

        "longitude":
            14.57521,

        "elevation_m":
            362,

        "scenario_environment":
            "SUBURBAN_OPEN"
    }
}


# =========================================================
# CARRIER PROFILES
# =========================================================

CARRIER_PROFILES = {

    "N78_3510": {

        "technology":
            "5G",

        "band":
            "n78",

        "duplex":
            "TDD",

        "downlink_center_frequency_mhz":
            3510.0,

        "uplink_center_frequency_mhz":
            3510.0,

        "bandwidth_mhz":
            60,

        "default_tx_power_dbm":
            43.0,

        "spectrum_basis":
            (
                "Synthetic carrier aligned to public "
                "T-Mobile CZ 3480-3540 MHz allocation"
            )
    },


    "N28_773": {

        "technology":
            "5G",

        "band":
            "n28",

        "duplex":
            "FDD",

        "downlink_center_frequency_mhz":
            773.0,

        "uplink_center_frequency_mhz":
            718.0,

        "bandwidth_mhz":
            10,

        "default_tx_power_dbm":
            40.0,

        "spectrum_basis":
            (
                "Synthetic carrier aligned to public "
                "T-Mobile CZ 700 MHz allocation"
            )
    },


    "LTE_B3_SYNTHETIC": {

        "technology":
            "4G",

        "band":
            "B3",

        "duplex":
            "FDD",

        "downlink_center_frequency_mhz":
            1800.0,

        "uplink_center_frequency_mhz":
            1710.0,

        "bandwidth_mhz":
            20,

        "default_tx_power_dbm":
            40.0,

        "spectrum_basis":
            "Synthetic LTE 1800 MHz lab layer"
    }
}


# =========================================================
# ANTENNA PROFILES
# =========================================================

ANTENNA_PROFILES = {

    "LOW_MID_PANEL": {

        "model_type":
            "PASSIVE_SECTOR_PANEL",

        "max_gain_dbi":
            17.0,

        "horizontal_3db_beamwidth_deg":
            65.0,

        "vertical_3db_beamwidth_deg":
            8.0,

        "max_horizontal_attenuation_db":
            30.0,

        "max_vertical_attenuation_db":
            30.0
    },


    "N78_AAU": {

        "model_type":
            "ACTIVE_ARRAY",

        "max_gain_dbi":
            24.0,

        "horizontal_3db_beamwidth_deg":
            65.0,

        "vertical_3db_beamwidth_deg":
            8.0,

        "max_horizontal_attenuation_db":
            30.0,

        "max_vertical_attenuation_db":
            30.0
    }
}


# =========================================================
# HELPERS
# =========================================================

def build_cell(
    site_code,
    sector_code,
    antenna_code,
    carrier_profile
):

    carrier = CARRIER_PROFILES[
        carrier_profile
    ]


    return {

        "cell_id":
            (
                f"CELL-{site_code}-"
                f"{sector_code}-"
                f"{carrier['band'].upper()}"
            ),

        "technology":
            carrier[
                "technology"
            ],

        "band":
            carrier[
                "band"
            ],

        "duplex":
            carrier[
                "duplex"
            ],

        "antenna_system":
            antenna_code,

        "downlink_center_frequency_mhz":
            carrier[
                "downlink_center_frequency_mhz"
            ],

        "uplink_center_frequency_mhz":
            carrier[
                "uplink_center_frequency_mhz"
            ],

        "bandwidth_mhz":
            carrier[
                "bandwidth_mhz"
            ],

        "tx_power_dbm":
            carrier[
                "default_tx_power_dbm"
            ],

        "spectrum_basis":
            carrier[
                "spectrum_basis"
            ],

        "enabled":
            True
    }


def build_sector(
    site_code,
    sector_code,
    azimuth_deg,
    low_mid_tilt_deg,
    n78_tilt_deg
):

    low_mid_antenna_id = (
        f"ANT-{site_code}-"
        f"{sector_code}-LOWMID"
    )

    n78_antenna_id = (
        f"ANT-{site_code}-"
        f"{sector_code}-N78"
    )


    return {

        "sector_id":
            (
                f"SECTOR-{site_code}-"
                f"{sector_code}"
            ),

        "azimuth_deg":
            azimuth_deg,


        "antenna_systems": {

            low_mid_antenna_id: {

                "profile":
                    "LOW_MID_PANEL",

                "azimuth_deg":
                    azimuth_deg,

                "mechanical_tilt_deg":
                    0.0,

                "electrical_tilt_deg":
                    low_mid_tilt_deg,

                "cells": [

                    build_cell(
                        site_code,
                        sector_code,
                        low_mid_antenna_id,
                        "N28_773"
                    ),

                    build_cell(
                        site_code,
                        sector_code,
                        low_mid_antenna_id,
                        "LTE_B3_SYNTHETIC"
                    )
                ]
            },


            n78_antenna_id: {

                "profile":
                    "N78_AAU",

                "azimuth_deg":
                    azimuth_deg,

                "mechanical_tilt_deg":
                    0.0,

                "electrical_tilt_deg":
                    n78_tilt_deg,

                "cells": [

                    build_cell(
                        site_code,
                        sector_code,
                        n78_antenna_id,
                        "N78_3510"
                    )
                ]
            }
        }
    }


def build_site(
    site_id,
    site_code,
    anchor_key,
    antenna_height_agl_m,
    azimuths_deg,
    low_mid_tilt_deg,
    n78_tilt_deg
):

    anchor = REFERENCE_LOCALITIES[
        anchor_key
    ]


    return {

        "site_id":
            site_id,

        "site_code":
            site_code,

        "anchor_locality":
            anchor[
                "name"
            ],

        "latitude":
            anchor[
                "latitude"
            ],

        "longitude":
            anchor[
                "longitude"
            ],

        "ground_elevation_m":
            anchor[
                "elevation_m"
            ],

        "antenna_height_agl_m":
            antenna_height_agl_m,

        "location_is_real_bts":
            False,

        "location_basis":
            "synthetic site at real locality anchor",

        "sectors": {

            "A":
                build_sector(
                    site_code,
                    "A",
                    azimuths_deg[0],
                    low_mid_tilt_deg,
                    n78_tilt_deg
                ),

            "B":
                build_sector(
                    site_code,
                    "B",
                    azimuths_deg[1],
                    low_mid_tilt_deg,
                    n78_tilt_deg
                ),

            "C":
                build_sector(
                    site_code,
                    "C",
                    azimuths_deg[2],
                    low_mid_tilt_deg,
                    n78_tilt_deg
                )
        }
    }


# =========================================================
# SYNTHETIC RAN SITES
# =========================================================

SYNTHETIC_SITES = {

    "SITE-JESENICE-01":
        build_site(
            site_id=
                "SITE-JESENICE-01",

            site_code=
                "JES",

            anchor_key=
                "JESENICE",

            antenna_height_agl_m=
                30.0,

            azimuths_deg=
                (
                    45.0,
                    165.0,
                    285.0
                ),

            low_mid_tilt_deg=
                5.0,

            n78_tilt_deg=
                6.0
        ),


    "SITE-ZDIMERICE-01":
        build_site(
            site_id=
                "SITE-ZDIMERICE-01",

            site_code=
                "ZDI",

            anchor_key=
                "ZDIMERICE",

            antenna_height_agl_m=
                27.0,

            azimuths_deg=
                (
                    40.0,
                    160.0,
                    280.0
                ),

            low_mid_tilt_deg=
                4.5,

            n78_tilt_deg=
                5.5
        ),


    "SITE-OSNICE-01":
        build_site(
            site_id=
                "SITE-OSNICE-01",

            site_code=
                "OSN",

            anchor_key=
                "OSNICE",

            antenna_height_agl_m=
                32.0,

            azimuths_deg=
                (
                    10.0,
                    130.0,
                    250.0
                ),

            low_mid_tilt_deg=
                4.0,

            n78_tilt_deg=
                5.0
        ),


    "SITE-VESTEC-01":
        build_site(
            site_id=
                "SITE-VESTEC-01",

            site_code=
                "VES",

            anchor_key=
                "VESTEC",

            antenna_height_agl_m=
                28.0,

            azimuths_deg=
                (
                    60.0,
                    180.0,
                    300.0
                ),

            low_mid_tilt_deg=
                5.0,

            n78_tilt_deg=
                6.0
        ),


    "SITE-PRUHONICE-01":
        build_site(
            site_id=
                "SITE-PRUHONICE-01",

            site_code=
                "PRU",

            anchor_key=
                "PRUHONICE",

            antenna_height_agl_m=
                30.0,

            azimuths_deg=
                (
                    30.0,
                    150.0,
                    270.0
                ),

            low_mid_tilt_deg=
                5.0,

            n78_tilt_deg=
                6.0
        ),


    # -----------------------------------------------------
    # DOLNI JIRCANY SYNTHETIC SITE
    # -----------------------------------------------------
    #
    # The first synthetic version used:
    #
    # 60 / 180 / 300 degrees
    #
    # The deterministic UE sample bearings for this
    # observation area happened to be:
    #
    # 0 / 120 / 240 degrees
    #
    # That placed every UE sample exactly on a boundary
    # between two 120-degree sectors and produced an
    # artificial equal-power interference condition.
    #
    # We preserve the normal 120-degree sector spacing
    # but rotate the entire synthetic site by 17 degrees.
    #
    # This is NOT presented as a measured operator
    # azimuth. Exact sector orientation remains a
    # learning-lab assumption.
    # -----------------------------------------------------

    "SITE-DOLNI-JIRCANY-01":
        build_site(
            site_id=
                "SITE-DOLNI-JIRCANY-01",

            site_code=
                "DJI",

            anchor_key=
                "DOLNI_JIRCANY",

            antenna_height_agl_m=
                28.0,

            azimuths_deg=
                (
                    77.0,
                    197.0,
                    317.0
                ),

            low_mid_tilt_deg=
                4.5,

            n78_tilt_deg=
                5.5
        )
}


# =========================================================
# OBSERVATION AREAS
# =========================================================

OBSERVATION_AREAS = {

    "UE-JESENICE": {

        "name":
            "Jesenice centre",

        "anchor":
            "JESENICE",

        "nominal_active_ues":
            160,

        "traffic_weight":
            1.00
    },


    "UE-ZDIMERICE": {

        "name":
            "Zdiměřice residential",

        "anchor":
            "ZDIMERICE",

        "nominal_active_ues":
            95,

        "traffic_weight":
            0.70
    },


    "UE-KOCANDA": {

        "name":
            "Kocanda",

        "anchor":
            "KOCANDA",

        "nominal_active_ues":
            110,

        "traffic_weight":
            0.80
    },


    "UE-OSNICE": {

        "name":
            "Osnice",

        "anchor":
            "OSNICE",

        "nominal_active_ues":
            85,

        "traffic_weight":
            0.65
    },


    "UE-VESTEC": {

        "name":
            "Vestec",

        "anchor":
            "VESTEC",

        "nominal_active_ues":
            145,

        "traffic_weight":
            0.95
    },


    "UE-DOLNI-JIRCANY": {

        "name":
            "Dolní Jirčany",

        "anchor":
            "DOLNI_JIRCANY",

        "nominal_active_ues":
            70,

        "traffic_weight":
            0.55
    },


    "UE-PRUHONICE": {

        "name":
            "Průhonice",

        "anchor":
            "PRUHONICE",

        "nominal_active_ues":
            180,

        "traffic_weight":
            1.10
    },


    "UE-HERINK": {

        "name":
            "Herink",

        "anchor":
            "HERINK",

        "nominal_active_ues":
            65,

        "traffic_weight":
            0.50
    }
}


for area in OBSERVATION_AREAS.values():

    anchor = REFERENCE_LOCALITIES[
        area[
            "anchor"
        ]
    ]

    area[
        "latitude"
    ] = anchor[
        "latitude"
    ]

    area[
        "longitude"
    ] = anchor[
        "longitude"
    ]

    area[
        "ground_elevation_m"
    ] = anchor[
        "elevation_m"
    ]

    area[
        "environment"
    ] = anchor[
        "scenario_environment"
    ]

    area[
        "ue_height_agl_m"
    ] = 1.5


# =========================================================
# WEATHER INPUT POLICY
# =========================================================

WEATHER_INPUT_POLICY = {

    "reference_location":
        "Jesenice",

    "mode":
        "RECORDED_OBSERVATION",

    "required_fields": [

        "timestamp",

        "temperature_c",

        "pressure_hpa",

        "relative_humidity_pct",

        "rain_rate_mm_per_h"
    ],

    "optional_fields": [

        "wind_speed_m_per_s",

        "wind_direction_deg"
    ],

    "rf_usage": {

        "rain":
            "ITU-R P.838",

        "atmospheric_gases":
            "ITU-R P.676"
    }
}


# =========================================================
# RF MODEL POLICY
# =========================================================

RF_MODEL_POLICY = {

    "geometry": {

        "use_real_lat_lon":
            True,

        "use_ground_elevation":
            True,

        "calculate_2d_distance":
            True,

        "calculate_3d_distance":
            True,

        "calculate_bearing":
            True,

        "calculate_vertical_angle":
            True
    },


    "antenna_pattern": {

        "use_sector_azimuth":
            True,

        "use_electrical_tilt":
            True,

        "use_mechanical_tilt":
            True,

        "use_horizontal_pattern":
            True,

        "use_vertical_pattern":
            True
    },


    "propagation": {

        "primary_model":
            "3GPP TR 38.901",

        "free_space_reference":
            "ITU-R P.525",

        "rain_model":
            "ITU-R P.838",

        "gas_model":
            "ITU-R P.676"
    },


    "interference": {

        "same_frequency_cells":
            True,

        "power_sum_in_linear_domain":
            True,

        "noise_floor":
            True
    },


    "kpi_derivation": {

        "rsrp":
            "derived from received reference signal",

        "sinr":
            (
                "serving signal divided by "
                "interference plus noise"
            ),

        "active_users":
            (
                "population-scaled synthetic "
                "time-of-day traffic demand"
            ),

        "prb_utilization":
            (
                "traffic/capacity proxy derived from "
                "bandwidth and radio conditions"
            )
    },


    "forbidden_shortcuts": [

        "fixed tilt-to-RSRP penalty",

        "fixed TX-power-to-SINR penalty",

        "weather causes arbitrary large KPI drop",

        "claiming synthetic sites are real BTS sites"
    ]
}