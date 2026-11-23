"""EODHD, the one data source. The API token comes from the EODHD_API_TOKEN environment variable (a GitHub secret in the
workflow); it is never written to a file or a log. Raw vendor data is used in memory only: the repository publishes the
track's own values, never EODHD's prices."""
from __future__ import annotations

import datetime as dt
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://eodhd.com/api/"


def _get(path: str, **params) -> object:
    token = os.environ.get("EODHD_API_TOKEN")
    if not token:
        raise RuntimeError("EODHD_API_TOKEN is not set.")
    query = urllib.parse.urlencode({**params, "api_token": token, "fmt": "json"})
    url = BASE + path + "?" + query
    for attempt in range(6):
        try:
            with urllib.request.urlopen(url, timeout=60) as response:
                return json.load(response)
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < 5:
                time.sleep(2 ** (attempt + 1))
                continue
            raise RuntimeError(f"EODHD {path} returned {e.code}.") from None   # the URL holds the token: never shown


def symbol(code: str) -> str:
    return code + ".US"


def daily(code: str, start: dt.date, end: dt.date) -> dict[dt.date, dict]:
    """Closing price, adjusted close (dividends and splits) and volume, by date."""
    rows = _get("eod/" + symbol(code), **{"from": start.isoformat(), "to": end.isoformat()})
    return {dt.date.fromisoformat(r["date"]): {"close": float(r["close"]), "adjusted": float(r["adjusted_close"]),
                                              "volume": float(r.get("volume") or 0)} for r in rows}


def largest(limit: int = 100, offset: int = 0) -> list[str]:
    """The largest US listings by the vendor's market capitalization: the pool the ranking draws from. The screener returns
    at most 100 rows a request; `offset` pages past them (the Joe 10 uses the first page only)."""
    rows = _get("screener", sort="market_capitalization.desc", filters=json.dumps([["exchange", "=", "us"]]),
                limit=limit, offset=offset)
    return [r["code"].replace(".", "-") for r in rows.get("data", [])]


def company(code: str, on: dt.date) -> dict:
    """Name, type, country, exchange, CIK, and shares outstanding as last reported on or before `on`."""
    data = _get("fundamentals/" + symbol(code), filter="General,outstandingShares")
    return parse_company(code, data, on)


def _table(value) -> dict:
    """A field EODHD normally sends as an object; anything else (text such as "NA", a list, nothing) as an empty one."""
    return value if isinstance(value, dict) else {}


def parse_company(code: str, data, on: dt.date) -> dict:
    """The fundamentals answer, read defensively: a listing whose share counts aren't the usual table has no reported
    shares, so the rules can't rank it (rules.eligible requires shares above zero). It is named in the log."""
    data = _table(data)
    general = _table(data.get("General"))
    quarters = _table(data.get("outstandingShares")).get("quarters")
    rows = quarters.values() if isinstance(quarters, dict) else quarters if isinstance(quarters, list) else []
    reported = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        try:
            day = dt.date.fromisoformat(row["dateFormatted"])
            shares = float(row.get("shares") or 0)
        except (KeyError, TypeError, ValueError):
            continue
        if day <= on and shares > 0:
            reported.append((day, shares))
    if not reported:
        print(f"No shares outstanding reported for {code} on or before {on}; it can't be ranked.")
    return {
        "name": general.get("Name") or "",
        "type": general.get("Type") or "",
        "country": general.get("CountryISO") or "",
        "exchange": general.get("Exchange") or "",
        "cik": str(general.get("CIK") or "").lstrip("0"),
        "shares": max(reported)[1] if reported else 0.0,
    }
