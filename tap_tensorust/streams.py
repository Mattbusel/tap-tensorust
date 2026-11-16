"""Stream definitions for tap-tensorust.

Every stream is full table: the API answers the current state of each table (marks as of the latest
10-Q, the live Q3 2026 markdown list, the current exposure ledger), so a scheduled sync keeps the
warehouse copy current and the target's primary keys dedupe it.
"""

from __future__ import annotations

import csv
import io
import typing as t

from singer_sdk import typing as th
from singer_sdk.pagination import JSONPathPaginator

from tap_tensorust.client import TensorustStream

if t.TYPE_CHECKING:
    import requests
    from singer_sdk.helpers.types import Context, Record

EXPOSURE_LISTS = ["BIOSECURE", "1260H", "UFLPA", "SEC889", "FCC_COVERED"]

_str = th.StringType
_num = th.NumberType
_int = th.IntegerType


class DatasetsCatalogStream(TensorustStream):
    """The Tensorust dataset catalog: 145 entity-level datasets with price tiers and sample links."""

    name = "datasets_catalog"
    path = "/datasets"
    primary_keys = ("slug",)
    replication_key = None
    records_jsonpath = "$.datasets[*]"
    page_size = 50

    schema = th.PropertiesList(
        th.Property("slug", _str, required=True, description="Dataset id, used by the dataset_sample stream"),
        th.Property("name", _str),
        th.Property("line", _str, description="One-line description"),
        th.Property("category", _str),
        th.Property("rows", _int, description="Rows in the full file, when published"),
        th.Property("tiers", th.ArrayType(_str), description="License tiers with prices"),
        th.Property("page", _str, description="Dataset page on tensorust.com"),
        th.Property("sample_csv", _str, description="Free 25-row sample CSV, when one exists"),
        th.Property("buy_url", _str),
    ).to_dict()

    def get_new_paginator(self) -> JSONPathPaginator:
        return JSONPathPaginator("$.next_offset")

    def get_url_params(self, context: Context | None, next_page_token: t.Any | None) -> dict[str, t.Any]:
        return {"limit": self.page_size, "offset": next_page_token or 0}

    def generate_child_contexts(self, record: Record, context: Context | None) -> t.Iterable[Context | None]:
        if not record.get("sample_csv"):
            return
        wanted = self.config.get("dataset_slugs") or []
        if wanted and record["slug"] not in wanted:
            return
        yield {"slug": record["slug"]}


class DatasetSampleStream(TensorustStream):
    """Each dataset's free 25-row sample, one record per sample row (columns differ per dataset)."""

    name = "dataset_sample"
    path = "/datasets/{slug}"
    parent_stream_type = DatasetsCatalogStream
    primary_keys = ("dataset_slug", "row_number")
    replication_key = None
    state_partitioning_keys: t.ClassVar[list[str]] = []

    schema = th.PropertiesList(
        th.Property("dataset_slug", _str, required=True),
        th.Property("row_number", _int, required=True, description="1-based row number within the sample"),
        th.Property(
            "row", th.ObjectType(additional_properties=True), description="The sample row, column name to value"
        ),
    ).to_dict()

    def get_url_params(self, context: Context | None, next_page_token: t.Any | None) -> dict[str, t.Any]:
        return {"sample": 1}

    def validate_response(self, response: requests.Response) -> None:
        if response.status_code == 404:  # dataset without a published sample: skip it, do not fail the run
            return
        super().validate_response(response)

    def parse_response(self, response: requests.Response) -> t.Iterable[dict]:
        if response.status_code == 404:
            return
        reader = csv.DictReader(io.StringIO(response.text))
        for i, row in enumerate(reader, start=1):
            yield {"row_number": i, "row": {k: v for k, v in row.items() if k is not None}}

    def post_process(self, row: Record, context: Context | None = None) -> Record | None:
        row["dataset_slug"] = (context or {}).get("slug")
        return row


class CreditDisagreementsStream(TensorustStream):
    """Companies whose first-lien loan two or more BDC managers mark 10+ points apart, widest gap first."""

    name = "credit_disagreements"
    path = "/openbb/credit_disagreements"
    primary_keys = ("company", "as_of")
    replication_key = None

    schema = th.PropertiesList(
        th.Property("company", _str, required=True),
        th.Property("gap_points", _num, description="Highest minus lowest manager mark, in points of par"),
        th.Property("lowest_mark_pct_of_par", _num),
        th.Property("lowest_manager", _str),
        th.Property("highest_mark_pct_of_par", _num),
        th.Property("highest_manager", _str),
        th.Property("loan_par_usd", _num),
        th.Property("funds", _int, description="BDC funds holding the loan"),
        th.Property("as_of", th.DateType, required=True, description="10-Q period end the marks come from"),
    ).to_dict()


class Q3CutsStream(TensorustStream):
    """BDC funds that cut a first-lien mark 5+ points from Jun 30 to Sep 30 2026, from each Q3 10-Q as it posts."""

    name = "q3_cuts"
    path = "/openbb/credit_q3_cuts"
    primary_keys = ("company", "fund")
    replication_key = None

    schema = th.PropertiesList(
        th.Property("company", _str, required=True),
        th.Property("fund", _str, required=True),
        th.Property("manager", _str),
        th.Property("jun30_pct_of_par", _num),
        th.Property("sep30_pct_of_par", _num),
        th.Property("change_points", _num),
        th.Property("par_usd", _num),
        th.Property("filed", th.DateType, description="Date the Q3 10-Q was filed on EDGAR"),
        th.Property(
            "holders_not_filed_yet_above",
            _int,
            description="Holders that have not filed Q3 yet and still carry the loan 5+ points higher",
        ),
    ).to_dict()


class LenderMarksStream(TensorustStream):
    """What every BDC fund marks one company's first-lien term loan at, one record per company and fund.

    Companies come from the `companies` setting. Left unset, the tap uses the companies in the
    credit_disagreements list (top 10 without a key, the full list with one).
    """

    name = "lender_marks"
    path = "/openbb/bdc_marks"
    primary_keys = ("company", "fund", "as_of")
    replication_key = None
    state_partitioning_keys: t.ClassVar[list[str]] = []

    schema = th.PropertiesList(
        th.Property("query", _str, description="The company name the record was requested with"),
        th.Property("company", _str, required=True, description="Company name as the BDC schedules spell it"),
        th.Property("fund", _str, required=True),
        th.Property("manager", _str),
        th.Property("mark_pct_of_par", _num, description="Jun 30 2026 fair value as % of par"),
        th.Property("prior_mark_pct_of_par", _num, description="Mar 31 2026 mark (keyed)"),
        th.Property("sep30_mark_pct_of_par", _num, description="Sep 30 2026 mark once filed (keyed)"),
        th.Property("par_usd", _num, description="Fund's par (keyed)"),
        th.Property("filing", _str, description="Link to the SEC filing (keyed)"),
        th.Property("as_of", th.DateType, required=True),
    ).to_dict()

    _companies: list[str] | None = None

    def _company_list(self) -> list[str]:
        if self._companies is None:
            configured = [c.strip() for c in self.config.get("companies") or [] if c and c.strip()]
            if configured:
                self._companies = configured
            else:
                resp = self.requests_session.get(
                    f"{self.url_base}/openbb/credit_disagreements", headers=self.http_headers, timeout=60
                )
                resp.raise_for_status()
                self._companies = [r["company"] for r in resp.json() if r.get("company")]
        return self._companies

    @property
    def partitions(self) -> list[dict] | None:
        return [{"company": c} for c in self._company_list()]

    def get_url_params(self, context: Context | None, next_page_token: t.Any | None) -> dict[str, t.Any]:
        return {"company": (context or {}).get("company", "")}

    def post_process(self, row: Record, context: Context | None = None) -> Record | None:
        row["query"] = (context or {}).get("company")
        return row


class ExposureAwardsStream(TensorustStream):
    """Federal research awards whose 2025-26 papers name a vendor on a banned-vendor list.

    Default: an award search per list in `exposure_lists` (up to 50 largest awards per list, free).
    With `institutions` set: every award of each institution (the 5 largest without a key; every
    award with the evidence sentence and paper link with a key).
    """

    name = "exposure_awards"
    path = "/exposure"
    primary_keys = ("award",)
    replication_key = None
    state_partitioning_keys: t.ClassVar[list[str]] = []

    schema = th.PropertiesList(
        th.Property("award", _str, required=True, description="Award number (FAIN)"),
        th.Property("recipient", _str),
        th.Property("recipient_uei", _str),
        th.Property("state", _str),
        th.Property("agency", _str),
        th.Property("title", _str),
        th.Property("fy25_obligations", _num),
        th.Property("fy26_amount", _num),
        th.Property("project_end", th.DateType),
        th.Property("vendors", _str, description="Listed vendors named in the papers, comma separated"),
        th.Property("lists", _str, description="Banned-vendor lists those vendors are on, comma separated"),
        th.Property("rule_status", _str, description="Per-rule status, e.g. 'BIOSECURE-851: grace_eligible'"),
        th.Property("attribution", _str, description="likely_paid, narrow or broad"),
        th.Property("in_force_or_no_grace", th.BooleanType),
        th.Property("papers", _int),
        th.Property("latest_paper", th.DateType),
        th.Property("evidence", _str, description="Methods sentence naming the vendor (keyed institution pulls)"),
        th.Property("evidence_paper", _str),
        th.Property("source_query", _str, description="list:<LIST> or institution:<name> that returned the award"),
    ).to_dict()

    _seen: set[str] | None = None

    @property
    def partitions(self) -> list[dict] | None:
        institutions = [i.strip() for i in self.config.get("institutions") or [] if i and i.strip()]
        if institutions:
            return [{"institution": i} for i in institutions]
        lists = self.config.get("exposure_lists") or EXPOSURE_LISTS
        return [{"list": str(x).upper()} for x in lists]

    def get_url(self, context: Context | None) -> str:
        if (context or {}).get("institution"):
            return f"{self.url_base}/openbb/exposure_institution"
        return f"{self.url_base}/exposure"

    def get_url_params(self, context: Context | None, next_page_token: t.Any | None) -> dict[str, t.Any]:
        ctx = context or {}
        if ctx.get("institution"):
            return {"institution": ctx["institution"]}
        return {"search": 1, "list": ctx.get("list", ""), "limit": 50}

    def parse_response(self, response: requests.Response) -> t.Iterable[dict]:
        body = response.json()
        rows = body if isinstance(body, list) else body.get("items", [])
        yield from rows

    def post_process(self, row: Record, context: Context | None = None) -> Record | None:
        if self._seen is None:
            self._seen = set()
        if row.get("award") in self._seen:  # the same award can sit on two lists
            return None
        self._seen.add(row.get("award"))
        for k in ("vendors", "lists"):
            if isinstance(row.get(k), list):
                row[k] = ", ".join(row[k])
        rules = row.pop("rules", None)
        if isinstance(rules, dict) and "rule_status" not in row:
            row["rule_status"] = "; ".join(f"{k}: {v}" for k, v in rules.items())
        flag = row.get("in_force_or_no_grace")
        if isinstance(flag, str):
            row["in_force_or_no_grace"] = flag.lower() in ("yes", "true", "1")
        ctx = context or {}
        row["source_query"] = (
            f"institution:{ctx['institution']}" if ctx.get("institution") else f"list:{ctx.get('list')}"
        )
        return {k: row.get(k) for k in self.schema["properties"]}
