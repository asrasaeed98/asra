from findings_api.licensing import is_allowed, normalize_license


def test_cc0_allowed_data_gov():
    assert normalize_license("cc-zero") == "CC0"
    assert is_allowed("CC0", "data_gov") is True


def test_cc_by_rejected_data_gov():
    assert is_allowed("CC_BY", "data_gov") is False


def test_cc_by_allowed_world_bank():
    assert is_allowed("CC_BY", "world_bank") is True
