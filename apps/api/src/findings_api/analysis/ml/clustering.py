"""Exploratory ML models (run after primary statistical tests)."""

from __future__ import annotations

import math

import pandas as pd
from sklearn.cluster import DBSCAN, KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.neighbors import LocalOutlierFactor
from sklearn.preprocessing import StandardScaler

from findings_api.analysis.profile import read_table_frame, sql_ident
from findings_api.analysis.types import Finding, TableProfile

_MIN_ML_ROWS = 50
_ML_ROW_GATE = 200
_RANDOM_STATE = 42
_MIN_SILHOUETTE = 0.15
_MIN_PCA_VARIANCE = 0.25


def _score(value: float, *, p_value: float | None = None) -> float:
    if p_value is None or p_value <= 0:
        return abs(value)
    return abs(value) * min(20.0, -math.log10(p_value))


def _numeric_frame(conn, table: str, numeric_cols: list[str]) -> tuple[pd.DataFrame, list[str]]:
    df = read_table_frame(conn, table)
    cols = [c for c in numeric_cols if c in df.columns][:8]
    work = df[cols].apply(pd.to_numeric, errors="coerce").dropna()
    return work, cols


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
    work, cols = _numeric_frame(conn, table, numeric_cols)
    if len(work) < _MIN_ML_ROWS:
        return []

    scaled = StandardScaler().fit_transform(work)
    best_k = None
    best_score = -1.0
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

    if best_k is None or best_score < _MIN_SILHOUETTE:
        return []

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
            caveat="clusters are exploratory patterns in numeric fields — not causal groups",
            sql=f"SELECT {', '.join(sql_ident(c) for c in cols)} FROM {table}",
            datasets=[resource_id],
            score=_score(float(best_score)),
            details={"dataset_title": dataset_title, "k": best_k, "silhouette": best_score},
        )
    ]


def run_dbscan(
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
    work, cols = _numeric_frame(conn, table, numeric_cols)
    if len(work) < _MIN_ML_ROWS:
        return []

    scaled = StandardScaler().fit_transform(work)
    labels = DBSCAN(eps=1.2, min_samples=max(5, len(work) // 100)).fit_predict(scaled)
    clusters = sorted({int(x) for x in labels if x >= 0})
    if len(clusters) < 2:
        return []

    mask = labels >= 0
    try:
        sil = silhouette_score(scaled[mask], labels[mask]) if mask.sum() >= _MIN_ML_ROWS else -1.0
    except ValueError:
        sil = -1.0
    if sil < _MIN_SILHOUETTE:
        return []

    noise_pct = float((labels == -1).mean())
    idx = finding_offset + 1
    return [
        Finding(
            id=f"f_{idx}",
            type="dbscan_cluster",
            title=f"DBSCAN found {len(clusters)} density clusters (silhouette = {sil:.2f})",
            columns=cols,
            value=round(float(sil), 4),
            p_value=None,
            n=int(mask.sum()),
            method="dbscan",
            caveat="density clusters may include noise points; interpret with domain context",
            sql=f"SELECT {', '.join(sql_ident(c) for c in cols)} FROM {table}",
            datasets=[resource_id],
            score=_score(float(sil)),
            details={
                "dataset_title": dataset_title,
                "n_clusters": len(clusters),
                "noise_pct": round(noise_pct, 4),
            },
        )
    ]


def run_pca_structure(
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
    work, cols = _numeric_frame(conn, table, numeric_cols)
    if len(work) < _MIN_ML_ROWS or len(cols) < 2:
        return []

    scaled = StandardScaler().fit_transform(work)
    n_comp = min(3, len(cols), len(work))
    pca = PCA(n_components=n_comp, random_state=_RANDOM_STATE)
    pca.fit(scaled)
    pc1 = float(pca.explained_variance_ratio_[0])
    if pc1 < _MIN_PCA_VARIANCE:
        return []

    idx = finding_offset + 1
    return [
        Finding(
            id=f"f_{idx}",
            type="pca_structure",
            title=f"First principal component explains {pc1:.0%} of numeric variation",
            columns=cols,
            value=round(pc1, 4),
            p_value=None,
            n=len(work),
            method="pca",
            caveat="PCA summarizes correlation structure — not a significance test",
            sql=f"SELECT {', '.join(sql_ident(c) for c in cols)} FROM {table}",
            datasets=[resource_id],
            score=_score(pc1),
            details={
                "dataset_title": dataset_title,
                "explained_variance_ratio": [round(float(x), 4) for x in pca.explained_variance_ratio_],
            },
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
    if n_rows < max(100, _ML_ROW_GATE // 2) or len(numeric_cols) < 1:
        return []
    from sklearn.ensemble import IsolationForest

    work, cols = _numeric_frame(conn, table, numeric_cols)
    if len(work) < 100:
        return []

    scaled = StandardScaler().fit_transform(work)
    model = IsolationForest(random_state=_RANDOM_STATE, contamination=0.02)
    scores = model.fit_predict(scaled)
    anomaly_n = int((scores == -1).sum())
    if anomaly_n == 0:
        return []

    rate = anomaly_n / len(work)
    if rate < 0.005:
        return []

    idx = finding_offset + 1
    return [
        Finding(
            id=f"f_{idx}",
            type="anomaly_top_rows",
            title=f"Isolation Forest flagged {anomaly_n} unusual rows ({rate:.1%} of n = {len(work)})",
            columns=cols,
            value=round(float(rate), 4),
            p_value=None,
            n=len(work),
            method="isolation_forest",
            caveat="unusual rows may be data quality issues or rare valid cases",
            sql=f"SELECT {', '.join(sql_ident(c) for c in cols)} FROM {table}",
            datasets=[resource_id],
            score=_score(float(rate)),
            details={"dataset_title": dataset_title, "anomaly_count": anomaly_n},
        )
    ]


def run_lof_anomaly(
    conn,
    table: str,
    numeric_cols: list[str],
    *,
    resource_id: str,
    dataset_title: str,
    n_rows: int,
    finding_offset: int,
) -> list[Finding]:
    if n_rows < max(100, _ML_ROW_GATE // 2) or len(numeric_cols) < 1:
        return []
    work, cols = _numeric_frame(conn, table, numeric_cols)
    if len(work) < 100:
        return []

    scaled = StandardScaler().fit_transform(work)
    n_neighbors = min(35, max(5, len(work) // 20))
    model = LocalOutlierFactor(n_neighbors=n_neighbors, contamination=0.02)
    pred = model.fit_predict(scaled)
    anomaly_n = int((pred == -1).sum())
    if anomaly_n == 0:
        return []

    rate = anomaly_n / len(work)
    if rate < 0.005:
        return []

    idx = finding_offset + 1
    return [
        Finding(
            id=f"f_{idx}",
            type="lof_anomaly",
            title=f"Local Outlier Factor flagged {anomaly_n} unusual rows ({rate:.1%})",
            columns=cols,
            value=round(float(rate), 4),
            p_value=None,
            n=len(work),
            method="lof",
            caveat="local outliers are relative to nearby rows — verify before treating as errors",
            sql=f"SELECT {', '.join(sql_ident(c) for c in cols)} FROM {table}",
            datasets=[resource_id],
            score=_score(float(rate)),
            details={"dataset_title": dataset_title, "anomaly_count": anomaly_n},
        )
    ]


def run_ml_suite(
    conn,
    profile: TableProfile,
    *,
    finding_offset: int = 0,
) -> list[Finding]:
    """Run all ML models after primary statistical tests."""
    findings: list[Finding] = []
    offset = finding_offset
    runners = (
        run_clustering,
        run_dbscan,
        run_pca_structure,
        run_anomaly,
        run_lof_anomaly,
    )
    for runner in runners:
        batch = runner(
            conn,
            profile.table,
            profile.numeric,
            resource_id=profile.resource_id,
            dataset_title=profile.title,
            n_rows=profile.n_rows,
            finding_offset=offset,
        )
        findings.extend(batch)
        offset += len(batch)
    return findings
