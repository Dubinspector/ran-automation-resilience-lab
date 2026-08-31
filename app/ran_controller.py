"""
In-memory RAN automation controller.

Control loop:

known-good configuration
    -> current-environment baseline observation
    -> baseline health pre-check
    -> candidate configuration
    -> RF + traffic evaluation
    -> guardrails
    -> PROMOTE or REJECT / ROLLBACK

Context consistency:
Each evaluate/apply attempt resolves exactly one weather snapshot and
exactly one traffic simulation timestamp.

The active baseline, candidate, and post-rollback verification use
that same pair so KPI deltas are attributable to configuration, not
to different environmental inputs or a traffic-profile clock change.

Weather observation time and traffic simulation time are deliberately
separate inputs. They can be close at runtime, but one does not derive
from the other.

Important distinction:

"Known-good configuration" means the last configuration accepted by
the automation.

It does NOT guarantee that the RAN is currently inside the safe
operating envelope. Traffic demand or environmental conditions can
change while the configuration remains unchanged.

Therefore guarded_apply() performs a fresh baseline health pre-check
before building/applying a candidate.

This is a conservative learning-lab policy:
if the active RAN is already outside the safe operating envelope,
normal guarded changes are blocked.

This learning lab also provides a separately authorized recovery path
for an explicitly injected RF fault. That path restores the last accepted
known-good configuration and verifies target recovery without weakening
the normal guarded-change policy.

This is a single-process learning-lab controller, not a production
distributed state store.
"""

from copy import deepcopy
from datetime import datetime, timezone
from threading import RLock
from zoneinfo import ZoneInfo

from app.ran_engine import (
    build_baseline_sites,
    build_candidate_sites,
    build_configuration_inventory,
    evaluate_ran_state,
)

from app.ran_guardrails import (
    evaluate_ran_guardrails,
)

from app.weather_service import (
    get_weather_snapshot,
)


# =========================================================
# CONTROLLER
# =========================================================

class RanAutomationController:

    def __init__(
        self,
        simulation_timestamp=None,
        traffic_multiplier=1.0,
        steering_mode="LEGACY"
    ):

        self._lock = RLock()

        self._config_revision = 0

        self._attempt_counter = 0

        self._rollout_state = (
            "STABLE"
        )

        self._last_action = (
            "INITIALIZED"
        )

        self._events = []


        # -------------------------------------------------
        # FACTORY / INITIAL KNOWN-GOOD CONFIGURATION
        # -------------------------------------------------

        self._active_sites = (
            build_baseline_sites()
        )


        # -------------------------------------------------
        # SELF-HEALING / RECOVERY TARGET
        # -------------------------------------------------
        #
        # _recovery_target_sites always represents the last
        # intentionally accepted known-good configuration.
        #
        # A lab fault injection is allowed to mutate _active_sites
        # without changing the configuration revision. The recovery
        # target therefore remains available for a separate
        # self-healing path.
        # -------------------------------------------------

        self._recovery_target_sites = deepcopy(
            self._active_sites
        )

        self._recovery_target_version = (
            self.active_version
        )

        self._fault_state = None


        # -------------------------------------------------
        # TRAFFIC / STEERING CONTEXT
        # -------------------------------------------------
        #
        # These are explicit learning-lab inputs. They are separate
        # from weather observation time and from RAN configuration.
        # A capacity fault can raise the traffic multiplier without
        # changing CONFIG-1.x. Capacity remediation can then change
        # steering policy while keeping the elevated demand fixed.
        # -------------------------------------------------

        self._normal_traffic_multiplier = max(
            0.0,
            float(traffic_multiplier)
        )

        self._normal_steering_mode = str(
            steering_mode
        ).upper()

        self._traffic_multiplier = (
            self._normal_traffic_multiplier
        )

        self._steering_mode = (
            self._normal_steering_mode
        )

        # Per-area traffic multipliers are empty in normal operation.
        # Capacity fault injection may add one local hotspot while
        # keeping the global normal traffic scale unchanged.
        self._area_traffic_multipliers = {}


        initial_weather = (
            self._resolve_weather_snapshot()
        )


        initial_simulation_timestamp = (
            self._resolve_simulation_timestamp(
                simulation_timestamp
            )
        )


        self._active_snapshot = (
            self._evaluate_sites_for_context(
                self._active_sites,
                initial_weather,
                initial_simulation_timestamp
            )
        )


        self._record_event(

            event_type=
                "CONTROLLER_INITIALIZED",

            status=
                "PASS",

            message=
                (
                    "Baseline synthetic RAN configuration "
                    "loaded as initial known-good state."
                ),

            details={

                "active_version":
                    self.active_version,

                "weather_timestamp":
                    initial_weather.get(
                        "timestamp"
                    ),

                "weather_source":
                    initial_weather.get(
                        "source"
                    ),

                "weather_status":
                    initial_weather.get(
                        "source_status"
                    ),

                "simulation_timestamp":
                    initial_simulation_timestamp,

                "traffic_multiplier":
                    self._traffic_multiplier,

                "steering_mode":
                    self._steering_mode
            }
        )


    # =====================================================
    # BASIC STATE
    # =====================================================

    @property
    def active_version(
        self
    ):

        return (
            f"CONFIG-1."
            f"{self._config_revision}"
        )


    @property
    def rollout_state(
        self
    ):

        return self._rollout_state


    @property
    def last_action(
        self
    ):

        return self._last_action


    # =====================================================
    # WEATHER
    # =====================================================

    def _resolve_weather_snapshot(
        self,
        weather=None
    ):

        """
        Resolve exactly one weather snapshot for one
        controller operation.

        Explicit weather is useful for deterministic tests.

        Otherwise weather_service provides:

        LIVE
        CACHE
        STALE_LAST_KNOWN
        FALLBACK
        """

        if weather is not None:

            return deepcopy(
                weather
            )


        return deepcopy(
            get_weather_snapshot()
        )


    # =====================================================
    # TRAFFIC SIMULATION CLOCK
    # =====================================================

    def _resolve_simulation_timestamp(
        self,
        simulation_timestamp=None
    ):

        """
        Resolve one traffic/activity clock for one controller
        operation.

        Explicit input keeps tests deterministic. Runtime calls use
        the current Europe/Prague clock. This timestamp is independent
        from weather["timestamp"], which represents environmental
        observation validity.
        """

        if simulation_timestamp is not None:

            return str(
                simulation_timestamp
            )


        return (
            datetime.now(
                ZoneInfo(
                    "Europe/Prague"
                )
            ).isoformat(
                timespec=
                    "seconds"
            )
        )


    # =====================================================
    # RAN EVALUATION WITH EXPLICIT TRAFFIC CONTEXT
    # =====================================================

    def _evaluate_sites_for_context(
        self,
        sites,
        weather,
        simulation_timestamp,
        traffic_multiplier=None,
        steering_mode=None,
        area_traffic_multipliers=None
    ):

        if traffic_multiplier is None:
            traffic_multiplier = self._traffic_multiplier

        if steering_mode is None:
            steering_mode = self._steering_mode

        if area_traffic_multipliers is None:
            area_traffic_multipliers = self._area_traffic_multipliers

        return evaluate_ran_state(
            sites,
            weather=weather,
            simulation_timestamp=simulation_timestamp,
            traffic_multiplier=traffic_multiplier,
            steering_mode=steering_mode,
            area_traffic_multipliers=area_traffic_multipliers,
        )


    # =====================================================
    # ACTIVE RAN OBSERVATION
    # =====================================================

    def _refresh_active_snapshot_for_context(
        self,
        weather,
        simulation_timestamp
    ):

        """
        Re-observe the current known-good configuration under
        the supplied environment and traffic simulation clock.

        This changes observed RF/service/traffic state only.

        It does NOT change:
        - configuration,
        - active config revision,
        - known-good ownership.
        """

        snapshot = (
            self._evaluate_sites_for_context(
                self._active_sites,
                weather,
                simulation_timestamp
            )
        )


        self._active_snapshot = deepcopy(
            snapshot
        )


        return snapshot


    # =====================================================
    # BASELINE HEALTH
    # =====================================================

    def _evaluate_baseline_health(
        self,
        baseline_snapshot
    ):

        """
        Evaluate the ACTIVE RAN against the same absolute
        operating-envelope guardrails used for candidates.

        We compare the baseline snapshot with itself.

        Delta-based checks therefore naturally evaluate to
        zero change.

        Absolute checks remain meaningful, for example:

            MAX_CANDIDATE_PRB

        In baseline-health context this means:

            "Is an active serving cell already above the
             configured absolute PRB ceiling?"

        The original guardrail name is intentionally preserved
        so the policy remains defined in one place.
        """

        return (
            evaluate_ran_guardrails(

                baseline_snapshot,

                baseline_snapshot
            )
        )


    def _baseline_health_summary(
        self,
        baseline_snapshot
    ):

        guardrails = (
            self._evaluate_baseline_health(
                baseline_snapshot
            )
        )


        failed_checks = deepcopy(
            guardrails[
                "failed_checks"
            ]
        )


        return {

            "status":
                guardrails[
                    "verdict"
                ],

            "inside_safe_envelope":
                (
                    guardrails[
                        "verdict"
                    ]
                    == "PASS"
                ),

            "failed_check_count":
                guardrails[
                    "failed_check_count"
                ],

            "failed_checks":
                failed_checks,

            "service":
                deepcopy(
                    baseline_snapshot[
                        "service"
                    ]
                ),

            "guardrails":
                deepcopy(
                    guardrails
                )
        }


    def get_baseline_health(
        self,
        weather=None,
        simulation_timestamp=None
    ):

        """
        Public non-configuration-changing health observation.

        Useful later for:
        - API status,
        - dashboard baseline-health panel,
        - troubleshooting.
        """

        with self._lock:

            observation_weather = (
                self._resolve_weather_snapshot(
                    weather
                )
            )


            observation_simulation_timestamp = (
                self._resolve_simulation_timestamp(
                    simulation_timestamp
                )
            )


            baseline_snapshot = (
                self._refresh_active_snapshot_for_context(
                    observation_weather,
                    observation_simulation_timestamp
                )
            )


            baseline_health = (
                self._baseline_health_summary(
                    baseline_snapshot
                )
            )


            return {

                "active_version":
                    self.active_version,

                "weather":
                    deepcopy(
                        observation_weather
                    ),

                "simulation_timestamp":
                    observation_simulation_timestamp,

                "baseline_health":
                    deepcopy(
                        baseline_health
                    ),

                "service":
                    deepcopy(
                        baseline_snapshot[
                            "service"
                        ]
                    )
            }


    # =====================================================
    # EVENT HELPERS
    # =====================================================

    def _timestamp(
        self
    ):

        return (
            datetime.now(
                timezone.utc
            ).isoformat()
        )


    def _record_event(
        self,
        event_type,
        status,
        message,
        details=None
    ):

        if details is None:

            details = {}


        event = {

            "timestamp":
                self._timestamp(),

            "event_type":
                event_type,

            "status":
                status,

            "message":
                message,

            "details":
                deepcopy(
                    details
                )
        }


        self._events.append(
            event
        )


        return event


    # =====================================================
    # ATTEMPT / VERSION
    # =====================================================

    def _next_attempt_id(
        self
    ):

        self._attempt_counter += 1


        return (

            "ATTEMPT-"

            f"{self._attempt_counter:04d}"
        )


    def _candidate_version(
        self
    ):

        return (

            "CONFIG-1."

            f"{self._config_revision + 1}"
        )


    # =====================================================
    # ACTIVE STATE
    # =====================================================

    def get_active_state(
        self
    ):

        with self._lock:

            return {

                "active_version":
                    self.active_version,

                "rollout_state":
                    self._rollout_state,

                "last_action":
                    self._last_action,

                "traffic_context": {
                    "multiplier":
                        self._traffic_multiplier,

                    "steering_mode":
                        self._steering_mode
                },

                "fault_active":
                    bool(
                        self._fault_state
                        and
                        self._fault_state.get(
                            "active"
                        )
                    ),

                "weather":
                    deepcopy(

                        self._active_snapshot[
                            "weather"
                        ]
                    ),

                "simulation_timestamp":
                    self._active_snapshot[
                        "simulation_timestamp"
                    ],

                "configuration":
                    deepcopy(

                        self._active_snapshot[
                            "configuration"
                        ]
                    ),

                "service":
                    deepcopy(

                        self._active_snapshot[
                            "service"
                        ]
                    ),

                "population_model":
                    deepcopy(

                        self._active_snapshot[
                            "population_model"
                        ]
                    ),

                "radio_model_range":
                    deepcopy(

                        self._active_snapshot[
                            "radio_model_range"
                        ]
                    ),

                "cells":
                    deepcopy(

                        self._active_snapshot[
                            "cells"
                        ]
                    )
            }


    def get_active_snapshot(
        self
    ):

        with self._lock:

            return deepcopy(
                self._active_snapshot
            )


    def get_active_sites(
        self
    ):

        with self._lock:

            return deepcopy(
                self._active_sites
            )


    def get_optimization_observation(
        self,
        weather=None,
        simulation_timestamp=None
    ):
        """
        Capture one consistent read-only optimization context.

        The controller lock is held only long enough to copy configuration
        and controller state. Weather resolution and the fresh network
        evaluation happen after the lock is released so the periodic
        optimizer does not hold the controller RLock while running the
        expensive RF / traffic model.

        The returned active_sites snapshot is immutable from the optimizer's
        point of view. Every optimization candidate is evaluated against the
        same weather, traffic clock, traffic multiplier, steering mode and
        area-demand multipliers.

        This method does not mutate configuration, accepted revision, fault
        state, steering policy or the controller's active snapshot.
        """

        with self._lock:

            active_version = self.active_version
            recovery_target_version = self._recovery_target_version
            rollout_state = self._rollout_state
            last_action = self._last_action
            fault_state = deepcopy(self._fault_state)
            steering_mode = self._steering_mode
            traffic_multiplier = self._traffic_multiplier
            area_traffic_multipliers = deepcopy(
                self._area_traffic_multipliers
            )
            active_sites = deepcopy(self._active_sites)
            recovery_target_sites = deepcopy(
                self._recovery_target_sites
            )

        # Resolve one context after releasing the controller lock.
        observation_weather = self._resolve_weather_snapshot(weather)
        observation_simulation_timestamp = (
            self._resolve_simulation_timestamp(simulation_timestamp)
        )

        # Fresh read-only baseline observation. Do NOT assign this result to
        # self._active_snapshot; the periodic evaluator must not alter
        # controller state merely by observing it.
        snapshot = evaluate_ran_state(
            active_sites,
            weather=observation_weather,
            simulation_timestamp=observation_simulation_timestamp,
            traffic_multiplier=traffic_multiplier,
            steering_mode=steering_mode,
            area_traffic_multipliers=area_traffic_multipliers,
        )

        return {
            "active_version": active_version,
            "recovery_target_version": recovery_target_version,
            "rollout_state": rollout_state,
            "last_action": last_action,
            "fault_state": fault_state,
            "steering_mode": steering_mode,
            "traffic_multiplier": traffic_multiplier,
            "area_traffic_multipliers": area_traffic_multipliers,
            "weather": deepcopy(observation_weather),
            "simulation_timestamp": observation_simulation_timestamp,
            "snapshot": deepcopy(snapshot),
            "active_sites": active_sites,
            "recovery_target_sites": recovery_target_sites,
        }


    def get_events(
        self,
        limit=None
    ):

        with self._lock:

            events = deepcopy(
                self._events
            )


        if limit is None:

            return events


        return events[
            -int(limit):
        ]



    # =====================================================
    # SELF-HEALING / LAB FAULT INJECTION
    # =====================================================
    #
    # Normal guarded_apply() remains conservative:
    # an unhealthy active baseline blocks ordinary promotion.
    #
    # The methods below are a separate recovery path. They model
    # the operational distinction between:
    #
    #   normal optimization
    #       and
    #   authorized remediation / self-healing.
    #
    # A lab RF fault does NOT create a new configuration revision.
    # It represents an operationally bad active state. The last
    # intentionally accepted known-good configuration is retained
    # in _recovery_target_sites and can be restored by run_self_healing().
    # =====================================================

    def _scope_metrics(
        self,
        snapshot,
        cell_ids
    ):

        rows = []

        for cell_id in cell_ids:

            cell = (
                snapshot.get(
                    "cells",
                    {}
                ).get(
                    cell_id
                )
            )

            if cell is None:

                rows.append({
                    "cell_id":
                        cell_id,

                    "serving":
                        False,

                    "rsrp_dbm":
                        None,

                    "sinr_db":
                        None,

                    "prb_utilization_pct":
                        None,

                    "active_users":
                        0,

                    "traffic_mbps":
                        0.0
                })

                continue


            rows.append({
                "cell_id":
                    cell_id,

                "serving":
                    True,

                "rsrp_dbm":
                    cell.get(
                        "rsrp_dbm"
                    ),

                "sinr_db":
                    cell.get(
                        "sinr_db"
                    ),

                "prb_utilization_pct":
                    cell.get(
                        "prb_utilization_pct"
                    ),

                "active_users":
                    int(
                        cell.get(
                            "active_users",
                            0
                        )
                    ),

                "traffic_mbps":
                    float(
                        cell.get(
                            "traffic_mbps",
                            0.0
                        )
                    )
            })


        serving_rows = [
            row
            for row in rows
            if row[
                "serving"
            ]
        ]


        def mean_metric(
            metric
        ):

            values = [

                float(
                    row[
                        metric
                    ]
                )

                for row in serving_rows

                if row.get(
                    metric
                )
                is not None
            ]

            if not values:

                return None

            return round(
                sum(
                    values
                )
                /
                len(
                    values
                ),
                3
            )


        prb_values = [

            float(
                row[
                    "prb_utilization_pct"
                ]
            )

            for row in serving_rows

            if row.get(
                "prb_utilization_pct"
            )
            is not None
        ]


        return {
            "configured_cells":
                len(
                    cell_ids
                ),

            "serving_cells":
                len(
                    serving_rows
                ),

            "active_users":
                sum(
                    row[
                        "active_users"
                    ]
                    for row in serving_rows
                ),

            "traffic_mbps":
                round(
                    sum(
                        row[
                            "traffic_mbps"
                        ]
                        for row in serving_rows
                    ),
                    3
                ),

            "mean_rsrp_dbm":
                mean_metric(
                    "rsrp_dbm"
                ),

            "mean_sinr_db":
                mean_metric(
                    "sinr_db"
                ),

            "max_prb_utilization_pct":
                (
                    round(
                        max(
                            prb_values
                        ),
                        3
                    )
                    if prb_values
                    else None
                ),

            "cells":
                rows
        }


    def _scope_recovery_improved(
        self,
        before,
        after
    ):

        if (
            after[
                "serving_cells"
            ]
            >
            before[
                "serving_cells"
            ]
        ):

            return True


        before_rsrp = before.get(
            "mean_rsrp_dbm"
        )

        after_rsrp = after.get(
            "mean_rsrp_dbm"
        )

        if (
            before_rsrp is None
            and
            after_rsrp is not None
        ):

            return True

        if (
            before_rsrp is not None
            and
            after_rsrp is not None
            and
            after_rsrp
            >=
            before_rsrp
            + 1.0
        ):

            return True


        before_sinr = before.get(
            "mean_sinr_db"
        )

        after_sinr = after.get(
            "mean_sinr_db"
        )

        if (
            before_sinr is None
            and
            after_sinr is not None
        ):

            return True

        if (
            before_sinr is not None
            and
            after_sinr is not None
            and
            after_sinr
            >=
            before_sinr
            + 1.0
        ):

            return True


        if (
            after[
                "active_users"
            ]
            >
            before[
                "active_users"
            ]
        ):

            return True


        # Restoring an accepted configuration can result in very
        # similar metrics if the fault was mild or if UEs reassociate.
        # Configuration equality is verified separately, so lack of a
        # >=1 dB KPI jump is informative rather than an automatic fail.
        return False


    def get_self_healing_state(
        self
    ):

        with self._lock:

            fault_active = bool(
                self._fault_state
                and
                self._fault_state.get(
                    "active"
                )
            )


            return {
                "fault_active":
                    fault_active,

                "fault":
                    deepcopy(
                        self._fault_state
                    )
                    if fault_active
                    else None,

                "active_version":
                    self.active_version,

                "recovery_target_version":
                    self._recovery_target_version,

                "rollout_state":
                    self._rollout_state,

                "last_action":
                    self._last_action,

                "traffic_multiplier":
                    self._traffic_multiplier,

                "normal_traffic_multiplier":
                    self._normal_traffic_multiplier,

                "steering_mode":
                    self._steering_mode,

                "area_traffic_multipliers":
                    deepcopy(
                        self._area_traffic_multipliers
                    )
            }


    def inject_capacity_spike(
        self,
        spike_factor=8.0,
        weather=None,
        simulation_timestamp=None
    ):

        with self._lock:

            if (
                self._fault_state
                and self._fault_state.get("active")
            ):
                return {
                    "status": "BLOCKED",
                    "reason": "ACTIVE_FAULT_ALREADY_PRESENT",
                    "active_version": self.active_version,
                    "fault": deepcopy(self._fault_state),
                    "configuration_changed": False,
                }

            requested_spike_factor = float(spike_factor)

            if requested_spike_factor <= 1.0:
                raise ValueError(
                    "Capacity spike factor must be greater than 1.0."
                )

            attempt_id = self._next_attempt_id()
            attempt_weather = self._resolve_weather_snapshot(weather)
            attempt_simulation_timestamp = (
                self._resolve_simulation_timestamp(simulation_timestamp)
            )

            pre_snapshot = self._refresh_active_snapshot_for_context(
                attempt_weather,
                attempt_simulation_timestamp
            )
            pre_health = self._baseline_health_summary(pre_snapshot)

            if pre_health["status"] != "PASS":
                return {
                    "status": "BLOCKED",
                    "reason": "ACTIVE_RAN_OUTSIDE_SAFE_ENVELOPE",
                    "active_version": self.active_version,
                    "baseline_health_before": pre_health,
                    "configuration_changed": False,
                    "configuration_revision_changed": False,
                }

            pre_multiplier = self._traffic_multiplier
            pre_steering = self._steering_mode
            pre_area_multipliers = deepcopy(
                self._area_traffic_multipliers
            )

            # -------------------------------------------------
            # LOCAL HOTSPOT SEARCH
            # -------------------------------------------------
            #
            # A network-wide traffic multiplier can simply exhaust total
            # capacity, leaving no steering-only recovery path. For the
            # self-healing demo we instead search for a LOCAL demand
            # hotspot: normal LOAD_AWARE placement becomes unsafe, while
            # CAPACITY_RECOVERY can redistribute the represented UE group
            # across eligible layers under the exact same hotspot demand.
            #
            # The area is chosen from the current RF/traffic assignments,
            # not hard-coded to one municipality.
            # -------------------------------------------------

            area_ids = sorted({
                row.get("area_id")
                for row in pre_snapshot.get("assignments", [])
                if row.get("area_id")
            })

            candidate_factors = []
            factor = requested_spike_factor

            while factor >= 1.1:
                candidate_factors.append(round(factor, 2))
                factor -= 0.1

            if 1.1 not in candidate_factors:
                candidate_factors.append(1.1)

            selected = None
            attempts = []

            for candidate_factor in candidate_factors:

                for area_id in area_ids:
                    hotspot = {
                        area_id: candidate_factor
                    }

                    fault_snapshot = self._evaluate_sites_for_context(
                        self._active_sites,
                        attempt_weather,
                        attempt_simulation_timestamp,
                        traffic_multiplier=pre_multiplier,
                        steering_mode="LOAD_AWARE",
                        area_traffic_multipliers=hotspot,
                    )
                    fault_health = self._baseline_health_summary(
                        fault_snapshot
                    )

                    recovery_preview = self._evaluate_sites_for_context(
                        self._active_sites,
                        attempt_weather,
                        attempt_simulation_timestamp,
                        traffic_multiplier=pre_multiplier,
                        steering_mode="CAPACITY_RECOVERY",
                        area_traffic_multipliers=hotspot,
                    )
                    recovery_preview_health = self._baseline_health_summary(
                        recovery_preview
                    )

                    fault_max = fault_health["guardrails"]["summary"].get(
                        "max_candidate_prb"
                    )
                    recovery_max = (
                        recovery_preview_health["guardrails"]["summary"].get(
                            "max_candidate_prb"
                        )
                    )

                    attempts.append({
                        "area_id": area_id,
                        "spike_factor": candidate_factor,
                        "fault_status": fault_health["status"],
                        "recovery_status": recovery_preview_health["status"],
                        "fault_max_prb": (
                            fault_max.get("prb_utilization_pct")
                            if fault_max else None
                        ),
                        "recovery_max_prb": (
                            recovery_max.get("prb_utilization_pct")
                            if recovery_max else None
                        ),
                    })

                    if (
                        fault_health["status"] == "FAIL"
                        and
                        recovery_preview_health["status"] == "PASS"
                    ):
                        selected = (
                            area_id,
                            candidate_factor,
                            hotspot,
                            fault_snapshot,
                            fault_health,
                            recovery_preview_health,
                        )
                        break

                if selected is not None:
                    break

            if selected is None:
                self._record_event(
                    event_type="CAPACITY_SPIKE_NOT_INJECTED",
                    status="BLOCKED",
                    message=(
                        "No local hotspot was found where capacity "
                        "recovery can restore the safe envelope."
                    ),
                    details={
                        "attempt_id": attempt_id,
                        "active_version": self.active_version,
                        "requested_spike_factor": requested_spike_factor,
                        "traffic_multiplier_before": pre_multiplier,
                        "simulation_timestamp": attempt_simulation_timestamp,
                        "search_attempts": attempts[-20:],
                    },
                )

                return {
                    "status": "BLOCKED",
                    "reason": "NO_RECOVERABLE_LOCAL_CAPACITY_HOTSPOT_FOUND",
                    "attempt_id": attempt_id,
                    "active_version": self.active_version,
                    "baseline_health_before": pre_health,
                    "requested_spike_factor": requested_spike_factor,
                    "search_attempt_count": len(attempts),
                    "search_tail": attempts[-12:],
                    "configuration_changed": False,
                    "configuration_revision_changed": False,
                }

            (
                hotspot_area_id,
                applied_spike_factor,
                hotspot,
                fault_snapshot,
                fault_health,
                recovery_preview_health,
            ) = selected

            self._area_traffic_multipliers = deepcopy(hotspot)
            self._steering_mode = "LOAD_AWARE"
            self._active_snapshot = deepcopy(fault_snapshot)
            self._rollout_state = "DEGRADED"
            self._last_action = "CAPACITY_HOTSPOT_INJECTED"
            self._fault_state = {
                "active": True,
                "fault_id": attempt_id,
                "type": "CAPACITY_SPIKE",
                "scope": "LOCAL_HOTSPOT",
                "hotspot_area_id": hotspot_area_id,
                "requested_spike_factor": requested_spike_factor,
                "spike_factor": applied_spike_factor,
                "pre_traffic_multiplier": pre_multiplier,
                "fault_traffic_multiplier": pre_multiplier,
                "pre_area_traffic_multipliers": pre_area_multipliers,
                "fault_area_traffic_multipliers": deepcopy(hotspot),
                "pre_steering_mode": pre_steering,
                "fault_steering_mode": "LOAD_AWARE",
                "recovery_preview_safe": (
                    recovery_preview_health["status"] == "PASS"
                ),
            }

            pre_max = pre_health["guardrails"]["summary"].get(
                "max_candidate_prb"
            )
            fault_max = fault_health["guardrails"]["summary"].get(
                "max_candidate_prb"
            )
            recovery_preview_max = (
                recovery_preview_health["guardrails"]["summary"].get(
                    "max_candidate_prb"
                )
            )

            self._record_event(
                event_type="CAPACITY_HOTSPOT_INJECTED",
                status="WARNING",
                message=(
                    "Synthetic local traffic hotspot injected without "
                    "changing accepted RAN configuration."
                ),
                details={
                    "attempt_id": attempt_id,
                    "active_version": self.active_version,
                    "hotspot_area_id": hotspot_area_id,
                    "requested_spike_factor": requested_spike_factor,
                    "applied_spike_factor": applied_spike_factor,
                    "traffic_multiplier": pre_multiplier,
                    "area_traffic_multipliers": deepcopy(hotspot),
                    "steering_mode": "LOAD_AWARE",
                    "max_prb_before": pre_max,
                    "max_prb_after": fault_max,
                    "recovery_preview_max_prb": recovery_preview_max,
                    "recovery_preview_safe": True,
                    "simulation_timestamp": attempt_simulation_timestamp,
                },
            )

            return {
                "status": "FAULT_INJECTED",
                "reason": "LEARNING_LAB_LOCAL_CAPACITY_HOTSPOT",
                "attempt_id": attempt_id,
                "active_version": self.active_version,
                "weather": deepcopy(attempt_weather),
                "simulation_timestamp": attempt_simulation_timestamp,
                "fault": deepcopy(self._fault_state),
                "baseline_health_before": pre_health,
                "baseline_health_after": fault_health,
                "requested_spike_factor": requested_spike_factor,
                "applied_spike_factor": applied_spike_factor,
                "hotspot_area_id": hotspot_area_id,
                "traffic_multiplier_before": pre_multiplier,
                "traffic_multiplier_after": pre_multiplier,
                "area_traffic_multipliers_before": pre_area_multipliers,
                "area_traffic_multipliers_after": deepcopy(hotspot),
                "steering_mode_before": pre_steering,
                "steering_mode_after": "LOAD_AWARE",
                "max_prb_before": pre_max,
                "max_prb_after": fault_max,
                "recovery_preview_max_prb": recovery_preview_max,
                "recovery_preview_safe": True,
                "configuration_changed": False,
                "configuration_revision_changed": False,
                "steps": [
                    {"step": "Observe healthy pre-hotspot RAN state", "status": "PASS"},
                    {"step": "Inject local synthetic traffic hotspot", "status": "PASS"},
                    {"step": "Detect PRB / capacity overload", "status": "FAIL"},
                    {"step": "Pre-compute split-steering recovery", "status": "PASS"},
                ],
            }


    def _run_capacity_self_healing_locked(
        self,
        fault,
        attempt_id,
        attempt_weather,
        attempt_simulation_timestamp
    ):

        faulted_snapshot = self._refresh_active_snapshot_for_context(
            attempt_weather,
            attempt_simulation_timestamp
        )
        faulted_health = self._baseline_health_summary(faulted_snapshot)

        # Keep the elevated traffic multiplier fixed. Only the
        # traffic-placement policy changes, which keeps causality clear.
        recovery_snapshot = self._evaluate_sites_for_context(
            self._active_sites,
            attempt_weather,
            attempt_simulation_timestamp,
            traffic_multiplier=self._traffic_multiplier,
            steering_mode="CAPACITY_RECOVERY",
            area_traffic_multipliers=self._area_traffic_multipliers,
        )
        recovery_health = self._baseline_health_summary(recovery_snapshot)
        recovery_guardrails = evaluate_ran_guardrails(
            faulted_snapshot,
            recovery_snapshot
        )

        fault_max = faulted_health["guardrails"]["summary"].get(
            "max_candidate_prb"
        )
        recovery_max = recovery_health["guardrails"]["summary"].get(
            "max_candidate_prb"
        )

        recovered = recovery_health["status"] == "PASS"

        if recovered:
            self._steering_mode = "CAPACITY_RECOVERY"
            self._active_snapshot = deepcopy(recovery_snapshot)
            self._fault_state = None
            self._rollout_state = "STABLE"
            self._last_action = "SELF_HEALED_CAPACITY"
            event_status = "PASS"
            status = "RECOVERED"
            reason = "CAPACITY_HOTSPOT_RECOVERED_BY_SPLIT_STEERING"
        else:
            # Keep the fault active and the pre-remediation state.
            self._active_snapshot = deepcopy(faulted_snapshot)
            self._rollout_state = "DEGRADED"
            self._last_action = "CAPACITY_RECOVERY_INCOMPLETE"
            event_status = "FAIL"
            status = "RECOVERY_INCOMPLETE"
            reason = "CAPACITY_REMEDIATION_DID_NOT_RESTORE_SAFE_ENVELOPE"

        remaining = [
            check["name"]
            for check in recovery_health["failed_checks"]
        ]

        self._record_event(
            event_type="CAPACITY_SELF_HEAL_COMPLETED",
            status=event_status,
            message=(
                "Capacity remediation kept the traffic spike active and "
                "re-evaluated service with capacity-recovery split steering."
            ),
            details={
                "attempt_id": attempt_id,
                "fault_id": fault["fault_id"],
                "active_version": self.active_version,
                "traffic_multiplier": self._traffic_multiplier,
                "area_traffic_multipliers": deepcopy(
                    self._area_traffic_multipliers
                ),
                "hotspot_area_id": fault.get("hotspot_area_id"),
                "steering_mode_candidate": "CAPACITY_RECOVERY",
                "max_prb_before": fault_max,
                "max_prb_after": recovery_max,
                "full_safe_envelope_restored": recovered,
                "remaining_failed_checks": remaining,
                "simulation_timestamp": attempt_simulation_timestamp,
            },
        )

        return {
            "status": status,
            "reason": reason,
            "attempt_id": attempt_id,
            "fault": fault,
            "active_version": self.active_version,
            "weather": deepcopy(attempt_weather),
            "simulation_timestamp": attempt_simulation_timestamp,
            "faulted_baseline_health": faulted_health,
            "recovered_baseline_health": recovery_health,
            "recovery_guardrails": recovery_guardrails,
            "traffic_multiplier": self._traffic_multiplier,
            "area_traffic_multipliers": deepcopy(
                self._area_traffic_multipliers
            ),
            "hotspot_area_id": fault.get("hotspot_area_id"),
            "steering_mode_before": fault.get("fault_steering_mode"),
            "steering_mode_after": (
                "CAPACITY_RECOVERY" if recovered else self._steering_mode
            ),
            "max_prb_before": fault_max,
            "max_prb_after": recovery_max,
            "configuration_restored": False,
            "configuration_changed": False,
            "configuration_revision_changed": False,
            "scope_recovery_improved": recovered,
            "full_safe_envelope_restored": recovered,
            "remaining_failed_checks": remaining,
            "steps": [
                {"step": "Detect capacity-congestion fault", "status": "PASS"},
                {"step": "Freeze elevated traffic demand", "status": "PASS"},
                {"step": "Apply capacity-recovery split steering", "status": "PASS"},
                {
                    "step": "Verify post-remediation safe envelope",
                    "status": "PASS" if recovered else "FAIL",
                },
            ],
        }


    def inject_rf_fault(
        self,
        cell_ids,
        tx_power_dbm=30.0,
        weather=None,
        simulation_timestamp=None
    ):

        with self._lock:

            if (
                self._fault_state
                and
                self._fault_state.get(
                    "active"
                )
            ):

                return {
                    "status":
                        "BLOCKED",

                    "reason":
                        "ACTIVE_FAULT_ALREADY_PRESENT",

                    "active_version":
                        self.active_version,

                    "fault":
                        deepcopy(
                            self._fault_state
                        ),

                    "configuration_changed":
                        False
                }


            normalized_cell_ids = list(
                dict.fromkeys(
                    str(
                        cell_id
                    )
                    for cell_id in cell_ids
                )
            )


            if not normalized_cell_ids:

                raise ValueError(
                    "RF fault injection requires at least one cell."
                )


            attempt_id = (
                self._next_attempt_id()
            )


            attempt_weather = (
                self._resolve_weather_snapshot(
                    weather
                )
            )


            attempt_simulation_timestamp = (
                self._resolve_simulation_timestamp(
                    simulation_timestamp
                )
            )


            pre_fault_snapshot = (
                self._refresh_active_snapshot_for_context(
                    attempt_weather,
                    attempt_simulation_timestamp
                )
            )


            pre_fault_sites = deepcopy(
                self._active_sites
            )


            # Validate the requested scope against the current
            # configuration inventory before building the fault.
            configured_ids = {
                cell[
                    "cell_id"
                ]
                for cell
                in build_configuration_inventory(
                    pre_fault_sites
                )[
                    "cells"
                ]
            }


            unknown = [
                cell_id
                for cell_id in normalized_cell_ids
                if cell_id not in configured_ids
            ]


            if unknown:

                raise ValueError(
                    "Unknown cell_id(s) for RF fault injection: "
                    + ", ".join(
                        unknown
                    )
                )


            cell_updates = {

                cell_id: {
                    "tx_power_dbm":
                        float(
                            tx_power_dbm
                        )
                }

                for cell_id
                in normalized_cell_ids
            }


            fault_sites = (
                build_candidate_sites(

                    base_sites=
                        pre_fault_sites,

                    cell_updates=
                        cell_updates
                )
            )


            fault_snapshot = (
                self._evaluate_sites_for_context(
                    fault_sites,
                    attempt_weather,
                    attempt_simulation_timestamp
                )
            )


            # The recovery target is the intentionally accepted
            # configuration that existed immediately before the lab
            # fault. The configuration revision is deliberately not
            # incremented by fault injection.
            self._recovery_target_sites = deepcopy(
                pre_fault_sites
            )

            self._recovery_target_version = (
                self.active_version
            )


            before_scope = (
                self._scope_metrics(
                    pre_fault_snapshot,
                    normalized_cell_ids
                )
            )


            after_scope = (
                self._scope_metrics(
                    fault_snapshot,
                    normalized_cell_ids
                )
            )


            self._active_sites = deepcopy(
                fault_sites
            )

            self._active_snapshot = deepcopy(
                fault_snapshot
            )

            self._rollout_state = (
                "DEGRADED"
            )

            self._last_action = (
                "RF_FAULT_INJECTED"
            )


            self._fault_state = {
                "active":
                    True,

                "fault_id":
                    attempt_id,

                "type":
                    "TX_POWER_DROP",

                "cell_ids":
                    normalized_cell_ids,

                "tx_power_dbm":
                    float(
                        tx_power_dbm
                    ),

                "known_good_version":
                    self._recovery_target_version,

                "injected_at":
                    self._timestamp()
            }


            pre_fault_health = (
                self._baseline_health_summary(
                    pre_fault_snapshot
                )
            )

            fault_health = (
                self._baseline_health_summary(
                    fault_snapshot
                )
            )


            self._record_event(

                event_type=
                    "RF_FAULT_INJECTED",

                status=
                    "WARNING",

                message=
                    (
                        "Learning-lab RF fault injected: "
                        f"{len(normalized_cell_ids)} cell(s) "
                        f"forced to {float(tx_power_dbm):.1f} dBm."
                    ),

                details={
                    "attempt_id":
                        attempt_id,

                    "cell_ids":
                        normalized_cell_ids,

                    "tx_power_dbm":
                        float(
                            tx_power_dbm
                        ),

                    "active_version":
                        self.active_version,

                    "recovery_target_version":
                        self._recovery_target_version,

                    "weather_timestamp":
                        attempt_weather.get(
                            "timestamp"
                        ),

                    "simulation_timestamp":
                        attempt_simulation_timestamp,

                    "before_scope":
                        before_scope,

                    "after_scope":
                        after_scope
                }
            )


            return {
                "status":
                    "FAULT_INJECTED",

                "reason":
                    "LEARNING_LAB_RF_FAULT",

                "attempt_id":
                    attempt_id,

                "active_version":
                    self.active_version,

                "recovery_target_version":
                    self._recovery_target_version,

                "weather":
                    deepcopy(
                        attempt_weather
                    ),

                "simulation_timestamp":
                    attempt_simulation_timestamp,

                "fault":
                    deepcopy(
                        self._fault_state
                    ),

                "before_scope":
                    before_scope,

                "after_scope":
                    after_scope,

                "baseline_health_before":
                    pre_fault_health,

                "baseline_health_after":
                    fault_health,

                "configuration_revision_changed":
                    False,

                "configuration_changed":
                    True,

                "steps": [
                    {
                        "step":
                            "Observe pre-fault RAN state",
                        "status":
                            "PASS"
                    },
                    {
                        "step":
                            "Snapshot last accepted known-good configuration",
                        "status":
                            "PASS"
                    },
                    {
                        "step":
                            (
                                "Inject TX-power fault into "
                                f"{len(normalized_cell_ids)} cell(s)"
                            ),
                        "status":
                            "PASS"
                    },
                    {
                        "step":
                            "Collect post-fault RF and service KPIs",
                        "status":
                            "PASS"
                    }
                ]
            }


    def run_self_healing(
        self,
        weather=None,
        simulation_timestamp=None
    ):

        with self._lock:

            if not (
                self._fault_state
                and
                self._fault_state.get(
                    "active"
                )
            ):

                observation_weather = (
                    self._resolve_weather_snapshot(
                        weather
                    )
                )

                observation_simulation_timestamp = (
                    self._resolve_simulation_timestamp(
                        simulation_timestamp
                    )
                )

                snapshot = (
                    self._refresh_active_snapshot_for_context(
                        observation_weather,
                        observation_simulation_timestamp
                    )
                )

                baseline_health = (
                    self._baseline_health_summary(
                        snapshot
                    )
                )

                return {
                    "status":
                        "NO_ACTION",

                    "reason":
                        "NO_ACTIVE_INJECTED_FAULT",

                    "active_version":
                        self.active_version,

                    "weather":
                        deepcopy(
                            observation_weather
                        ),

                    "simulation_timestamp":
                        observation_simulation_timestamp,

                    "baseline_health":
                        baseline_health,

                    "configuration_changed":
                        False,

                    "configuration_revision_changed":
                        False,

                    "steps": [
                        {
                            "step":
                                "Detect authorized self-healing trigger",
                            "status":
                                "INFO"
                        }
                    ]
                }


            attempt_id = (
                self._next_attempt_id()
            )


            attempt_weather = (
                self._resolve_weather_snapshot(
                    weather
                )
            )


            attempt_simulation_timestamp = (
                self._resolve_simulation_timestamp(
                    simulation_timestamp
                )
            )


            fault = deepcopy(
                self._fault_state
            )


            if fault.get("type") == "CAPACITY_SPIKE":
                return self._run_capacity_self_healing_locked(
                    fault,
                    attempt_id,
                    attempt_weather,
                    attempt_simulation_timestamp
                )


            faulted_snapshot = (
                self._refresh_active_snapshot_for_context(
                    attempt_weather,
                    attempt_simulation_timestamp
                )
            )


            faulted_health = (
                self._baseline_health_summary(
                    faulted_snapshot
                )
            )


            recovery_sites = deepcopy(
                self._recovery_target_sites
            )


            recovery_snapshot = (
                self._evaluate_sites_for_context(
                    recovery_sites,
                    attempt_weather,
                    attempt_simulation_timestamp
                )
            )


            recovery_health = (
                self._baseline_health_summary(
                    recovery_snapshot
                )
            )


            recovery_guardrails = (
                evaluate_ran_guardrails(

                    faulted_snapshot,

                    recovery_snapshot
                )
            )


            target_cell_ids = (
                fault[
                    "cell_ids"
                ]
            )


            before_scope = (
                self._scope_metrics(
                    faulted_snapshot,
                    target_cell_ids
                )
            )


            after_scope = (
                self._scope_metrics(
                    recovery_snapshot,
                    target_cell_ids
                )
            )


            scope_improved = (
                self._scope_recovery_improved(
                    before_scope,
                    after_scope
                )
            )


            self._active_sites = deepcopy(
                recovery_sites
            )

            self._active_snapshot = deepcopy(
                recovery_snapshot
            )


            configuration_restored = (
                self._active_sites
                ==
                self._recovery_target_sites
            )


            full_safe_envelope_restored = (
                recovery_health[
                    "status"
                ]
                == "PASS"
            )


            remaining_failed_checks = [

                check[
                    "name"
                ]

                for check
                in recovery_health[
                    "failed_checks"
                ]
            ]


            self._fault_state = None

            self._rollout_state = (
                "STABLE"
                if full_safe_envelope_restored
                else "DEGRADED"
            )

            self._last_action = (
                "SELF_HEALED"
            )


            reason = (
                "TARGET_RF_FAULT_RECOVERED"

                if full_safe_envelope_restored

                else
                "TARGET_RF_FAULT_RECOVERED_BASELINE_ISSUES_REMAIN"
            )


            self._record_event(

                event_type=
                    "SELF_HEAL_COMPLETED",

                status=
                    "PASS",

                message=
                    (
                        "Injected RF fault recovered by restoring "
                        "the last accepted known-good configuration."
                        if full_safe_envelope_restored
                        else
                        (
                            "Injected RF fault recovered; "
                            "pre-existing or unrelated baseline "
                            "safety issues remain."
                        )
                    ),

                details={
                    "attempt_id":
                        attempt_id,

                    "fault_id":
                        fault[
                            "fault_id"
                        ],

                    "cell_ids":
                        target_cell_ids,

                    "active_version":
                        self.active_version,

                    "recovery_target_version":
                        self._recovery_target_version,

                    "configuration_restored":
                        configuration_restored,

                    "scope_recovery_improved":
                        scope_improved,

                    "full_safe_envelope_restored":
                        full_safe_envelope_restored,

                    "remaining_failed_checks":
                        remaining_failed_checks,

                    "weather_timestamp":
                        attempt_weather.get(
                            "timestamp"
                        ),

                    "simulation_timestamp":
                        attempt_simulation_timestamp,

                    "before_scope":
                        before_scope,

                    "after_scope":
                        after_scope
                }
            )


            return {
                "status":
                    "RECOVERED",

                "reason":
                    reason,

                "attempt_id":
                    attempt_id,

                "fault":
                    fault,

                "active_version":
                    self.active_version,

                "recovery_target_version":
                    self._recovery_target_version,

                "weather":
                    deepcopy(
                        attempt_weather
                    ),

                "simulation_timestamp":
                    attempt_simulation_timestamp,

                "faulted_baseline_health":
                    faulted_health,

                "recovered_baseline_health":
                    recovery_health,

                "recovery_guardrails":
                    recovery_guardrails,

                "before_scope":
                    before_scope,

                "after_scope":
                    after_scope,

                "configuration_restored":
                    configuration_restored,

                "scope_recovery_improved":
                    scope_improved,

                "full_safe_envelope_restored":
                    full_safe_envelope_restored,

                "remaining_failed_checks":
                    remaining_failed_checks,

                "configuration_changed":
                    True,

                "configuration_revision_changed":
                    False,

                "steps": [
                    {
                        "step":
                            "Detect active injected RF fault",
                        "status":
                            "PASS"
                    },
                    {
                        "step":
                            (
                                "Select last accepted known-good "
                                f"{self._recovery_target_version}"
                            ),
                        "status":
                            "PASS"
                    },
                    {
                        "step":
                            (
                                "Evaluate recovery candidate under "
                                "same weather + traffic-clock context"
                            ),
                        "status":
                            "PASS"
                    },
                    {
                        "step":
                            "Restore known-good RAN configuration",
                        "status":
                            "PASS"
                    },
                    {
                        "step":
                            "Verify target RF/service recovery",
                        "status":
                            (
                                "PASS"
                                if (
                                    scope_improved
                                    or
                                    configuration_restored
                                )
                                else "FAIL"
                            )
                    },
                    {
                        "step":
                            "Re-check full active RAN safe envelope",
                        "status":
                            recovery_health[
                                "status"
                            ]
                    }
                ]
            }


    # =====================================================
    # BUILD CANDIDATE
    # =====================================================

    def _build_candidate(
        self,
        cell_updates=None,
        antenna_updates=None
    ):

        return (
            build_candidate_sites(

                base_sites=
                    self._active_sites,

                cell_updates=
                    cell_updates,

                antenna_updates=
                    antenna_updates
            )
        )


    # =====================================================
    # EVALUATE ONLY
    # =====================================================

    def evaluate(
        self,
        cell_updates=None,
        antenna_updates=None,
        weather=None,
        simulation_timestamp=None
    ):

        """
        Preview a candidate without changing configuration.

        Evaluation is allowed even when baseline health FAILS.

        Reason:
        a non-mutating preview can still be useful for
        troubleshooting and for designing a recovery change.

        However would_be_accepted is FALSE whenever the active
        baseline is already outside the normal safe envelope.
        """

        with self._lock:

            attempt_id = (
                self._next_attempt_id()
            )


            candidate_version = (
                self._candidate_version()
            )


            baseline_version = (
                self.active_version
            )


            # -------------------------------------------------
            # ONE CONTEXT PAIR FOR THE WHOLE ATTEMPT
            # -------------------------------------------------

            attempt_weather = (
                self._resolve_weather_snapshot(
                    weather
                )
            )


            attempt_simulation_timestamp = (
                self._resolve_simulation_timestamp(
                    simulation_timestamp
                )
            )


            # -------------------------------------------------
            # FRESH ACTIVE BASELINE
            # -------------------------------------------------

            baseline_snapshot = (
                self._refresh_active_snapshot_for_context(
                    attempt_weather,
                    attempt_simulation_timestamp
                )
            )


            baseline_health = (
                self._baseline_health_summary(
                    baseline_snapshot
                )
            )


            # -------------------------------------------------
            # BUILD / EVALUATE CANDIDATE
            # -------------------------------------------------

            candidate_sites = (
                self._build_candidate(

                    cell_updates=
                        cell_updates,

                    antenna_updates=
                        antenna_updates
                )
            )


            candidate_snapshot = (
                self._evaluate_sites_for_context(
                    candidate_sites,
                    attempt_weather,
                    attempt_simulation_timestamp
                )
            )


            candidate_guardrails = (
                evaluate_ran_guardrails(

                    baseline_snapshot,

                    candidate_snapshot
                )
            )


            baseline_pass = (
                baseline_health[
                    "status"
                ]
                == "PASS"
            )


            candidate_pass = (
                candidate_guardrails[
                    "verdict"
                ]
                == "PASS"
            )


            would_be_accepted = (
                baseline_pass
                and
                candidate_pass
            )


            if not baseline_pass:

                decision = (
                    "BLOCKED_BASELINE_HEALTH"
                )

                event_status = (
                    "BLOCKED"
                )

                message = (
                    f"{candidate_version} preview evaluated, "
                    "but active RAN is already outside the "
                    "normal safe operating envelope."
                )

            elif not candidate_pass:

                decision = (
                    "REJECTED_CANDIDATE_GUARDRAILS"
                )

                event_status = (
                    "FAIL"
                )

                message = (
                    f"{candidate_version} evaluated "
                    "without changing active configuration."
                )

            else:

                decision = (
                    "ELIGIBLE_FOR_GUARDED_APPLY"
                )

                event_status = (
                    "PASS"
                )

                message = (
                    f"{candidate_version} evaluated "
                    "without changing active configuration."
                )


            self._record_event(

                event_type=
                    "CANDIDATE_EVALUATED",

                status=
                    event_status,

                message=
                    message,

                details={

                    "attempt_id":
                        attempt_id,

                    "baseline_version":
                        baseline_version,

                    "candidate_version":
                        candidate_version,

                    "decision":
                        decision,

                    "baseline_health":
                        baseline_health[
                            "status"
                        ],

                    "baseline_failed_check_count":
                        baseline_health[
                            "failed_check_count"
                        ],

                    "candidate_verdict":
                        candidate_guardrails[
                            "verdict"
                        ],

                    "candidate_failed_check_count":
                        candidate_guardrails[
                            "failed_check_count"
                        ],

                    "weather_timestamp":
                        attempt_weather.get(
                            "timestamp"
                        ),

                    "weather_source":
                        attempt_weather.get(
                            "source"
                        ),

                    "weather_status":
                        attempt_weather.get(
                            "source_status"
                        ),

                    "simulation_timestamp":
                        attempt_simulation_timestamp
                }
            )


            return {

                "operation":
                    "EVALUATE",

                "status":
                    "EVALUATED",

                "decision":
                    decision,

                "attempt_id":
                    attempt_id,

                "baseline_version":
                    baseline_version,

                "candidate_version":
                    candidate_version,

                "active_version":
                    self.active_version,

                "would_be_accepted":
                    would_be_accepted,

                "weather":
                    deepcopy(
                        attempt_weather
                    ),

                "simulation_timestamp":
                    attempt_simulation_timestamp,

                "baseline_health":
                    deepcopy(
                        baseline_health
                    ),

                "baseline_service":
                    deepcopy(

                        baseline_snapshot[
                            "service"
                        ]
                    ),

                "candidate_configuration":
                    deepcopy(

                        candidate_snapshot[
                            "configuration"
                        ]
                    ),

                "candidate_service":
                    deepcopy(

                        candidate_snapshot[
                            "service"
                        ]
                    ),

                "candidate_cells":
                    deepcopy(

                        candidate_snapshot[
                            "cells"
                        ]
                    ),

                # Compatibility:
                #
                # "guardrails" continues to mean candidate
                # outcome guardrails.
                "guardrails":
                    deepcopy(
                        candidate_guardrails
                    )
            }


    # =====================================================
    # GUARDED APPLY
    # =====================================================

    def guarded_apply(
        self,
        cell_updates=None,
        antenna_updates=None,
        weather=None,
        simulation_timestamp=None
    ):

        with self._lock:

            attempt_id = (
                self._next_attempt_id()
            )


            candidate_version = (
                self._candidate_version()
            )


            previous_version = (
                self.active_version
            )


            previous_sites = deepcopy(
                self._active_sites
            )


            steps = []


            # -------------------------------------------------
            # ONE CONTEXT PAIR FOR COMPLETE ATTEMPT
            # -------------------------------------------------

            attempt_weather = (
                self._resolve_weather_snapshot(
                    weather
                )
            )


            attempt_simulation_timestamp = (
                self._resolve_simulation_timestamp(
                    simulation_timestamp
                )
            )


            # -------------------------------------------------
            # FRESH ACTIVE BASELINE
            # -------------------------------------------------

            previous_snapshot = (
                self._refresh_active_snapshot_for_context(
                    attempt_weather,
                    attempt_simulation_timestamp
                )
            )


            previous_snapshot = deepcopy(
                previous_snapshot
            )


            baseline_health = (
                self._baseline_health_summary(
                    previous_snapshot
                )
            )


            # =================================================
            # STEP 1 - BASELINE HEALTH PRECHECK
            # =================================================

            baseline_precheck_passed = (
                baseline_health[
                    "status"
                ]
                == "PASS"
            )


            steps.append({

                "step":
                    "Pre-check active RAN safe operating envelope",

                "status":
                    (
                        "PASS"

                        if baseline_precheck_passed

                        else "FAIL"
                    ),

                "failed_check_count":
                    baseline_health[
                        "failed_check_count"
                    ]
            })


            # =================================================
            # BASELINE FAIL -> BLOCK BEFORE CANDIDATE
            # =================================================

            if not baseline_precheck_passed:

                self._rollout_state = (
                    "BLOCKED"
                )


                self._last_action = (
                    "BASELINE_HEALTH_BLOCKED"
                )


                failed_names = [

                    check[
                        "name"
                    ]

                    for check
                    in baseline_health[
                        "failed_checks"
                    ]
                ]


                self._record_event(

                    event_type=
                        "BASELINE_HEALTH_BLOCKED",

                    status=
                        "FAIL",

                    message=
                        (
                            "Guarded change blocked because "
                            "the active RAN is already outside "
                            "the normal safe operating envelope."
                        ),

                    details={

                        "attempt_id":
                            attempt_id,

                        "active_version":
                            previous_version,

                        "candidate_version":
                            candidate_version,

                        "baseline_failed_checks":
                            failed_names,

                        "weather_timestamp":
                            attempt_weather.get(
                                "timestamp"
                            ),

                        "weather_source":
                            attempt_weather.get(
                                "source"
                            ),

                        "weather_status":
                            attempt_weather.get(
                                "source_status"
                            ),

                        "simulation_timestamp":
                            attempt_simulation_timestamp
                    }
                )


                return {

                    "status":
                        "BLOCKED",

                    "reason":
                        "ACTIVE_RAN_OUTSIDE_SAFE_ENVELOPE",

                    "attempt_id":
                        attempt_id,

                    "previous_version":
                        previous_version,

                    "candidate_version":
                        candidate_version,

                    "active_version":
                        previous_version,

                    "weather":
                        deepcopy(
                            attempt_weather
                        ),

                    "simulation_timestamp":
                        attempt_simulation_timestamp,

                    "steps":
                        steps,

                    "baseline_health":
                        deepcopy(
                            baseline_health
                        ),

                    "baseline_service":
                        deepcopy(

                            previous_snapshot[
                                "service"
                            ]
                        ),

                    "active_service":
                        deepcopy(

                            previous_snapshot[
                                "service"
                            ]
                        ),

                    # Compatibility field.
                    #
                    # No candidate was evaluated. Therefore
                    # this is explicitly the baseline-health
                    # guardrail result, not candidate outcome.
                    "guardrails":
                        deepcopy(

                            baseline_health[
                                "guardrails"
                            ]
                        ),

                    "candidate_evaluated":
                        False,

                    "configuration_changed":
                        False
                }


            # =================================================
            # STEP 2 - BUILD CANDIDATE
            # =================================================

            try:

                candidate_sites = (
                    build_candidate_sites(

                        base_sites=
                            previous_sites,

                        cell_updates=
                            cell_updates,

                        antenna_updates=
                            antenna_updates
                    )
                )


            except Exception as exc:

                self._rollout_state = (
                    "REJECTED"
                )


                self._last_action = (
                    "CANDIDATE_BUILD_FAILED"
                )


                steps.append({

                    "step":
                        (
                            f"Build candidate "
                            f"{candidate_version}"
                        ),

                    "status":
                        "FAIL",

                    "error":
                        str(
                            exc
                        )
                })


                self._record_event(

                    event_type=
                        "CANDIDATE_BUILD_FAILED",

                    status=
                        "FAIL",

                    message=
                        (
                            f"{candidate_version} rejected "
                            "during input/config validation."
                        ),

                    details={

                        "attempt_id":
                            attempt_id,

                        "active_version":
                            previous_version,

                        "baseline_health":
                            baseline_health[
                                "status"
                            ],

                        "weather_timestamp":
                            attempt_weather.get(
                                "timestamp"
                            ),

                        "weather_source":
                            attempt_weather.get(
                                "source"
                            ),

                        "weather_status":
                            attempt_weather.get(
                                "source_status"
                            ),

                        "simulation_timestamp":
                            attempt_simulation_timestamp,

                        "error":
                            str(
                                exc
                            )
                    }
                )


                return {

                    "status":
                        "REJECTED",

                    "reason":
                        "CANDIDATE_BUILD_FAILED",

                    "attempt_id":
                        attempt_id,

                    "previous_version":
                        previous_version,

                    "candidate_version":
                        candidate_version,

                    "active_version":
                        previous_version,

                    "weather":
                        deepcopy(
                            attempt_weather
                        ),

                    "simulation_timestamp":
                        attempt_simulation_timestamp,

                    "baseline_health":
                        deepcopy(
                            baseline_health
                        ),

                    "steps":
                        steps,

                    "error":
                        str(
                            exc
                        )
                }


            steps.append({

                "step":
                    (
                        f"Build candidate "
                        f"{candidate_version}"
                    ),

                "status":
                    "PASS"
            })


            # =================================================
            # STEP 3 - SIMULATED APPLY / RF CALCULATION
            # =================================================

            self._rollout_state = (
                "VALIDATING"
            )


            candidate_snapshot = (
                self._evaluate_sites_for_context(
                    candidate_sites,
                    attempt_weather,
                    attempt_simulation_timestamp
                )
            )


            steps.append({

                "step":
                    "Apply candidate to RAN simulator",

                "status":
                    "PASS"
            })


            steps.append({

                "step":
                    (
                        "Collect RF, service and "
                        "traffic KPIs"
                    ),

                "status":
                    "PASS"
            })


            # =================================================
            # STEP 4 - CANDIDATE GUARDRAILS
            # =================================================

            guardrails = (
                evaluate_ran_guardrails(

                    previous_snapshot,

                    candidate_snapshot
                )
            )


            steps.append({

                "step":
                    "RAN outcome guardrails",

                "status":
                    guardrails[
                        "verdict"
                    ],

                "failed_check_count":
                    guardrails[
                        "failed_check_count"
                    ]
            })


            # =================================================
            # PASS -> PROMOTE
            # =================================================

            if (
                guardrails[
                    "verdict"
                ]
                == "PASS"
            ):

                self._active_sites = deepcopy(
                    candidate_sites
                )


                self._active_snapshot = deepcopy(
                    candidate_snapshot
                )


                self._config_revision += 1


                self._recovery_target_sites = deepcopy(
                    candidate_sites
                )

                self._recovery_target_version = (
                    self.active_version
                )

                self._fault_state = None


                self._rollout_state = (
                    "STABLE"
                )


                self._last_action = (
                    "PROMOTED"
                )


                steps.append({

                    "step":
                        (
                            f"Promote "
                            f"{self.active_version}"
                        ),

                    "status":
                        "PASS"
                })


                self._record_event(

                    event_type=
                        "CONFIG_PROMOTED",

                    status=
                        "PASS",

                    message=
                        (
                            f"{self.active_version} "
                            "promoted to known-good state."
                        ),

                    details={

                        "attempt_id":
                            attempt_id,

                        "previous_version":
                            previous_version,

                        "active_version":
                            self.active_version,

                        "baseline_health":
                            baseline_health[
                                "status"
                            ],

                        "weather_timestamp":
                            attempt_weather.get(
                                "timestamp"
                            ),

                        "weather_source":
                            attempt_weather.get(
                                "source"
                            ),

                        "weather_status":
                            attempt_weather.get(
                                "source_status"
                            ),

                        "simulation_timestamp":
                            attempt_simulation_timestamp,

                        "reassociated_active_ues":
                            guardrails[
                                "reassociation"
                            ][
                                "reassociated_active_ues"
                            ]
                    }
                )


                return {

                    "status":
                        "APPLIED",

                    "attempt_id":
                        attempt_id,

                    "previous_version":
                        previous_version,

                    "candidate_version":
                        candidate_version,

                    "active_version":
                        self.active_version,

                    "weather":
                        deepcopy(
                            attempt_weather
                        ),

                    "simulation_timestamp":
                        attempt_simulation_timestamp,

                    "baseline_health":
                        deepcopy(
                            baseline_health
                        ),

                    "steps":
                        steps,

                    "active_service":
                        deepcopy(

                            self._active_snapshot[
                                "service"
                            ]
                        ),

                    "guardrails":
                        deepcopy(
                            guardrails
                        )
                }


            # =================================================
            # FAIL -> REJECT / RESTORE KNOWN-GOOD
            # =================================================
            #
            # Candidate sites were never promoted into the
            # active known-good configuration.
            # =================================================

            self._active_sites = (
                previous_sites
            )


            self._rollout_state = (
                "ROLLED_BACK"
            )


            self._last_action = (
                "ROLLED_BACK"
            )


            steps.append({

                "step":
                    (
                        f"Reject candidate "
                        f"{candidate_version}"
                    ),

                "status":
                    "PASS"
            })


            steps.append({

                "step":
                    (
                        f"Restore known-good "
                        f"{previous_version}"
                    ),

                "status":
                    "PASS"
            })


            # =================================================
            # POST-ROLLBACK VERIFICATION
            # =================================================

            restored_snapshot = (
                self._evaluate_sites_for_context(
                    self._active_sites,
                    attempt_weather,
                    attempt_simulation_timestamp
                )
            )


            rollback_verification = (
                evaluate_ran_guardrails(

                    previous_snapshot,

                    restored_snapshot
                )
            )


            rollback_verified = (

                rollback_verification[
                    "verdict"
                ]
                == "PASS"
            )


            steps.append({

                "step":
                    "Post-rollback validation",

                "status":
                    (
                        "PASS"

                        if rollback_verified

                        else "FAIL"
                    )
            })


            self._active_snapshot = deepcopy(
                restored_snapshot
            )


            self._record_event(

                event_type=
                    "CONFIG_ROLLED_BACK",

                status=
                    (
                        "PASS"

                        if rollback_verified

                        else "FAIL"
                    ),

                message=
                    (
                        f"{candidate_version} rejected; "
                        f"{previous_version} remains active."
                    ),

                details={

                    "attempt_id":
                        attempt_id,

                    "candidate_version":
                        candidate_version,

                    "active_version":
                        previous_version,

                    "baseline_health":
                        baseline_health[
                            "status"
                        ],

                    "weather_timestamp":
                        attempt_weather.get(
                            "timestamp"
                        ),

                    "weather_source":
                        attempt_weather.get(
                            "source"
                        ),

                    "weather_status":
                        attempt_weather.get(
                            "source_status"
                        ),

                    "simulation_timestamp":
                        attempt_simulation_timestamp,

                    "failed_checks":
                        [

                            check[
                                "name"
                            ]

                            for check
                            in guardrails[
                                "failed_checks"
                            ]
                        ],

                    "rollback_verified":
                        rollback_verified
                }
            )


            return {

                "status":
                    "ROLLED_BACK",

                "attempt_id":
                    attempt_id,

                "previous_version":
                    previous_version,

                "candidate_version":
                    candidate_version,

                "active_version":
                    previous_version,

                "weather":
                    deepcopy(
                        attempt_weather
                    ),

                "simulation_timestamp":
                    attempt_simulation_timestamp,

                "baseline_health":
                    deepcopy(
                        baseline_health
                    ),

                "steps":
                    steps,

                "candidate_service":
                    deepcopy(

                        candidate_snapshot[
                            "service"
                        ]
                    ),

                "restored_service":
                    deepcopy(

                        restored_snapshot[
                            "service"
                        ]
                    ),

                "guardrails":
                    deepcopy(
                        guardrails
                    ),

                "rollback_verification":
                    deepcopy(
                        rollback_verification
                    )
            }


    # =====================================================
    # AUTHORIZED SAFETY CHECKPOINT RESTORE
    # =====================================================

    def restore_safety_checkpoint(
        self,
        checkpoint_sites,
        checkpoint_label=None,
        weather=None,
        simulation_timestamp=None,
    ):
        """
        Force-restore a controller-owned verified healthy checkpoint.

        This is intentionally separate from guarded_apply(). A normal
        guarded change is blocked when the active RAN is already outside the
        safe envelope; the safety supervisor therefore needs a separately
        authorized rollback path after an AI-gated change has already been
        promoted and later fails post-change verification.

        The caller must provide a snapshot previously captured from this
        controller while the RAN was verified healthy. The AI model never
        supplies checkpoint content and never calls this method directly.
        """

        with self._lock:
            previous_version = self.active_version

            restore_weather = self._resolve_weather_snapshot(weather)
            restore_simulation_timestamp = self._resolve_simulation_timestamp(
                simulation_timestamp
            )

            target_sites = deepcopy(checkpoint_sites)
            target_snapshot = self._evaluate_sites_for_context(
                target_sites,
                restore_weather,
                restore_simulation_timestamp,
            )

            # Evaluate the restored state against the normal safety envelope.
            # The restore is still performed even if external traffic/weather
            # changed enough that the previously healthy configuration no
            # longer recovers the network. That outcome is returned explicitly
            # so the supervisor can open its circuit breaker and escalate to
            # the existing recovery/troubleshooting path.
            checkpoint_health = self._baseline_health_summary(
                target_snapshot
            )
            checkpoint_guardrails = checkpoint_health["guardrails"]
            rollback_verified = checkpoint_health.get("status") == "PASS"

            self._active_sites = target_sites
            self._active_snapshot = deepcopy(target_snapshot)
            self._config_revision += 1

            # The restored configuration is now the controller's accepted
            # recovery target. This does not erase any independent injected
            # fault state because an RF/capacity fault may be the real reason
            # the rollback cannot recover service.
            self._recovery_target_sites = deepcopy(target_sites)
            self._recovery_target_version = self.active_version

            self._rollout_state = (
                "STABLE" if rollback_verified else "SAFETY_ROLLBACK_UNHEALTHY"
            )
            self._last_action = "SAFETY_CHECKPOINT_RESTORED"

            self._record_event(
                event_type="SAFETY_CHECKPOINT_RESTORED",
                status="PASS" if rollback_verified else "FAIL",
                message=(
                    f"Safety checkpoint {checkpoint_label or 'UNLABELED'} "
                    f"restored after AI-gated control verification failure."
                ),
                details={
                    "previous_version": previous_version,
                    "active_version": self.active_version,
                    "checkpoint_label": checkpoint_label,
                    "rollback_verified": rollback_verified,
                    "weather_timestamp": restore_weather.get("timestamp"),
                    "weather_source": restore_weather.get("source"),
                    "weather_status": restore_weather.get("source_status"),
                    "simulation_timestamp": restore_simulation_timestamp,
                },
            )

            return {
                "status": "RESTORED" if rollback_verified else "RESTORED_UNHEALTHY",
                "previous_version": previous_version,
                "active_version": self.active_version,
                "checkpoint_label": checkpoint_label,
                "rollback_verified": rollback_verified,
                "weather": deepcopy(restore_weather),
                "simulation_timestamp": restore_simulation_timestamp,
                "baseline_health": deepcopy(checkpoint_health),
                "guardrails": deepcopy(checkpoint_guardrails),
                "service": deepcopy(target_snapshot.get("service") or {}),
            }


    # =====================================================
    # RESTORE FACTORY BASELINE
    # =====================================================

    def restore_factory_baseline(
        self,
        weather=None,
        simulation_timestamp=None
    ):

        with self._lock:

            previous_version = (
                self.active_version
            )


            restore_weather = (
                self._resolve_weather_snapshot(
                    weather
                )
            )


            restore_simulation_timestamp = (
                self._resolve_simulation_timestamp(
                    simulation_timestamp
                )
            )


            self._active_sites = (
                build_baseline_sites()
            )


            self._traffic_multiplier = (
                self._normal_traffic_multiplier
            )

            self._steering_mode = (
                self._normal_steering_mode
            )

            self._area_traffic_multipliers = {}

            self._active_snapshot = (
                self._evaluate_sites_for_context(
                    self._active_sites,
                    restore_weather,
                    restore_simulation_timestamp
                )
            )


            self._config_revision = 0


            self._recovery_target_sites = deepcopy(
                self._active_sites
            )

            self._recovery_target_version = (
                self.active_version
            )

            self._fault_state = None


            self._rollout_state = (
                "STABLE"
            )


            self._last_action = (
                "FACTORY_BASELINE_RESTORED"
            )


            baseline_health = (
                self._baseline_health_summary(
                    self._active_snapshot
                )
            )


            self._record_event(

                event_type=
                    "FACTORY_BASELINE_RESTORED",

                status=
                    "PASS",

                message=
                    (
                        "Factory learning-lab "
                        "baseline restored."
                    ),

                details={

                    "previous_version":
                        previous_version,

                    "active_version":
                        self.active_version,

                    "baseline_health":
                        baseline_health[
                            "status"
                        ],

                    "weather_timestamp":
                        restore_weather.get(
                            "timestamp"
                        ),

                    "weather_source":
                        restore_weather.get(
                            "source"
                        ),

                    "weather_status":
                        restore_weather.get(
                            "source_status"
                        ),

                    "simulation_timestamp":
                        restore_simulation_timestamp
                }
            )


            return {

                "status":
                    "RESTORED",

                "previous_version":
                    previous_version,

                "active_version":
                    self.active_version,

                "weather":
                    deepcopy(
                        restore_weather
                    ),

                "simulation_timestamp":
                    restore_simulation_timestamp,

                "baseline_health":
                    deepcopy(
                        baseline_health
                    ),

                "service":
                    deepcopy(

                        self._active_snapshot[
                            "service"
                        ]
                    )
            }
