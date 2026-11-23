"""The tiers (PREREGISTRATION-TIERS.md): the Joe 10's rules with 25, 50 and 100 companies, and the ranking archive. No network."""
import csv
import datetime as dt
import hashlib

from forward import common, tiers
from tests.test_joe10 import FakeMarket


def setup(tmp_path, monkeypatch, end):
    codes = [f"C{i:03d}" for i in range(120)] + ["SPY"]
    market = FakeMarket(codes, end, holidays={dt.date(2026, 11, 26)})
    monkeypatch.setattr(common.eodhd, "daily", market.daily)
    monkeypatch.setattr(common.eodhd, "largest", market.largest)
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
        assert int(r["listings"]) == 120


def test_rankings_are_archived_even_before_any_tier_starts(tmp_path, monkeypatch):
    market, today = setup(tmp_path, monkeypatch, dt.date(2027, 1, 15))
    tiers._save(tiers.ARCHIVE_STATE, {"last_date": "2026-11-24"})
    today.value = dt.date(2026, 12, 14)
    tiers.daily()
    rows = list(csv.DictReader((tmp_path / "archive" / "hashes.csv").open()))
    assert [(r["ranked"], r["purpose"]) for r in rows] == [("2026-12-11", "quarterly ranking 2026-12")]
