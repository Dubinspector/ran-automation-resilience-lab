import json

from app.rf_model import evaluate_rf_snapshot


# =========================================================
# RECORDED WEATHER OBSERVATION
# =========================================================
#
# Nearby Osnice weather station.
#
# Timestamp:
# 2026-08-28 00:40 CEST
#
# Recorded values:
#
# Temperature:
# 20.5 C
#
# Relative humidity:
# 58.9 %
#
# Pressure:
# 1014.1 hPa
#
# Daily precipitation:
# 0.0 mm
#
# For this dry snapshot we use:
# rain_rate_mm_per_h = 0.0
#
# Pressure is preserved in the observation even though
# the current compact gas model does not yet use it.
# =========================================================

WEATHER_OBSERVATION = {

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
# RUN RF MODEL
# =========================================================

snapshot = evaluate_rf_snapshot(
    WEATHER_OBSERVATION
)


# =========================================================
# BASIC MODEL INFORMATION
# =========================================================

print()
print("=" * 80)
print("RF MODEL BASELINE TEST")
print("=" * 80)

print()

print(
    "Weather timestamp:",
    snapshot["weather"]["timestamp"]
)

print(
    "Temperature [C]:",
    snapshot["weather"]["temperature_c"]
)

print(
    "Pressure [hPa]:",
    snapshot["weather"]["pressure_hpa"]
)

print(
    "Relative humidity [%]:",
    snapshot["weather"]["relative_humidity_pct"]
)

print(
    "Rain rate [mm/h]:",
    snapshot["weather"]["rain_rate_mm_per_h"]
)


print()

print(
    "UE samples:",
    snapshot["ue_sample_count"]
)

print(
    "Radio links:",
    snapshot["radio_link_count"]
)

print(
    "Serving links:",
    snapshot["serving_link_count"]
)

print(
    "Links outside nominal UMa range:",
    snapshot["out_of_nominal_uma_range_links"]
)


# =========================================================
# ONE JESENICE N78 SERVING EXAMPLE
# =========================================================

jesenice_n78 = [

    result

    for result
    in snapshot["serving_links"]

    if (
        result["area_id"]
        == "UE-JESENICE"

        and result["band"]
        == "n78"
    )
]


print()
print("=" * 80)
print("JESENICE - N78 SERVING LINK EXAMPLE")
print("=" * 80)


if not jesenice_n78:

    print(
        "No Jesenice n78 serving link found."
    )

else:

    # Pick the first deterministic synthetic UE point
    # around the Jesenice locality.

    example = sorted(

        jesenice_n78,

        key=lambda item:
            item["sample_id"]

    )[0]


    fields = {

        "UE sample":
            example["sample_id"],

        "Serving cell":
            example["cell_id"],

        "Site":
            example["site_id"],

        "Sector":
            example["sector_id"],

        "Antenna":
            example["antenna_id"],


        "Frequency [MHz]":
            example["frequency_mhz"],

        "Bandwidth [MHz]":
            example["bandwidth_mhz"],

        "TX power [dBm]":
            example["tx_power_dbm"],


        "Distance 2D [m]":
            example["distance_2d_m"],

        "Distance 3D [m]":
            example["distance_3d_m"],

        "Bearing [deg]":
            example["bearing_deg"],

        "Elevation angle [deg]":
            example["elevation_angle_deg"],


        "Sector azimuth [deg]":
            example["antenna_azimuth_deg"],

        "Electrical tilt [deg]":
            example["electrical_tilt_deg"],

        "Horizontal offset [deg]":
            example["horizontal_offset_deg"],

        "Vertical offset [deg]":
            example["vertical_offset_deg"],

        "Antenna gain toward UE [dBi]":
            example["antenna_gain_dbi"],


        "Propagation":
            example["propagation_condition"],

        "Free-space reference [dB]":
            example["free_space_reference_db"],

        "3GPP path loss [dB]":
            example["path_loss_db"],


        "Rain specific loss [dB/km]":
            example["rain_specific_db_per_km"],

        "Rain link loss [dB]":
            example["rain_attenuation_db"],

        "Gas specific loss [dB/km]":
            example["gas_specific_db_per_km"],

        "Gas link loss [dB]":
            example["gas_attenuation_db"],


        "Received carrier power [dBm]":
            example["received_carrier_power_dbm"],

        "RSRP proxy [dBm]":
            example["rsrp_dbm"],

        "Interference [dBm]":
            example["aggregate_interference_dbm"],

        "Noise per RE [dBm]":
            example["noise_per_re_dbm"],

        "SINR [dB]":
            example["sinr_db"],

        "Interferer count":
            example["interferer_count"]
    }


    for name, value in fields.items():

        print(
            f"{name:<38} {value}"
        )


    print()

    print(
        "Strongest interferers:"
    )


    for interferer in example[
        "strongest_interferers"
    ]:

        print(

            "  ",

            interferer[
                "cell_id"
            ],

            "|",

            interferer[
                "site_id"
            ],

            "| RSRP:",

            interferer[
                "rsrp_dbm"
            ],

            "dBm"
        )


# =========================================================
# CELL SUMMARY
# =========================================================

print()
print("=" * 80)
print("SERVING CELL RF SUMMARY")
print("=" * 80)


for cell in snapshot[
    "cell_summary"
]:

    print()

    print(
        cell["cell_id"]
    )

    print(
        "  Served samples:",
        cell["served_samples"]
    )

    print(
        "  Representative UE weight:",
        cell["representative_ue_weight"]
    )

    print(
        "  Mean RSRP [dBm]:",
        cell["weighted_mean_rsrp_dbm"]
    )

    print(
        "  Mean SINR [dB]:",
        cell["weighted_mean_sinr_db"]
    )

    print(
        "  Areas:",
        ", ".join(
            cell["served_areas"]
        )
    )


# =========================================================
# GLOBAL RANGE CHECKS
# =========================================================

serving_links = snapshot[
    "serving_links"
]


rsrp_values = [

    item["rsrp_dbm"]

    for item
    in serving_links
]


sinr_values = [

    item["sinr_db"]

    for item
    in serving_links
]


rain_losses = [

    item["rain_attenuation_db"]

    for item
    in serving_links
]


gas_losses = [

    item["gas_attenuation_db"]

    for item
    in serving_links
]


print()
print("=" * 80)
print("GLOBAL SANITY CHECK")
print("=" * 80)

print()

print(
    "Minimum serving RSRP [dBm]:",
    round(
        min(rsrp_values),
        2
    )
)

print(
    "Maximum serving RSRP [dBm]:",
    round(
        max(rsrp_values),
        2
    )
)


print(
    "Minimum SINR [dB]:",
    round(
        min(sinr_values),
        2
    )
)

print(
    "Maximum SINR [dB]:",
    round(
        max(sinr_values),
        2
    )
)


print(
    "Maximum rain loss [dB]:",
    round(
        max(rain_losses),
        6
    )
)

print(
    "Maximum gaseous loss [dB]:",
    round(
        max(gas_losses),
        6
    )
)


print()
print("=" * 80)
print("MODEL NOTES")
print("=" * 80)

print(
    """
Do not judge the model only by PASS / FAIL yet.

We are checking whether the physical quantities
have plausible orders of magnitude.

In particular:

- RSRP should vary with geometry, frequency,
  antenna direction and propagation condition.

- SINR should react to co-channel interference.

- Rain attenuation should be essentially zero
  for this recorded dry observation.

- Gas attenuation at sub-6 GHz over these local
  distances should be small.

- A 12 degree tilt or high TX power is NOT
  automatically bad.

Only after this baseline looks sensible will
the RAN automation layer compare before/after
RF snapshots and decide whether a candidate
configuration is acceptable.
"""
)