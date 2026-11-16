"""Shared REST client for the Tensorust Data API (https://shop.tensorust.com/api)."""

from __future__ import annotations

import typing as t
from importlib import metadata

from singer_sdk.streams import RESTStream

if t.TYPE_CHECKING:
    from singer_sdk.helpers.types import Context

DEFAULT_API_URL = "https://shop.tensorust.com/api"

try:
    _VERSION = metadata.version("tap-tensorust")
except metadata.PackageNotFoundError:  # running from a source checkout
    _VERSION = "0.0.0"


class TensorustStream(RESTStream):
    """Base stream: one base URL, an optional Tensorust key sent as a bearer token.

    Without a key every endpoint answers a free preview (for example the top 10 rows).
    With a Tensorust enterprise key (tdk_...) the same endpoints answer the full rows.
    """

    records_jsonpath = "$[*]"

    @property
    def url_base(self) -> str:
        return str(self.config.get("api_url") or DEFAULT_API_URL).rstrip("/")

    @property
    def http_headers(self) -> dict:
        headers = {"User-Agent": f"tap-tensorust/{_VERSION}", "Accept": "application/json, text/csv"}
        key = self.config.get("api_key")
        if key:
            headers["Authorization"] = f"Bearer {key}"
        return headers

    @property
    def keyed(self) -> bool:
        """True when a key is configured (the API decides whether it unlocks full rows)."""
        return bool(self.config.get("api_key"))

    def get_url_params(self, context: Context | None, next_page_token: t.Any | None) -> dict[str, t.Any]:
        return {}
