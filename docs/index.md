# tap-tensorust

Singer tap for the [Tensorust](https://tensorust.com) Data API, built with the [Meltano Singer SDK](https://sdk.meltano.com).
It loads private credit loan marks, lender disagreements, Q3 2026 markdowns, banned-vendor federal award exposure and
the Tensorust dataset catalog into any Singer target (Snowflake, BigQuery, Postgres, DuckDB, ...).

It runs without a key. Every stream then returns the free preview (for example the top 10 rows). A Tensorust
enterprise key (`tdk_...`) returns the full rows: https://shop.tensorust.com/offers/enterprise-api

## Install

```bash
meltano add extractor tap-tensorust
# or, without Meltano
pip install git+https://github.com/Mattbusel/tap-tensorust.git
```

## Streams

| Stream | Grain | Without a key | With a key |
| --- | --- | --- | --- |
| `datasets_catalog` | one Tensorust dataset (145) | all | all |
| `dataset_sample` | one row of a dataset's free 25-row sample | all published samples | same |
| `credit_disagreements` | one company whose BDC lenders mark its first-lien loan 10+ points apart | top 10 | full list |
| `q3_cuts` | one fund's 5+ point markdown of a loan, Jun 30 to Sep 30 2026, from Q3 10-Qs as they post | top 10 | every cut |
| `lender_marks` | one company and BDC fund: the fund's mark as % of par | 3 funds per company | every fund, par, prior and Sep 30 mark, filing link |
| `exposure_awards` | one federal research award whose 2025-26 papers name a vendor on a banned-vendor list | up to 50 largest per list | with `institutions`: every award with the evidence sentence |

All streams are full table: the API answers the current state of each table, so a scheduled sync keeps the
warehouse copy current and the target's primary keys dedupe it. Data comes from SEC 10-Q schedules of investments
(BDC marks), NIH/NSF award records and 2025-26 papers (exposure), and the Federal Register, eCFR, FCC and DHS
(banned-vendor lists).

## Settings

| Setting | Description |
| --- | --- |
| `api_key` | Tensorust enterprise key, sent as `Authorization: Bearer`. Optional. |
| `api_url` | Base URL, default `https://shop.tensorust.com/api`. |
| `companies` | Borrower names for `lender_marks`. Unset: the companies in `credit_disagreements`. |
| `dataset_slugs` | Slugs whose samples `dataset_sample` pulls. Unset: every published sample. |
| `exposure_lists` | `BIOSECURE`, `1260H`, `UFLPA`, `SEC889`, `FCC_COVERED`. Unset: all five. |
| `institutions` | Award recipients (name or UEI). When set, `exposure_awards` pulls each institution's awards. |

Example `config.json`:

```json
{
  "companies": ["Pluralsight", "Assembly Intermediate"],
  "dataset_slugs": ["afida-foreign-farmland"],
  "exposure_lists": ["BIOSECURE", "SEC889"]
}
```

## Run

```bash
tap-tensorust --about
tap-tensorust --config config.json --discover > catalog.json
tap-tensorust --config config.json | target-duckdb --config target.json
```

With Meltano:

```bash
meltano add extractor tap-tensorust
meltano config set tap-tensorust companies '["Pluralsight"]'
meltano add loader target-duckdb
meltano run tap-tensorust target-duckdb
```

## Develop

```bash
pip install -e ".[dev]"
pytest
```

The tests run the SDK's standard tap tests against the live public API, keyless.

## Other ways to reach the same data

- MCP server: https://shop.tensorust.com/api/mcp
- OpenBB: [openbb-tensorust](https://github.com/Mattbusel/openbb-tensorust)
- Plain HTTP catalog: https://shop.tensorust.com/api/datasets

Maintained by Matthew Busel (Tensorust LLC). MIT license.
