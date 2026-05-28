"""Tests for World Bank indicator deduplication."""

from findings_api.catalog.worldbank_diversity import indicator_family, title_family


def test_title_family_groups_country_aid_variants():
    a = " International aid disbursed to total education, ADB to Laos (USD million)  "
    b = " International aid disbursed to total education, AFD to Burkina Faso (USD million)  "
    assert title_family(a) == title_family(b)


def test_indicator_family_caps_gpe_series():
    a = indicator_family(
        "5.1.1_LAO.TOTA.AID.ADB",
        " International aid disbursed to total education, ADB to Laos (USD million)  ",
    )
    b = indicator_family(
        "5.1.2_BFA.TOTA.AID.AFD",
        " International aid disbursed to total education, AFD to Burkina Faso (USD million)  ",
    )
    assert a == b


def test_wdi_indicators_stay_distinct():
    a = indicator_family("SL.UEM.TOTL.ZS", "Unemployment")
    b = indicator_family("NY.GDP.MKTP.CD", "GDP")
    assert a != b
