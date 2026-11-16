"""Unit tests that need no network."""

from tap_tensorust.streams import EXPOSURE_LISTS, ExposureAwardsStream
from tap_tensorust.tap import TapTensorust


def _tap(config=None):
    return TapTensorust(config=config or {}, parse_env_config=False, validate_config=True)


def test_streams():
    names = sorted(s.name for s in _tap().discover_streams())
    assert names == [
        "credit_disagreements",
        "dataset_sample",
        "datasets_catalog",
        "exposure_awards",
        "lender_marks",
        "q3_cuts",
    ]


def test_bearer_header_only_with_key():
    keyless = _tap().streams["q3_cuts"]
    assert "Authorization" not in keyless.http_headers
    keyed = _tap({"api_key": "tdk_test"}).streams["q3_cuts"]
    assert keyed.http_headers["Authorization"] == "Bearer tdk_test"


def test_exposure_partitions():
    assert [p["list"] for p in _tap().streams["exposure_awards"].partitions] == EXPOSURE_LISTS
    inst = _tap({"institutions": ["Stanford University"]}).streams["exposure_awards"]
    assert inst.partitions == [{"institution": "Stanford University"}]
    assert inst.get_url({"institution": "Stanford University"}).endswith("/openbb/exposure_institution")


def test_exposure_normalizes_search_rows():
    stream: ExposureAwardsStream = _tap().streams["exposure_awards"]
    row = stream.post_process(
        {
            "award": "A1",
            "vendors": ["dji"],
            "lists": ["1260H", "FCC_COVERED"],
            "rules": {"ASDA-1825": "in_force_no_new_funds"},
            "in_force_or_no_grace": True,
            "extra": 1,
        },
        {"list": "1260H"},
    )
    assert row["vendors"] == "dji"
    assert row["lists"] == "1260H, FCC_COVERED"
    assert row["rule_status"] == "ASDA-1825: in_force_no_new_funds"
    assert row["source_query"] == "list:1260H"
    assert "extra" not in row
    assert stream.post_process({"award": "A1"}, {"list": "SEC889"}) is None  # deduped


def test_exposure_normalizes_institution_rows():
    stream = _tap({"institutions": ["Harvard"]}).streams["exposure_awards"]
    row = stream.post_process({"award": "B2", "in_force_or_no_grace": "no"}, {"institution": "Harvard"})
    assert row["in_force_or_no_grace"] is False
    assert row["source_query"] == "institution:Harvard"


def test_lender_marks_uses_configured_companies():
    stream = _tap({"companies": [" Pluralsight ", ""]}).streams["lender_marks"]
    assert stream.partitions == [{"company": "Pluralsight"}]
