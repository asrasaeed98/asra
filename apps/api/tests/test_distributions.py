from findings_api.catalog.distributions import ranked_distributions, score_distribution


def test_prefers_csv_download_over_landing_page():
    dcat = {
        "distribution": [
            {"accessURL": "https://data.example.gov", "format": "csv"},
            {
                "downloadURL": "https://s3.amazonaws.com/bucket/data.csv",
                "format": "csv",
            },
        ]
    }
    ranked = ranked_distributions(dcat)
    assert ranked[0][0].endswith(".csv")
    assert ranked[0][2] > ranked[1][2]


def test_penalizes_zip():
    assert score_distribution({"downloadURL": "https://x.com/file.zip"}) < score_distribution(
        {"downloadURL": "https://x.com/file.csv"}
    )
