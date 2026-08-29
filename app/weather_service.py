"""
Live weather service for the RAN automation learning lab.

The service retrieves current weather for the Jesenice
scenario from Open-Meteo and normalizes it into the weather
dictionary expected by the RF model.

Important design goals:

1. Weather is environmental RF input, not a direct reason
   to change RAN configuration.

2. The same normalized snapshot can later be passed through:

       weather
           -> RF model
           -> UE association
           -> traffic / PRB
           -> guardrails

3. Successful Open-Meteo responses are cached for 10 minutes.

4. If Open-Meteo becomes unavailable:
   - use the last successful snapshot when available;
   - otherwise use the recorded learning-lab fallback.

5. Rain returned by Open-Meteo is an accumulated amount over
   the response interval. It is converted into mm/hour before
   being passed into the RF rain-attenuation model.
"""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
import os
from threading import RLock
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen


# =========================================================
# LOCATION
# =========================================================
#
# Scenario centre:
# Jesenice u Prahy
#
# Coordinates can be overridden through environment
# variables if we later want to reuse the service for
# another synthetic scenario.
# =========================================================

WEATHER_LATITUDE = float(
    os.getenv(
        "WEATHER_LATITUDE",
        "49.96876",
    )
)

WEATHER_LONGITUDE = float(
    os.getenv(
        "WEATHER_LONGITUDE",
        "14.51581",
    )
)

WEATHER_LOCATION_NAME = os.getenv(
    "WEATHER_LOCATION_NAME",
    "Jesenice u Prahy",
)

WEATHER_TIMEZONE = os.getenv(
    "WEATHER_TIMEZONE",
    "Europe/Prague",
)


# =========================================================
# CACHE / NETWORK POLICY
# =========================================================

WEATHER_CACHE_TTL_SECONDS = int(
    os.getenv(
        "WEATHER_CACHE_TTL_SECONDS",
        "600",
    )
)

WEATHER_HTTP_TIMEOUT_SECONDS = float(
    os.getenv(
        "WEATHER_HTTP_TIMEOUT_SECONDS",
        "5",
    )
)


# =========================================================
# OPEN-METEO
# =========================================================

OPEN_METEO_URL = (
    "https://api.open-meteo.com/v1/forecast"
)

OPEN_METEO_CURRENT_VARIABLES = (
    "temperature_2m",
    "relative_humidity_2m",
    "surface_pressure",
    "rain",
    "precipitation",
    "weather_code",
    "wind_speed_10m",
    "wind_direction_10m",
)


# =========================================================
# RECORDED FALLBACK
# =========================================================
#
# This is the same dry baseline that has already been used
# by the learning lab.
#
# It is intentionally retained as a deterministic final
# fallback so an Internet/API outage does not break the RAN
# automation simulator.
# =========================================================

FALLBACK_WEATHER = {

    "timestamp":
        "2026-08-28T00:40:00+02:00",

    "temperature_c":
        20.5,

    "pressure_hpa":
        1014.1,

    "relative_humidity_pct":
        58.9,

    "rain_rate_mm_per_h":
        0.0,

    "rain_interval_mm":
        0.0,

    "rain_interval_seconds":
        None,

    "precipitation_interval_mm":
        0.0,

    "weather_code":
        None,

    "wind_speed_m_per_s":
        None,

    "wind_direction_deg":
        None,

    "source":
        "RECORDED_LAB_FALLBACK",

    "source_status":
        "FALLBACK",

    "location": {

        "name":
            WEATHER_LOCATION_NAME,

        "latitude":
            WEATHER_LATITUDE,

        "longitude":
            WEATHER_LONGITUDE,

        "timezone":
            WEATHER_TIMEZONE,
    },

    "fetched_at":
        None,

    "cache_age_seconds":
        None,

    "cache_ttl_seconds":
        WEATHER_CACHE_TTL_SECONDS,

    "error":
        None,
}


# =========================================================
# IN-MEMORY CACHE
# =========================================================
#
# This is intentionally process-local.
#
# Later, when the application runs with multiple replicas,
# this would not be a distributed cache. That distinction
# should remain explicit in the learning lab.
# =========================================================

_cache_lock = RLock()

_last_successful_snapshot = None

_last_successful_monotonic = None


# =========================================================
# SMALL HELPERS
# =========================================================

def _utc_now_iso():

    return (
        datetime
        .now(
            timezone.utc
        )
        .isoformat(
            timespec="seconds"
        )
    )


def _number(
    value,
    default=None,
):

    if value is None:

        return default


    try:

        return float(
            value
        )

    except (
        TypeError,
        ValueError,
    ):

        return default


def _build_open_meteo_url():

    params = {

        "latitude":
            WEATHER_LATITUDE,

        "longitude":
            WEATHER_LONGITUDE,

        "current":
            ",".join(
                OPEN_METEO_CURRENT_VARIABLES
            ),

        "temperature_unit":
            "celsius",

        "precipitation_unit":
            "mm",

        "wind_speed_unit":
            "ms",

        "timezone":
            WEATHER_TIMEZONE,
    }


    return (
        OPEN_METEO_URL
        + "?"
        + urlencode(
            params
        )
    )


# =========================================================
# TIMESTAMP NORMALIZATION
# =========================================================

def _normalize_weather_timestamp(
    payload,
    current,
):

    raw_time = current.get(
        "time"
    )


    if not raw_time:

        return _utc_now_iso()


    utc_offset_seconds = int(
        payload.get(
            "utc_offset_seconds",
            0,
        )
    )


    offset = timezone(
        timedelta(
            seconds=
                utc_offset_seconds
        )
    )


    try:

        parsed = datetime.fromisoformat(
            raw_time
        )


        if (
            parsed.tzinfo
            is None
        ):

            parsed = parsed.replace(
                tzinfo=offset
            )


        return parsed.isoformat(
            timespec="seconds"
        )

    except ValueError:

        return raw_time


# =========================================================
# RAIN NORMALIZATION
# =========================================================

def _calculate_rain_rate(
    rain_interval_mm,
    interval_seconds,
):

    """
    Convert accumulated rain in the current Open-Meteo
    interval into an equivalent rain rate in mm/hour.

    Example:

        0.5 mm during 900 seconds

        0.5 * 3600 / 900

        = 2.0 mm/hour

    The RF model needs a rate because ITU-R P.838 rain
    attenuation uses R in mm/hour.
    """

    rain_interval_mm = float(
        rain_interval_mm
    )


    interval_seconds = float(
        interval_seconds
    )


    if (
        interval_seconds
        <= 0
    ):

        return 0.0


    return round(

        rain_interval_mm
        * 3600.0
        / interval_seconds,

        3,
    )


# =========================================================
# RESPONSE NORMALIZATION
# =========================================================

def _normalize_open_meteo_response(
    payload,
):

    current = payload.get(
        "current"
    )


    if not isinstance(
        current,
        dict,
    ):

        raise ValueError(
            "Open-Meteo response has no current weather object"
        )


    required_fields = (

        "temperature_2m",

        "relative_humidity_2m",

        "surface_pressure",
    )


    missing = [

        field

        for field
        in required_fields

        if current.get(
            field
        )
        is None
    ]


    if missing:

        raise ValueError(

            "Open-Meteo current weather is missing: "

            + ", ".join(
                missing
            )
        )


    interval_seconds = int(

        current.get(
            "interval"
        )

        or 900
    )


    rain_interval_mm = (

        _number(
            current.get(
                "rain"
            ),
            0.0,
        )

        or 0.0
    )


    precipitation_interval_mm = (

        _number(
            current.get(
                "precipitation"
            ),
            0.0,
        )

        or 0.0
    )


    rain_rate_mm_per_h = (
        _calculate_rain_rate(

            rain_interval_mm,

            interval_seconds,
        )
    )


    return {

        "timestamp":
            _normalize_weather_timestamp(
                payload,
                current,
            ),

        "temperature_c":
            round(
                float(
                    current[
                        "temperature_2m"
                    ]
                ),
                2,
            ),

        "pressure_hpa":
            round(
                float(
                    current[
                        "surface_pressure"
                    ]
                ),
                2,
            ),

        "relative_humidity_pct":
            round(
                float(
                    current[
                        "relative_humidity_2m"
                    ]
                ),
                2,
            ),

        "rain_rate_mm_per_h":
            rain_rate_mm_per_h,

        "rain_interval_mm":
            round(
                rain_interval_mm,
                3,
            ),

        "rain_interval_seconds":
            interval_seconds,

        "precipitation_interval_mm":
            round(
                precipitation_interval_mm,
                3,
            ),

        "weather_code":
            current.get(
                "weather_code"
            ),

        "wind_speed_m_per_s":
            _number(
                current.get(
                    "wind_speed_10m"
                )
            ),

        "wind_direction_deg":
            _number(
                current.get(
                    "wind_direction_10m"
                )
            ),

        "source":
            "OPEN_METEO",

        "source_status":
            "LIVE",

        "location": {

            "name":
                WEATHER_LOCATION_NAME,

            "latitude":
                payload.get(
                    "latitude",
                    WEATHER_LATITUDE,
                ),

            "longitude":
                payload.get(
                    "longitude",
                    WEATHER_LONGITUDE,
                ),

            "elevation_m":
                payload.get(
                    "elevation"
                ),

            "timezone":
                payload.get(
                    "timezone",
                    WEATHER_TIMEZONE,
                ),

            "timezone_abbreviation":
                payload.get(
                    "timezone_abbreviation"
                ),
        },

        "fetched_at":
            _utc_now_iso(),

        "cache_age_seconds":
            0.0,

        "cache_ttl_seconds":
            WEATHER_CACHE_TTL_SECONDS,

        "error":
            None,
    }


# =========================================================
# NETWORK FETCH
# =========================================================

def _fetch_open_meteo():

    url = (
        _build_open_meteo_url()
    )


    request = Request(

        url,

        headers={

            "User-Agent":
                (
                    "ran-automation-resilience-lab/"
                    "weather-service"
                )
        },
    )


    with urlopen(
        request,
        timeout=
            WEATHER_HTTP_TIMEOUT_SECONDS,
    ) as response:

        body = response.read()


    payload = json.loads(
        body.decode(
            "utf-8"
        )
    )


    if (
        payload.get(
            "error"
        )
        is True
    ):

        raise RuntimeError(

            "Open-Meteo error: "

            + str(
                payload.get(
                    "reason",
                    "unknown error",
                )
            )
        )


    return (
        _normalize_open_meteo_response(
            payload
        )
    )


# =========================================================
# CACHE HELPERS
# =========================================================

def _cached_snapshot():

    if (
        _last_successful_snapshot
        is None
        or
        _last_successful_monotonic
        is None
    ):

        return None


    age = (
        time.monotonic()
        - _last_successful_monotonic
    )


    if (
        age
        >= WEATHER_CACHE_TTL_SECONDS
    ):

        return None


    result = deepcopy(
        _last_successful_snapshot
    )


    result[
        "source_status"
    ] = "CACHE"


    result[
        "cache_age_seconds"
    ] = round(
        age,
        1,
    )


    return result


def _stale_last_known(
    error,
):

    if (
        _last_successful_snapshot
        is None
        or
        _last_successful_monotonic
        is None
    ):

        return None


    age = (
        time.monotonic()
        - _last_successful_monotonic
    )


    result = deepcopy(
        _last_successful_snapshot
    )


    result[
        "source_status"
    ] = "STALE_LAST_KNOWN"


    result[
        "cache_age_seconds"
    ] = round(
        age,
        1,
    )


    result[
        "error"
    ] = str(
        error
    )


    return result


def _fallback_snapshot(
    error,
):

    result = deepcopy(
        FALLBACK_WEATHER
    )


    result[
        "fetched_at"
    ] = _utc_now_iso()


    result[
        "error"
    ] = str(
        error
    )


    return result


# =========================================================
# PUBLIC API
# =========================================================

def get_weather_snapshot(
    force_refresh=False,
):

    """
    Return the normalized weather snapshot.

    Normal behaviour:

        first request
            -> Open-Meteo
            -> LIVE

        next requests within 10 minutes
            -> CACHE

        refresh after cache expiry
            -> Open-Meteo

        Open-Meteo failure with previous data
            -> STALE_LAST_KNOWN

        Open-Meteo failure without previous data
            -> FALLBACK

    force_refresh=True bypasses the fresh-cache check.
    """

    global _last_successful_snapshot

    global _last_successful_monotonic


    with _cache_lock:

        if not force_refresh:

            cached = (
                _cached_snapshot()
            )


            if cached is not None:

                return cached


        try:

            fresh = (
                _fetch_open_meteo()
            )


            _last_successful_snapshot = (
                deepcopy(
                    fresh
                )
            )


            _last_successful_monotonic = (
                time.monotonic()
            )


            return deepcopy(
                fresh
            )


        except Exception as error:

            stale = (
                _stale_last_known(
                    error
                )
            )


            if stale is not None:

                return stale


            return (
                _fallback_snapshot(
                    error
                )
            )


def clear_weather_cache():

    """
    Test / troubleshooting helper.

    It intentionally does not affect any RAN configuration
    state.
    """

    global _last_successful_snapshot

    global _last_successful_monotonic


    with _cache_lock:

        _last_successful_snapshot = None

        _last_successful_monotonic = None