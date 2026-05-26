from __future__ import annotations

import math

import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

from findings_api.analysis.profile import read_table_frame, sql_ident
from findings_api.analysis.types import Finding

_MIN_ML_ROWS = 50
_ML_ROW_GATE = 1000
_RANDOM_STATE = 42


def _score(value: float) -> float:
    return abs(value)


def run_clustering(
    conn,
    table: str,
    numeric_cols: list[str],
    *,
    resource_id: str,
    dataset_title: str,
    n_rows: int,
    finding_offset: int,
) -> list[Finding]:
    if n_rows < _ML_ROW_GATE or len(numeric_cols) < 2:
        return []
    df = read_table_frame(conn, table)
    cols = [c for c in numeric_cols if c in df.columns][:8]
    work = df[cols].apply(pd.to_numeric, errors="coerce").dropna()
    if len(work) < _MIN_ML_ROWS:
        return []

    scaled = StandardScaler().fit_transform(work)
    best_k = None
    best_score = -1.0
    best_model = None
    for k in range(2, min(6, len(work))):
        model = KMeans(n_clusters=k, random_state=_RANDOM_STATE, n_init=10)
        labels = model.fit_predict(scaled)
        if len(set(labels)) < 2:
            continue
        try:
            sil = silhouette_score(scaled, labels)
        except ValueError:
            continue
        if sil > best_score:
            best_score = sil
            best_k = k
            best_model = model

    if best_model is None or best_k is None:
        return []

    labels = best_model.labels_
    sizes = {str(i): int((labels == i).sum()) for i in range(best_k)}
    idx = finding_offset + 1
    return [
        Finding(
            id=f"f_{idx}",
            type="kmeans_cluster",
            title=f"K-means found {best_k} clusters (silhouette = {best_score:.2f}, n = {len(work)})",
            columns=cols,
            value=round(float(best_score), 4),
            p_value=None,
            n=len(work),
            method="kmeans",
            caveat="clusters are exploratory, not causal groups",
            sql=f"SELECT {', '.join(sql_ident(c) for c in cols)} FROM {table}",
            datasets=[resource_id],
            score=_score(float(best_score)),
            details={"dataset_title": dataset_title, "cluster_sizes": sizes, "k": best_k},
        )
    ]


def run_anomaly(
    conn,
    table: str,
    numeric_cols: list[str],
    *,
    resource_id: str,
    dataset_title: str,
    n_rows: int,
    finding_offset: int,
) -> list[Finding]:
    if n_rows < max(100, _ML_ROW_GATE // 10) or len(numeric_cols) < 1:
        return []
    from sklearn.ensemble import IsolationForest

    df = read_table_frame(conn, table)
    cols = [c for c in numeric_cols if c in df.columns][:8]
    work = df[cols].apply(pd.to_numeric, errors="coerce").dropna()
    if len(work) < 100:
        return []

    scaled = StandardScaler().fit_transform(work)
    model = IsolationForest(random_state=_RANDOM_STATE, contamination=0.02)
    scores = model.fit_predict(scaled)
    anomaly_n = int((scores == -1).sum())
    if anomaly_n == 0:
        return []

    idx = finding_offset + 1
    rate = anomaly_n / len(work)
    return [
        Finding(
            id=f"f_{idx}",
            type="anomaly_top_rows",
            title=f"Isolation Forest flagged {anomaly_n} anomalous rows ({rate:.1%} of n = {len(work)})",
            columns=cols,
            value=round(float(rate), 4),
            p_value=None,
            n=len(work),
            method="isolation_forest",
            caveat="anomalies may be data quality issues or rare valid cases",
            sql=f"SELECT {', '.join(sql_ident(c) for c in cols)} FROM {table}",
            datasets=[resource_id],
            score=_score(float(rate)),
            details={"dataset_title": dataset_title, "anomaly_count": anomaly_n},
        )
    ]
