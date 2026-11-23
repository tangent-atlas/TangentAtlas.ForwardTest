"""Reading EODHD's fundamentals answer, as the ranking does. No network."""
import datetime as dt

from forward import eodhd

ON = dt.date(2026, 11, 23)
GENERAL = {"Name": "Example Inc", "Type": "Common Stock", "CountryISO": "US", "Exchange": "NYSE", "CIK": "0000123"}


def test_the_latest_shares_reported_on_or_before_the_date():
    data = {"General": GENERAL, "outstandingShares": {"quarters": {
        "0": {"dateFormatted": "2026-06-30", "shares": 1000},
        "1": {"dateFormatted": "2026-09-30", "shares": "1100"},
        "2": {"dateFormatted": "2026-12-31", "shares": 1200}}}}          # after the date: not yet reported
    info = eodhd.parse_company("EX", data, ON)
    assert info["shares"] == 1100 and info["cik"] == "123" and info["type"] == "Common Stock"


def test_share_counts_that_are_not_the_usual_table_leave_a_listing_unranked(capsys):
    for odd in ["NA", "", None, [], {"quarters": "NA"}, {"quarters": [{"dateFormatted": "2026-09-30", "shares": "NA"}]}]:
        info = eodhd.parse_company("ODD", {"General": GENERAL, "outstandingShares": odd}, ON)
        assert info["shares"] == 0.0 and info["name"] == "Example Inc"
    assert "ODD" in capsys.readouterr().out


def test_a_list_of_quarters_is_read_like_a_table():
    data = {"General": GENERAL, "outstandingShares": {"quarters": [{"dateFormatted": "2026-09-30", "shares": 900}]}}
    assert eodhd.parse_company("EX", data, ON)["shares"] == 900


def test_an_answer_that_is_not_an_object_at_all():
    assert eodhd.parse_company("EX", "NA", ON)["shares"] == 0.0
    assert eodhd.parse_company("EX", {"General": "NA"}, ON)["name"] == ""
