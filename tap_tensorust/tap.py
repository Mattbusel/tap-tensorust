"""Tensorust tap class."""

from __future__ import annotations

from singer_sdk import Tap
from singer_sdk import typing as th

from tap_tensorust import streams
from tap_tensorust.client import DEFAULT_API_URL


class TapTensorust(Tap):
    """Singer tap for the Tensorust Data API.

    Streams: datasets_catalog, dataset_sample, credit_disagreements, q3_cuts, lender_marks, exposure_awards.
    Runs without a key (free previews). A Tensorust enterprise key returns the full rows.
    """

    name = "tap-tensorust"

    config_jsonschema = th.PropertiesList(
        th.Property(
            "api_key",
            th.StringType,
            secret=True,
            title="API Key",
            description=(
                "Tensorust enterprise key (it starts with tdk_), sent as a bearer token. Optional: without it every "
                "stream returns the free preview (for example the top 10 rows); with it, the full rows. "
                "Keys: https://shop.tensorust.com/offers/enterprise-api"
            ),
        ),
        th.Property(
            "api_url",
            th.StringType,
            default=DEFAULT_API_URL,
            title="API URL",
            description="Override the API base URL. Rarely needed.",
        ),
        th.Property(
            "companies",
            th.ArrayType(th.StringType),
            title="Companies",
            description=(
                "Borrower names for the lender_marks stream, as BDC schedules spell them (a prefix works, "
                'e.g. ["Pluralsight", "Assembly Intermediate"]). Leave unset to use the companies in '
                "the credit_disagreements list."
            ),
        ),
        th.Property(
            "dataset_slugs",
            th.ArrayType(th.StringType),
            title="Dataset Slugs",
            description=(
                "Dataset slugs whose 25-row samples the dataset_sample stream pulls. Sync datasets_catalog "
                "first to see them. Leave unset to pull every published sample."
            ),
        ),
        th.Property(
            "exposure_lists",
            th.ArrayType(th.StringType),
            title="Exposure Lists",
            description=(
                "Banned-vendor lists for the exposure_awards search: BIOSECURE, 1260H, UFLPA, SEC889, "
                "FCC_COVERED. Leave unset for all five."
            ),
        ),
        th.Property(
            "institutions",
            th.ArrayType(th.StringType),
            title="Institutions",
            description=(
                "Federal award recipients (name or UEI) for exposure_awards, e.g. "
                '["Stanford University"]. When set, the stream pulls each institution\'s awards instead '
                "of the per-list search: the 5 largest without a key, every award with its evidence "
                "sentence with one."
            ),
        ),
    ).to_dict()

    def discover_streams(self) -> list[streams.TensorustStream]:
        return [
            streams.DatasetsCatalogStream(self),
            streams.DatasetSampleStream(self),
            streams.CreditDisagreementsStream(self),
            streams.Q3CutsStream(self),
            streams.LenderMarksStream(self),
            streams.ExposureAwardsStream(self),
        ]


if __name__ == "__main__":
    TapTensorust.cli()
