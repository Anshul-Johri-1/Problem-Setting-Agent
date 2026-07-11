"""Request signing and transport for the Polygon API.

Signing recipe (verified 2026-07-11 against the Codeforces API help page and
cross-checked against polyman's reference implementation):

    apiSig = <rand> + sha512_hex( "<rand>/<methodName>?<sorted_params>#<apiSecret>" )

where:
  * <rand> is a 6-character random prefix.
  * <sorted_params> includes every request param PLUS `apiKey` and `time`,
    EXCLUDES `apiSig` itself, sorted lexicographically by name (then by value;
    a param dict has unique names so the value tiebreak never actually triggers).
  * the params in the *hashed string* use RAW (un-URL-encoded) values.
  * the params in the *actual POST body* are URL-encoded normally.

Two things that are easy to get wrong and are deliberately handled here:
  1. The hash is over raw values; the body is encoded. `requests` encodes the
     body for us, and we build the hash string from raw values separately.
  2. `time` is computed ONCE and reused for both the signature and the body.
     (polyman computes it twice, which can desync by a second at a tick
     boundary and produce a spurious signature mismatch.)

Requests are POST application/x-www-form-urlencoded because sources (statement
text, solution/generator files) are far too large for a query string.
"""

from __future__ import annotations

import hashlib
import os
import random
import string
from dataclasses import dataclass
from typing import Any, Mapping

import requests

DEFAULT_BASE_URL = "https://polygon.codeforces.com/api"
_RAND_ALPHABET = string.ascii_lowercase + string.digits


class PolygonAPIError(RuntimeError):
    """Raised when the API returns status=FAILED or a transport error occurs."""

    def __init__(self, method: str, message: str, *, http_status: int | None = None):
        self.method = method
        self.http_status = http_status
        super().__init__(f"{method}: {message}")


def _to_str(value: Any) -> str:
    """Match polyman/JS coercion: booleans become 'true'/'false', not 'True'."""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


@dataclass
class PolygonSession:
    api_key: str
    api_secret: str
    base_url: str = DEFAULT_BASE_URL
    timeout: int = 60

    # ------------------------------------------------------------------ #
    # Construction
    # ------------------------------------------------------------------ #
    @classmethod
    def from_env(cls) -> "PolygonSession":
        """Build a session from environment variables.

        Reads POLYGON_API_KEY and POLYGON_API_SECRET directly from the
        environment. The raw secret is never returned, logged, or exposed to
        callers beyond its use inside the signing function.
        """
        key = os.environ.get("POLYGON_API_KEY", "").strip()
        secret = os.environ.get("POLYGON_API_SECRET", "").strip()
        if not key or not secret:
            raise PolygonAPIError(
                "auth",
                "POLYGON_API_KEY / POLYGON_API_SECRET missing from environment. "
                "Copy .env.example to .env and fill them in.",
            )
        base = os.environ.get("POLYGON_API_BASE_URL", DEFAULT_BASE_URL).strip()
        return cls(api_key=key, api_secret=secret, base_url=base or DEFAULT_BASE_URL)

    # ------------------------------------------------------------------ #
    # Signing
    # ------------------------------------------------------------------ #
    def _signature(self, method: str, params: Mapping[str, str], rand: str) -> str:
        # `params` here already includes apiKey and time, excludes apiSig.
        sorted_pairs = sorted(params.items())  # (name, value); names are unique
        param_string = "&".join(f"{k}={v}" for k, v in sorted_pairs)
        to_hash = f"{rand}/{method}?{param_string}#{self.api_secret}"
        digest = hashlib.sha512(to_hash.encode("utf-8")).hexdigest()
        return rand + digest

    def _build_params(self, method: str, params: Mapping[str, Any]) -> dict[str, str]:
        """Return the full string-valued param dict, apiSig included."""
        import time as _time

        now = str(int(_time.time()))
        base = {k: _to_str(v) for k, v in params.items()}
        base["apiKey"] = self.api_key
        base["time"] = now

        rand = "".join(random.choices(_RAND_ALPHABET, k=6))
        base["apiSig"] = self._signature(method, base, rand)
        return base

    # ------------------------------------------------------------------ #
    # Transport
    # ------------------------------------------------------------------ #
    def call(self, method: str, params: Mapping[str, Any] | None = None, *, raw: bool = False):
        """Invoke a Polygon API method. Returns parsed `result` (or raw text).

        Raises PolygonAPIError on FAILED status or transport failure. The raw
        request/response should be logged by the caller (audit trail, §7); this
        layer never logs the secret.
        """
        params = params or {}
        signed = self._build_params(method, params)
        url = f"{self.base_url}/{method}"
        try:
            resp = requests.post(
                url,
                data=signed,  # requests URL-encodes the body for us
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise PolygonAPIError(method, f"transport error: {exc}") from exc

        if raw:
            if resp.status_code != 200:
                raise PolygonAPIError(
                    method,
                    f"HTTP {resp.status_code}: {resp.text[:500]}",
                    http_status=resp.status_code,
                )
            return resp.content

        # Polygon returns JSON envelopes: {"status": "OK"|"FAILED", ...}
        try:
            data = resp.json()
        except ValueError:
            raise PolygonAPIError(
                method,
                f"non-JSON response (HTTP {resp.status_code}): {resp.text[:500]}",
                http_status=resp.status_code,
            )

        if data.get("status") == "FAILED":
            raise PolygonAPIError(method, data.get("comment", "unknown error"),
                                  http_status=resp.status_code)
        return data.get("result")
