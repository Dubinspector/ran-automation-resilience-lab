import math

from collections import defaultdict
from copy import deepcopy
from datetime import datetime

from app.rf_model import (
    clamp,
    evaluate_all_links,
    select_serving_links_and_sinr,
)


# =========================================================
# POPULATION REFERENCE
# =========================================================
#
# Municipal population:
# official population baseline at 2025-01-01.
#
# Jesenice municipal-part proportions:
# 2021 census.
#
# These demographic inputs are used to scale synthetic
# traffic demand. They are NOT mobile-network measurements.
# =========================================================

POPULATION_REFERENCE = {

    "reference_date":
        "2025-01-01",

    "municipalities": {

        "JESENICE":
            10460,

        "VESTEC":
            3195,

        "PRUHONICE":
            2846,

        "PSARY":
            4254,

        "HERINK":
            1167
    },


    "jesenice_parts_2021_census": {

        "JESENICE":
            6112,

        "HORNI_JIRCANY":
            926,

        "OSNICE":
            1920,

        "ZDIMERICE":
            1687
    },


    "psary_parts_2021_census": {

        "PSARY":
            1493,

        "DOLNI_JIRCANY":
            2796
    }
}


# =========================================================
# OBSERVATION-AREA POPULATION ESTIMATES
# =========================================================

JESENICE_2025_AREA_ESTIMATES = {

    # Jesenice + temporarily HornĂ­ JirÄŤany
    "UE-JESENICE":
        6915,

    "UE-ZDIMERICE":
        1658,

    "UE-OSNICE":
        1510,

    "UE-KOCANDA":
        377
}


# =========================================================
# DOLNI JIRCANY ESTIMATE
# =========================================================

DOLNI_JIRCANY_2025_ESTIMATE = round(

    POPULATION_REFERENCE[
        "municipalities"
    ][
        "PSARY"
    ]

    * POPULATION_REFERENCE[
        "psary_parts_2021_census"
    ][
        "DOLNI_JIRCANY"
    ]

    / sum(

        POPULATION_REFERENCE[
            "psary_parts_2021_census"
        ].values()
    )
)


AREA_POPULATION_ESTIMATES = {

    **JESENICE_2025_AREA_ESTIMATES,


    "UE-VESTEC":
        POPULATION_REFERENCE[
            "municipalities"
        ][
            "VESTEC"
        ],


    "UE-PRUHONICE":
        POPULATION_REFERENCE[
            "municipalities"
        ][
            "PRUHONICE"
        ],


    "UE-HERINK":
        POPULATION_REFERENCE[
            "municipalities"
        ][
            "HERINK"
        ],


    "UE-DOLNI-JIRCANY":
        DOLNI_JIRCANY_2025_ESTIMATE
}


# =========================================================
# HUMAN T-MOBILE SIM POOL
# =========================================================

TMOBILE_HUMAN_SIM_PER_RESIDENT_PROXY = (
    0.536
)


# =========================================================
# TIME-OF-DAY ACTIVITY MODEL
# =========================================================

ACTIVITY_PROFILES = (

    {
        "name":
            "NIGHT",

        "start_hour":
            0,

        "end_hour":
            5,

        "active_fraction":
            0.025,

        "avg_active_ue_demand_mbps":
            0.60
    },


    {
        "name":
            "EARLY_MORNING",

        "start_hour":
            5,

        "end_hour":
            7,

        "active_fraction":
            0.055,

        "avg_active_ue_demand_mbps":
            0.75
    },


    {
        "name":
            "MORNING_COMMUTE",

        "start_hour":
            7,

        "end_hour":
            9,

        "active_fraction":
            0.115,

        "avg_active_ue_demand_mbps":
            1.10
    },


    {
        "name":
            "DAYTIME",

        "start_hour":
            9,

        "end_hour":
            16,

        "active_fraction":
            0.090,

        "avg_active_ue_demand_mbps":
            1.00
    },


    {
        "name":
            "EVENING_BUSY_HOUR",

        "start_hour":
            16,

        "end_hour":
            20,

        "active_fraction":
            0.160,

        "avg_active_ue_demand_mbps":
            1.40
    },


    {
        "name":
            "EVENING",

        "start_hour":
            20,

        "end_hour":
            23,

        "active_fraction":
            0.120,

        "avg_active_ue_demand_mbps":
            1.20
    },


    {
        "name":
            "LATE_EVENING",

        "start_hour":
            23,

        "end_hour":
            24,

        "active_fraction":
            0.050,

        "avg_active_ue_demand_mbps":
            0.80
    }
)


# =========================================================
# SERVICEABILITY POLICY
# =========================================================
#
# These are operational lab guardrails.
#
# RF physics calculates:
#
# RSRP
# SINR
#
# This policy maps those outputs into:
#
# HEALTHY
# DEGRADED
# UNSERVICEABLE
# =========================================================

SERVICEABILITY_POLICY = {

    "minimum_rsrp_dbm":
        -118.0,

    "minimum_sinr_db":
        -5.0,

    "healthy_rsrp_dbm":
        -105.0,

    "healthy_sinr_db":
        0.0
}


# =========================================================
# CAPACITY MODEL
# =========================================================

CAPACITY_EFFICIENCY_FACTOR = (
    0.55
)


MAX_SPECTRAL_EFFICIENCY_BPS_HZ = (
    6.0
)


# =========================================================
# TIMESTAMP
# =========================================================

def parse_iso_timestamp(
    timestamp
):

    return datetime.fromisoformat(

        timestamp.replace(
            "Z",
            "+00:00"
        )
    )


# =========================================================
# ACTIVITY PROFILE
# =========================================================

def get_activity_profile(
    timestamp
):

    hour = (
        parse_iso_timestamp(
            timestamp
        ).hour
    )


    for profile in ACTIVITY_PROFILES:

        if (

            profile[
                "start_hour"
            ]

            <= hour

            < profile[
                "end_hour"
            ]
        ):

            return deepcopy(
                profile
            )


    raise ValueError(

        f"No traffic activity "
        f"profile for hour {hour}"
    )


# =========================================================
# AREA DEMAND
# =========================================================

def build_area_demand(
    timestamp
):

    profile = (
        get_activity_profile(
            timestamp
        )
    )


    areas = {}


    for (
        area_id,
        population
    ) in (
        AREA_POPULATION_ESTIMATES.items()
    ):


        human_sim_pool = round(

            population

            * TMOBILE_HUMAN_SIM_PER_RESIDENT_PROXY
        )


        active_ues = round(

            human_sim_pool

            * profile[
                "active_fraction"
            ]
        )


        areas[
            area_id
        ] = {

            "population_estimate":
                population,

            "human_tm_sim_pool_estimate":
                human_sim_pool,

            "active_ues":
                active_ues,

            "activity_profile":
                profile[
                    "name"
                ],

            "active_fraction":
                profile[
                    "active_fraction"
                ],

            "avg_active_ue_demand_mbps":
                profile[
                    "avg_active_ue_demand_mbps"
                ]
        }


    return {

        "timestamp":
            timestamp,

        "activity_profile":
            profile,

        "areas":
            areas,

        "total_population_estimate":
            sum(

                item[
                    "population_estimate"
                ]

                for item
                in areas.values()
            ),

        "total_human_tm_sim_pool_estimate":
            sum(

                item[
                    "human_tm_sim_pool_estimate"
                ]

                for item
                in areas.values()
            ),

        "total_active_ues":
            sum(

                item[
                    "active_ues"
                ]

                for item
                in areas.values()
            )
    }


# =========================================================
# SERVICEABILITY
# =========================================================

def classify_serviceability(
    link
):

    # -----------------------------------------------------
    # PROPAGATION MODEL RANGE
    # -----------------------------------------------------

    if not link.get(
        "within_uma_distance_range",
        False
    ):

        return {

            "class":
                "OUT_OF_MODEL_RANGE",

            "serviceable":
                False
        }


    # -----------------------------------------------------
    # UNSERVICEABLE
    # -----------------------------------------------------

    if (

        link[
            "rsrp_dbm"
        ]

        < SERVICEABILITY_POLICY[
            "minimum_rsrp_dbm"
        ]

        or

        link[
            "sinr_db"
        ]

        < SERVICEABILITY_POLICY[
            "minimum_sinr_db"
        ]
    ):

        return {

            "class":
                "UNSERVICEABLE",

            "serviceable":
                False
        }


    # -----------------------------------------------------
    # DEGRADED BUT USABLE
    # -----------------------------------------------------

    if (

        link[
            "rsrp_dbm"
        ]

        < SERVICEABILITY_POLICY[
            "healthy_rsrp_dbm"
        ]

        or

        link[
            "sinr_db"
        ]

        < SERVICEABILITY_POLICY[
            "healthy_sinr_db"
        ]
    ):

        return {

            "class":
                "DEGRADED",

            "serviceable":
                True
        }


    # -----------------------------------------------------
    # HEALTHY
    # -----------------------------------------------------

    return {

        "class":
            "HEALTHY",

        "serviceable":
            True
    }


# =========================================================
# CAPACITY SCORE
# =========================================================

def capacity_score_mbps(
    link
):

    spectral_efficiency = clamp(

        link[
            "shannon_efficiency_bps_hz"
        ],

        0.0,

        MAX_SPECTRAL_EFFICIENCY_BPS_HZ
    )


    return (

        link[
            "bandwidth_mhz"
        ]

        * spectral_efficiency

        * CAPACITY_EFFICIENCY_FACTOR
    )


# =========================================================
# INTEGER SPLIT
# =========================================================

def split_integer_across_samples(
    total,
    sample_ids
):

    sample_ids = sorted(
        sample_ids
    )


    if not sample_ids:

        return {}


    base = (

        total

        // len(
            sample_ids
        )
    )


    remainder = (

        total

        % len(
            sample_ids
        )
    )


    result = {}


    for (
        index,
        sample_id
    ) in enumerate(
        sample_ids
    ):


        result[
            sample_id
        ] = (

            base

            + (

                1

                if index
                < remainder

                else 0
            )
        )


    return result


# =========================================================
# RADIO SERVICE SNAPSHOT
# =========================================================

def build_radio_service_snapshot(
    weather,
    sites=None,
    observation_areas=None,
    antenna_profiles=None
):

    evaluation = (
        evaluate_all_links(

            weather,

            sites,

            observation_areas,

            antenna_profiles
        )
    )


    valid_links = [

        link

        for link
        in evaluation[
            "links"
        ]

        if link[
            "within_uma_distance_range"
        ]
    ]


    excluded_links = [

        link

        for link
        in evaluation[
            "links"
        ]

        if not link[
            "within_uma_distance_range"
        ]
    ]


    serving_by_layer = (
        select_serving_links_and_sinr(

            valid_links,

            weather
        )
    )


    for link in serving_by_layer:


        link[
            "serviceability"
        ] = (
            classify_serviceability(
                link
            )
        )


        link[
            "capacity_score_mbps"
        ] = round(

            capacity_score_mbps(
                link
            ),

            3
        )


    return {

        "ue_samples":
            evaluation[
                "ue_samples"
            ],

        "all_link_count":
            len(
                evaluation[
                    "links"
                ]
            ),

        "valid_link_count":
            len(
                valid_links
            ),

        "excluded_out_of_model_range_link_count":
            len(
                excluded_links
            ),

        "serving_by_layer":
            serving_by_layer
    }


# =========================================================
# PRIMARY RADIO LAYER
# =========================================================
#
# A UE must not be counted independently as one active user
# on n28, B3 AND n78.
#
#
# Selection policy:
#
# 1. UNSERVICEABLE layers are never candidates.
#
# 2. If at least one HEALTHY layer exists, only HEALTHY
#    layers are considered.
#
# 3. DEGRADED layers are considered only when there is no
#    HEALTHY alternative.
#
# 4. Within the eligible class, choose the layer with the
#    highest estimated capacity score.
#
#
# This is still a simplified learning-lab steering model.
#
# It is NOT intended to reproduce full 3GPP cell
# selection/reselection, handover, measurement events,
# priorities or operator mobility policy.
# =========================================================

def choose_primary_layer(
    candidates
):

    # -----------------------------------------------------
    # HEALTHY CANDIDATES
    # -----------------------------------------------------

    healthy_candidates = [

        link

        for link
        in candidates

        if (

            link[
                "serviceability"
            ][
                "serviceable"
            ]

            and

            link[
                "serviceability"
            ][
                "class"
            ]
            == "HEALTHY"
        )
    ]


    if healthy_candidates:

        return max(

            healthy_candidates,

            key=lambda item: (

                item[
                    "capacity_score_mbps"
                ],

                item[
                    "rsrp_dbm"
                ],

                item[
                    "sinr_db"
                ]
            )
        )


    # -----------------------------------------------------
    # DEGRADED FALLBACK
    # -----------------------------------------------------

    degraded_candidates = [

        link

        for link
        in candidates

        if (

            link[
                "serviceability"
            ][
                "serviceable"
            ]

            and

            link[
                "serviceability"
            ][
                "class"
            ]
            == "DEGRADED"
        )
    ]


    if degraded_candidates:

        return max(

            degraded_candidates,

            key=lambda item: (

                item[
                    "capacity_score_mbps"
                ],

                item[
                    "rsrp_dbm"
                ],

                item[
                    "sinr_db"
                ]
            )
        )


    # -----------------------------------------------------
    # NO USABLE LAYER
    # -----------------------------------------------------

    return None


# =========================================================
# LOAD-AWARE PRIMARY LAYER
# =========================================================
#
# This deterministic learning-lab policy adds projected load to
# radio quality when selecting a primary serving layer. It is NOT
# a reproduction of T-Mobile mobility, scheduler, handover or
# vendor-specific load-balancing parameters.
#
# The normal controller runtime uses LOAD_AWARE. Existing focused
# model tests can still use LEGACY, preserving the older static
# capacity-score selection as a deterministic reference path.
# =========================================================

BAND_STEERING_PRIORITY = {
    "n78": 3,
    "B3": 2,
    "n28": 1,
}


def eligible_primary_candidates(candidates):
    healthy = [
        link
        for link in candidates
        if (
            link["serviceability"]["serviceable"]
            and link["serviceability"]["class"] == "HEALTHY"
        )
    ]

    if healthy:
        return healthy

    return [
        link
        for link in candidates
        if (
            link["serviceability"]["serviceable"]
            and link["serviceability"]["class"] == "DEGRADED"
        )
    ]


def projected_prb_pct(
    link,
    record,
    additional_active_ues,
    demand_per_ue_mbps,
):
    # A candidate may be evaluated before it has carried any
    # traffic. Do not require a persistent cell aggregation record
    # just to calculate projected load.
    #
    # This is important because cell_records is a defaultdict.
    # Reading cell_records[cell_id] during ranking would create a
    # placeholder record with bandwidth_mhz=None. That placeholder
    # would later be mistaken for an actual serving-cell KPI record.
    if record is None:
        record = {
            "weight_sum": 0,
            "weighted_efficiency_sum": 0.0,
            "traffic_mbps": 0.0,
        }

    bounded_efficiency = clamp(
        link["shannon_efficiency_bps_hz"],
        0.0,
        MAX_SPECTRAL_EFFICIENCY_BPS_HZ,
    )

    current_weight = record["weight_sum"]
    projected_weight = current_weight + additional_active_ues

    projected_efficiency_sum = (
        record["weighted_efficiency_sum"]
        + bounded_efficiency * additional_active_ues
    )

    mean_efficiency = (
        projected_efficiency_sum / projected_weight
        if projected_weight > 0
        else bounded_efficiency
    )

    estimated_capacity_mbps = (
        link["bandwidth_mhz"]
        * mean_efficiency
        * CAPACITY_EFFICIENCY_FACTOR
    )

    projected_traffic_mbps = (
        record["traffic_mbps"]
        + additional_active_ues * demand_per_ue_mbps
    )

    return (
        projected_traffic_mbps
        / max(estimated_capacity_mbps, 0.001)
        * 100.0
    )


def choose_load_aware_primary_layer(
    candidates,
    cell_records,
    sample_active_ues,
    demand_per_ue_mbps,
):
    eligible = eligible_primary_candidates(candidates)

    if not eligible:
        return None

    def ranking(link):
        # Use .get() deliberately. Merely scoring a candidate must
        # not create a new defaultdict entry.
        record = cell_records.get(
            link["cell_id"]
        )

        projected = projected_prb_pct(
            link,
            record,
            sample_active_ues,
            demand_per_ue_mbps,
        )

        # Lower projected PRB wins. Tie-breakers preserve preference
        # for wider capacity layers and then stronger RF.
        return (
            projected,
            -BAND_STEERING_PRIORITY.get(link["band"], 0),
            -link["capacity_score_mbps"],
            -link["rsrp_dbm"],
            -link["sinr_db"],
            link["cell_id"],
        )

    return min(eligible, key=ranking)



# =========================================================
# CELL-RECORD UPDATE
# =========================================================
#
# One synthetic RF sample represents a group of active UEs.
# Normal LOAD_AWARE steering keeps that group together on one
# primary layer. CAPACITY_RECOVERY is a stronger remediation mode:
# it may split the represented UE group across eligible layers so
# projected PRB headroom can be used more evenly.
#
# This is a learning-lab abstraction of emergency load balancing,
# not a claim about a specific operator/vendor mobility algorithm.
# =========================================================

def add_users_to_cell_record(
    record,
    link,
    active_ues,
    demand_per_ue_mbps,
):
    active_ues = int(active_ues)

    if active_ues <= 0:
        return

    traffic_mbps = active_ues * demand_per_ue_mbps

    record["active_users"] += active_ues
    record["traffic_mbps"] += traffic_mbps
    record["weighted_rsrp_sum"] += link["rsrp_dbm"] * active_ues
    record["weighted_sinr_sum"] += link["sinr_db"] * active_ues

    bounded_efficiency = clamp(
        link["shannon_efficiency_bps_hz"],
        0.0,
        MAX_SPECTRAL_EFFICIENCY_BPS_HZ,
    )

    record["weighted_efficiency_sum"] += bounded_efficiency * active_ues
    record["weight_sum"] += active_ues
    record["bandwidth_mhz"] = link["bandwidth_mhz"]
    record["technology"] = link["technology"]
    record["band"] = link["band"]
    record["site_id"] = link["site_id"]
    record["sector_id"] = link["sector_id"]
    record["serviceability_classes"][link["serviceability"]["class"]] += active_ues


def build_assignment_row(
    sample_id,
    area_id,
    active_ues,
    demand_per_ue_mbps,
    link,
    steering_mode,
):
    return {
        "sample_id": sample_id,
        "area_id": area_id,
        "active_ues": active_ues,
        "traffic_mbps": round(active_ues * demand_per_ue_mbps, 3),
        "status": "SERVED",
        "primary_cell_id": link["cell_id"],
        "site_id": link["site_id"],
        "sector_id": link["sector_id"],
        "technology": link["technology"],
        "band": link["band"],
        "bandwidth_mhz": link["bandwidth_mhz"],
        "rsrp_dbm": link["rsrp_dbm"],
        "sinr_db": link["sinr_db"],
        "serviceability": link["serviceability"]["class"],
        "capacity_score_mbps": link["capacity_score_mbps"],
        "steering_mode": steering_mode,
    }


def distribute_capacity_recovery_users(
    candidates,
    cell_records,
    sample_active_ues,
    demand_per_ue_mbps,
):
    """
    Emergency load-balancing policy used only by the remediation path.

    Each RF sample represents a population cluster, not one literal UE.
    The recovery policy therefore distributes the represented UEs across
    eligible serving layers one UE at a time. Every allocation chooses the
    candidate with the lowest projected PRB after that allocation.

    The elevated demand is unchanged; only placement changes.
    """
    allocations = {}
    allocation_links = {}

    for _ in range(int(sample_active_ues)):
        selected = choose_load_aware_primary_layer(
            candidates,
            cell_records,
            1,
            demand_per_ue_mbps,
        )

        if selected is None:
            break

        cell_id = selected["cell_id"]

        add_users_to_cell_record(
            cell_records[cell_id],
            selected,
            1,
            demand_per_ue_mbps,
        )

        allocations[cell_id] = allocations.get(cell_id, 0) + 1
        allocation_links[cell_id] = selected

    return allocations, allocation_links


# =========================================================
# COMPLETE TRAFFIC SNAPSHOT
# =========================================================

def build_traffic_snapshot(
    weather,
    sites=None,
    observation_areas=None,
    antenna_profiles=None,
    simulation_timestamp=None,
    traffic_multiplier=1.0,
    steering_mode="LEGACY",
    area_traffic_multipliers=None
):

    # -----------------------------------------------------
    # POPULATION / TRAFFIC DEMAND
    # -----------------------------------------------------
    #
    # Environmental observation time and traffic simulation
    # time are separate inputs.
    #
    # Backward-compatibility fallback:
    # direct callers that do not yet supply a simulation clock
    # retain the previous deterministic behaviour. The RAN
    # engine/controller now pass this value explicitly.
    # -----------------------------------------------------

    if simulation_timestamp is None:

        simulation_timestamp = (
            weather[
                "timestamp"
            ]
        )


    demand = (
        build_area_demand(
            simulation_timestamp
        )
    )


    traffic_multiplier = max(
        0.0,
        float(traffic_multiplier)
    )


    # Optional per-area multipliers allow the learning lab to model a
    # local traffic hotspot without multiplying demand everywhere.
    #
    # Example:
    #     {"UE-DOLNI-JIRCANY": 3.0}
    #
    # This is synthetic scenario input, not measured operator traffic.
    if area_traffic_multipliers is None:
        area_traffic_multipliers = {}

    normalized_area_traffic_multipliers = {}

    for area_id, factor in area_traffic_multipliers.items():
        normalized_area_traffic_multipliers[str(area_id)] = max(
            0.0,
            float(factor)
        )


    # Global multiplier defines the normal operating scale. A local
    # hotspot factor is then applied only to the selected area.
    for area_id, area in demand["areas"].items():
        local_multiplier = normalized_area_traffic_multipliers.get(
            area_id,
            1.0
        )

        area["active_ues"] = int(
            round(
                area["active_ues"]
                * traffic_multiplier
                * local_multiplier
            )
        )

        area["traffic_multiplier"] = round(
            traffic_multiplier * local_multiplier,
            3
        )


    demand["total_active_ues"] = sum(
        area["active_ues"]
        for area in demand["areas"].values()
    )


    steering_mode = str(steering_mode).upper()

    if steering_mode not in {
        "LEGACY",
        "LOAD_AWARE",
        "CAPACITY_RECOVERY",
    }:
        raise ValueError(
            f"Unsupported steering_mode: {steering_mode}"
        )


    # -----------------------------------------------------
    # RF SERVICE STATE
    # -----------------------------------------------------

    radio = (
        build_radio_service_snapshot(

            weather,

            sites,

            observation_areas,

            antenna_profiles
        )
    )


    # -----------------------------------------------------
    # RF SAMPLES BY AREA
    # -----------------------------------------------------

    samples_by_area = (
        defaultdict(
            list
        )
    )


    for sample in radio[
        "ue_samples"
    ]:


        samples_by_area[
            sample[
                "area_id"
            ]
        ].append(

            sample[
                "sample_id"
            ]
        )


    # -----------------------------------------------------
    # DISTRIBUTE ACTIVE USERS ACROSS SAMPLE POINTS
    # -----------------------------------------------------

    active_ues_by_sample = {}


    for (
        area_id,
        area_demand
    ) in demand[
        "areas"
    ].items():


        active_ues_by_sample.update(

            split_integer_across_samples(

                area_demand[
                    "active_ues"
                ],

                samples_by_area.get(
                    area_id,
                    []
                )
            )
        )


    # -----------------------------------------------------
    # RADIO LAYERS PER SAMPLE
    # -----------------------------------------------------

    serving_layers_by_sample = (

        defaultdict(
            list
        )
    )


    for link in radio[
        "serving_by_layer"
    ]:


        serving_layers_by_sample[
            link[
                "sample_id"
            ]
        ].append(
            link
        )


    # -----------------------------------------------------
    # CELL AGGREGATION
    # -----------------------------------------------------

    assignments = []


    cell_records = defaultdict(

        lambda: {

            "active_users":
                0,

            "traffic_mbps":
                0.0,

            "weighted_rsrp_sum":
                0.0,

            "weighted_sinr_sum":
                0.0,

            "weighted_efficiency_sum":
                0.0,

            "weight_sum":
                0,

            "bandwidth_mhz":
                None,

            "technology":
                None,

            "band":
                None,

            "site_id":
                None,

            "sector_id":
                None,

            "serviceability_classes":
                defaultdict(
                    int
                )
        }
    )


    served_active_ues = 0

    unserved_active_ues = 0


    # =====================================================
    # ASSIGN TRAFFIC TO PRIMARY SERVING CELL
    # =====================================================

    for sample in radio[
        "ue_samples"
    ]:


        sample_id = (
            sample[
                "sample_id"
            ]
        )


        area_id = (
            sample[
                "area_id"
            ]
        )


        sample_active_ues = (
            active_ues_by_sample.get(

                sample_id,

                0
            )
        )


        candidates = (
            serving_layers_by_sample.get(

                sample_id,

                []
            )
        )


        demand_per_ue = (
            demand[
                "areas"
            ][
                area_id
            ][
                "avg_active_ue_demand_mbps"
            ]
        )


        # -------------------------------------------------
        # CAPACITY-RECOVERY REMEDIATION
        # -------------------------------------------------
        #
        # Unlike normal steering, the represented UE group may be
        # split across multiple eligible layers. The traffic demand
        # itself remains unchanged.
        # -------------------------------------------------

        if steering_mode == "CAPACITY_RECOVERY":

            (
                recovery_allocations,
                recovery_links,
            ) = distribute_capacity_recovery_users(
                candidates,
                cell_records,
                sample_active_ues,
                demand_per_ue,
            )

            allocated_ues = sum(recovery_allocations.values())
            served_active_ues += allocated_ues

            missing_ues = sample_active_ues - allocated_ues
            unserved_active_ues += missing_ues

            for cell_id in sorted(recovery_allocations):
                allocation_ues = recovery_allocations[cell_id]

                if allocation_ues <= 0:
                    continue

                assignments.append(
                    build_assignment_row(
                        sample_id,
                        area_id,
                        allocation_ues,
                        demand_per_ue,
                        recovery_links[cell_id],
                        "CAPACITY_RECOVERY",
                    )
                )

            if missing_ues > 0:
                assignments.append({
                    "sample_id": sample_id,
                    "area_id": area_id,
                    "active_ues": missing_ues,
                    "status": "UNSERVED",
                    "primary_cell_id": None,
                    "available_layers": [
                        {
                            "cell_id": item["cell_id"],
                            "band": item["band"],
                            "rsrp_dbm": item["rsrp_dbm"],
                            "sinr_db": item["sinr_db"],
                            "serviceability": item["serviceability"]["class"],
                        }
                        for item in candidates
                    ],
                    "steering_mode": "CAPACITY_RECOVERY",
                })

            continue

        if steering_mode == "LOAD_AWARE":

            primary = (
                choose_load_aware_primary_layer(
                    candidates,
                    cell_records,
                    sample_active_ues,
                    demand_per_ue
                )
            )

        else:

            primary = (
                choose_primary_layer(
                    candidates
                )
            )


        # -------------------------------------------------
        # UNSERVED
        # -------------------------------------------------

        if primary is None:


            unserved_active_ues += (
                sample_active_ues
            )


            assignments.append({

                "sample_id":
                    sample_id,

                "area_id":
                    area_id,

                "active_ues":
                    sample_active_ues,

                "status":
                    "UNSERVED",

                "primary_cell_id":
                    None,

                "available_layers": [

                    {

                        "cell_id":
                            item[
                                "cell_id"
                            ],

                        "band":
                            item[
                                "band"
                            ],

                        "rsrp_dbm":
                            item[
                                "rsrp_dbm"
                            ],

                        "sinr_db":
                            item[
                                "sinr_db"
                            ],

                        "serviceability":
                            item[
                                "serviceability"
                            ][
                                "class"
                            ]
                    }

                    for item
                    in candidates
                ]
            })


            continue


        # -------------------------------------------------
        # SERVED
        # -------------------------------------------------

        served_active_ues += (
            sample_active_ues
        )


        sample_traffic_mbps = (

            sample_active_ues

            * demand_per_ue
        )


        record = (

            cell_records[
                primary[
                    "cell_id"
                ]
            ]
        )


        record[
            "active_users"
        ] += (
            sample_active_ues
        )


        record[
            "traffic_mbps"
        ] += (
            sample_traffic_mbps
        )


        record[
            "weighted_rsrp_sum"
        ] += (

            primary[
                "rsrp_dbm"
            ]

            * sample_active_ues
        )


        record[
            "weighted_sinr_sum"
        ] += (

            primary[
                "sinr_db"
            ]

            * sample_active_ues
        )


        bounded_efficiency = clamp(

            primary[
                "shannon_efficiency_bps_hz"
            ],

            0.0,

            MAX_SPECTRAL_EFFICIENCY_BPS_HZ
        )


        record[
            "weighted_efficiency_sum"
        ] += (

            bounded_efficiency

            * sample_active_ues
        )


        record[
            "weight_sum"
        ] += (
            sample_active_ues
        )


        record[
            "bandwidth_mhz"
        ] = (
            primary[
                "bandwidth_mhz"
            ]
        )


        record[
            "technology"
        ] = (
            primary[
                "technology"
            ]
        )


        record[
            "band"
        ] = (
            primary[
                "band"
            ]
        )


        record[
            "site_id"
        ] = (
            primary[
                "site_id"
            ]
        )


        record[
            "sector_id"
        ] = (
            primary[
                "sector_id"
            ]
        )


        record[
            "serviceability_classes"
        ][
            primary[
                "serviceability"
            ][
                "class"
            ]
        ] += (
            sample_active_ues
        )


        assignments.append({

            "sample_id":
                sample_id,

            "area_id":
                area_id,

            "active_ues":
                sample_active_ues,

            "traffic_mbps":
                round(
                    sample_traffic_mbps,
                    3
                ),

            "status":
                "SERVED",

            "primary_cell_id":
                primary[
                    "cell_id"
                ],

            "site_id":
                primary[
                    "site_id"
                ],

            "sector_id":
                primary[
                    "sector_id"
                ],

            "technology":
                primary[
                    "technology"
                ],

            "band":
                primary[
                    "band"
                ],

            "bandwidth_mhz":
                primary[
                    "bandwidth_mhz"
                ],

            "rsrp_dbm":
                primary[
                    "rsrp_dbm"
                ],

            "sinr_db":
                primary[
                    "sinr_db"
                ],

            "serviceability":
                primary[
                    "serviceability"
                ][
                    "class"
                ],

            "capacity_score_mbps":
                primary[
                    "capacity_score_mbps"
                ]
        })


    # =====================================================
    # BUILD CELL KPI SUMMARY
    # =====================================================

    cells = []


    for (
        cell_id,
        record
    ) in sorted(
        cell_records.items()
    ):


        weight = max(

            record[
                "weight_sum"
            ],

            1
        )


        mean_rsrp_dbm = (

            record[
                "weighted_rsrp_sum"
            ]

            / weight
        )


        mean_sinr_db = (

            record[
                "weighted_sinr_sum"
            ]

            / weight
        )


        mean_spectral_efficiency = (

            record[
                "weighted_efficiency_sum"
            ]

            / weight
        )


        estimated_capacity_mbps = (

            record[
                "bandwidth_mhz"
            ]

            * mean_spectral_efficiency

            * CAPACITY_EFFICIENCY_FACTOR
        )


        prb_utilization_pct = clamp(

            (

                record[
                    "traffic_mbps"
                ]

                / max(

                    estimated_capacity_mbps,

                    0.001
                )
            )

            * 100.0,

            0.0,

            100.0
        )


        cells.append({

            "cell_id":
                cell_id,

            "site_id":
                record[
                    "site_id"
                ],

            "sector_id":
                record[
                    "sector_id"
                ],

            "technology":
                record[
                    "technology"
                ],

            "band":
                record[
                    "band"
                ],

            "bandwidth_mhz":
                record[
                    "bandwidth_mhz"
                ],

            "active_users":
                record[
                    "active_users"
                ],

            "traffic_mbps":
                round(

                    record[
                        "traffic_mbps"
                    ],

                    2
                ),

            "weighted_mean_rsrp_dbm":
                round(

                    mean_rsrp_dbm,

                    2
                ),

            "weighted_mean_sinr_db":
                round(

                    mean_sinr_db,

                    2
                ),

            "weighted_mean_spectral_efficiency_bps_hz":
                round(

                    mean_spectral_efficiency,

                    3
                ),

            "estimated_capacity_mbps":
                round(

                    estimated_capacity_mbps,

                    2
                ),

            "prb_utilization_pct":
                round(

                    prb_utilization_pct,

                    1
                ),

            "serviceability_ue_mix":
                dict(

                    record[
                        "serviceability_classes"
                    ]
                )
        })


    # =====================================================
    # SERVICE COVERAGE SUMMARY
    # =====================================================

    total_requested = (
        demand[
            "total_active_ues"
        ]
    )


    service_ratio = (

        served_active_ues
        / total_requested

        if total_requested > 0

        else 1.0
    )


    return {

        "weather_timestamp":
            weather[
                "timestamp"
            ],

        "simulation_timestamp":
            simulation_timestamp,


        "traffic_context": {
            "multiplier":
                round(
                    traffic_multiplier,
                    3
                ),

            "area_traffic_multipliers":
                deepcopy(
                    normalized_area_traffic_multipliers
                ),

            "steering_mode":
                steering_mode
        },


        "population_model": {

            "reference_date":
                POPULATION_REFERENCE[
                    "reference_date"
                ],

            "total_population_estimate":
                demand[
                    "total_population_estimate"
                ],

            "tmobile_human_sim_per_resident_proxy":
                TMOBILE_HUMAN_SIM_PER_RESIDENT_PROXY,

            "total_human_tm_sim_pool_estimate":
                demand[
                    "total_human_tm_sim_pool_estimate"
                ],

            "activity_profile":
                demand[
                    "activity_profile"
                ],

            "total_active_ues":
                total_requested
        },


        "radio_model_range": {

            "all_links":
                radio[
                    "all_link_count"
                ],

            "valid_links":
                radio[
                    "valid_link_count"
                ],

            "excluded_out_of_model_range_links":
                radio[
                    "excluded_out_of_model_range_link_count"
                ]
        },


        "serviceability_policy":
            deepcopy(
                SERVICEABILITY_POLICY
            ),


        "service": {

            "requested_active_ues":
                total_requested,

            "served_active_ues":
                served_active_ues,

            "unserved_active_ues":
                unserved_active_ues,

            "served_ratio_pct":
                round(

                    service_ratio
                    * 100.0,

                    2
                )
        },


        "areas":
            demand[
                "areas"
            ],


        "assignments":
            assignments,


        "cells":
            cells
    }
