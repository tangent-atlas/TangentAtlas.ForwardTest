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


def listings(exchange: str, limit: int = 100, offset: int = 0) -> list[tuple[str, float]]:
    """One exchange's listings (NYSE or NASDAQ), largest first by the vendor's market capitalization, as (code, market cap).
    The screener's "us" filter also returns over-the-counter lines (foreign companies' ordinary shares and depositary
    receipts on the pink sheets); asking for one exchange at a time leaves them out."""
    rows = _get("screener", sort="market_capitalization.desc", filters=json.dumps([["exchange", "=", exchange]]),
                limit=limit, offset=offset)
    return [(r["code"].replace(".", "-"), float(r.get("market_capitalization") or 0)) for r in rows.get("data", [])]


def company(code: str, on: dt.date) -> dict:
    """Name, type, country, exchange, CIK, and shares outstanding as last reported on or before `on`. Two requests, as the
    backtest's loader makes them (TangentAtlas.Backtest, Eodhd.cs): `filter=General` answers with the General object
    itself, and `filter=outstandingShares` with {"annual": ..., "quarterly": ...}."""
    general = _get("fundamentals/" + symbol(code), filter="General")
    shares = _get("fundamentals/" + symbol(code), filter="outstandingShares")
    return parse_company(code, general, shares, on)


def _table(value) -> dict:
    """A field EODHD normally sends as an object; anything else (text such as "NA", a list, nothing) as an empty one."""
    return value if isinstance(value, dict) else {}


US_NAMES = {"US", "USA", "UNITED STATES", "UNITED STATES OF AMERICA"}


def head_office(general: dict) -> str:
    """The company's head-office country from its address: "US" for the United States, otherwise the country as the vendor
    names it, "" when there is no address. Not CountryISO, which EODHD sets to "US" for every listing on a US exchange
    (Taiwan Semiconductor included; found November 23, 2026)."""
    country = str(_table(general.get("AddressData")).get("Country") or "").strip()
    return "US" if country.upper() in US_NAMES else country


def parse_company(code: str, general, shares, on: dt.date) -> dict:
    """The two fundamentals answers, read defensively: a listing whose share counts aren't the usual table has no reported
    shares, so the rules can't rank it (rules.eligible requires shares above zero). It is named in the log."""
    general = _table(general)
    shares = _table(shares)
    quarterly = shares.get("quarterly", shares.get("quarters"))
    rows = quarterly.values() if isinstance(quarterly, dict) else quarterly if isinstance(quarterly, list) else []
    reported = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        try:
            day = dt.date.fromisoformat(row["dateFormatted"])
            count = float(row.get("shares") or 0)
        except (KeyError, TypeError, ValueError):
            continue
        if day <= on and count > 0:
            reported.append((day, count))
    if not reported:
        print(f"No shares outstanding reported for {code} on or before {on}; it can't be ranked.")
    return {
        "name": general.get("Name") or "",
        "type": "Depositary Receipt" if str(general.get("HomeCategory") or "").upper().startswith("ADR")
                else general.get("Type") or "",
        "country": head_office(general),
        "exchange": general.get("Exchange") or "",
        "cik": str(general.get("CIK") or "").lstrip("0"),
        "shares": max(reported)[1] if reported else 0.0,
    }
