from collections import defaultdict

from app.traffic_model import (
    build_radio_service_snapshot,
)


# =========================================================
# SAME BASELINE WEATHER
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
# BUILD RADIO SERVICE SNAPSHOT
# =========================================================

snapshot = build_radio_service_snapshot(
    WEATHER_OBSERVATION
)


# =========================================================
# DOLNI JIRCANY ONLY
# =========================================================

dolni_jircany = [

    link

    for link
    in snapshot[
        "serving_by_layer"
    ]

    if link[
        "area_id"
    ]
    == "UE-DOLNI-JIRCANY"
]


by_sample = defaultdict(
    list
)


for link in dolni_jircany:

    by_sample[
        link[
            "sample_id"
        ]
    ].append(
        link
    )


print()
print("=" * 100)
print("DOLNI JIRCANY - RADIO LAYER DIAGNOSTIC")
print("=" * 100)

print()

print(
    "All RF links:",
    snapshot[
        "all_link_count"
    ]
)

print(
    "Valid RF links:",
    snapshot[
        "valid_link_count"
    ]
)

print(
    "Excluded out-of-range links:",
    snapshot[
        "excluded_out_of_model_range_link_count"
    ]
)


# =========================================================
# PRINT EVERY LAYER FOR EVERY SAMPLE
# =========================================================

for sample_id in sorted(
    by_sample
):

    print()
    print("-" * 100)

    print(
        sample_id
    )

    print("-" * 100)


    links = sorted(

        by_sample[
            sample_id
        ],

        key=lambda item:
            item[
                "band"
            ]
    )


    for link in links:

        serviceability = (
            link[
                "serviceability"
            ][
                "class"
            ]
        )


        print()

        print(
            "Band:",
            link[
                "band"
            ]
        )

        print(
            "  Best cell:",
            link[
                "cell_id"
            ]
        )

        print(
            "  Site:",
            link[
                "site_id"
            ]
        )

        print(
            "  Sector:",
            link[
                "sector_id"
            ]
        )

        print(
            "  Frequency [MHz]:",
            link[
                "frequency_mhz"
            ]
        )

        print(
            "  Bandwidth [MHz]:",
            link[
                "bandwidth_mhz"
            ]
        )

        print(
            "  RSRP [dBm]:",
            link[
                "rsrp_dbm"
            ]
        )

        print(
            "  SINR [dB]:",
            link[
                "sinr_db"
            ]
        )

        print(
            "  Serviceability:",
            serviceability
        )

        print(
            "  Capacity score [Mbps]:",
            link[
                "capacity_score_mbps"
            ]
        )

        print(
            "  Distance [m]:",
            link[
                "distance_2d_m"
            ]
        )

        print(
            "  Antenna gain [dBi]:",
            link[
                "antenna_gain_dbi"
            ]
        )

        print(
            "  Path loss [dB]:",
            link[
                "path_loss_db"
            ]
        )

        print(
            "  Aggregate interference [dBm]:",
            link[
                "aggregate_interference_dbm"
            ]
        )

        print(
            "  Strongest interferers:"
        )


        for interferer in link[
            "strongest_interferers"
        ][
            :3
        ]:

            print(

                "    ",

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
# SUMMARY
# =========================================================

print()
print("=" * 100)
print("WHAT WE ARE LOOKING FOR")
print("=" * 100)

print(
    """
For every Dolni Jircany UE sample we want to answer:

1. Is n78 DEGRADED because of weak RSRP,
   poor SINR, or both?

2. Is n28 HEALTHY?

3. Is LTE B3 HEALTHY?

4. If no HEALTHY alternative exists, then using
   DEGRADED n78 is consistent with the current
   steering policy.

5. If a HEALTHY n28 or B3 exists but n78 is still
   selected, then we have a logic bug.

Do not change thresholds or antenna parameters yet.

First diagnose the actual RF outputs.
"""
)