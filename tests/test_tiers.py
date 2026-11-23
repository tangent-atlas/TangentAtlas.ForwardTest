"""The tiers (PREREGISTRATION-TIERS.md): the Joe 10's rules with 25, 50 and 100 companies, and the ranking archive. No network."""
import csv
import datetime as dt
import hashlib

from forward import common, tiers
from tests.test_joe10 import FakeMarket


def setup(tmp_path, monkeypatch, end):
    codes = [f"C{i:03d}" for i in range(320)] + ["SPY"]
    market = FakeMarket(codes, end, holidays={dt.date(2026, 11, 26)})
    monkeypatch.setattr(common.eodhd, "daily", market.daily)
    stocks = [c for c in codes if c != "SPY"]
    by_exchange = {"NYSE": [(c, 1e12 - i) for i, c in enumerate(stocks) if i % 2 == 0],
                   "NASDAQ": [(c, 1e12 - i) for i, c in enumerate(stocks) if i % 2 == 1]}
    pages = []
    def listings(exchange, limit=100, offset=0):     # the screener, one exchange at a time: at most 100 rows a request
        assert limit <= 100
        pages.append((exchange, offset))
        return by_exchange[exchange][offset:offset + limit]
    monkeypatch.setattr(common.eodhd, "listings", listings)
    market.pages = pages
    monkeypatch.setattr(common.eodhd, "company", market.company)
    monkeypatch.setattr(tiers, "STATE_DIR", tmp_path / "state")
    monkeypatch.setattr(tiers, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(tiers, "REPORTS", tmp_path / "reports")
    monkeypatch.setattr(tiers, "HASHES", tmp_path / "archive" / "hashes.csv")
    monkeypatch.setattr(tiers, "ARCHIVE_STATE", tmp_path / "state" / "archive.json")
    monkeypatch.setenv("ARCHIVE_DIR", str(tmp_path / "private"))
    tiers._candidates.clear()

    class Today(dt.date):
        value = dt.date(2026, 11, 24)
        @classmethod
        def today(cls):
            return cls.value
    monkeypatch.setattr(common.dt, "date", Today)
    return market, Today


def test_each_tier_starts_after_freezing_holds_its_size_and_rebalances_in_december(tmp_path, monkeypatch):
    market, today = setup(tmp_path, monkeypatch, dt.date(2027, 1, 15))
    tiers.init()
    for name, size in tiers.TIERS.items():
        state = tiers._load(tiers.state_path(name))
        assert state["started"] is None and state["ranked_at_start"] == "2026-11-23"
        assert len(state["portfolio"]["weights"]) == size

    today.value = dt.date(2026, 12, 31)
    tiers._candidates.clear()                      # a later run starts with nothing in memory
    tiers.daily()
    today.value = dt.date(2027, 1, 15)
    tiers.daily()                                  # the first run in January writes December's report
    for name, size in tiers.TIERS.items():
        state = tiers._load(tiers.state_path(name))
        assert state["started"] == "2026-11-25"     # the first close after the day it was frozen
        assert "rebalance 2026-12" in state["done"]
        assert len(state["portfolio"]["weights"]) == size
        with tiers.track_path(name).open() as f:
            assert len(f.readlines()) > 25
    assert dt.date(2026, 12, 11) in market.ranked_on
    assert set(market.pages) == {("NYSE", 0), ("NYSE", 100), ("NASDAQ", 0), ("NASDAQ", 100)}   # read only as far as needed
    assert (tmp_path / "reports" / "joe50-2026-12.md").exists()


def test_every_ranking_is_archived_privately_and_its_hash_published_once(tmp_path, monkeypatch):
    market, today = setup(tmp_path, monkeypatch, dt.date(2027, 1, 15))
    tiers.init(["joe25"])
    today.value = dt.date(2027, 1, 15)
    tiers._candidates.clear()
    tiers.daily()
    tiers._candidates.clear()
    tiers.daily()                                  # a second run the same day publishes nothing new
    rows = list(csv.DictReader((tmp_path / "archive" / "hashes.csv").open()))
    assert [r["ranked"] for r in rows] == ["2026-11-23", "2026-12-11"]
    for r in rows:
        body = (tmp_path / "private" / r["file"]).read_bytes()
        assert hashlib.sha256(body).hexdigest() == r["sha256"]
        assert int(r["listings"]) == 300


def test_rankings_are_archived_even_before_any_tier_starts(tmp_path, monkeypatch):
    market, today = setup(tmp_path, monkeypatch, dt.date(2027, 1, 15))
    tiers._save(tiers.ARCHIVE_STATE, {"last_date": "2026-11-24"})
    today.value = dt.date(2026, 12, 14)
    tiers.daily()
    rows = list(csv.DictReader((tmp_path / "archive" / "hashes.csv").open()))
    assert [(r["ranked"], r["purpose"]) for r in rows] == [("2026-12-11", "quarterly ranking 2026-12")]


def test_a_ranking_that_cannot_fill_a_tier_stops_the_run(tmp_path, monkeypatch):
    import pytest
    from forward import rules
    setup(tmp_path, monkeypatch, dt.date(2026, 11, 23))
    few = [rules.Candidate(f"S{i}", f"S{i}", f"S{i}", "Common Stock", "US", "NYSE", 100.0, 1e6, 1e9) for i in range(60)]
    monkeypatch.setattr(tiers, "candidates_as_of", lambda day, purpose: tiers._candidates.setdefault(day, few))
    assert len(tiers.ranking(dt.date(2026, 12, 11), 50, "test")["shares"]) == 50
    with pytest.raises(RuntimeError, match="found 60 eligible"):
        tiers.ranking(dt.date(2026, 12, 11), 100, "test")


def test_the_pool_is_the_300_largest_companies_the_rules_accept(tmp_path, monkeypatch):
    """Listings the rules exclude (here every 20th, a depositary receipt; and a young listing) don't count toward the 300,
    and share classes of one company count once; the walk goes as far down the list as it must."""
    market, today = setup(tmp_path, monkeypatch, dt.date(2026, 11, 23))
    company = market.company
    def mixed(code, on):
        info = company(code, on)
        i = int(code[1:])
        if i % 20 == 0:
            info = {**info, "type": "Depositary Receipt"}
        if code == "C002":
            info = {**info, "cik": "C001"}               # a second share class of C001
        return info
    monkeypatch.setattr(common.eodhd, "company", mixed)
    market.series["C003"] = {d: v for d, v in market.series["C003"].items() if d >= dt.date(2026, 6, 1)}   # a new listing
    pool = tiers.candidates_as_of(dt.date(2026, 11, 20), "test")
    from forward import rules
    eligible = [c for c in pool if rules.eligible(c)]
    assert len({c.cik for c in eligible}) == 300
    assert len(pool) == 318 and pool[-1].code == "C317"     # 16 depositary receipts, one young listing, one second class
    assert all(not rules.eligible(c) for c in pool if c.code in ("C000", "C020", "C003"))


def test_too_few_eligible_companies_stops_the_run(tmp_path, monkeypatch):
    import pytest
    market, today = setup(tmp_path, monkeypatch, dt.date(2026, 11, 23))
    company = market.company
    monkeypatch.setattr(common.eodhd, "company",
                        lambda code, on: {**company(code, on), "type": "Depositary Receipt" if int(code[1:]) % 3 == 0 else "Common Stock"})
    with pytest.raises(RuntimeError, match="Only 213 companies"):
        tiers.candidates_as_of(dt.date(2026, 11, 20), "test")
