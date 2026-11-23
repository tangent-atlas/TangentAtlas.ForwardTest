# The Joe 10 forward test, and the personal-index tiers

A public, dated record of how the **Joe 10** performs from November 2026 on: Tangent Atlas's generic model of a personal index, run by rules frozen before its first day. Beside it, from late November 2026, the **Joe 25, Joe 50 and Joe 100**: the same rules with more companies, one for each account size a customer's personal index defaults to.

- **The rules and predictions:** [PREREGISTRATION-JOE10.md](PREREGISTRATION-JOE10.md), archived on Zenodo as version 1.1 before the track began.
- **The track:** [data/joe10.csv](data/joe10.csv), updated after every US market close: the share in stocks, and the Joe 10 and SPY, each starting at 1.0.
- **The tiers' rules and predictions:** [PREREGISTRATION-TIERS.md](PREREGISTRATION-TIERS.md), archived on Zenodo as version 1.2 before their first close. Their tracks: [data/joe25.csv](data/), `joe50.csv`, `joe100.csv`.
- **Monthly reports:** [reports/](reports/), every model every month, each also a release that Zenodo archives with its own DOI.
- **The ranking archive:** at every quarterly ranking the full ranking inputs (the 300 largest US listings) are kept privately, because they hold the vendor's licensed prices; their SHA-256 hashes are published the same day in [archive/hashes.csv](archive/hashes.csv), so any model later rebuilt from them can be shown to have had no look-ahead.

In short, the Joe 10 holds the 10 largest US companies by full market value, weighted by size at each quarterly rebalance and traded back to those weights every day (Constant Weight). Its cash is set every day so its volatility stays at 15%, about an index fund's volatility in an average month. It is compared with SPY, and with SPY plus cash at the same risk.

## Check it yourself

The track is computed by [forward/](forward/) from closing prices and nothing else. With the rules and any source of daily closing prices, anyone can recompute every row. The code that runs each day is the code in this repository: see [.github/workflows/daily.yml](.github/workflows/daily.yml) and the run history under Actions.

```
python -m pytest            # the rules, on synthetic markets with known answers
EODHD_API_TOKEN=... python -m forward.joe10 daily
EODHD_API_TOKEN=... python -m forward.tiers daily
```

## History of this record

Version 1.0 (November 4, 2026) froze a forward test of the Ken 11, the illustration on tangentatlas.com, built for one fictional customer (his own risk and his own exclusions). It was withdrawn on November 4, 2026, before its first close, so that the public record tests a generic model rather than an illustration; no Ken 11 results were ever computed. Its rules remain in version 1.0 on Zenodo.

Version 1.2 (November 2026) adds the Joe 25, Joe 50 and Joe 100 and the ranking archive. The Joe 10's rules, code and track are unchanged.

## What this is not

Hypothetical performance of published rules, before taxes, computed from closing prices. It is not an account, not an offer to sell or buy anything, and not investment advice. Past and simulated results don't predict future ones.

## Licence

Apache License 2.0. Prices come from EODHD and are used under its licence; they are not redistributed here.
