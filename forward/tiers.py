"""The personal-index tiers: the Joe 25, Joe 50 and Joe 100 (PREREGISTRATION-TIERS.md), beside the Joe 10.

    python -m forward.tiers init      # freeze every tier not yet started: ranked at the latest close, started at the next
    python -m forward.tiers daily     # archive any quarterly ranking that has closed, then bring each tier up to date

Each tier is the Joe 10's rules with a different number of companies, ranked from a wider pool: the 300 largest companies on
the NYSE and Nasdaq that the rules accept (US head office, common stock, not a depositary receipt, 12 months of trading). The
rules run through the Joe 10's own code (`joe10.Portfolio`, `rules`).
State in state/<tier>.json, the series in data/<tier>.csv, monthly reports in reports/<tier>-YYYY-MM.md.

The ranking archive: at every quarterly ranking (and each tier's start) the full ranking inputs of every listing examined are
written to ARCHIVE_DIR (default archive-private/, never committed: it holds EODHD's prices, which are licensed), and the file's
SHA-256 is appended to archive/hashes.csv, which is public. Anyone later shown an archive file can check it against the hash
published on the day, so a model rebuilt from it (any number of companies, any risk setting) had no look-ahead.
"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import heapq
import json
import os
import sys
from pathlib import Path

from . import common, eodhd, joe10, rules

# The tiers (frozen in PREREGISTRATION-TIERS.md): name -> number of companies.  Every other rule is the Joe 10's.
TIERS = {"joe25": 25, "joe50": 50, "joe100": 100}
LABELS = {"joe25": "Joe 25", "joe50": "Joe 50", "joe100": "Joe 100"}
POOL = 300                    # eligible companies the ranking draws from: the largest on EXCHANGES that the rules accept
EXCHANGES = ("NYSE", "NASDAQ")
BACKFILL_DAYS = 45            # calendar days held fully invested before the start, to give the thermostat its 21 returns

ROOT = common.ROOT
STATE_DIR = ROOT / "state"
DATA_DIR = ROOT / "data"
REPORTS = ROOT / "reports"
HASHES = ROOT / "archive" / "hashes.csv"
ARCHIVE_STATE = ROOT / "state" / "archive.json"
HASH_FIELDS = ["ranked", "purpose", "file", "sha256", "listings"]

_candidates: dict[dt.date, list[rules.Candidate]] = {}


def archive_dir() -> Path:
    return Path(os.environ.get("ARCHIVE_DIR") or ROOT / "archive-private")


def state_path(name: str) -> Path:
    return STATE_DIR / f"{name}.json"


def track_path(name: str) -> Path:
    return DATA_DIR / f"{name}.csv"


def _load(path: Path) -> dict:
    return json.loads(path.read_text())


def _save(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")


def listings_by_value():
    """Every NYSE and Nasdaq listing, largest first by the vendor's market capitalization (the two exchanges merged), each
    once; the screener's pages (100 rows at most) are fetched only as far as they are read."""
    def exchange(name):
        offset = 0
        while True:
            page = eodhd.listings(name, 100, offset)
            yield from page
            if len(page) < 100:
                return
            offset += 100
    seen = set()
    for code, _ in heapq.merge(*(exchange(name) for name in EXCHANGES), key=lambda row: -row[1]):
        if code not in seen:
            seen.add(code)
            yield code


def candidates_as_of(day: dt.date, purpose: str) -> list[rules.Candidate]:
    """The pool at `day`'s close: listings examined in order of market value until POOL companies pass the rules (share
    classes of one company count once). Every listing examined is kept with its inputs, fetched once per run, and archived
    (with the hash published)."""
    if day in _candidates:
        return _candidates[day]
    candidates, companies = [], set()
    for code in listings_by_value():
        c = common.candidate(code, day)
        if c is None:
            continue
        candidates.append(c)
        if rules.eligible(c, joe10.EXCLUDED):
            companies.add(c.cik or c.code)
            if len(companies) == POOL:
                break
    else:
        raise RuntimeError(f"Only {len(companies)} companies on the NYSE and Nasdaq pass the rules on {day}; the pool is {POOL}.")
    check_share_counts(day, candidates)
    _candidates[day] = candidates
    _archive(day, purpose, candidates)
    return candidates


MISSING_LIMIT = 0.10          # more than this share of the pool's US common stocks without share counts stops the run


def check_share_counts(day: dt.date, candidates: list[rules.Candidate]) -> None:
    """A data problem stops the run, naming what is missing, instead of quietly leaving companies out of the index."""
    common_us = [c for c in candidates if c.security_type.lower() == "common stock" and c.country.upper() in ("US", "")]
    missing = [c.code for c in common_us if c.shares <= 0]
    if not common_us or len(missing) > MISSING_LIMIT * len(common_us):
        raise RuntimeError(f"Share counts are missing for {len(missing)} of {len(common_us)} US common stocks in the pool on "
                           f"{day} ({', '.join(missing[:20])}{' ...' if len(missing) > 20 else ''}): check EODHD before ranking.")


def _archive(day: dt.date, purpose: str, candidates: list[rules.Candidate]) -> None:
    ranked = {code: i + 1 for i, (code, _) in enumerate(rules.rank(candidates, len(candidates)))}
    rows = [{"code": c.code, "cik": c.cik, "name": c.name, "type": c.security_type, "country": c.country,
             "exchange": c.exchange, "close": c.close, "volume": c.volume, "shares": c.shares, "seasoned": c.seasoned, "value": c.value,
             "rank": ranked.get(c.code)} for c in sorted(candidates, key=lambda c: c.code)]
    body = json.dumps({"ranked": day.isoformat(), "pool": POOL, "exchanges": list(EXCHANGES), "listings": rows}, indent=1, sort_keys=True).encode() + b"\n"
    name = f"ranking-{day.isoformat()}.json"
    existing = list(csv.DictReader(HASHES.open())) if HASHES.exists() else []
    if any(r["file"] == name for r in existing):
        return                       # archived and published once; a later run never rewrites it (the vendor revises data)
    folder = archive_dir()
    folder.mkdir(parents=True, exist_ok=True)
    (folder / name).write_bytes(body)
    digest = hashlib.sha256(body).hexdigest()
    HASHES.parent.mkdir(parents=True, exist_ok=True)
    new = not HASHES.exists()
    with HASHES.open("a", newline="") as f:
        w = csv.DictWriter(f, HASH_FIELDS)
        if new:
            w.writeheader()
        w.writerow({"ranked": day.isoformat(), "purpose": purpose, "file": name, "sha256": digest, "listings": len(rows)})


def ranking(day: dt.date, size: int, purpose: str) -> dict:
    top = rules.rank(candidates_as_of(day, purpose), size, joe10.EXCLUDED, set())
    if len(top) < size:
        raise RuntimeError(f"The ranking on {day} found {len(top)} eligible companies; the tier needs {size}.")
    chosen = {code for code, _ in top}
    return {"ranked": day.isoformat(), "shares": {c.code: c.shares for c in _candidates[day] if c.code in chosen}}


def archive_rankings() -> None:
    """Archive every quarterly ranking that has closed since the last run (whether or not any tier has started)."""
    today = dt.date.today()
    state = _load(ARCHIVE_STATE) if ARCHIVE_STATE.exists() else {"last_date": today.isoformat()}
    last = dt.date.fromisoformat(state["last_date"])
    for kind, day, quarter in common.quarter_events(last, today):
        if kind == "rank":
            candidates_as_of(day, f"quarterly ranking {quarter}")
    state["last_date"] = today.isoformat()
    _save(ARCHIVE_STATE, state)


def init(names: list[str] | None = None) -> None:
    """Freeze each tier not yet started: ranked at the latest close, held fully invested for the backfill, started at the
    first close after today."""
    today = dt.date.today()
    spy = eodhd.daily("SPY", today - dt.timedelta(days=10), today)
    day = max(d for d in spy if d < today) if any(d < today for d in spy) else max(spy)
    if not ARCHIVE_STATE.exists():
        _save(ARCHIVE_STATE, {"last_date": today.isoformat()})      # quarterly rankings are archived from today on
    for name in names or list(TIERS):
        if state_path(name).exists():
            print(f"{LABELS[name]} is already initialized.")
            continue
        start = ranking(day, TIERS[name], "start of the tiers")
        data = common.bars(sorted(start["shares"]) + ["SPY"], day - dt.timedelta(days=BACKFILL_DAYS + 10), day)
        closes = {c: data[c][max(d for d in data[c] if d <= day)]["close"] for c in start["shares"]}
        first = min(d for d in data["SPY"] if d >= day - dt.timedelta(days=BACKFILL_DAYS))
        p = joe10.Portfolio(joe10.weights_from(start["shares"], closes))
        p._trade_to(dict(p.weights), common.adjusted_on({c: data[c] for c in p.weights}, first))   # fully invested, before the start
        p.cash, p.stocks_after = 0.0, 1.0
        done = [f"{kind} {quarter}" for kind, d, quarter in common.quarter_events(first - dt.timedelta(days=100), today)
                if d <= day]
        state = {"model": LABELS[name], "size": TIERS[name], "frozen_on": today.isoformat(), "ranked_at_start": day.isoformat(),
                 "start_holdings": start, "started": None, "last_date": first.isoformat(), "pending": None, "done": done,
                 "value": None, "spy": None, "spy_adjusted": None}
        joe10.store(state, p)
        _save(state_path(name), state)
        advance(name, state)


def advance(name: str, state: dict) -> None:
    """The Joe 10's daily step (joe10.advance), for one tier: quarter events, the backfill, the start, then each close."""
    size = TIERS[name]
    p = joe10.portfolio_of(state)
    last = dt.date.fromisoformat(state["last_date"])
    today = dt.date.today()
    data = common.bars(sorted(set(p.weights) | set(p.units) | {"SPY"}), last - dt.timedelta(days=10), today)
    rows = []
    for day in sorted(d for d in data["SPY"] if d > last):
        previous = dt.date.fromisoformat(state["last_date"])
        for kind, target, quarter in common.quarter_events(previous, day):
            key = f"{kind} {quarter}"
            if key in state["done"]:
                continue
            if kind == "rank":
                state["pending"] = ranking(previous, size, f"quarterly ranking {quarter}")
            elif state["pending"]:
                new = set(state["pending"]["shares"]) - set(data)
                if new:
                    data.update(common.bars(new, previous - dt.timedelta(days=10), today))
                closes = {c: data[c][max(d for d in data[c] if d <= previous)]["close"] for c in state["pending"]["shares"]}
                p.rebalance({c: s * closes[c] for c, s in state["pending"]["shares"].items()}, common.adjusted_on(data, previous))
                state["pending"] = None
            state["done"].append(key)

        adjusted = common.adjusted_on(data, day)
        spy = data["SPY"][day]["adjusted"]
        frozen = dt.date.fromisoformat(state["frozen_on"])
        if state["started"] is None:
            stocks = sum(u * adjusted[c] for c, u in p.units.items())
            p.sleeve_returns = (p.sleeve_returns + [stocks / p.stocks_after - 1])[-(rules.WINDOW + 5):]
            p._trade_to({c: stocks * w for c, w in p.weights.items()}, adjusted)
            p.cash, p.stocks_after = 0.0, stocks
            if day > frozen and len(p.sleeve_returns) >= rules.WINDOW:
                scale = 1.0 / stocks                                   # the track starts at 1.0
                p.units = {c: u * scale for c, u in p.units.items()}
                p.stocks_after = 1.0
                p.start(adjusted)
                state["started"], state["value"], state["spy"], state["spy_adjusted"] = day.isoformat(), p.value(adjusted), 1.0, spy
        else:
            p.close(adjusted)
            state["value"] = p.value(adjusted)
            state["spy"] *= spy / state["spy_adjusted"]
            state["spy_adjusted"] = spy
        state["last_date"] = day.isoformat()
        if state["started"] is not None:
            share = (state["value"] - p.cash) / state["value"]
            rows.append({"date": day.isoformat(), "stock_share": f"{share:.6f}", name: f"{state['value']:.8f}",
                         "spy": f"{state['spy']:.8f}"})
    joe10.store(state, p)
    _save(state_path(name), state)
    if rows:
        path = track_path(name)
        new = not path.exists()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", newline="") as f:
            w = csv.DictWriter(f, ["date", "stock_share", name, "spy"])
            if new:
                w.writeheader()
            w.writerows(rows)


def report(name: str, month: str) -> Path | None:
    with track_path(name).open() as f:
        rows = [r for r in csv.DictReader(f) if r["date"][:7] <= month]
    if len(rows) < 3:
        return None
    dates = [dt.date.fromisoformat(r["date"]) for r in rows]
    model = [float(r[name]) for r in rows]
    spy = [float(r["spy"]) for r in rows]
    j, s = common.stats(model, dates), common.stats(spy, dates)
    scale = j["volatility"] / s["volatility"] if j["volatility"] and s["volatility"] else 1.0
    mixed = [1.0]
    for a, b in zip(spy, spy[1:]):
        mixed.append(mixed[-1] * (1 + scale * (b / a - 1)))
    m = common.stats(mixed, dates)
    pct = lambda x: "n/a" if x is None else f"{x:.1%}"
    line = lambda label, x, v: f"| {label} | {pct(x['total'])} | {pct(x['annual'])} | {pct(x['volatility'])} | {pct(x['worst'])} | ${500_000 * v:,.0f} |"
    text = "\n".join([
        f"# The {LABELS[name]} forward test: {month}", "",
        f"From the close of {rows[0]['date']} to the close of {rows[-1]['date']}. Hypothetical performance of frozen, published rules"
        " (PREREGISTRATION-TIERS.md), computed from closing prices; not an account, not a recommendation. As in an IRA: no tax;"
        " the SEC fee is the only trading cost; cash earns nothing.", "",
        "| | Total return | Annual return | Volatility | Worst drop | $500,000 is now |", "|---|---|---|---|---|---|",
        line(LABELS[name], j, model[-1]), line("SPY", s, spy[-1]), line(f"SPY + {1 - scale:.0%} cash (same risk)", m, mixed[-1]), "",
        f"Stock share today: {float(rows[-1]['stock_share']):.0%}. Annual return is shown once the track is a year old.", ""])
    REPORTS.mkdir(exist_ok=True)
    path = REPORTS / f"{name}-{month}.md"
    path.write_text(text)
    return path


def daily() -> None:
    archive_rankings()
    for name in TIERS:
        if not state_path(name).exists():
            continue
        state = _load(state_path(name))
        before = state["last_date"]
        advance(name, state)
        if state["started"] and before[:7] != state["last_date"][:7]:
            report(name, before[:7])


if __name__ == "__main__":
    command = sys.argv[1]
    if command == "init":
        init(sys.argv[2:] or None)
    elif command == "daily":
        daily()
    else:
        sys.exit("Commands: init [joe25 joe50 joe100], daily")
