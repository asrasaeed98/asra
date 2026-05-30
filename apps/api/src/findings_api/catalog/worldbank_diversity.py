"""Group World Bank indicators to limit near-duplicate catalog entries."""

from __future__ import annotations

import re

# Prefer well-known macro indicators before the general catalog walk.
CURATED_INDICATORS = (
    "NY.GDP.MKTP.CD",
    "NY.GDP.MKTP.KD.ZG",
    "NY.GDP.PCAP.CD",
    "SL.UEM.TOTL.ZS",
    "SP.POP.TOTL",
    "SP.DYN.LE00.IN",
    "SP.DYN.IMRT",
    "FP.CPI.TOTL.ZG",
    "BN.CAB.XOKA.CD",
    "GC.DOD.TOTL.GD.ZS",
    "NE.EXP.GNFS.CD",
    "NE.IMP.GNFS.CD",
    "IT.NET.USER.ZS",
    "SE.ADT.LITR.ZS",
    "SE.PRM.ENRR",
    "SI.POV.DDAY",
    "EG.ELC.ACCS.ZS",
    "EG.CFT.ACCS.ZS",
    "EN.ATM.CO2E.PC",
    "SH.H2O.BASW.ZS",
    "SH.STA.BASS.ZS",
    "AG.LND.FRST.K2",
    "MS.MIL.XPND.GD.ZS",
    "DT.ODA.ODAT.GI.ZS",
    "FI.res.totl.cd",
)

# Strip donor/country suffixes: ", ADB to Laos (USD million)"
_DONOR_COUNTRY_SUFFIX = re.compile(
    r",\s*[A-Z0-9]{2,6}\s+to\s+[^,(]+(?:\([^)]*\))?\s*",
    re.IGNORECASE,
)


def title_family(title: str) -> str:
    """Normalize titles so country/donor variants share one family."""
    t = (title or "").strip().lower()
    t = _DONOR_COUNTRY_SUFFIX.sub("", t)
    t = re.sub(r"\s+", " ", t).strip(" ,;-")
    return t[:160] if t else "unknown"


def indicator_family(indicator_id: str, title: str) -> str:
    """Stable family key for deduplication."""
    ind_id = (indicator_id or "").strip()
    # Standard WDI codes (SL.UEM.TOTL.ZS) are distinct economic series.
    if re.match(r"^[A-Z]{2}\.[A-Z0-9._]+$", ind_id):
        return f"wdi:{ind_id}"
    # Country/donor variants share a title family (e.g. GPE aid disbursement rows).
    return f"title:{title_family(title)}"


def primary_topic(topics: list[dict] | None) -> str:
    if not topics:
        return "general"
    for item in topics:
        if isinstance(item, dict):
            val = (item.get("value") or "").strip()
            if val:
                return val.lower()
    return "general"
