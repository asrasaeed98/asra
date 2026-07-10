"""Tool definitions and executors for the NYC Tonight agent.

Each tool has (1) an Anthropic tool schema in ``TOOL_DEFINITIONS`` and (2) a
Python executor. ``execute_tool`` dispatches a tool_use block to the right
executor and returns both a text payload for Claude and structured "cards"
for the frontend to render.

External calls are best-effort: any failure returns a small, structured error
dict instead of raising, so Claude can still produce a helpful reply.
"""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import quote_plus, urlencode

import httpx

try:  # zoneinfo ships with Python 3.9+
    from zoneinfo import ZoneInfo

    NYC_TZ = ZoneInfo("America/New_York")
except Exception:  # pragma: no cover - fallback if tzdata missing
    NYC_TZ = None

logger = logging.getLogger("nyc_tonight.tools")

HTTP_TIMEOUT = 12.0
DEFAULT_LOCATION = "New York, NY"


# ---------------------------------------------------------------------------
# Tool schemas (sent to Claude)
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "search_restaurants",
        "description": (
            "Search for restaurants in New York City. Use this for any dining, "
            "food, drinks, or 'where should I eat' request. Returns a handful of "
            "matching restaurants with price tier, rating, address, and a "
            "reservation deep-link. Map vague terms yourself: 'cheap' -> price_tier "
            "1, 'moderate' -> 2, 'upscale/fancy' -> 3-4."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "neighborhood": {
                    "type": "string",
                    "description": "NYC neighborhood or area, e.g. 'Chinatown', 'Williamsburg', 'East Village'. Omit for all of NYC.",
                },
                "cuisine": {
                    "type": "string",
                    "description": "Cuisine or food type, e.g. 'chinese', 'pizza', 'ramen', 'cocktail bar'.",
                },
                "price_tier": {
                    "type": "integer",
                    "enum": [1, 2, 3, 4],
                    "description": "Price tier 1 (cheap/$) to 4 (expensive/$$$$).",
                },
                "party_size": {
                    "type": "integer",
                    "description": "Number of people. Defaults to 2. Used for the reservation link.",
                },
                "time": {
                    "type": "string",
                    "description": "Desired dining time, e.g. '7pm', '19:30'. Used for the reservation link.",
                },
                "open_now": {
                    "type": "boolean",
                    "description": "Only return places open right now.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "search_events",
        "description": (
            "Search for live events happening in/around New York City: concerts, "
            "sports, comedy, theater, family shows, etc. Use this for 'what's "
            "happening', 'something fun tonight', or any request about shows or "
            "events. Returns events with venue, date/time and a ticket link."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "neighborhood_or_area": {
                    "type": "string",
                    "description": "Area to bias results, e.g. 'Williamsburg', 'Brooklyn', 'Manhattan'.",
                },
                "date": {
                    "type": "string",
                    "description": "Date as 'tonight', 'today', 'tomorrow', 'weekend', or YYYY-MM-DD. Defaults to tonight.",
                },
                "category": {
                    "type": "string",
                    "enum": ["music", "sports", "arts", "comedy", "theater", "family"],
                    "description": "Event category. 'arts' covers theater/arts & culture.",
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
            "Build a pre-filled reservation search URL for a specific restaurant on "
            "OpenTable or Resy. The URL just opens a search page in the user's "
            "browser — it does NOT complete a booking. Restaurant cards already "
            "include a reservation link, so only call this if the user asks for a "
            "link to a specific named restaurant."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "restaurant_name": {"type": "string", "description": "Name of the restaurant."},
                "platform_hint": {
                    "type": "string",
                    "enum": ["opentable", "resy"],
                    "description": "Which platform to link to. Defaults to opentable.",
                },
                "party_size": {"type": "integer", "description": "Number of people. Defaults to 2."},
                "date": {"type": "string", "description": "Date as YYYY-MM-DD. Defaults to today."},
                "time": {"type": "string", "description": "Time, e.g. '7pm' or '19:00'. Defaults to 19:00."},
            },
            "required": ["restaurant_name"],
        },
    },
]


# ---------------------------------------------------------------------------
# Small parsing helpers
# ---------------------------------------------------------------------------

def _now_nyc() -> datetime:
    return datetime.now(NYC_TZ) if NYC_TZ else datetime.now()


def _parse_time(value: str | None, default: str = "19:00") -> str:
    """Normalize a time string to 'HH:MM' (24h)."""
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
    hour = max(0, min(hour, 23))
    minute = max(0, min(minute, 59))
    return f"{hour:02d}:{minute:02d}"


def _parse_date(value: str | None) -> str:
    """Normalize a date keyword or string to 'YYYY-MM-DD' (defaults to today NYC)."""
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
    """Return (startUTC, endUTC) ISO-Z strings covering the requested local day(s).

    'weekend' spans from now through end of the coming Sunday; a bare date spans
    that single local day; 'tonight' spans from now to end of today.
    """
    now = _now_nyc()
    v = (value or "tonight").strip().lower()

    if v == "weekend":
        # From now until end of the upcoming Sunday.
        days_until_sun = (6 - now.weekday()) % 7
        end_local = (now + timedelta(days=days_until_sun)).replace(
            hour=23, minute=59, second=59, microsecond=0
        )
        start_local = now
    elif v in ("today", "tonight", "now", "") or re.match(r"^\d{4}-\d{2}-\d{2}$", v) is None:
        # Tonight / today: now -> end of today.
        start_local = now
        end_local = now.replace(hour=23, minute=59, second=59, microsecond=0)
    else:
        day = datetime.fromisoformat(v)
        if NYC_TZ:
            day = day.replace(tzinfo=NYC_TZ)
        start_local = day.replace(hour=0, minute=0, second=0, microsecond=0)
        end_local = day.replace(hour=23, minute=59, second=59, microsecond=0)

    def to_z(dt: datetime) -> str:
        if dt.tzinfo is not None:
            dt = dt.astimezone(ZoneInfo("UTC")) if NYC_TZ else dt
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    return to_z(start_local), to_z(end_local)


def _location_string(neighborhood: str | None) -> str:
    if not neighborhood:
        return DEFAULT_LOCATION
    neighborhood = neighborhood.strip()
    if "new york" in neighborhood.lower() or ", ny" in neighborhood.lower():
        return neighborhood
    return f"{neighborhood}, New York, NY"


def _price_to_dollars(tier: int | None) -> str | None:
    if not tier:
        return None
    return "$" * max(1, min(int(tier), 4))


# ---------------------------------------------------------------------------
# Reservation deep-link builder (shared + exposed as a tool)
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
        # Resy has no documented public deep-link with prefilled date/time;
        # link to the NYC search page pre-filled with the restaurant query.
        url = "https://resy.com/cities/new-york-ny?" + urlencode({"query": name})
        platform_label = "Resy"
    else:
        params = {
            "term": name,
            "covers": covers,
            "dateTime": f"{day}T{hhmm}",
        }
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


# ---------------------------------------------------------------------------
# Restaurant search: Yelp Fusion (primary) + Google Places (fallback)
# ---------------------------------------------------------------------------

def _yelp_search(
    location: str,
    cuisine: str | None,
    price_tier: int | None,
    open_now: bool | None,
    limit: int = 8,
) -> list[dict[str, Any]]:
    api_key = os.getenv("YELP_API_KEY")
    if not api_key:
        raise RuntimeError("YELP_API_KEY not set")

    params: dict[str, Any] = {
        "location": location,
        "limit": limit,
        "sort_by": "best_match",
        "categories": "restaurants",
    }
    if cuisine:
        params["term"] = cuisine
    if price_tier:
        params["price"] = str(price_tier)
    if open_now:
        params["open_now"] = "true"

    resp = httpx.get(
        "https://api.yelp.com/v3/businesses/search",
        params=params,
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=HTTP_TIMEOUT,
    )
    resp.raise_for_status()
    businesses = resp.json().get("businesses", [])

    cards = []
    for b in businesses:
        loc = b.get("location", {})
        address = ", ".join(loc.get("display_address", []) or [])
        cards.append(
            {
                "type": "restaurant",
                "source": "yelp",
                "name": b.get("name"),
                "price": b.get("price"),
                "rating": b.get("rating"),
                "review_count": b.get("review_count"),
                "categories": [c.get("title") for c in b.get("categories", [])],
                "address": address,
                "image_url": b.get("image_url"),
                "url": b.get("url"),
                "is_closed": b.get("is_closed"),
            }
        )
    return cards


_GOOGLE_PRICE_MAP = {
    "PRICE_LEVEL_FREE": "$",
    "PRICE_LEVEL_INEXPENSIVE": "$",
    "PRICE_LEVEL_MODERATE": "$$",
    "PRICE_LEVEL_EXPENSIVE": "$$$",
    "PRICE_LEVEL_VERY_EXPENSIVE": "$$$$",
}


def _google_places_search(
    query_text: str,
    open_now: bool | None,
    limit: int = 8,
) -> list[dict[str, Any]]:
    api_key = os.getenv("GOOGLE_PLACES_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_PLACES_API_KEY not set")

    field_mask = ",".join(
        [
            "places.displayName",
            "places.formattedAddress",
            "places.rating",
            "places.userRatingCount",
            "places.priceLevel",
            "places.googleMapsUri",
            "places.currentOpeningHours.openNow",
            "places.primaryTypeDisplayName",
        ]
    )
    body: dict[str, Any] = {"textQuery": query_text, "maxResultCount": limit}
    if open_now:
        body["openNow"] = True

    resp = httpx.post(
        "https://places.googleapis.com/v1/places:searchText",
        json=body,
        headers={
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": field_mask,
        },
        timeout=HTTP_TIMEOUT,
    )
    resp.raise_for_status()
    places = resp.json().get("places", [])

    cards = []
    for p in places:
        opening = (p.get("currentOpeningHours") or {}).get("openNow")
        primary_type = (p.get("primaryTypeDisplayName") or {}).get("text")
        cards.append(
            {
                "type": "restaurant",
                "source": "google",
                "name": (p.get("displayName") or {}).get("text"),
                "price": _GOOGLE_PRICE_MAP.get(p.get("priceLevel")),
                "rating": p.get("rating"),
                "review_count": p.get("userRatingCount"),
                "categories": [primary_type] if primary_type else [],
                "address": p.get("formattedAddress"),
                "image_url": None,
                "url": p.get("googleMapsUri"),
                "is_closed": (opening is False),
            }
        )
    return cards


def search_restaurants(params: dict[str, Any]) -> dict[str, Any]:
    neighborhood = params.get("neighborhood")
    cuisine = params.get("cuisine")
    price_tier = params.get("price_tier")
    party_size = params.get("party_size") or 2
    time = params.get("time")
    open_now = params.get("open_now")

    location = _location_string(neighborhood)
    cards: list[dict[str, Any]] = []
    source_used = None
    notes: list[str] = []

    # Primary: Yelp
    try:
        cards = _yelp_search(location, cuisine, price_tier, open_now)
        source_used = "yelp"
    except Exception as exc:  # noqa: BLE001
        logger.warning("Yelp search failed: %s", exc)
        notes.append(f"Yelp unavailable ({exc}).")

    # Fallback / enrichment: Google Places
    if not cards:
        query_bits = [cuisine or "restaurants", "in", location]
        query_text = " ".join(str(b) for b in query_bits if b)
        try:
            cards = _google_places_search(query_text, open_now)
            source_used = "google"
        except Exception as exc:  # noqa: BLE001
            logger.warning("Google Places search failed: %s", exc)
            notes.append(f"Google Places unavailable ({exc}).")

    # Attach a reservation deep-link to each card.
    for c in cards:
        if c.get("name"):
            res = make_reservation_url(
                c["name"], "opentable", party_size, _parse_date(None), time
            )
            c["reservation_url"] = res["url"]
            c["reservation_platform"] = res["platform"]

    if not cards:
        return {
            "content": {
                "ok": False,
                "message": "No restaurants found. "
                + (" ".join(notes) if notes else "The search returned no results."),
                "location": location,
            },
            "cards": [],
        }

    return {
        "content": {
            "ok": True,
            "source": source_used,
            "location": location,
            "count": len(cards),
            "results": [
                {
                    "name": c["name"],
                    "price": c.get("price"),
                    "rating": c.get("rating"),
                    "categories": c.get("categories"),
                    "address": c.get("address"),
                    "is_closed": c.get("is_closed"),
                }
                for c in cards
            ],
            "notes": notes or None,
        },
        "cards": cards,
    }


# ---------------------------------------------------------------------------
# Event search: Ticketmaster Discovery
# ---------------------------------------------------------------------------

_TM_SEGMENT = {
    "music": "Music",
    "sports": "Sports",
    "arts": "Arts & Theatre",
    "theater": "Arts & Theatre",
    "comedy": "Arts & Theatre",
    "family": "Family",
}


def search_events(params: dict[str, Any]) -> dict[str, Any]:
    api_key = os.getenv("TICKETMASTER_API_KEY")
    area = params.get("neighborhood_or_area")
    date = params.get("date")
    category = params.get("category")
    keyword = params.get("keyword")

    if not api_key:
        return {
            "content": {"ok": False, "message": "TICKETMASTER_API_KEY not set."},
            "cards": [],
        }

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
        logger.warning("Ticketmaster search failed: %s", exc)
        return {
            "content": {"ok": False, "message": f"Ticketmaster unavailable ({exc})."},
            "cards": [],
        }

    cards = []
    for e in events:
        dates = e.get("dates", {}).get("start", {})
        venues = (e.get("_embedded", {}) or {}).get("venues", []) or []
        venue = venues[0] if venues else {}
        venue_name = venue.get("name")
        city = (venue.get("city") or {}).get("name")
        images = e.get("images", []) or []
        image_url = images[0].get("url") if images else None
        classifications = e.get("classifications", []) or []
        seg = None
        if classifications:
            seg = (classifications[0].get("segment") or {}).get("name")

        cards.append(
            {
                "type": "event",
                "source": "ticketmaster",
                "name": e.get("name"),
                "venue": venue_name,
                "city": city,
                "date": dates.get("localDate"),
                "time": dates.get("localTime"),
                "datetime": dates.get("dateTime"),
                "category": seg,
                "image_url": image_url,
                "url": e.get("url"),
            }
        )

    if not cards:
        return {
            "content": {
                "ok": True,
                "count": 0,
                "message": "No events matched that. Try a different date, area, or category.",
            },
            "cards": [],
        }

    return {
        "content": {
            "ok": True,
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


_EXECUTORS = {
    "search_restaurants": search_restaurants,
    "search_events": search_events,
    "build_reservation_link": build_reservation_link,
}


def execute_tool(name: str, tool_input: dict[str, Any]) -> dict[str, Any]:
    """Run a tool by name. Always returns {'content': <json-able>, 'cards': [...]}."""
    executor = _EXECUTORS.get(name)
    if executor is None:
        return {"content": {"ok": False, "message": f"Unknown tool: {name}"}, "cards": []}
    try:
        return executor(tool_input or {})
    except Exception as exc:  # noqa: BLE001 - never let a tool crash the loop
        logger.exception("Tool %s crashed", name)
        return {"content": {"ok": False, "message": f"Tool {name} error: {exc}"}, "cards": []}
