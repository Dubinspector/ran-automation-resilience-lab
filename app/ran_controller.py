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

A production system could later add a separately authorized recovery
workflow for changes intended specifically to remediate an unhealthy
baseline.

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
        simulation_timestamp=None
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


        initial_weather = (
            self._resolve_weather_snapshot()
        )


        initial_simulation_timestamp = (
            self._resolve_simulation_timestamp(
                simulation_timestamp
            )
        )


        self._active_snapshot = (
            evaluate_ran_state(

                self._active_sites,

                weather=
                    initial_weather,

                simulation_timestamp=
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
                    initial_simulation_timestamp
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
            evaluate_ran_state(

                self._active_sites,

                weather=
                    weather,

                simulation_timestamp=
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
                evaluate_ran_state(

                    candidate_sites,

                    weather=
                        attempt_weather,

                    simulation_timestamp=
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
                evaluate_ran_state(

                    candidate_sites,

                    weather=
                        attempt_weather,

                    simulation_timestamp=
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
                evaluate_ran_state(

                    self._active_sites,

                    weather=
                        attempt_weather,

                    simulation_timestamp=
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


            self._active_snapshot = (
                evaluate_ran_state(

                    self._active_sites,

                    weather=
                        restore_weather,

                    simulation_timestamp=
                        restore_simulation_timestamp
                )
            )


            self._config_revision = 0


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
