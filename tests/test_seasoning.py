"""The seasoning rule (amendment of November 23, 2026): a listing is ranked once it has traded for 12 months. No network."""
import datetime as dt

from forward import common, joe10, rules
from tests.test_joe10 import FakeMarket


def test_the_seasoning_date_is_twelve_months_earlier():
    assert rules.seasoning_date(dt.date(2026, 12, 11)) == dt.date(2025, 12, 11)
    assert rules.seasoning_date(dt.date(2028, 2, 29)) == dt.date(2027, 2, 28)
    assert rules.seasoning_date(dt.date(2027, 1, 8)) == dt.date(2026, 1, 8)


def test_a_listing_that_has_not_traded_for_twelve_months_is_not_eligible():
    young = rules.Candidate("NEW", "1", "New Corp", "Common Stock", "US", "NASDAQ", 100.0, 1e6, 1e10, seasoned=False)
    assert not rules.eligible(young)
    assert rules.rank([young, rules.Candidate("OLD", "2", "Old Corp", "Common Stock", "US", "NYSE", 1.0, 1e6, 1e9)], 10) == \
        [("OLD", 1e9)]


def test_candidates_are_seasoned_by_their_first_close(monkeypatch):
    day = dt.date(2026, 12, 11)
    market = FakeMarket(["OLD", "EDGE", "NEW", "GONE"], day,
                        listed={"EDGE": dt.date(2025, 12, 11), "NEW": dt.date(2025, 12, 12)})
    market.series["GONE"] = {d: v for d, v in market.series["GONE"].items() if d < dt.date(2026, 11, 1)}   # stopped trading
    monkeypatch.setattr(common.eodhd, "daily", market.daily)
    monkeypatch.setattr(common.eodhd, "company", market.company)
    got = {c: common.candidate(c, day) for c in ["OLD", "EDGE", "NEW", "GONE"]}
    assert got["OLD"].seasoned and got["EDGE"].seasoned and not got["NEW"].seasoned
    assert got["GONE"] is None


def test_the_joe10_ranking_leaves_out_a_young_giant(monkeypatch):
    day = dt.date(2026, 12, 11)
    codes = [f"C{i:02d}" for i in range(12)] + ["GIANT"]
    market = FakeMarket(codes, day, listed={"GIANT": dt.date(2026, 6, 12)})
    company = market.company
    market.company = lambda code, on: {**company(code, on), "shares": 1e12 if code == "GIANT" else 1e9}
    monkeypatch.setattr(common.eodhd, "daily", market.daily)
    monkeypatch.setattr(common.eodhd, "company", market.company)
    monkeypatch.setattr(common.eodhd, "largest", lambda limit=100, offset=0: codes)
    ranked = joe10.rank_as_of(day)
    assert "GIANT" not in ranked["shares"] and len(ranked["shares"]) == 10
