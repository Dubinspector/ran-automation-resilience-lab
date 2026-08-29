from app.traffic_model import build_traffic_snapshot


# =========================================================
# SAME RECORDED WEATHER SNAPSHOT AS RF BASELINE TEST
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
# BUILD TRAFFIC SNAPSHOT
# =========================================================

snapshot = build_traffic_snapshot(
    WEATHER_OBSERVATION
)


# =========================================================
# GLOBAL POPULATION / TRAFFIC MODEL
# =========================================================

print()
print("=" * 90)
print("TRAFFIC MODEL BASELINE TEST")
print("=" * 90)

population = snapshot[
    "population_model"
]

service = snapshot[
    "service"
]

radio_range = snapshot[
    "radio_model_range"
]


print()

print(
    "Weather timestamp:",
    snapshot[
        "weather_timestamp"
    ]
)

print(
    "Population estimate:",
    population[
        "total_population_estimate"
    ]
)

print(
    "Human T-Mobile SIM proxy:",
    population[
        "total_human_tm_sim_pool_estimate"
    ]
)

print(
    "Activity profile:",
    population[
        "activity_profile"
    ][
        "name"
    ]
)

print(
    "Active fraction:",
    population[
        "activity_profile"
    ][
        "active_fraction"
    ]
)

print(
    "Average demand per active UE [Mbps]:",
    population[
        "activity_profile"
    ][
        "avg_active_ue_demand_mbps"
    ]
)

print(
    "Total active UEs:",
    population[
        "total_active_ues"
    ]
)


# =========================================================
# MODEL-RANGE CHECK
# =========================================================

print()
print("=" * 90)
print("RF MODEL RANGE")
print("=" * 90)

print()

print(
    "All calculated links:",
    radio_range[
        "all_links"
    ]
)

print(
    "Valid links used by service model:",
    radio_range[
        "valid_links"
    ]
)

print(
    "Excluded out-of-range links:",
    radio_range[
        "excluded_out_of_model_range_links"
    ]
)


# =========================================================
# AREA DEMAND
# =========================================================

print()
print("=" * 90)
print("AREA DEMAND")
print("=" * 90)


for (
    area_id,
    area
) in sorted(
    snapshot[
        "areas"
    ].items()
):

    print()

    print(
        area_id
    )

    print(
        "  Population estimate:",
        area[
            "population_estimate"
        ]
    )

    print(
        "  Human T-Mobile SIM proxy:",
        area[
            "human_tm_sim_pool_estimate"
        ]
    )

    print(
        "  Active UEs:",
        area[
            "active_ues"
        ]
    )

    print(
        "  Avg traffic / active UE [Mbps]:",
        area[
            "avg_active_ue_demand_mbps"
        ]
    )


# =========================================================
# SERVICEABILITY
# =========================================================

print()
print("=" * 90)
print("SERVICEABILITY")
print("=" * 90)

print()

print(
    "Requested active UEs:",
    service[
        "requested_active_ues"
    ]
)

print(
    "Served active UEs:",
    service[
        "served_active_ues"
    ]
)

print(
    "Unserved active UEs:",
    service[
        "unserved_active_ues"
    ]
)

print(
    "Served ratio [%]:",
    service[
        "served_ratio_pct"
    ]
)


# =========================================================
# UNSERVED SAMPLES
# =========================================================

unserved_assignments = [

    item

    for item
    in snapshot[
        "assignments"
    ]

    if item[
        "status"
    ]
    == "UNSERVED"
]


print()
print("=" * 90)
print("UNSERVED UE SAMPLES")
print("=" * 90)


if not unserved_assignments:

    print()
    print(
        "No unserved UE samples."
    )

else:

    for item in unserved_assignments:

        print()

        print(
            item[
                "sample_id"
            ]
        )

        print(
            "  Area:",
            item[
                "area_id"
            ]
        )

        print(
            "  Active UEs affected:",
            item[
                "active_ues"
            ]
        )

        print(
            "  Available radio layers:"
        )


        for layer in item[
            "available_layers"
        ]:

            print(
                "   ",
                layer[
                    "band"
                ],
                "|",
                layer[
                    "cell_id"
                ],
                "| RSRP:",
                layer[
                    "rsrp_dbm"
                ],
                "dBm",
                "| SINR:",
                layer[
                    "sinr_db"
                ],
                "dB",
                "|",
                layer[
                    "serviceability"
                ]
            )


# =========================================================
# ACTIVE CELLS
# =========================================================

print()
print("=" * 90)
print("ACTIVE SERVING CELLS")
print("=" * 90)


for cell in sorted(

    snapshot[
        "cells"
    ],

    key=lambda item: (
        item[
            "site_id"
        ],
        item[
            "cell_id"
        ]
    )
):

    print()

    print(
        cell[
            "cell_id"
        ]
    )

    print(
        "  Site:",
        cell[
            "site_id"
        ]
    )

    print(
        "  Sector:",
        cell[
            "sector_id"
        ]
    )

    print(
        "  Technology / band:",
        cell[
            "technology"
        ],
        "/",
        cell[
            "band"
        ]
    )

    print(
        "  Bandwidth [MHz]:",
        cell[
            "bandwidth_mhz"
        ]
    )

    print(
        "  Active users:",
        cell[
            "active_users"
        ]
    )

    print(
        "  Traffic [Mbps]:",
        cell[
            "traffic_mbps"
        ]
    )

    print(
        "  Mean RSRP [dBm]:",
        cell[
            "weighted_mean_rsrp_dbm"
        ]
    )

    print(
        "  Mean SINR [dB]:",
        cell[
            "weighted_mean_sinr_db"
        ]
    )

    print(
        "  Estimated capacity [Mbps]:",
        cell[
            "estimated_capacity_mbps"
        ]
    )

    print(
        "  PRB utilization [%]:",
        cell[
            "prb_utilization_pct"
        ]
    )

    print(
        "  Serviceability UE mix:",
        cell[
            "serviceability_ue_mix"
        ]
    )


# =========================================================
# TOP LOADED CELLS
# =========================================================

top_loaded = sorted(

    snapshot[
        "cells"
    ],

    key=lambda item:
        item[
            "prb_utilization_pct"
        ],

    reverse=True
)


print()
print("=" * 90)
print("TOP 10 CELLS BY PRB UTILIZATION")
print("=" * 90)


for (
    index,
    cell
) in enumerate(
    top_loaded[
        :10
    ],
    start=1
):

    print(

        f"{index:>2}.",

        cell[
            "cell_id"
        ],

        "| PRB:",
        cell[
            "prb_utilization_pct"
        ],

        "%",

        "| UEs:",
        cell[
            "active_users"
        ],

        "| Traffic:",
        cell[
            "traffic_mbps"
        ],

        "Mbps",

        "| Capacity:",
        cell[
            "estimated_capacity_mbps"
        ],

        "Mbps",

        "| SINR:",
        cell[
            "weighted_mean_sinr_db"
        ],

        "dB"
    )


# =========================================================
# TOTALS CHECK
# =========================================================

users_on_cells = sum(

    cell[
        "active_users"
    ]

    for cell
    in snapshot[
        "cells"
    ]
)


print()
print("=" * 90)
print("CONSISTENCY CHECK")
print("=" * 90)

print()

print(
    "Requested active UEs:",
    service[
        "requested_active_ues"
    ]
)

print(
    "Users assigned to serving cells:",
    users_on_cells
)

print(
    "Unserved active UEs:",
    service[
        "unserved_active_ues"
    ]
)

print(
    "Assigned + unserved:",
    (
        users_on_cells
        + service[
            "unserved_active_ues"
        ]
    )
)


if (
    users_on_cells
    + service[
        "unserved_active_ues"
    ]
    ==
    service[
        "requested_active_ues"
    ]
):

    print(
        "Accounting check: PASS"
    )

else:

    print(
        "Accounting check: FAIL"
    )


print()
print("=" * 90)
print("EXPECTED ORDER OF MAGNITUDE")
print("=" * 90)

print(
    """
For the 00:40 NIGHT profile we expect roughly:

Population model:
~20,441 residents

Human T-Mobile subscription proxy:
~10,956 subscriptions

Active traffic UEs:
~274

This does NOT mean only 274 phones exist.

It means the current learning-lab traffic profile
assumes roughly 2.5% of the estimated human SIM pool is
actively carrying traffic during this snapshot.

The important checks are:

1. Assigned users + unserved users must equal
   requested active users.

2. A weak best-detected cell must not automatically
   count as usable service.

3. Links outside the configured RF model range must be
   excluded from serving/interference calculations.

4. PRB utilization must arise from traffic demand
   relative to estimated capacity, not from a manually
   injected KPI value.
"""
)