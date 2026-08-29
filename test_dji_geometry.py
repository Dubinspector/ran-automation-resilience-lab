from app.jesenice_scenario import (
    SYNTHETIC_SITES,
    OBSERVATION_AREAS,
)

from app.rf_model import (
    generate_ue_sample_points,
    initial_bearing_deg,
    wrap_angle_180,
)


SITE_ID = "SITE-DOLNI-JIRCANY-01"
AREA_ID = "UE-DOLNI-JIRCANY"


site = SYNTHETIC_SITES[
    SITE_ID
]


samples = generate_ue_sample_points(
    OBSERVATION_AREAS
)


dji_samples = [

    sample

    for sample
    in samples

    if sample[
        "area_id"
    ]
    == AREA_ID
]


print()
print("=" * 100)
print("DOLNI JIRCANY - SECTOR GEOMETRY DIAGNOSTIC")
print("=" * 100)


print()

print(
    "Site:",
    SITE_ID
)

print(
    "Latitude:",
    site[
        "latitude"
    ]
)

print(
    "Longitude:",
    site[
        "longitude"
    ]
)


print()

print(
    "Sector azimuths:"
)


for (
    sector_key,
    sector
) in site[
    "sectors"
].items():

    print(

        f"  Sector {sector_key}:",
        sector[
            "azimuth_deg"
        ],
        "deg"
    )


# =========================================================
# UE -> SECTOR GEOMETRY
# =========================================================

for sample in sorted(

    dji_samples,

    key=lambda item:
        item[
            "sample_id"
        ]
):


    bearing = (
        initial_bearing_deg(

            site[
                "latitude"
            ],

            site[
                "longitude"
            ],

            sample[
                "latitude"
            ],

            sample[
                "longitude"
            ]
        )
    )


    print()

    print("-" * 100)

    print(
        sample[
            "sample_id"
        ]
    )

    print(
        "Distance from locality centre [m]:",
        sample[
            "sample_radius_from_area_center_m"
        ]
    )

    print(
        "Bearing from site [deg]:",
        round(
            bearing,
            3
        )
    )


    offsets = []


    for (
        sector_key,
        sector
    ) in site[
        "sectors"
    ].items():


        offset = (
            wrap_angle_180(

                bearing

                - sector[
                    "azimuth_deg"
                ]
            )
        )


        offsets.append(

            (
                abs(
                    offset
                ),

                sector_key,

                offset
            )
        )


        print(

            f"  Sector {sector_key} "

            f"azimuth "
            f"{sector['azimuth_deg']:>6.1f}°"

            f" -> offset "

            f"{offset:>8.3f}°"
        )


    offsets.sort()


    closest = offsets[
        0
    ]

    second = offsets[
        1
    ]


    print()

    print(
        "Closest sector:",
        closest[
            1
        ],

        "| offset:",
        round(
            closest[
                2
            ],
            3
        ),
        "deg"
    )


    print(
        "Second closest:",
        second[
            1
        ],

        "| offset:",
        round(
            second[
                2
            ],
            3
        ),
        "deg"
    )


    separation = (

        second[
            0
        ]

        - closest[
            0
        ]
    )


    print(
        "Angular preference margin [deg]:",
        round(
            separation,
            3
        )
    )


    if separation < 1.0:

        print(
            "DIAGNOSIS: UE IS EFFECTIVELY ON A SECTOR BOUNDARY"
        )

    elif separation < 10.0:

        print(
            "DIAGNOSIS: UE IS CLOSE TO A SECTOR BOUNDARY"
        )

    else:

        print(
            "DIAGNOSIS: UE HAS A CLEAR PRIMARY SECTOR"
        )


print()
print("=" * 100)
print("INTERPRETATION")
print("=" * 100)

print(
    """
If multiple samples show almost equal absolute angular
offset to two sectors, the low SINR is being driven by
the synthetic geometry.

In that case we should NOT:

- relax SINR thresholds,
- artificially increase TX power,
- add a fixed interference correction.

Instead we should remove the pathological symmetry from
the synthetic topology / UE sampling and then rerun the
RF calculation.
"""
)