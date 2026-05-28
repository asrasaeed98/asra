"""Join two analysis tables safely (row cap, overlap scoring, composite keys)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace

from findings_api.analysis.profile import sql_ident
from findings_api.config import settings

_MIN_MATCHED_ROWS = 8
_AUTO_JOIN_SCORE = 0.75
_MAX_SUGGESTIONS = 12

# Semantic alias groups — columns in the same group may pair across datasets.
_ALIAS_GROUPS: tuple[frozenset[str], ...] = (
    frozenset({"countryiso3code", "country", "country_code", "nation", "geo_country"}),
    frozenset({"state", "state_code", "state_abbr", "stusps", "state_name"}),
    frozenset({"fips", "fips_code", "geo_id", "geoid", "county_fips"}),
    frozenset({"year", "yr", "fiscal_year", "calendar_year"}),
    frozenset({"date", "time_period", "period", "obs_date"}),
    frozenset({"id", "identifier", "record_id", "series_id"}),
)

_PREFERRED_SINGLES = (
    "countryiso3code",
    "country",
    "state",
    "state_code",
    "fips",
    "year",
    "date",
    "id",
)

_COMPOSITE_PAIRS: tuple[tuple[str, str], ...] = (
    ("country", "year"),
    ("countryiso3code", "year"),
    ("state", "year"),
    ("fips", "year"),
    ("state", "date"),
    ("country", "date"),
)


@dataclass(frozen=True)
class JoinSuggestion:
    """A candidate join between two ingested tables."""

    keys: list[str]
    left_keys: list[str]
    right_keys: list[str]
    label: str
    matched_rows: int
    overlap_left_pct: float
    overlap_right_pct: float
    score: float
    ok: bool
    warning: str | None = None
    auto_recommended: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


def normalize_join_on(
    *,
    join_keys: list[str] | None = None,
    join_on: list[dict[str, str]] | None = None,
) -> list[tuple[str, str]]:
    """Resolve session config to (left_col, right_col) pairs."""
    if join_on:
        pairs: list[tuple[str, str]] = []
        for item in join_on:
            left = (item.get("left") or "").strip()
            right = (item.get("right") or "").strip()
            if left and right:
                pairs.append((left, right))
        if pairs:
            return pairs
    if join_keys:
        return [(k, k) for k in join_keys if k]
    return []


def _max_duplication(conn, table: str, columns: list[str]) -> int:
    cols = ", ".join(sql_ident(c) for c in columns)
    row = conn.execute(
        f"""
        SELECT COALESCE(MAX(c), 0)::BIGINT FROM (
          SELECT COUNT(*) AS c FROM {table} GROUP BY {cols}
        )
        """
    ).fetchone()
    return int(row[0])


def _join_condition(left_alias: str, right_alias: str, pairs: list[tuple[str, str]]) -> str:
    parts = [
        f"{left_alias}.{sql_ident(left)} = {right_alias}.{sql_ident(right)}"
        for left, right in pairs
    ]
    return " AND ".join(parts)


def max_key_duplication(conn, table: str, join_key: str) -> int:
    return _max_duplication(conn, table, [join_key])


def count_join_rows(conn, left: str, right: str, join_key: str) -> int:
    return count_join_rows_on(conn, left, right, [(join_key, join_key)])


def count_join_rows_on(
    conn, left: str, right: str, pairs: list[tuple[str, str]]
) -> int:
    cond = _join_condition("l", "r", pairs)
    row = conn.execute(
        f"SELECT COUNT(*)::BIGINT FROM {left} AS l INNER JOIN {right} AS r ON {cond}"
    ).fetchone()
    return int(row[0])


def _key_overlap(
    conn, left: str, right: str, pairs: list[tuple[str, str]]
) -> tuple[float, float]:
    """Return (left_key_overlap_pct, right_key_overlap_pct) on distinct composite keys."""
    left_cols = ", ".join(f"l.{sql_ident(lk)}" for lk, _ in pairs)
    right_cols = ", ".join(f"r.{sql_ident(rk)}" for _, rk in pairs)
    left_on = " AND ".join(
        f"l.{sql_ident(lk)} = r.{sql_ident(rk)}" for lk, rk in pairs
    )

    left_distinct = int(
        conn.execute(
            f"SELECT COUNT(*)::BIGINT FROM (SELECT DISTINCT {left_cols} FROM {left} AS l)"
        ).fetchone()[0]
    )
    right_distinct = int(
        conn.execute(
            f"SELECT COUNT(*)::BIGINT FROM (SELECT DISTINCT {right_cols} FROM {right} AS r)"
        ).fetchone()[0]
    )
    if left_distinct == 0 or right_distinct == 0:
        return 0.0, 0.0

    matched_left = int(
        conn.execute(
            f"""
            SELECT COUNT(*)::BIGINT FROM (
              SELECT DISTINCT {left_cols}
              FROM {left} AS l
              WHERE EXISTS (
                SELECT 1 FROM {right} AS r WHERE {left_on}
              )
            )
            """
        ).fetchone()[0]
    )
    matched_right = int(
        conn.execute(
            f"""
            SELECT COUNT(*)::BIGINT FROM (
              SELECT DISTINCT {right_cols}
              FROM {right} AS r
              WHERE EXISTS (
                SELECT 1 FROM {left} AS l WHERE {left_on}
              )
            )
            """
        ).fetchone()[0]
    )
    return matched_left / left_distinct, matched_right / right_distinct


def assess_join(conn, left: str, right: str, join_key: str) -> tuple[bool, int, str | None]:
    return assess_join_on(conn, left, right, [(join_key, join_key)])[:3]


def assess_join_on(
    conn, left: str, right: str, pairs: list[tuple[str, str]]
) -> tuple[bool, int, str | None, float, float]:
    """Return (ok, matched_rows, warning, overlap_left_pct, overlap_right_pct)."""
    if not pairs:
        return False, 0, "No join columns specified", 0.0, 0.0

    left_cols = [p[0] for p in pairs]
    right_cols = [p[1] for p in pairs]

    dup_left = _max_duplication(conn, left, left_cols)
    dup_right = _max_duplication(conn, right, right_cols)
    if dup_left > 1 and dup_right > 1:
        return (
            False,
            0,
            "Join key repeats in both datasets — try a composite key or filter rows",
            0.0,
            0.0,
        )

    overlap_left, overlap_right = _key_overlap(conn, left, right, pairs)
    matched = count_join_rows_on(conn, left, right, pairs)

    if matched < _MIN_MATCHED_ROWS:
        return (
            False,
            matched,
            "Too few matching rows — analyzing datasets separately",
            overlap_left,
            overlap_right,
        )
    if matched > settings.row_cap:
        return (
            False,
            matched,
            f"Join would produce {matched:,} rows (max {settings.row_cap:,}) — analyzing separately",
            overlap_left,
            overlap_right,
        )
    return True, matched, None, overlap_left, overlap_right


def build_joined_table(conn, left: str, right: str, join_key: str) -> tuple[str, int]:
    return build_joined_table_on(conn, left, right, [(join_key, join_key)])


def build_joined_table_on(
    conn, left: str, right: str, pairs: list[tuple[str, str]]
) -> tuple[str, int]:
    joined = "analysis_joined"
    if all(left == right for left, right in pairs):
        using = ", ".join(sql_ident(left) for left, _ in pairs)
        sql = f"SELECT * FROM {left} INNER JOIN {right} USING ({using})"
    else:
        cond = _join_condition("l", "r", pairs)
        sql = (
            f"SELECT l.*, r.* FROM {left} AS l "
            f"INNER JOIN {right} AS r ON {cond}"
        )
    conn.execute(f"CREATE OR REPLACE TABLE {joined} AS {sql}")
    count = int(conn.execute(f"SELECT COUNT(*) FROM {joined}").fetchone()[0])
    return joined, count


def _alias_group(name: str) -> frozenset[str] | None:
    low = name.lower()
    for group in _ALIAS_GROUPS:
        if low in group:
            return group
    return None


def _column_maps(profiles: list[dict]) -> tuple[dict[str, str], dict[str, str]]:
    left_map = {c["name"].lower(): c["name"] for c in profiles[0]["columns"]}
    right_map = {c["name"].lower(): c["name"] for c in profiles[1]["columns"]}
    return left_map, right_map


def _exact_shared_pairs(left_map: dict[str, str], right_map: dict[str, str]) -> list[tuple[str, str]]:
    shared = set(left_map) & set(right_map)
    ordered: list[tuple[str, str]] = []
    for pref in _PREFERRED_SINGLES:
        if pref in shared:
            col = left_map[pref]
            ordered.append((col, col))
    for key in sorted(shared):
        col = left_map[key]
        if (col, col) not in ordered:
            ordered.append((col, col))
    return ordered


def _alias_pairs(left_map: dict[str, str], right_map: dict[str, str]) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for lkey, lcol in left_map.items():
        group = _alias_group(lkey)
        if not group:
            continue
        for rkey, rcol in right_map.items():
            if rkey not in group or lkey == rkey:
                continue
            pair = (lcol, rcol)
            if pair not in seen:
                seen.add(pair)
                pairs.append(pair)
    return pairs


def _composite_candidates(
    singles: list[tuple[str, str]],
    left_map: dict[str, str],
    right_map: dict[str, str],
) -> list[list[tuple[str, str]]]:
    """Build composite join candidates from high-value (geo, time) templates."""
    by_low = {(l.lower(), r.lower()): (l, r) for l, r in singles}
    composites: list[list[tuple[str, str]]] = []
    seen: set[tuple[tuple[str, str], ...]] = set()

    def add_pair(parts: list[tuple[str, str]]) -> None:
        key = tuple(parts)
        if key not in seen:
            seen.add(key)
            composites.append(parts)

    for geo_hint, time_hint in _COMPOSITE_PAIRS:
        geo_group = _alias_group(geo_hint)
        time_group = _alias_group(time_hint)
        if not geo_group or not time_group:
            continue
        geo_singles = [p for p in singles if p[0].lower() in geo_group]
        time_singles = [p for p in singles if p[0].lower() in time_group]
        for g in geo_singles[:2]:
            for t in time_singles[:2]:
                add_pair([g, t])

    # Exact shared name composites from preferred pairs
    shared_low = set(left_map) & set(right_map)
    for a_hint, b_hint in _COMPOSITE_PAIRS:
        if a_hint in shared_low and b_hint in shared_low:
            add_pair([(left_map[a_hint], left_map[a_hint]), (left_map[b_hint], left_map[b_hint])])

    return composites


def _label_for_pairs(pairs: list[tuple[str, str]]) -> str:
    if len(pairs) == 1:
        left, right = pairs[0]
        return left if left == right else f"{left} ↔ {right}"
    parts = []
    for left, right in pairs:
        parts.append(left if left == right else f"{left}↔{right}")
    return " + ".join(parts)


def _score_candidate(
    ok: bool,
    overlap_left: float,
    overlap_right: float,
    pairs: list[tuple[str, str]],
) -> float:
    if not ok:
        return round(min(overlap_left, overlap_right) * 0.5, 4)
    base = min(overlap_left, overlap_right)
    bonus = 0.0
    if pairs:
        low = pairs[0][0].lower()
        if low in _PREFERRED_SINGLES[:4]:
            bonus += 0.05
    if len(pairs) > 1:
        bonus += 0.03
    return round(min(1.0, base + bonus), 4)


def _evaluate_candidate(
    conn,
    left_table: str,
    right_table: str,
    pairs: list[tuple[str, str]],
) -> JoinSuggestion:
    ok, matched, warning, overlap_left, overlap_right = assess_join_on(
        conn, left_table, right_table, pairs
    )
    score = _score_candidate(ok, overlap_left, overlap_right, pairs)
    left_keys = [p[0] for p in pairs]
    right_keys = [p[1] for p in pairs]
    display_keys = left_keys if left_keys == right_keys else [
        f"{l}↔{r}" for l, r in pairs
    ]
    return JoinSuggestion(
        keys=display_keys,
        left_keys=left_keys,
        right_keys=right_keys,
        label=_label_for_pairs(pairs),
        matched_rows=matched,
        overlap_left_pct=round(overlap_left, 4),
        overlap_right_pct=round(overlap_right, 4),
        score=score,
        ok=ok,
        warning=warning,
    )


def suggest_joins(conn, profiles: list[dict]) -> list[JoinSuggestion]:
    """Rank join candidates by overlap quality (singles + composites + aliases)."""
    if len(profiles) < 2:
        return []

    left_table = profiles[0].get("analysis_table") or profiles[0]["raw_table"]
    right_table = profiles[1].get("analysis_table") or profiles[1]["raw_table"]
    left_map, right_map = _column_maps(profiles)

    single_pairs = _exact_shared_pairs(left_map, right_map) + _alias_pairs(left_map, right_map)
    # Deduplicate singles preserving order
    seen_s: set[tuple[str, str]] = set()
    unique_singles: list[tuple[str, str]] = []
    for p in single_pairs:
        if p not in seen_s:
            seen_s.add(p)
            unique_singles.append(p)

    candidate_sets: list[list[tuple[str, str]]] = [[p] for p in unique_singles]
    candidate_sets.extend(_composite_candidates(unique_singles, left_map, right_map))

    seen_labels: set[str] = set()
    suggestions: list[JoinSuggestion] = []
    for pairs in candidate_sets:
        try:
            suggestion = _evaluate_candidate(conn, left_table, right_table, pairs)
        except Exception:
            continue
        if suggestion.label in seen_labels:
            continue
        seen_labels.add(suggestion.label)
        suggestions.append(suggestion)

    suggestions.sort(key=lambda s: (s.ok, s.score, s.matched_rows), reverse=True)

    marked = False
    result: list[JoinSuggestion] = []
    for s in suggestions[: _MAX_SUGGESTIONS * 2]:
        if not marked and s.ok and s.score >= _AUTO_JOIN_SCORE:
            result.append(replace(s, auto_recommended=True))
            marked = True
        else:
            result.append(s)
        if len(result) >= _MAX_SUGGESTIONS:
            break
    return result


def safe_join_columns(conn, profiles: list[dict]) -> list[str]:
    """Backward-compatible list of suggested join labels (ok candidates first)."""
    return [s.label for s in suggest_joins(conn, profiles) if s.ok][:12]


def auto_join_selection(suggestions: list[JoinSuggestion]) -> JoinSuggestion | None:
    for s in suggestions:
        if s.auto_recommended and s.ok:
            return s
    for s in suggestions:
        if s.ok:
            return s
    return None
