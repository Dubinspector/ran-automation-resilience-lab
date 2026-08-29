"""
RF model for the Jesenice u Prahy RAN learning lab.

This module uses:
- real geographic locality anchors from app.jesenice_scenario,
- synthetic sites / sectors / cells,
- deterministic UE sample points around each observation area,
- 3GPP-style sector antenna patterns,
- 3GPP UMa LOS / NLOS path-loss equations,
- ITU-R P.838 rain attenuation,
- a compact sub-54-GHz gaseous attenuation approximation reproduced
  in ITU-R P.2001 and based on ITU-R P.676,
- co-channel interference and thermal noise for SINR.

It is intentionally NOT a ray tracer and NOT a production RF planner.

Important limitations:
- site positions are synthetic learning-lab locations,
- generated UE points are synthetic samples around real localities,
- LOS/NLOS is selected from a deterministic scenario class, not from
  building-by-building ray tracing,
- ground elevation at generated UE samples uses the area's locality
  elevation as an approximation,
- diffraction, foliage, indoor penetration, shadow fading and fast fading
  are not yet modelled,
- RSRP is a proxy derived from received carrier power and occupied
  subcarriers under an equal-power assumption.
"""

import math
from collections import defaultdict
from copy import deepcopy

from app.jesenice_scenario import (
    ANTENNA_PROFILES,
    OBSERVATION_AREAS,
    SYNTHETIC_SITES,
)


EARTH_RADIUS_M = 6_371_000.0
SPEED_OF_LIGHT_M_S = 299_792_458.0
MIN_UMa_DISTANCE_M = 10.0
REFERENCE_TEMPERATURE_K = 290.0
DEFAULT_UE_NOISE_FIGURE_DB = 7.0


# =========================================================
# UE SAMPLE DISTRIBUTION
# =========================================================
#
# Every locality is represented by multiple outdoor UE
# sample points.
#
# This is important because:
#
# - a whole village must not behave like one UE,
# - some site/locality anchors have identical coordinates,
# - different sides of a sector must see different antenna
#   gain and interference.
#
# These are synthetic sample points around real geographic
# locality centres.
# =========================================================

UE_SAMPLE_LAYOUTS = {

    "SUBURBAN_RESIDENTIAL": {

        "radii_m":
            (
                180.0,
                420.0
            ),

        "bearings_deg":
            (
                20.0,
                140.0,
                260.0
            )
    },


    "SUBURBAN_MIXED": {

        "radii_m":
            (
                220.0,
                520.0
            ),

        "bearings_deg":
            (
                10.0,
                130.0,
                250.0
            )
    },


    "SUBURBAN_OPEN": {

        "radii_m":
            (
                300.0,
                750.0
            ),

        "bearings_deg":
            (
                0.0,
                120.0,
                240.0
            )
    },


    "ROLLING_SUBURBAN": {

        "radii_m":
            (
                250.0,
                650.0
            ),

        "bearings_deg":
            (
                35.0,
                155.0,
                275.0
            )
    }
}


# =========================================================
# PROPAGATION CONDITION
# =========================================================
#
# This is still a SCENARIO assumption.
#
# We currently do not have a building-by-building ray tracer
# or full terrain profile between every BS and UE.
#
# Therefore:
#
# SUBURBAN_OPEN -> representative LOS
#
# Other suburban classes -> representative NLOS
#
# The actual path-loss equation itself is physics /
# measurement based; only the LOS/NLOS classification
# is simplified.
# =========================================================

ENVIRONMENT_TO_PROPAGATION_CONDITION = {

    "SUBURBAN_OPEN":
        "LOS",

    "SUBURBAN_MIXED":
        "NLOS",

    "SUBURBAN_RESIDENTIAL":
        "NLOS",

    "ROLLING_SUBURBAN":
        "NLOS"
}


# =========================================================
# ITU-R P.838 RAIN COEFFICIENTS
# =========================================================
#
# frequency GHz:
#
# (
#   k_H,
#   alpha_H,
#   k_V,
#   alpha_V
# )
#
# The current lab only needs the sub-6 GHz range.
#
# P.838's coefficient table begins at 1 GHz.
#
# Our 773 MHz n28 layer therefore uses the 1 GHz
# coefficients as a conservative approximation.
#
# At those frequencies rain attenuation over local links is
# extremely small anyway.
# =========================================================

P838_COEFFICIENTS = {

    1.0:
        (
            0.0000259,
            0.9691,
            0.0000308,
            0.8592
        ),

    1.5:
        (
            0.0000443,
            1.0185,
            0.0000574,
            0.8957
        ),

    2.0:
        (
            0.0000847,
            1.0664,
            0.0000998,
            0.9490
        ),

    2.5:
        (
            0.0001321,
            1.1209,
            0.0001464,
            1.0085
        ),

    3.0:
        (
            0.0001390,
            1.2322,
            0.0001942,
            1.0688
        ),

    3.5:
        (
            0.0001155,
            1.4189,
            0.0002346,
            1.1387
        ),

    4.0:
        (
            0.0001071,
            1.6009,
            0.0002461,
            1.2476
        ),

    4.5:
        (
            0.0001340,
            1.6948,
            0.0002347,
            1.3987
        ),

    5.0:
        (
            0.0002162,
            1.6969,
            0.0002428,
            1.5317
        ),

    5.5:
        (
            0.0003909,
            1.6499,
            0.0003115,
            1.5882
        ),

    6.0:
        (
            0.0007056,
            1.5900,
            0.0004878,
            1.5728
        ),

    7.0:
        (
            0.0019150,
            1.4810,
            0.0014250,
            1.4745
        ),

    8.0:
        (
            0.0041150,
            1.3905,
            0.0034500,
            1.3797
        ),

    9.0:
        (
            0.0075350,
            1.3155,
            0.0066910,
            1.2895
        ),

    10.0:
        (
            0.0121700,
            1.2571,
            0.0112900,
            1.2156
        )
}


# =========================================================
# OCCUPIED SUBCARRIERS
# =========================================================
#
# Used for an approximate conversion:
#
# received carrier power
#
#       ↓
#
# reference-element power / RSRP proxy
#
# It is preferable to bandwidth / SCS alone because real
# OFDM carriers leave guard bands.
# =========================================================

LTE_OCCUPIED_SUBCARRIERS = {

    5:
        25 * 12,

    10:
        50 * 12,

    15:
        75 * 12,

    20:
        100 * 12
}


NR_FR1_15KHZ_OCCUPIED_SUBCARRIERS = {

    5:
        25 * 12,

    10:
        52 * 12,

    15:
        79 * 12,

    20:
        106 * 12
}


NR_FR1_30KHZ_OCCUPIED_SUBCARRIERS = {

    20:
        51 * 12,

    40:
        106 * 12,

    50:
        133 * 12,

    60:
        162 * 12,

    80:
        217 * 12,

    100:
        273 * 12
}


# =========================================================
# BASIC HELPERS
# =========================================================

def clamp(
    value,
    minimum,
    maximum
):

    return max(
        minimum,
        min(
            maximum,
            value
        )
    )


def dbm_to_mw(
    dbm
):

    return (
        10.0
        ** (
            dbm / 10.0
        )
    )


def mw_to_dbm(
    mw
):

    if mw <= 0.0:

        return float(
            "-inf"
        )


    return (
        10.0
        * math.log10(
            mw
        )
    )


def wrap_angle_180(
    angle_deg
):

    return (
        (
            angle_deg
            + 180.0
        )
        % 360.0
        - 180.0
    )


# =========================================================
# GEOGRAPHIC GEOMETRY
# =========================================================

def haversine_distance_m(
    lat1_deg,
    lon1_deg,
    lat2_deg,
    lon2_deg
):

    lat1 = math.radians(
        lat1_deg
    )

    lat2 = math.radians(
        lat2_deg
    )


    delta_lat = math.radians(
        lat2_deg
        - lat1_deg
    )


    delta_lon = math.radians(
        lon2_deg
        - lon1_deg
    )


    a = (

        math.sin(
            delta_lat / 2.0
        ) ** 2

        + math.cos(
            lat1
        )

        * math.cos(
            lat2
        )

        * math.sin(
            delta_lon / 2.0
        ) ** 2
    )


    c = (
        2.0
        * math.atan2(

            math.sqrt(
                a
            ),

            math.sqrt(
                1.0 - a
            )
        )
    )


    return (
        EARTH_RADIUS_M
        * c
    )


def initial_bearing_deg(
    lat1_deg,
    lon1_deg,
    lat2_deg,
    lon2_deg
):

    lat1 = math.radians(
        lat1_deg
    )

    lat2 = math.radians(
        lat2_deg
    )


    delta_lon = math.radians(
        lon2_deg
        - lon1_deg
    )


    y = (

        math.sin(
            delta_lon
        )

        * math.cos(
            lat2
        )
    )


    x = (

        math.cos(
            lat1
        )

        * math.sin(
            lat2
        )

        - math.sin(
            lat1
        )

        * math.cos(
            lat2
        )

        * math.cos(
            delta_lon
        )
    )


    return (

        math.degrees(
            math.atan2(
                y,
                x
            )
        )

        % 360.0
    )


def destination_point(
    latitude_deg,
    longitude_deg,
    bearing_deg,
    distance_m
):

    angular_distance = (
        distance_m
        / EARTH_RADIUS_M
    )


    lat1 = math.radians(
        latitude_deg
    )


    lon1 = math.radians(
        longitude_deg
    )


    bearing = math.radians(
        bearing_deg
    )


    lat2 = math.asin(

        math.sin(
            lat1
        )

        * math.cos(
            angular_distance
        )

        + math.cos(
            lat1
        )

        * math.sin(
            angular_distance
        )

        * math.cos(
            bearing
        )
    )


    lon2 = (

        lon1

        + math.atan2(

            math.sin(
                bearing
            )

            * math.sin(
                angular_distance
            )

            * math.cos(
                lat1
            ),

            math.cos(
                angular_distance
            )

            - math.sin(
                lat1
            )

            * math.sin(
                lat2
            )
        )
    )


    return {

        "latitude":
            math.degrees(
                lat2
            ),

        "longitude":
            math.degrees(
                lon2
            )
    }


# =========================================================
# SYNTHETIC UE POINTS AROUND REAL LOCALITIES
# =========================================================

def generate_ue_sample_points(
    observation_areas=None
):

    if observation_areas is None:

        observation_areas = (
            OBSERVATION_AREAS
        )


    samples = []


    for area_index, (
        area_id,
        area
    ) in enumerate(
        observation_areas.items()
    ):

        layout = (
            UE_SAMPLE_LAYOUTS.get(

                area[
                    "environment"
                ],

                UE_SAMPLE_LAYOUTS[
                    "SUBURBAN_MIXED"
                ]
            )
        )


        combinations = []


        # Rotate the pattern for each locality so every area
        # does not generate UE points on identical bearings.

        rotation_deg = (
            area_index
            * 17.0
        ) % 360.0


        for radius_m in layout[
            "radii_m"
        ]:

            for bearing_deg in layout[
                "bearings_deg"
            ]:

                combinations.append(

                    (
                        radius_m,

                        (
                            bearing_deg
                            + rotation_deg
                        )
                        % 360.0
                    )
                )


        sample_count = len(
            combinations
        )


        total_ues = int(
            area[
                "nominal_active_ues"
            ]
        )


        base_ues = (
            total_ues
            // sample_count
        )


        remainder = (
            total_ues
            % sample_count
        )


        for sample_index, (
            radius_m,
            bearing_deg
        ) in enumerate(
            combinations,
            start=1
        ):

            point = (
                destination_point(

                    area[
                        "latitude"
                    ],

                    area[
                        "longitude"
                    ],

                    bearing_deg,

                    radius_m
                )
            )


            assigned_ues = (

                base_ues

                + (
                    1

                    if sample_index
                    <= remainder

                    else 0
                )
            )


            samples.append({

                "sample_id":
                    (
                        f"{area_id}-"
                        f"P{sample_index:02d}"
                    ),

                "area_id":
                    area_id,

                "area_name":
                    area[
                        "name"
                    ],

                "latitude":
                    point[
                        "latitude"
                    ],

                "longitude":
                    point[
                        "longitude"
                    ],


                # Until we add a real elevation raster,
                # the locality elevation is used for
                # generated points around that locality.

                "ground_elevation_m":
                    area[
                        "ground_elevation_m"
                    ],

                "ground_elevation_basis":
                    (
                        "locality anchor "
                        "approximation"
                    ),

                "ue_height_agl_m":
                    area[
                        "ue_height_agl_m"
                    ],

                "environment":
                    area[
                        "environment"
                    ],

                "representative_active_ues":
                    assigned_ues,

                "sample_radius_from_area_center_m":
                    radius_m,

                "sample_bearing_from_area_center_deg":
                    bearing_deg
            })


    return samples


# =========================================================
# WEATHER
# =========================================================

def saturation_vapor_pressure_hpa(
    temperature_c
):

    return (

        6.112

        * math.exp(

            (
                17.62
                * temperature_c
            )

            / (
                243.12
                + temperature_c
            )
        )
    )


def water_vapor_density_g_m3(
    temperature_c,
    relative_humidity_pct
):

    saturation_hpa = (
        saturation_vapor_pressure_hpa(
            temperature_c
        )
    )


    vapor_pressure_hpa = (

        saturation_hpa

        * clamp(
            relative_humidity_pct,
            0.0,
            100.0
        )

        / 100.0
    )


    temperature_k = (
        temperature_c
        + 273.15
    )


    return (

        216.7

        * vapor_pressure_hpa

        / temperature_k
    )


# =========================================================
# P.838 INTERPOLATION
# =========================================================

def _interpolate_log_value(
    x,
    x1,
    y1,
    x2,
    y2
):

    if x1 == x2:

        return y1


    fraction = (

        (
            math.log10(
                x
            )

            - math.log10(
                x1
            )
        )

        / (
            math.log10(
                x2
            )

            - math.log10(
                x1
            )
        )
    )


    return (

        10.0

        ** (

            math.log10(
                y1
            )

            + fraction

            * (
                math.log10(
                    y2
                )

                - math.log10(
                    y1
                )
            )
        )
    )


def _interpolate_linear_value(
    x,
    x1,
    y1,
    x2,
    y2
):

    if x1 == x2:

        return y1


    fraction = (

        (
            x
            - x1
        )

        / (
            x2
            - x1
        )
    )


    return (

        y1

        + fraction

        * (
            y2
            - y1
        )
    )


def p838_coefficients(
    frequency_ghz
):

    frequencies = sorted(
        P838_COEFFICIENTS
    )


    effective_frequency = clamp(

        frequency_ghz,

        frequencies[
            0
        ],

        frequencies[
            -1
        ]
    )


    if (
        effective_frequency
        in P838_COEFFICIENTS
    ):

        return (

            P838_COEFFICIENTS[
                effective_frequency
            ],

            effective_frequency
        )


    lower = frequencies[
        0
    ]

    upper = frequencies[
        -1
    ]


    for index in range(
        len(
            frequencies
        ) - 1
    ):

        left = frequencies[
            index
        ]

        right = frequencies[
            index + 1
        ]


        if (
            left
            <= effective_frequency
            <= right
        ):

            lower = left
            upper = right

            break


    (
        k_h1,
        alpha_h1,
        k_v1,
        alpha_v1
    ) = (
        P838_COEFFICIENTS[
            lower
        ]
    )


    (
        k_h2,
        alpha_h2,
        k_v2,
        alpha_v2
    ) = (
        P838_COEFFICIENTS[
            upper
        ]
    )


    k_h = _interpolate_log_value(

        effective_frequency,

        lower,
        k_h1,

        upper,
        k_h2
    )


    k_v = _interpolate_log_value(

        effective_frequency,

        lower,
        k_v1,

        upper,
        k_v2
    )


    alpha_h = _interpolate_linear_value(

        effective_frequency,

        lower,
        alpha_h1,

        upper,
        alpha_h2
    )


    alpha_v = _interpolate_linear_value(

        effective_frequency,

        lower,
        alpha_v1,

        upper,
        alpha_v2
    )


    return (

        (
            k_h,
            alpha_h,
            k_v,
            alpha_v
        ),

        effective_frequency
    )


# =========================================================
# RAIN ATTENUATION
# =========================================================

def rain_specific_attenuation_db_per_km(
    frequency_ghz,
    rain_rate_mm_per_h,
    path_elevation_deg=0.0,
    polarization_tilt_deg=45.0
):

    if rain_rate_mm_per_h <= 0.0:

        return 0.0


    (
        (
            k_h,
            alpha_h,
            k_v,
            alpha_v
        ),

        _
    ) = p838_coefficients(
        frequency_ghz
    )


    theta = math.radians(
        path_elevation_deg
    )


    tau = math.radians(
        polarization_tilt_deg
    )


    orientation_term = (

        math.cos(
            theta
        ) ** 2

        * math.cos(
            2.0
            * tau
        )
    )


    k = (

        k_h
        + k_v

        + (
            k_h
            - k_v
        )

        * orientation_term

    ) / 2.0


    alpha = (

        k_h
        * alpha_h

        + k_v
        * alpha_v

        + (
            k_h
            * alpha_h

            - k_v
            * alpha_v
        )

        * orientation_term

    ) / (
        2.0
        * k
    )


    return (

        k

        * (
            rain_rate_mm_per_h
            ** alpha
        )
    )


# =========================================================
# GASEOUS ATTENUATION
# =========================================================

def gaseous_specific_attenuation_db_per_km(
    frequency_ghz,
    temperature_c,
    relative_humidity_pct,
    mean_ground_elevation_m
):

    if not (
        0.0
        < frequency_ghz
        < 54.0
    ):

        raise ValueError(
            (
                "Simplified gas model "
                "requires 0 < f < 54 GHz"
            )
        )


    rho_surface = (
        water_vapor_density_g_m3(

            temperature_c,

            relative_humidity_pct
        )
    )


    rho_sea = (

        rho_surface

        * math.exp(

            mean_ground_elevation_m

            / 2000.0
        )
    )


    f = frequency_ghz


    # Oxygen.

    gamma_o = (

        (
            7.2

            / (
                f ** 2
                + 0.34
            )

            + 0.62

            / (
                (
                    54.0
                    - f
                ) ** 1.16

                + 0.83
            )
        )

        * f ** 2

        * 1e-3
    )


    # Water vapour.

    eta = (

        0.955

        + 0.006
        * rho_sea
    )


    gamma_w = (

        (
            0.046

            + 0.0019
            * rho_sea

            + (

                3.98
                * eta

                / (
                    (
                        f
                        - 22.235
                    ) ** 2

                    + 9.42
                    * eta ** 2
                )
            )

            * (
                1.0

                + (

                    (
                        f
                        - 22.0
                    )

                    / (
                        f
                        + 22.0
                    )

                ) ** 2
            )
        )

        * f ** 2

        * rho_sea

        * 1e-4
    )


    return (
        gamma_o
        + gamma_w
    )


# =========================================================
# FREE SPACE REFERENCE
# =========================================================

def free_space_path_loss_db(
    distance_m,
    frequency_mhz
):

    distance_km = (

        max(
            distance_m,
            1.0
        )

        / 1000.0
    )


    return (

        32.45

        + 20.0
        * math.log10(
            distance_km
        )

        + 20.0
        * math.log10(
            frequency_mhz
        )
    )


# =========================================================
# 3GPP UMa LOS PATH LOSS
# =========================================================

def uma_los_path_loss_db(
    distance_2d_m,
    h_bs_agl_m,
    h_ue_agl_m,
    frequency_mhz
):

    d2d = max(

        distance_2d_m,

        MIN_UMa_DISTANCE_M
    )


    height_difference = (
        h_bs_agl_m
        - h_ue_agl_m
    )


    d3d = math.sqrt(

        d2d ** 2

        + height_difference ** 2
    )


    fc_ghz = (
        frequency_mhz
        / 1000.0
    )


    effective_environment_height_m = (
        1.0
    )


    h_bs_prime = max(

        h_bs_agl_m
        - effective_environment_height_m,

        0.1
    )


    h_ue_prime = max(

        h_ue_agl_m
        - effective_environment_height_m,

        0.1
    )


    breakpoint_m = (

        4.0

        * h_bs_prime

        * h_ue_prime

        * (
            fc_ghz
            * 1e9
        )

        / SPEED_OF_LIGHT_M_S
    )


    if d2d <= breakpoint_m:

        path_loss_db = (

            28.0

            + 22.0
            * math.log10(
                d3d
            )

            + 20.0
            * math.log10(
                fc_ghz
            )
        )


    else:

        path_loss_db = (

            28.0

            + 40.0
            * math.log10(
                d3d
            )

            + 20.0
            * math.log10(
                fc_ghz
            )

            - 9.0

            * math.log10(

                breakpoint_m ** 2

                + height_difference ** 2
            )
        )


    return {

        "path_loss_db":
            path_loss_db,

        "distance_3d_m":
            d3d,

        "breakpoint_m":
            breakpoint_m,

        "within_nominal_distance_range":
            (
                10.0
                <= d2d
                <= 5000.0
            )
    }


# =========================================================
# 3GPP UMa NLOS PATH LOSS
# =========================================================

def uma_nlos_path_loss_db(
    distance_2d_m,
    h_bs_agl_m,
    h_ue_agl_m,
    frequency_mhz
):

    los = (
        uma_los_path_loss_db(

            distance_2d_m,

            h_bs_agl_m,

            h_ue_agl_m,

            frequency_mhz
        )
    )


    d3d = los[
        "distance_3d_m"
    ]


    fc_ghz = (
        frequency_mhz
        / 1000.0
    )


    nlos_prime_db = (

        13.54

        + 39.08
        * math.log10(
            d3d
        )

        + 20.0
        * math.log10(
            fc_ghz
        )

        - 0.6

        * (
            h_ue_agl_m
            - 1.5
        )
    )


    return {

        "path_loss_db":
            max(

                los[
                    "path_loss_db"
                ],

                nlos_prime_db
            ),

        "distance_3d_m":
            d3d,

        "breakpoint_m":
            los[
                "breakpoint_m"
            ],

        "los_path_loss_db":
            los[
                "path_loss_db"
            ],

        "nlos_prime_path_loss_db":
            nlos_prime_db,

        "within_nominal_distance_range":
            los[
                "within_nominal_distance_range"
            ]
    }


# =========================================================
# ANTENNA PATTERN
# =========================================================

def antenna_gain_toward_point_dbi(
    antenna_profile,
    antenna_azimuth_deg,
    mechanical_tilt_deg,
    electrical_tilt_deg,
    bearing_to_ue_deg,
    elevation_angle_to_ue_deg
):

    horizontal_offset_deg = (
        wrap_angle_180(

            bearing_to_ue_deg

            - antenna_azimuth_deg
        )
    )


    total_downtilt_deg = (

        mechanical_tilt_deg

        + electrical_tilt_deg
    )


    # Positive tilt means downward.
    #
    # Therefore a 6 degree down-tilt has a boresight
    # elevation of -6 degrees relative to the horizon.

    boresight_elevation_deg = (
        -total_downtilt_deg
    )


    vertical_offset_deg = (

        elevation_angle_to_ue_deg

        - boresight_elevation_deg
    )


    horizontal_3db = (
        antenna_profile[
            "horizontal_3db_beamwidth_deg"
        ]
    )


    vertical_3db = (
        antenna_profile[
            "vertical_3db_beamwidth_deg"
        ]
    )


    max_horizontal = (
        antenna_profile[
            "max_horizontal_attenuation_db"
        ]
    )


    max_vertical = (
        antenna_profile[
            "max_vertical_attenuation_db"
        ]
    )


    horizontal_attenuation_db = min(

        12.0

        * (
            horizontal_offset_deg
            / horizontal_3db
        ) ** 2,

        max_horizontal
    )


    vertical_attenuation_db = min(

        12.0

        * (
            vertical_offset_deg
            / vertical_3db
        ) ** 2,

        max_vertical
    )


    combined_cap_db = max(

        max_horizontal,

        max_vertical
    )


    combined_attenuation_db = min(

        horizontal_attenuation_db
        + vertical_attenuation_db,

        combined_cap_db
    )


    gain_dbi = (

        antenna_profile[
            "max_gain_dbi"
        ]

        - combined_attenuation_db
    )


    return {

        "gain_dbi":
            gain_dbi,

        "horizontal_offset_deg":
            horizontal_offset_deg,

        "vertical_offset_deg":
            vertical_offset_deg,

        "combined_attenuation_db":
            combined_attenuation_db,

        "total_downtilt_deg":
            total_downtilt_deg
    }


# =========================================================
# OFDM / RSRP HELPERS
# =========================================================

def default_subcarrier_spacing_khz(
    cell
):

    if (
        cell[
            "technology"
        ]
        == "4G"
    ):

        return 15.0


    if (
        cell[
            "band"
        ]
        == "n78"
    ):

        return 30.0


    return 15.0


def occupied_subcarriers(
    cell
):

    bandwidth_mhz = int(
        cell[
            "bandwidth_mhz"
        ]
    )


    if (
        cell[
            "technology"
        ]
        == "4G"

        and bandwidth_mhz
        in LTE_OCCUPIED_SUBCARRIERS
    ):

        return (
            LTE_OCCUPIED_SUBCARRIERS[
                bandwidth_mhz
            ]
        )


    if (
        cell[
            "band"
        ]
        == "n78"

        and bandwidth_mhz
        in NR_FR1_30KHZ_OCCUPIED_SUBCARRIERS
    ):

        return (
            NR_FR1_30KHZ_OCCUPIED_SUBCARRIERS[
                bandwidth_mhz
            ]
        )


    if (
        cell[
            "technology"
        ]
        == "5G"

        and bandwidth_mhz
        in NR_FR1_15KHZ_OCCUPIED_SUBCARRIERS
    ):

        return (
            NR_FR1_15KHZ_OCCUPIED_SUBCARRIERS[
                bandwidth_mhz
            ]
        )


    scs_hz = (

        default_subcarrier_spacing_khz(
            cell
        )

        * 1000.0
    )


    estimated = int(

        (
            bandwidth_mhz
            * 1e6
            * 0.90
        )

        / scs_hz
    )


    return max(
        estimated,
        12
    )


# =========================================================
# THERMAL NOISE
# =========================================================

def thermal_noise_per_re_dbm(
    cell,
    temperature_c,
    noise_figure_db=
        DEFAULT_UE_NOISE_FIGURE_DB
):

    temperature_k = max(

        temperature_c
        + 273.15,

        1.0
    )


    scs_hz = (

        default_subcarrier_spacing_khz(
            cell
        )

        * 1000.0
    )


    temperature_correction_db = (

        10.0

        * math.log10(

            temperature_k

            / REFERENCE_TEMPERATURE_K
        )
    )


    return (

        -174.0

        + temperature_correction_db

        + 10.0
        * math.log10(
            scs_hz
        )

        + noise_figure_db
    )


# =========================================================
# WEATHER VALIDATION
# =========================================================

def _validate_weather(
    weather
):

    required = (

        "timestamp",

        "temperature_c",

        "pressure_hpa",

        "relative_humidity_pct",

        "rain_rate_mm_per_h"
    )


    missing = [

        field

        for field
        in required

        if field
        not in weather
    ]


    if missing:

        raise ValueError(

            "Weather observation is missing: "

            + ", ".join(
                missing
            )
        )


# =========================================================
# FLATTEN RAN TOPOLOGY
# =========================================================

def flatten_cells(
    sites=None
):

    if sites is None:

        sites = (
            SYNTHETIC_SITES
        )


    cells = []


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
                antenna_system
            ) in sector[
                "antenna_systems"
            ].items():


                profile_name = (
                    antenna_system[
                        "profile"
                    ]
                )


                for cell in antenna_system[
                    "cells"
                ]:


                    if not cell.get(
                        "enabled",
                        True
                    ):

                        continue


                    cells.append({

                        "site_id":
                            site_id,

                        "site_code":
                            site[
                                "site_code"
                            ],

                        "sector_key":
                            sector_key,

                        "sector_id":
                            sector[
                                "sector_id"
                            ],

                        "site_latitude":
                            site[
                                "latitude"
                            ],

                        "site_longitude":
                            site[
                                "longitude"
                            ],

                        "site_ground_elevation_m":
                            site[
                                "ground_elevation_m"
                            ],

                        "antenna_height_agl_m":
                            site[
                                "antenna_height_agl_m"
                            ],

                        "antenna_id":
                            antenna_id,

                        "antenna_profile_name":
                            profile_name,

                        "antenna_azimuth_deg":
                            antenna_system[
                                "azimuth_deg"
                            ],

                        "mechanical_tilt_deg":
                            antenna_system[
                                "mechanical_tilt_deg"
                            ],

                        "electrical_tilt_deg":
                            antenna_system[
                                "electrical_tilt_deg"
                            ],

                        "cell":
                            deepcopy(
                                cell
                            )
                    })


    return cells


# =========================================================
# CALCULATE ONE BS -> UE LINK
# =========================================================

def calculate_link(
    flat_cell,
    ue_sample,
    weather,
    antenna_profiles=None
):

    if antenna_profiles is None:

        antenna_profiles = (
            ANTENNA_PROFILES
        )


    _validate_weather(
        weather
    )


    cell = flat_cell[
        "cell"
    ]


    # -----------------------------------------------------
    # DISTANCE / BEARING
    # -----------------------------------------------------

    distance_2d_m = (
        haversine_distance_m(

            flat_cell[
                "site_latitude"
            ],

            flat_cell[
                "site_longitude"
            ],

            ue_sample[
                "latitude"
            ],

            ue_sample[
                "longitude"
            ]
        )
    )


    bearing_deg = (
        initial_bearing_deg(

            flat_cell[
                "site_latitude"
            ],

            flat_cell[
                "site_longitude"
            ],

            ue_sample[
                "latitude"
            ],

            ue_sample[
                "longitude"
            ]
        )
    )


    # -----------------------------------------------------
    # HEIGHT GEOMETRY
    # -----------------------------------------------------

    bs_altitude_asl_m = (

        flat_cell[
            "site_ground_elevation_m"
        ]

        + flat_cell[
            "antenna_height_agl_m"
        ]
    )


    ue_altitude_asl_m = (

        ue_sample[
            "ground_elevation_m"
        ]

        + ue_sample[
            "ue_height_agl_m"
        ]
    )


    altitude_delta_m = (

        ue_altitude_asl_m

        - bs_altitude_asl_m
    )


    elevation_angle_deg = (

        math.degrees(

            math.atan2(

                altitude_delta_m,

                max(
                    distance_2d_m,
                    1.0
                )
            )
        )
    )


    # -----------------------------------------------------
    # ANTENNA GAIN TOWARD UE
    # -----------------------------------------------------

    antenna_profile = (

        antenna_profiles[
            flat_cell[
                "antenna_profile_name"
            ]
        ]
    )


    antenna_result = (
        antenna_gain_toward_point_dbi(

            antenna_profile,

            flat_cell[
                "antenna_azimuth_deg"
            ],

            flat_cell[
                "mechanical_tilt_deg"
            ],

            flat_cell[
                "electrical_tilt_deg"
            ],

            bearing_deg,

            elevation_angle_deg
        )
    )


    # -----------------------------------------------------
    # LOS / NLOS
    # -----------------------------------------------------

    propagation_condition = (

        ENVIRONMENT_TO_PROPAGATION_CONDITION.get(

            ue_sample[
                "environment"
            ],

            "NLOS"
        )
    )


    # -----------------------------------------------------
    # 3GPP PATH LOSS
    # -----------------------------------------------------

    if (
        propagation_condition
        == "LOS"
    ):

        path_loss_result = (
            uma_los_path_loss_db(

                distance_2d_m,

                flat_cell[
                    "antenna_height_agl_m"
                ],

                ue_sample[
                    "ue_height_agl_m"
                ],

                cell[
                    "downlink_center_frequency_mhz"
                ]
            )
        )


    else:

        path_loss_result = (
            uma_nlos_path_loss_db(

                distance_2d_m,

                flat_cell[
                    "antenna_height_agl_m"
                ],

                ue_sample[
                    "ue_height_agl_m"
                ],

                cell[
                    "downlink_center_frequency_mhz"
                ]
            )
        )


    path_distance_km = (

        path_loss_result[
            "distance_3d_m"
        ]

        / 1000.0
    )


    frequency_ghz = (

        cell[
            "downlink_center_frequency_mhz"
        ]

        / 1000.0
    )


    # -----------------------------------------------------
    # RAIN
    # -----------------------------------------------------

    rain_specific = (
        rain_specific_attenuation_db_per_km(

            frequency_ghz,

            weather[
                "rain_rate_mm_per_h"
            ],

            elevation_angle_deg,

            45.0
        )
    )


    rain_attenuation_db = (

        rain_specific

        * path_distance_km
    )


    # -----------------------------------------------------
    # ATMOSPHERIC GASES
    # -----------------------------------------------------

    mean_ground_elevation_m = (

        (
            flat_cell[
                "site_ground_elevation_m"
            ]

            + ue_sample[
                "ground_elevation_m"
            ]
        )

        / 2.0
    )


    gas_specific = (
        gaseous_specific_attenuation_db_per_km(

            frequency_ghz,

            weather[
                "temperature_c"
            ],

            weather[
                "relative_humidity_pct"
            ],

            mean_ground_elevation_m
        )
    )


    gas_attenuation_db = (

        gas_specific

        * path_distance_km
    )


    # -----------------------------------------------------
    # RECEIVED CARRIER POWER
    # -----------------------------------------------------

    received_carrier_power_dbm = (

        cell[
            "tx_power_dbm"
        ]

        + antenna_result[
            "gain_dbi"
        ]

        - path_loss_result[
            "path_loss_db"
        ]

        - rain_attenuation_db

        - gas_attenuation_db
    )


    # -----------------------------------------------------
    # RSRP PROXY
    # -----------------------------------------------------
    #
    # We do NOT simply call total carrier receive power RSRP.
    #
    # Carrier power is divided across the occupied OFDM
    # subcarriers.
    #
    # This remains an approximation because actual LTE/NR
    # RS power allocation can differ.
    # -----------------------------------------------------

    subcarriers = (
        occupied_subcarriers(
            cell
        )
    )


    rsrp_proxy_dbm = (

        received_carrier_power_dbm

        - 10.0

        * math.log10(
            subcarriers
        )
    )


    return {

        "sample_id":
            ue_sample[
                "sample_id"
            ],

        "area_id":
            ue_sample[
                "area_id"
            ],

        "area_name":
            ue_sample[
                "area_name"
            ],

        "representative_active_ues":
            ue_sample[
                "representative_active_ues"
            ],

        "environment":
            ue_sample[
                "environment"
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


        "site_id":
            flat_cell[
                "site_id"
            ],

        "sector_id":
            flat_cell[
                "sector_id"
            ],

        "antenna_id":
            flat_cell[
                "antenna_id"
            ],


        "distance_2d_m":
            round(
                distance_2d_m,
                1
            ),

        "distance_3d_m":
            round(

                path_loss_result[
                    "distance_3d_m"
                ],

                1
            ),


        "bearing_deg":
            round(
                bearing_deg,
                2
            ),

        "elevation_angle_deg":
            round(
                elevation_angle_deg,
                3
            ),


        "antenna_azimuth_deg":
            flat_cell[
                "antenna_azimuth_deg"
            ],

        "electrical_tilt_deg":
            flat_cell[
                "electrical_tilt_deg"
            ],

        "mechanical_tilt_deg":
            flat_cell[
                "mechanical_tilt_deg"
            ],


        "horizontal_offset_deg":
            round(

                antenna_result[
                    "horizontal_offset_deg"
                ],

                2
            ),

        "vertical_offset_deg":
            round(

                antenna_result[
                    "vertical_offset_deg"
                ],

                2
            ),

        "antenna_gain_dbi":
            round(

                antenna_result[
                    "gain_dbi"
                ],

                2
            ),


        "propagation_condition":
            propagation_condition,


        "path_loss_db":
            round(

                path_loss_result[
                    "path_loss_db"
                ],

                3
            ),


        "free_space_reference_db":
            round(

                free_space_path_loss_db(

                    path_loss_result[
                        "distance_3d_m"
                    ],

                    cell[
                        "downlink_center_frequency_mhz"
                    ]
                ),

                3
            ),


        "rain_specific_db_per_km":
            round(
                rain_specific,
                6
            ),

        "rain_attenuation_db":
            round(
                rain_attenuation_db,
                6
            ),


        "gas_specific_db_per_km":
            round(
                gas_specific,
                6
            ),

        "gas_attenuation_db":
            round(
                gas_attenuation_db,
                6
            ),


        "received_carrier_power_dbm":
            round(
                received_carrier_power_dbm,
                3
            ),

        "occupied_subcarriers":
            subcarriers,

        "rsrp_dbm":
            round(
                rsrp_proxy_dbm,
                3
            ),

        "rsrp_is_proxy":
            True,


        "within_uma_distance_range":
            path_loss_result[
                "within_nominal_distance_range"
            ]
    }


# =========================================================
# EVALUATE ALL LINKS
# =========================================================

def evaluate_all_links(
    weather,
    sites=None,
    observation_areas=None,
    antenna_profiles=None
):

    if sites is None:

        sites = (
            SYNTHETIC_SITES
        )


    if observation_areas is None:

        observation_areas = (
            OBSERVATION_AREAS
        )


    if antenna_profiles is None:

        antenna_profiles = (
            ANTENNA_PROFILES
        )


    _validate_weather(
        weather
    )


    flat_cells = (
        flatten_cells(
            sites
        )
    )


    ue_samples = (
        generate_ue_sample_points(
            observation_areas
        )
    )


    links = []


    for ue_sample in ue_samples:

        for flat_cell in flat_cells:

            links.append(
                calculate_link(

                    flat_cell,

                    ue_sample,

                    weather,

                    antenna_profiles
                )
            )


    return {

        "ue_samples":
            ue_samples,

        "links":
            links
    }


# =========================================================
# CARRIER GROUPING
# =========================================================

def _carrier_key(
    link
):

    return (

        link[
            "technology"
        ],

        link[
            "band"
        ],

        float(
            link[
                "frequency_mhz"
            ]
        )
    )


# =========================================================
# SERVING CELL + SINR
# =========================================================

def select_serving_links_and_sinr(
    links,
    weather,
    noise_figure_db=
        DEFAULT_UE_NOISE_FIGURE_DB
):

    _validate_weather(
        weather
    )


    grouped = defaultdict(
        list
    )


    # Group all cells using the same carrier for the
    # same representative UE point.

    for link in links:

        grouped[

            (
                link[
                    "sample_id"
                ],

                _carrier_key(
                    link
                )
            )

        ].append(
            link
        )


    serving_results = []


    for (
        (
            _,
            carrier_key
        ),

        candidates

    ) in grouped.items():


        # Strongest RSRP wins on this carrier layer.

        ordered = sorted(

            candidates,

            key=lambda item:
                item[
                    "rsrp_dbm"
                ],

            reverse=True
        )


        serving = deepcopy(
            ordered[
                0
            ]
        )


        interferers = ordered[
            1:
        ]


        # -------------------------------------------------
        # SIGNAL
        # -------------------------------------------------

        signal_mw = dbm_to_mw(
            serving[
                "rsrp_dbm"
            ]
        )


        # -------------------------------------------------
        # CO-CHANNEL INTERFERENCE
        # -------------------------------------------------

        interference_mw = sum(

            dbm_to_mw(
                item[
                    "rsrp_dbm"
                ]
            )

            for item
            in interferers
        )


        # -------------------------------------------------
        # THERMAL NOISE
        # -------------------------------------------------

        serving_cell = {

            "technology":
                serving[
                    "technology"
                ],

            "band":
                serving[
                    "band"
                ],

            "bandwidth_mhz":
                serving[
                    "bandwidth_mhz"
                ]
        }


        noise_dbm = (
            thermal_noise_per_re_dbm(

                serving_cell,

                weather[
                    "temperature_c"
                ],

                noise_figure_db
            )
        )


        noise_mw = dbm_to_mw(
            noise_dbm
        )


        # -------------------------------------------------
        # SINR
        # -------------------------------------------------

        sinr_linear = (

            signal_mw

            / (
                interference_mw
                + noise_mw
            )
        )


        sinr_db = (

            10.0

            * math.log10(
                sinr_linear
            )
        )


        # Shannon value is only a theoretical upper-bound
        # indicator, NOT an NR/LTE MCS implementation.

        shannon_efficiency = (

            math.log2(
                1.0
                + sinr_linear
            )
        )


        serving[
            "sinr_db"
        ] = round(
            sinr_db,
            3
        )


        serving[
            "noise_per_re_dbm"
        ] = round(
            noise_dbm,
            3
        )


        serving[
            "aggregate_interference_dbm"
        ] = round(

            mw_to_dbm(
                interference_mw
            ),

            3
        )


        serving[
            "interferer_count"
        ] = len(
            interferers
        )


        serving[
            "strongest_interferers"
        ] = [

            {
                "cell_id":
                    item[
                        "cell_id"
                    ],

                "site_id":
                    item[
                        "site_id"
                    ],

                "rsrp_dbm":
                    item[
                        "rsrp_dbm"
                    ]
            }

            for item
            in interferers[
                :5
            ]
        ]


        serving[
            "shannon_efficiency_bps_hz"
        ] = round(
            shannon_efficiency,
            3
        )


        serving[
            "carrier_key"
        ] = {

            "technology":
                carrier_key[
                    0
                ],

            "band":
                carrier_key[
                    1
                ],

            "frequency_mhz":
                carrier_key[
                    2
                ]
        }


        serving_results.append(
            serving
        )


    return serving_results


# =========================================================
# CELL RF SUMMARY
# =========================================================

def build_cell_rf_summary(
    serving_results
):

    per_cell = defaultdict(

        lambda: {

            "served_samples":
                0,

            "representative_ue_weight":
                0,

            "weighted_rsrp_sum":
                0.0,

            "weighted_sinr_sum":
                0.0,

            "weight_sum":
                0,

            "areas":
                set()
        }
    )


    for result in serving_results:

        ue_weight = int(

            result[
                "representative_active_ues"
            ]
        )


        record = (

            per_cell[
                result[
                    "cell_id"
                ]
            ]
        )


        record[
            "served_samples"
        ] += 1


        record[
            "representative_ue_weight"
        ] += ue_weight


        record[
            "weighted_rsrp_sum"
        ] += (

            result[
                "rsrp_dbm"
            ]

            * ue_weight
        )


        record[
            "weighted_sinr_sum"
        ] += (

            result[
                "sinr_db"
            ]

            * ue_weight
        )


        record[
            "weight_sum"
        ] += ue_weight


        record[
            "areas"
        ].add(
            result[
                "area_id"
            ]
        )


    summary = []


    for (
        cell_id,
        record
    ) in sorted(
        per_cell.items()
    ):

        weight_sum = max(

            record[
                "weight_sum"
            ],

            1
        )


        summary.append({

            "cell_id":
                cell_id,

            "served_samples":
                record[
                    "served_samples"
                ],

            "served_areas":
                sorted(
                    record[
                        "areas"
                    ]
                ),

            "representative_ue_weight":
                record[
                    "representative_ue_weight"
                ],

            "weighted_mean_rsrp_dbm":
                round(

                    record[
                        "weighted_rsrp_sum"
                    ]

                    / weight_sum,

                    2
                ),

            "weighted_mean_sinr_db":
                round(

                    record[
                        "weighted_sinr_sum"
                    ]

                    / weight_sum,

                    2
                )
        })


    return summary


# =========================================================
# COMPLETE RF SNAPSHOT
# =========================================================

def evaluate_rf_snapshot(
    weather,
    sites=None,
    observation_areas=None,
    antenna_profiles=None,
    noise_figure_db=
        DEFAULT_UE_NOISE_FIGURE_DB
):

    evaluation = (
        evaluate_all_links(

            weather,

            sites,

            observation_areas,

            antenna_profiles
        )
    )


    serving_results = (
        select_serving_links_and_sinr(

            evaluation[
                "links"
            ],

            weather,

            noise_figure_db
        )
    )


    cell_summary = (
        build_cell_rf_summary(
            serving_results
        )
    )


    out_of_range_count = sum(

        1

        for link
        in evaluation[
            "links"
        ]

        if not link[
            "within_uma_distance_range"
        ]
    )


    return {

        "weather":
            deepcopy(
                weather
            ),


        "model": {

            "geography":
                (
                    "real locality anchors + "
                    "synthetic UE samples"
                ),

            "path_loss":
                "3GPP UMa LOS/NLOS",

            "antenna_pattern":
                (
                    "3GPP-style parabolic "
                    "sector pattern scaled "
                    "to scenario gain"
                ),

            "rain":
                "ITU-R P.838",

            "gaseous_attenuation":
                (
                    "ITU-R P.2001 compact "
                    "sub-54-GHz terrestrial "
                    "formula"
                ),

            "rsrp":
                (
                    "equal-power-per-occupied-"
                    "subcarrier learning-lab "
                    "proxy"
                ),

            "sinr":
                (
                    "same-carrier linear "
                    "interference + thermal noise"
                ),

            "pressure_usage":
                (
                    "recorded and preserved, "
                    "but not used by the compact "
                    "P.2001 gas equation"
                )
        },


        "ue_sample_count":
            len(
                evaluation[
                    "ue_samples"
                ]
            ),


        "radio_link_count":
            len(
                evaluation[
                    "links"
                ]
            ),


        "serving_link_count":
            len(
                serving_results
            ),


        "out_of_nominal_uma_range_links":
            out_of_range_count,


        "ue_samples":
            evaluation[
                "ue_samples"
            ],


        "serving_links":
            serving_results,


        "cell_summary":
            cell_summary
    }