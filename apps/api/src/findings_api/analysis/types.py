from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ColumnProfile:
    name: str
    dtype: str
    kind: str  # numeric | categorical | datetime | other
    nunique: int
    null_pct: float


@dataclass
class TableProfile:
    table: str
    resource_id: str
    title: str
    n_rows: int
    columns: list[ColumnProfile] = field(default_factory=list)

    @property
    def numeric(self) -> list[str]:
        return [c.name for c in self.columns if c.kind == "numeric"]

    @property
    def categorical(self) -> list[str]:
        return [c.name for c in self.columns if c.kind == "categorical"]

    @property
    def datetime(self) -> list[str]:
        return [c.name for c in self.columns if c.kind == "datetime"]


@dataclass
class Finding:
    id: str
    type: str
    title: str
    columns: list[str]
    value: float | None
    p_value: float | None
    n: int
    method: str
    caveat: str
    sql: str
    datasets: list[str]
    score: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ChartSpec:
    id: str
    finding_id: str
    type: str
    title: str
    spec: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
