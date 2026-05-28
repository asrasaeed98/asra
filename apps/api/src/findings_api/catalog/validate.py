"""Pre-analysis validation for ingested tables."""

from __future__ import annotations

from dataclasses import dataclass

from findings_api.config import settings


@dataclass(frozen=True)
class TableValidation:
    ok: bool
    reason: str
    row_count: int = 0
    numeric_columns: int = 0
    categorical_columns: int = 0


def validate_table(conn, table: str, *, min_rows: int | None = None) -> TableValidation:
    """Ensure a loaded table is usable for automated analysis."""
    floor = min_rows if min_rows is not None else settings.analysis_min_rows
    row_count = int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
    if row_count < floor:
        return TableValidation(
            False,
            f"Dataset has only {row_count} row(s) — need at least {floor} for analysis",
            row_count=row_count,
        )

    cols = conn.execute(f"DESCRIBE {table}").fetchall()
    if not cols:
        return TableValidation(False, "Dataset has no columns", row_count=row_count)

    numeric = 0
    categorical = 0
    for _name, dtype, *_rest in cols:
        low = str(dtype).upper()
        if any(token in low for token in ("INT", "DOUBLE", "FLOAT", "DECIMAL", "NUMERIC", "BIGINT", "HUGEINT")):
            numeric += 1
        elif any(token in low for token in ("VARCHAR", "TEXT", "STRING", "BOOLEAN", "DATE", "TIMESTAMP")):
            categorical += 1

    if numeric + categorical == 0:
        return TableValidation(False, "No analyzable columns detected", row_count=row_count)

    null_only = 0
    for name, *_rest in cols:
        non_null = int(
            conn.execute(
                f'SELECT COUNT(*) FROM {table} WHERE "{name}" IS NOT NULL'
            ).fetchone()[0]
        )
        if non_null == 0:
            null_only += 1
    if null_only == len(cols):
        return TableValidation(False, "All columns are empty", row_count=row_count)

    if numeric == 0 and categorical < 2:
        return TableValidation(
            False,
            "Need at least one numeric column or two categorical columns for analysis",
            row_count=row_count,
            categorical_columns=categorical,
        )

    return TableValidation(
        True,
        "ok",
        row_count=row_count,
        numeric_columns=numeric,
        categorical_columns=categorical,
    )
