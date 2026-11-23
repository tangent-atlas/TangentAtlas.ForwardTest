# Pre-registration §23: the personal-index tiers (Joe 25, Joe 50, Joe 100)

*Written November 23, 2026. Frozen when version 1.2 of this repository is released and archived on Zenodo, before the tiers' first close. A change to these rules is a new model, published as such. The Joe 10 (PREREGISTRATION-JOE10.md, §20) is unchanged.*


> **Amendment of November 23, 2026 (version 1.3), before the tiers' first close.** The tiers follow the Joe 10's rules as amended the same day (PREREGISTRATION-JOE10.md, section 6: the head-office country, the vendor's ADR flag, and 12 months of trading before a listing is ranked). The pool is the 300 largest NYSE and Nasdaq companies that pass the rules (section 2). A ranking that finds fewer eligible companies than it needs stops the run instead of holding fewer. Versions 1.2 and 1.2.1 were released, but no tier had started: their first starts failed on a data-reading error, before any close was recorded.

## 1. Why these tracks exist

A customer's personal index holds as many companies as his account can hold accurately in whole shares (section 4). Small accounts hold 10, larger ones 25, 50 or 100. Each of those defaults gets its own public forward record, so every customer can see the record of the model his own account runs.

**When and why they were chosen, stated plainly:** after backtests run on November 22, 2026 (exploratory, 1993–2026, on reconstructed data before 2009). They showed annual return nearly the same for every number of companies from 10 to 250 (10.7–11.0% a year under the 15% thermostat), and risk falling as the number grows (worst drop −48% for 10 companies, −42% for 100). The tiers were chosen to match account sizes, **not** for return. The Joe 10's predictions and rules are not changed by them.

## 2. The rules (frozen)

Exactly the Joe 10's rules (§20, section 2), run by the same code (`forward/joe10.py` and `forward/rules.py`; as amended November 23, 2026), except:

- **Size:** the 25, 50 and 100 largest companies (the Joe 25, Joe 50 and Joe 100).
- **The pool:** the 300 largest companies on the NYSE and Nasdaq that pass the rules. Listings on the two exchanges are examined in order of the vendor's market capitalization until 300 companies pass (share classes of one company count once); those are then ranked by full market value as in the Joe 10. *(Amended November 23, 2026, before the first close; it was "the vendor's 300 largest US listings", of which only 111 passed the rules, because the vendor's US list includes over-the-counter lines of foreign companies.)* The Joe 10 still draws from the 100 largest US listings, which always hold its 10.
- **The start:** each tier is ranked at the close of the last trading day before the day it is initialized, held fully invested at those weights for the 45 calendar days before that close (only to give the thermostat its 21-day history, as the Joe 10 was before its start), and starts at 1.0 at the first close after the day it is initialized.
- **From then on:** the same quarterly schedule as the Joe 10 (ranked at the close of the second Friday of March, June, September and December; rebalanced at the close of the third Friday), the same thermostat at 15% with its 2-point and 0.5% bands, the SEC fee, no exclusions, cash earning nothing, every trade at the closing price, total return from adjusted closes.

The tracks are index values (fractional holdings), as the Joe 10's is. Customers' accounts hold whole shares; section 4 is how account size limits the number of companies so that whole shares stay close to these weights.

## 3. The ranking archive

At every quarterly ranking, and at the tiers' start, the full ranking inputs of every listing examined for the pool (company, CIK, type, country, exchange, closing price, volume, shares outstanding as last reported, market value, rank) are saved to a private archive, and the file's SHA-256 is published the same day in `archive/hashes.csv`. The inputs stay private because they hold the vendor's licensed prices; the hash proves later that a file was not changed after the day. From the archive, any number of companies or any risk setting can be rebuilt later without look-ahead (for example a Joe 250, or the two-speed thermostat), as agreed on November 5, 2026. Such rebuilt models are research, not part of this pre-registration.

## 4. The account-size rule (the product's default; published, mechanical)

A customer's default number of companies is the largest of 10, 25, 50 and 100 that his account can hold with the total whole-share rounding error (the sum of the differences between each holding's weight and its target) at or below 2% of the portfolio, with the thermostat at 60% in stocks. No fractional shares. At November 2026 prices this is about:

| Default | Account value from about |
|---|---|
| Joe 10 | any account (every holding has at least one share from about $35,000; accurate within 2% from about $110,000) |
| Joe 25 | $270,000 |
| Joe 50 | $650,000 |
| Joe 100 | $1,300,000 |

The thresholds are recomputed at each quarterly rebalance from that day's prices. An account moves up a tier only when it is 20% above the tier's threshold, and down only when it is 20% below the threshold of the tier it holds, and only at a quarterly rebalance. The customer may choose fewer companies; the rule is a limit, not a recommendation.

## 5. Reporting (the commitment)

Every tier is reported every month, in the same format as the Joe 10, next to the Joe 10, for as long as the forward test runs. No tier is dropped, renamed or restarted because of its results. The evaluations are at one, three and five years after the tiers' start, alongside the Joe 10's.

## 6. Benchmarks

As the Joe 10's: SPY fully invested, and SPY plus cash at each tier's own volatility (the strict comparison).

## 7. Predictions

**Claude's** (at the three-year evaluation, each on its own track):
- **T1.** The four tiers' (Joe 10, 25, 50, 100) annual returns are within 2 points of one another: no number of companies is clearly better on return.
- **T2.** Realized volatility is lower for the Joe 100 than for the Joe 10, and the Joe 100's worst drop is no deeper than the Joe 10's.
- **T3.** Tracking error against SPY falls as the number of companies grows (Joe 100 lowest, Joe 10 highest).
- **T4.** Each tier's annual return differs from SPY plus cash at its own volatility by between −1 and +3 points.

**The founder's** (recorded November 23, 2026, before the first close):
- **F23.** What the backtests show: more companies do not change the return, but lower the volatility and the worst drop. It works as a function of the number of companies: the more companies, the lower the volatility and the higher the Sharpe ratio, up to a point past which the gain diminishes against the number of companies that must be managed.

## 8. What this is not

Hypothetical performance of published rules, before tax, computed from closing prices: not an account, not an offer, not advice. Any figure shown in marketing is labelled as hypothetical forward performance, and its presentation is reviewed by counsel.
