# tap-tensorust

A Singer tap for the [Tensorust](https://tensorust.com) Data API, built with the [Meltano Singer SDK](https://sdk.meltano.com). It loads private credit loan marks, lender disagreements, Q3 2026 markdowns, banned-vendor federal award exposure and the Tensorust dataset catalog into any Singer target (Snowflake, BigQuery, Postgres, DuckDB and others). It runs without a key and returns free previews. A Tensorust enterprise key (`tdk_...`) returns full rows.

## Install

```bash
pip install git+https://github.com/Mattbusel/tap-tensorust.git
```

In Meltano, add it as a custom extractor with `pip_url: git+https://github.com/Mattbusel/tap-tensorust.git`.

## Example

```bash
echo '{"companies": ["Pluralsight"]}' > config.json
tap-tensorust --about
tap-tensorust --config config.json --discover > catalog.json
tap-tensorust --config config.json | target-duckdb --config target.json
```

Streams: `datasets_catalog`, `dataset_sample`, `credit_disagreements`, `q3_cuts`, `lender_marks`, `exposure_awards`. Set `api_key` in the config for full rows.

## Docs and license

- Streams and settings: [docs/index.md](https://github.com/Mattbusel/tap-tensorust/blob/main/docs/index.md)
- Sample config: [config.sample.json](https://github.com/Mattbusel/tap-tensorust/blob/main/config.sample.json)
- MIT license: [LICENSE](https://github.com/Mattbusel/tap-tensorust/blob/main/LICENSE)
