"""Join two analysis tables safely (row cap + duplication checks)."""

from __future__ import annotations

from findings_api.analysis.profile import sql_ident
from findings_api.config import settings


def max_key_duplication(conn, table: str, join_key: str) -> int:
    key = sql_ident(join_key)
    row = conn.execute(
        f"""
        SELECT COALESCE(MAX(c), 0)::BIGINT FROM (
          SELECT COUNT(*) AS c FROM {table} GROUP BY {key}
        )
        """
    ).fetchone()
    return int(row[0])


def count_join_rows(conn, left: str, right: str, join_key: str) -> int:
    key = sql_ident(join_key)
    row = conn.execute(
        f"""
        SELECT COUNT(*)::BIGINT FROM {left} AS l
        INNER JOIN {right} AS r ON l.{key} = r.{key}
        """
    ).fetchone()
    return int(row[0])


def assess_join(conn, left: str, right: str, join_key: str) -> tuple[bool, int, str | None]:
    """
    Return (ok, matched_rows, warning).

    Rejects joins that would explode (duplicate keys on both sides) or exceed row_cap.
    """
    dup_left = max_key_duplication(conn, left, join_key)
    dup_right = max_key_duplication(conn, right, join_key)
    if dup_left > 1 and dup_right > 1:
        return (
            False,
            0,
            "Join key repeats in both datasets — use filters or analyze separately",
        )

    matched = count_join_rows(conn, left, right, join_key)
    if matched < 8:
        return False, matched, "Too few matching rows — analyzing datasets separately"
    if matched > settings.row_cap:
        return (
            False,
            matched,
            f"Join would produce {matched:,} rows (max {settings.row_cap:,}) — analyzing separately",
        )
    return True, matched, None


def build_joined_table(conn, left: str, right: str, join_key: str) -> tuple[str, int]:
    joined = "analysis_joined"
    key = sql_ident(join_key)
    conn.execute(
        f"CREATE OR REPLACE TABLE {joined} AS "
        f"SELECT * FROM {left} INNER JOIN {right} USING ({key})"
    )
    count = int(conn.execute(f"SELECT COUNT(*) FROM {joined}").fetchone()[0])
    return joined, count


def safe_join_columns(conn, profiles: list[dict]) -> list[str]:
    """Shared column names that pass a quick join safety screen."""
    if len(profiles) < 2:
        return []

    names_sets = []
    for p in profiles:
        names_sets.append({c["name"].lower(): c["name"] for c in p["columns"]})
    shared = set(names_sets[0])
    for ns in names_sets[1:]:
        shared &= set(ns)

    preferred = ["countryiso3code", "country", "state", "state_code", "year", "date", "id"]
    ordered: list[str] = []
    for key in preferred:
        if key in shared:
            ordered.append(names_sets[0][key])
    for key in sorted(shared):
        canon = names_sets[0][key]
        if canon not in ordered:
            ordered.append(canon)

    left_table = profiles[0].get("analysis_table") or profiles[0]["raw_table"]
    right_table = profiles[1].get("analysis_table") or profiles[1]["raw_table"]
    safe: list[str] = []
    for col in ordered:
        try:
            ok, _, _ = assess_join(conn, left_table, right_table, col)
            if ok:
                safe.append(col)
        except Exception:
            continue
    return safe[:12]
