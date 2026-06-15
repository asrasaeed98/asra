import re

VISITOR_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.I,
)


def normalize_visitor_id(raw: str | None) -> str | None:
    if not raw:
        return None
    candidate = raw.strip().lower()
    if not VISITOR_RE.match(candidate):
        return None
    return candidate
