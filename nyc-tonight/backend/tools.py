"""Tool definitions and executors for the NYC Tonight Agent Lab.

Free-by-default sources:
- search_restaurants → NYC Open Data (DOHMH inspections)
- get_weather → Open-Meteo (no key)
- search_events → Ticketmaster if keyed, else local fixtures
- build_reservation_link → OpenTable/Resy deep-link URLs
"""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import httpx

try:
    from zoneinfo import ZoneInfo

    NYC_TZ = ZoneInfo("America/New_York")
except Exception:  # pragma: no cover
    NYC_TZ = None

logger = logging.getLogger("nyc_tonight.tools")

HTTP_TIMEOUT = 12.0
NYC_OPENDATA_URL = "https://data.cityofnewyork.us/resource/43nn-pn8j.json"
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
NYC_LAT, NYC_LON = 40.7128, -74.0060
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

# Rough neighborhood → borough / keyword hints for Open Data SoQL
_NEIGHBORHOOD_BORO = {
    "williamsburg": "Brooklyn",
    "brooklyn": "Brooklyn",
    "bushwick": "Brooklyn",
    "park slope": "Brooklyn",
    "dumbo": "Brooklyn",
    "chinatown": "Manhattan",
    "east village": "Manhattan",
    "west village": "Manhattan",
    "greenwich village": "Manhattan",
    "soho": "Manhattan",
    "tribeca": "Manhattan",
    "midtown": "Manhattan",
    "harlem": "Manhattan",
    "upper west side": "Manhattan",
    "upper east side": "Manhattan",
    "hell's kitchen": "Manhattan",
    "chelsea": "Manhattan",
    "astoria": "Queens",
    "queens": "Queens",
    "flushing": "Queens",
    "bronx": "Bronx",
    "staten island": "Staten Island",
}


TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "search_restaurants",
        "description": (
            "Search for restaurants in New York City using NYC Open Data "
            "(real restaurant names, cuisine, borough, address, inspection grade). "
            "Use for dining, food, drinks, or 'where should I eat'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "neighborhood": {
                    "type": "string",
                    "description": "NYC neighborhood or area, e.g. 'Chinatown', 'Williamsburg'.",
                },
                "cuisine": {
                    "type": "string",
                    "description": "Cuisine or food type, e.g. 'chinese', 'pizza', 'ramen'.",
                },
                "party_size": {
                    "type": "integer",
                    "description": "Number of people. Defaults to 2. Used for reservation link.",
                },
                "time": {
                    "type": "string",
                    "description": "Desired dining time, e.g. '7pm'. Used for reservation link.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "get_weather",
        "description": (
            "Get the current weather forecast for New York City. Use when the user asks "
            "about weather, rain, temperature, or whether outdoor plans make sense tonight."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "note": {
                    "type": "string",
                    "description": "Optional note; location is always NYC.",
                }
            },
            "required": [],
        },
    },
    {
        "name": "search_events",
        "description": (
            "Search for live events in/around New York City: concerts, sports, comedy, "
            "theater, family shows. Use for 'what's happening', 'something fun tonight'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "neighborhood_or_area": {
                    "type": "string",
                    "description": "Area to bias results, e.g. 'Williamsburg', 'Brooklyn'.",
                },
                "date": {
                    "type": "string",
                    "description": "Date as 'tonight', 'today', 'tomorrow', 'weekend', or YYYY-MM-DD.",
                },
                "category": {
                    "type": "string",
                    "enum": ["music", "sports", "arts", "comedy", "theater", "family"],
                    "description": "Event category.",
                },
                "keyword": {
                    "type": "string",
                    "description": "Optional free-text keyword, e.g. an artist or team name.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "build_reservation_link",
        "description": (
            "Build a pre-filled reservation search URL for a restaurant on OpenTable or Resy. "
            "Does NOT complete a booking. Restaurant cards already include a link; only call "
            "this if the user asks for a link to a specific named restaurant."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "restaurant_name": {"type": "string", "description": "Name of the restaurant."},
                "platform_hint": {
                    "type": "string",
                    "enum": ["opentable", "resy"],
                    "description": "Which platform. Defaults to opentable.",
                },
                "party_size": {"type": "integer", "description": "Number of people. Defaults to 2."},
                "date": {"type": "string", "description": "Date as YYYY-MM-DD. Defaults to today."},
                "time": {"type": "string", "description": "Time, e.g. '7pm'. Defaults to 19:00."},
            },
            "required": ["restaurant_name"],
        },
    },
]


def tool_sources_status() -> dict[str, Any]:
    """For /health — preferred backends (live calls fall back to fixtures on error)."""
    return {
        "restaurants": "nyc_open_data_or_fixtures",
        "weather": "open_meteo_or_fixtures",
        "events": "ticketmaster" if os.getenv("TICKETMASTER_API_KEY") else "fixtures",
        "reservation_links": "opentable_resy_deeplink",
        "nyc_opendata_token": bool(os.getenv("NYC_OPENDATA_APP_TOKEN")),
        "ticketmaster_configured": bool(os.getenv("TICKETMASTER_API_KEY")),
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_nyc() -> datetime:
    return datetime.now(NYC_TZ) if NYC_TZ else datetime.now()


def _parse_time(value: str | None, default: str = "19:00") -> str:
    if not value:
        return default
    v = value.strip().lower().replace(" ", "")
    m = re.match(r"^(\d{1,2})(?::(\d{2}))?(am|pm)?$", v)
    if not m:
        return default
    hour = int(m.group(1))
    minute = int(m.group(2) or 0)
    meridiem = m.group(3)
    if meridiem == "pm" and hour < 12:
        hour += 12
    elif meridiem == "am" and hour == 12:
        hour = 0
    return f"{max(0, min(hour, 23)):02d}:{max(0, min(minute, 59)):02d}"


def _parse_date(value: str | None) -> str:
    today = _now_nyc().date()
    if not value:
        return today.isoformat()
    v = value.strip().lower()
    if v in ("today", "tonight", "now"):
        return today.isoformat()
    if v == "tomorrow":
        return (today + timedelta(days=1)).isoformat()
    if re.match(r"^\d{4}-\d{2}-\d{2}$", v):
        return v
    return today.isoformat()


def _day_range_utc(value: str | None) -> tuple[str, str]:
    now = _now_nyc()
    v = (value or "tonight").strip().lower()

    if v == "weekend":
        days_until_sun = (6 - now.weekday()) % 7
        end_local = (now + timedelta(days=days_until_sun)).replace(
            hour=23, minute=59, second=59, microsecond=0
        )
        start_local = now
    elif v in ("today", "tonight", "now", "") or re.match(r"^\d{4}-\d{2}-\d{2}$", v) is None:
        start_local = now
        end_local = now.replace(hour=23, minute=59, second=59, microsecond=0)
    else:
        day = datetime.fromisoformat(v)
        if NYC_TZ:
            day = day.replace(tzinfo=NYC_TZ)
        start_local = day.replace(hour=0, minute=0, second=0, microsecond=0)
        end_local = day.replace(hour=23, minute=59, second=59, microsecond=0)

    def to_z(dt: datetime) -> str:
        if dt.tzinfo is not None and NYC_TZ:
            dt = dt.astimezone(ZoneInfo("UTC"))
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    return to_z(start_local), to_z(end_local)


# ---------------------------------------------------------------------------
# Reservation deep-links
# ---------------------------------------------------------------------------

def make_reservation_url(
    restaurant_name: str,
    platform_hint: str | None = "opentable",
    party_size: int | None = 2,
    date: str | None = None,
    time: str | None = None,
) -> dict[str, Any]:
    name = (restaurant_name or "").strip()
    platform = (platform_hint or "opentable").strip().lower()
    covers = party_size or 2
    day = _parse_date(date)
    hhmm = _parse_time(time)

    if platform == "resy":
        url = "https://resy.com/cities/new-york-ny?" + urlencode({"query": name})
        platform_label = "Resy"
    else:
        params = {"term": name, "covers": covers, "dateTime": f"{day}T{hhmm}"}
        url = "https://www.opentable.com/s?" + urlencode(params)
        platform_label = "OpenTable"

    return {
        "url": url,
        "platform": platform_label,
        "restaurant_name": name,
        "party_size": covers,
        "date": day,
        "time": hhmm,
    }


def build_reservation_link(params: dict[str, Any]) -> dict[str, Any]:
    if not params.get("restaurant_name"):
        return {"content": {"ok": False, "message": "restaurant_name is required."}, "cards": []}
    res = make_reservation_url(
        params["restaurant_name"],
        params.get("platform_hint"),
        params.get("party_size"),
        params.get("date"),
        params.get("time"),
    )
    return {"content": {"ok": True, **res}, "cards": []}


# ---------------------------------------------------------------------------
# Weather — Open-Meteo
# ---------------------------------------------------------------------------

_WMO = {
    0: "Clear",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Foggy",
    48: "Icy fog",
    51: "Light drizzle",
    61: "Light rain",
    63: "Rain",
    65: "Heavy rain",
    71: "Light snow",
    73: "Snow",
    80: "Rain showers",
    95: "Thunderstorm",
}


def get_weather(_params: dict[str, Any] | None = None) -> dict[str, Any]:
    try:
        resp = httpx.get(
            OPEN_METEO_URL,
            params={
                "latitude": NYC_LAT,
                "longitude": NYC_LON,
                "current": "temperature_2m,weather_code,precipitation,wind_speed_10m,relative_humidity_2m",
                "temperature_unit": "fahrenheit",
                "wind_speed_unit": "mph",
                "timezone": "America/New_York",
            },
            headers={"User-Agent": "nyc-tonight-agent-lab/0.2"},
            timeout=HTTP_TIMEOUT,
        )
        resp.raise_for_status()
        current = resp.json().get("current") or {}
        code = current.get("weather_code")
        condition = _WMO.get(int(code), "See details") if code is not None else "Unknown"
        temp = current.get("temperature_2m")
        payload = {
            "ok": True,
            "location": "New York City",
            "temperature_f": temp,
            "condition": condition,
            "summary": condition,
            "precipitation_mm": current.get("precipitation"),
            "wind_mph": current.get("wind_speed_10m"),
            "humidity_pct": current.get("relative_humidity_2m"),
            "source": "open_meteo",
        }
        card = {
            "type": "weather",
            "source": "open_meteo",
            "name": f"NYC weather: {condition}",
            "temperature_f": temp,
            "condition": condition,
            "wind_mph": current.get("wind_speed_10m"),
            "humidity_pct": current.get("relative_humidity_2m"),
        }
        return {"content": payload, "cards": [card]}
    except Exception as exc:  # noqa: BLE001
        logger.warning("Open-Meteo failed, using sample weather: %s", exc)
        # Deterministic fallback so Lesson 1 still demos get_weather offline
        payload = {
            "ok": True,
            "location": "New York City",
            "temperature_f": 68,
            "condition": "Partly cloudy",
            "summary": "Partly cloudy",
            "precipitation_mm": 0,
            "wind_mph": 8,
            "humidity_pct": 55,
            "source": "fixture",
            "message": "Sample weather (Open-Meteo unavailable).",
        }
        card = {
            "type": "weather",
            "source": "fixture",
            "name": "NYC weather: Partly cloudy",
            "temperature_f": 68,
            "condition": "Partly cloudy",
            "wind_mph": 8,
            "humidity_pct": 55,
        }
        return {"content": payload, "cards": [card]}


# ---------------------------------------------------------------------------
# Restaurants — NYC Open Data
# ---------------------------------------------------------------------------

def _attach_reservation(
    cards: list[dict[str, Any]], party_size: int, time: str | None
) -> list[dict[str, Any]]:
    for c in cards:
        if c.get("name"):
            res = make_reservation_url(
                c["name"], "opentable", party_size, _parse_date(None), time
            )
            c["reservation_url"] = res["url"]
            c["reservation_platform"] = res["platform"]
        if not c.get("url") and c.get("name"):
            c["url"] = (
                "https://www.google.com/maps/search/?api=1&query="
                + c["name"].replace(" ", "+")
                + "+NYC"
            )
    return cards


def _search_restaurants_fixtures(params: dict[str, Any]) -> dict[str, Any]:
    neighborhood = (params.get("neighborhood") or "").strip().lower()
    cuisine = (params.get("cuisine") or "").strip().lower()
    party_size = params.get("party_size") or 2
    time = params.get("time")
    path = FIXTURES_DIR / "restaurants.json"
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return {
            "content": {"ok": False, "message": f"Restaurant fixtures unavailable ({exc})."},
            "cards": [],
        }

    def match(r: dict[str, Any]) -> bool:
        blob = " ".join(
            str(r.get(k) or "")
            for k in ("name", "neighborhood", "boro", "cuisine", "address")
        ).lower()
        cats = " ".join(r.get("categories") or []).lower()
        blob = f"{blob} {cats}"
        if neighborhood and neighborhood not in blob:
            return False
        if cuisine and cuisine not in blob:
            return False
        return True

    filtered = [r for r in rows if match(r)]
    if not filtered:
        filtered = rows[:6]

    cards = []
    for r in filtered[:8]:
        cards.append(
            {
                "type": "restaurant",
                "source": "fixture",
                "name": r.get("name"),
                "price": None,
                "rating": None,
                "grade": r.get("grade"),
                "categories": r.get("categories") or ([r["cuisine"]] if r.get("cuisine") else []),
                "address": r.get("address"),
                "image_url": None,
                "is_closed": None,
            }
        )
    _attach_reservation(cards, party_size, time)
    return {
        "content": {
            "ok": True,
            "source": "fixtures",
            "count": len(cards),
            "message": "Using sample restaurants (NYC Open Data unavailable).",
            "results": [
                {
                    "name": c["name"],
                    "grade": c.get("grade"),
                    "categories": c.get("categories"),
                    "address": c.get("address"),
                }
                for c in cards
            ],
        },
        "cards": cards,
    }


def search_restaurants(params: dict[str, Any]) -> dict[str, Any]:
    neighborhood = (params.get("neighborhood") or "").strip()
    cuisine = (params.get("cuisine") or "").strip()
    party_size = params.get("party_size") or 2
    time = params.get("time")

    clauses = ["dba IS NOT NULL"]
    if cuisine:
        safe = cuisine.replace("'", "''")
        clauses.append(f"upper(cuisine_description) like upper('%{safe}%')")
    if neighborhood:
        boro = _NEIGHBORHOOD_BORO.get(neighborhood.lower())
        if boro:
            clauses.append(f"boro='{boro}'")
        safe_n = neighborhood.replace("'", "''")
        if not boro:
            clauses.append(
                f"(upper(street) like upper('%{safe_n}%') OR upper(dba) like upper('%{safe_n}%'))"
            )

    query: dict[str, Any] = {
        "$where": " AND ".join(clauses),
        "$limit": 40,
        "$order": "grade ASC, dba ASC",
        "$select": "camis,dba,cuisine_description,boro,building,street,zipcode,grade,phone",
    }
    headers = {"User-Agent": "nyc-tonight-agent-lab/0.2"}
    token = os.getenv("NYC_OPENDATA_APP_TOKEN")
    if token:
        headers["X-App-Token"] = token

    try:
        resp = httpx.get(
            NYC_OPENDATA_URL, params=query, headers=headers, timeout=HTTP_TIMEOUT
        )
        resp.raise_for_status()
        rows = resp.json()
    except Exception as exc:  # noqa: BLE001
        logger.warning("NYC Open Data failed, using fixtures: %s", exc)
        return _search_restaurants_fixtures(params)

    seen: set[str] = set()
    cards: list[dict[str, Any]] = []
    for row in rows:
        name = (row.get("dba") or "").strip().title()
        camis = str(row.get("camis") or name)
        if not name or camis in seen:
            continue
        seen.add(camis)
        address_parts = [
            row.get("building"),
            (row.get("street") or "").title() if row.get("street") else None,
            row.get("boro"),
            row.get("zipcode"),
        ]
        address = ", ".join(str(p) for p in address_parts if p)
        cuisine_label = row.get("cuisine_description")
        cards.append(
            {
                "type": "restaurant",
                "source": "nyc_open_data",
                "name": name,
                "price": None,
                "rating": None,
                "grade": row.get("grade"),
                "categories": [cuisine_label] if cuisine_label else [],
                "address": address,
                "image_url": None,
                "is_closed": None,
            }
        )
        if len(cards) >= 8:
            break

    if neighborhood and cards:
        nlow = neighborhood.lower()
        filtered = [
            c
            for c in cards
            if nlow in (c.get("address") or "").lower() or nlow in (c.get("name") or "").lower()
        ]
        if filtered:
            cards = filtered[:8]

    if not cards:
        return _search_restaurants_fixtures(params)

    _attach_reservation(cards, party_size, time)
    return {
        "content": {
            "ok": True,
            "source": "nyc_open_data",
            "count": len(cards),
            "results": [
                {
                    "name": c["name"],
                    "grade": c.get("grade"),
                    "categories": c.get("categories"),
                    "address": c.get("address"),
                }
                for c in cards
            ],
        },
        "cards": cards,
    }


# ---------------------------------------------------------------------------
# Events — Ticketmaster or fixtures
# ---------------------------------------------------------------------------

_TM_SEGMENT = {
    "music": "Music",
    "sports": "Sports",
    "arts": "Arts & Theatre",
    "theater": "Arts & Theatre",
    "comedy": "Arts & Theatre",
    "family": "Family",
}


def _load_event_fixtures() -> list[dict[str, Any]]:
    path = FIXTURES_DIR / "events.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not load event fixtures: %s", exc)
        return []
    today = _now_nyc().date().isoformat()
    for e in data:
        if not e.get("date"):
            e["date"] = today
    return data


def _search_events_fixtures(params: dict[str, Any]) -> dict[str, Any]:
    area = (params.get("neighborhood_or_area") or "").strip().lower()
    category = (params.get("category") or "").strip().lower()
    keyword = (params.get("keyword") or "").strip().lower()
    cards = _load_event_fixtures()

    def match(e: dict[str, Any]) -> bool:
        if category and (e.get("category") or "").lower() != category:
            # theater/arts soft match
            if not (
                category in ("arts", "theater")
                and (e.get("category") or "") in ("arts", "theater")
            ):
                return False
        blob = " ".join(
            str(e.get(k) or "")
            for k in ("name", "venue", "neighborhood", "city", "category")
        ).lower()
        if area and area not in blob:
            return False
        if keyword and keyword not in blob:
            return False
        return True

    filtered = [e for e in cards if match(e)]
    # If filters too tight, loosen to all fixtures so the lab still demos
    if not filtered and (area or category or keyword):
        filtered = cards[:5]
    else:
        filtered = filtered[:8]

    return {
        "content": {
            "ok": True,
            "source": "fixtures",
            "count": len(filtered),
            "message": (
                "Using sample events (set TICKETMASTER_API_KEY for live data)."
                if filtered
                else "No fixture events matched."
            ),
            "results": [
                {
                    "name": c["name"],
                    "venue": c.get("venue"),
                    "date": c.get("date"),
                    "time": c.get("time"),
                    "category": c.get("category"),
                }
                for c in filtered
            ],
        },
        "cards": filtered,
    }


def search_events(params: dict[str, Any]) -> dict[str, Any]:
    api_key = os.getenv("TICKETMASTER_API_KEY")
    if not api_key:
        return _search_events_fixtures(params)

    area = params.get("neighborhood_or_area")
    date = params.get("date")
    category = params.get("category")
    keyword = params.get("keyword")
    start_dt, end_dt = _day_range_utc(date)

    query: dict[str, Any] = {
        "apikey": api_key,
        "city": "New York",
        "startDateTime": start_dt,
        "endDateTime": end_dt,
        "size": 10,
        "sort": "date,asc",
    }
    if category:
        seg = _TM_SEGMENT.get(category.lower())
        if seg:
            query["classificationName"] = seg
    if keyword:
        query["keyword"] = keyword
    elif area:
        query["keyword"] = area

    try:
        resp = httpx.get(
            "https://app.ticketmaster.com/discovery/v2/events.json",
            params=query,
            timeout=HTTP_TIMEOUT,
        )
        resp.raise_for_status()
        events = resp.json().get("_embedded", {}).get("events", [])
    except Exception as exc:  # noqa: BLE001
        logger.warning("Ticketmaster failed, falling back to fixtures: %s", exc)
        return _search_events_fixtures(params)

    cards = []
    for e in events:
        dates = e.get("dates", {}).get("start", {})
        venues = (e.get("_embedded", {}) or {}).get("venues", []) or []
        venue = venues[0] if venues else {}
        images = e.get("images", []) or []
        classifications = e.get("classifications", []) or []
        seg = None
        if classifications:
            seg = (classifications[0].get("segment") or {}).get("name")
        cards.append(
            {
                "type": "event",
                "source": "ticketmaster",
                "name": e.get("name"),
                "venue": venue.get("name"),
                "city": (venue.get("city") or {}).get("name"),
                "date": dates.get("localDate"),
                "time": dates.get("localTime"),
                "datetime": dates.get("dateTime"),
                "category": seg,
                "image_url": images[0].get("url") if images else None,
                "url": e.get("url"),
            }
        )

    if not cards:
        return {
            "content": {
                "ok": True,
                "count": 0,
                "source": "ticketmaster",
                "message": "No events matched. Try a different date, area, or category.",
            },
            "cards": [],
        }

    return {
        "content": {
            "ok": True,
            "source": "ticketmaster",
            "count": len(cards),
            "window": {"start": start_dt, "end": end_dt},
            "results": [
                {
                    "name": c["name"],
                    "venue": c.get("venue"),
                    "date": c.get("date"),
                    "time": c.get("time"),
                    "category": c.get("category"),
                }
                for c in cards
            ],
        },
        "cards": cards,
    }


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

_EXECUTORS = {
    "search_restaurants": search_restaurants,
    "get_weather": get_weather,
    "search_events": search_events,
    "build_reservation_link": build_reservation_link,
}


def execute_tool(name: str, tool_input: dict[str, Any]) -> dict[str, Any]:
    executor = _EXECUTORS.get(name)
    if executor is None:
        return {"content": {"ok": False, "message": f"Unknown tool: {name}"}, "cards": []}
    try:
        return executor(tool_input or {})
    except Exception as exc:  # noqa: BLE001
        logger.exception("Tool %s crashed", name)
        return {"content": {"ok": False, "message": f"Tool {name} error: {exc}"}, "cards": []}
