"""Reading EODHD's fundamentals answers, as the ranking does (and as the backtest's loader does). No network."""
import datetime as dt

import pytest

from forward import eodhd, tiers, rules

ON = dt.date(2026, 11, 23)
GENERAL = {"Name": "Example Inc", "Type": "Common Stock", "CountryISO": "US", "Exchange": "NYSE", "CIK": "0000123"}


def test_the_latest_quarterly_shares_reported_on_or_before_the_date():
    shares = {"annual": {"0": {"dateFormatted": "2025-12-31", "shares": 900}}, "quarterly": {
        "0": {"dateFormatted": "2026-06-30", "shares": 1000},
        "1": {"dateFormatted": "2026-09-30", "shares": "1100"},
        "2": {"dateFormatted": "2026-12-31", "shares": 1200}}}          # after the date: not yet reported
    info = eodhd.parse_company("EX", GENERAL, shares, ON)
    assert info["shares"] == 1100 and info["cik"] == "123" and info["type"] == "Common Stock"


def test_company_asks_for_general_and_shares_separately(monkeypatch):
    asked = []
    def get(path, **params):
        asked.append(params["filter"])
        return GENERAL if params["filter"] == "General" else {"quarterly": {"0": {"dateFormatted": "2026-09-30", "shares": 5}}}
    monkeypatch.setattr(eodhd, "_get", get)
    assert eodhd.company("EX", ON)["shares"] == 5
    assert asked == ["General", "outstandingShares"]


def test_share_counts_that_are_not_the_usual_table_leave_a_listing_unranked(capsys):
    for odd in ["NA", "", None, [], {"quarterly": "NA"}, {"quarterly": [{"dateFormatted": "2026-09-30", "shares": "NA"}]}]:
        info = eodhd.parse_company("ODD", GENERAL, odd, ON)
        assert info["shares"] == 0.0 and info["name"] == "Example Inc"
    assert "ODD" in capsys.readouterr().out


def test_a_list_of_quarters_is_read_like_a_table():
    assert eodhd.parse_company("EX", GENERAL, {"quarterly": [{"dateFormatted": "2026-09-30", "shares": 900}]}, ON)["shares"] == 900


def test_an_answer_that_is_not_an_object_at_all():
    assert eodhd.parse_company("EX", "NA", "NA", ON) == {"name": "", "type": "", "country": "", "exchange": "", "cik": "",
                                                          "shares": 0.0}


def stock(code, shares, kind="Common Stock", country="US"):
    return rules.Candidate(code, code, code, kind, country, "NYSE", 100.0, 1e6, shares)


def test_missing_share_counts_for_the_pools_us_common_stocks_stop_the_run():
    pool = [stock(f"S{i}", 1e9) for i in range(20)] + [stock("ADR", 0, country="TW"), stock("ETF", 0, kind="ETF")]
    tiers.check_share_counts(ON, pool)                                   # foreign listings and funds may lack them
    tiers.check_share_counts(ON, pool + [stock("GAP", 0)])               # one in 21: within the limit
    with pytest.raises(RuntimeError, match="AAPL"):
        tiers.check_share_counts(ON, pool + [stock("AAPL", 0), stock("MSFT", 0), stock("NVDA", 0)])


def test_the_country_is_the_head_office_not_the_listing():
    """EODHD sets CountryISO to "US" for every US listing; the address says where the company is."""
    taiwan = {**GENERAL, "AddressData": {"City": "Hsinchu City", "Country": "Taiwan"}}
    assert eodhd.parse_company("TSM", taiwan, {}, ON)["country"] == "Taiwan"
    for name in ["United States", "USA", "united states of america"]:
        assert eodhd.parse_company("EX", {**GENERAL, "AddressData": {"Country": name}}, {}, ON)["country"] == "US"
    assert eodhd.parse_company("EX", GENERAL, {}, ON)["country"] == ""            # no address: not known, so not excluded
    assert eodhd.parse_company("EX", {**GENERAL, "AddressData": "NA"}, {}, ON)["country"] == ""


def test_the_vendors_adr_flag_marks_a_depositary_receipt():
    for flag in ["ADR", "ADR Primary"]:
        info = eodhd.parse_company("TSM", {**GENERAL, "HomeCategory": flag}, {}, ON)
        assert info["type"] == "Depositary Receipt" and not rules.eligible(
            rules.Candidate("TSM", "1", info["name"], info["type"], "US", "NYSE", 100.0, 1e6, 1e9))
    for flag in ["Domestic", "Domestic Primary", None]:
        assert eodhd.parse_company("EX", {**GENERAL, "HomeCategory": flag}, {}, ON)["type"] == "Common Stock"
