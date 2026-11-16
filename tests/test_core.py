"""Standard SDK tap tests, run keyless against the live public API."""

from singer_sdk.testing import get_tap_test_class

from tap_tensorust.tap import TapTensorust

SAMPLE_CONFIG = {
    "companies": ["Pluralsight", "Assembly Intermediate"],
    "dataset_slugs": ["afida-foreign-farmland"],
    "exposure_lists": ["SEC889"],
}

TestTapTensorust = get_tap_test_class(tap_class=TapTensorust, config=SAMPLE_CONFIG)
