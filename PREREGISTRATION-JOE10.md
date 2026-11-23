# Pre-registration §20: the Joe 10

*Frozen November 4, 2026, by Tangent Atlas, before the Joe 10 was run on any history and before its forward track's first close. Archived on Zenodo with version 1.1 of this repository. A change to these rules is a new model, published as such.*


> **Amendment of November 23, 2026 (version 1.3), before the December 2026 ranking.** See section 6. It changes no holding to date and no backtest result; it changes the December 2026 holdings (SpaceX, listed June 2026, is not ranked until it has traded for 12 months), and says so.

## 1. What it is

The Joe 10 is Tangent Atlas's generic model of a personal index, the one used to compare the personal index with an index fund, in backtests and in this forward test. It is built for anyone: the 10 largest US companies, no exclusions, held at about the risk an index fund carries in an average month. Its name says that: an ordinary investor's personal index. (The website's Ken 11 is an illustration built for one fictional customer; it is not tested here.)

## 2. The rules (frozen)

**The index.**
- **Eligible:** common stock of a US company, listed on a US exchange; no limited partnerships; no depositary receipts. No exclusions.
- **One company, one line:** share classes of one company (same SEC CIK) are ranked once, at the largest shares outstanding × price among its classes, and held through its most traded class.
- **Ranked by full market value:** shares outstanding as last reported (EODHD's quarterly series), in the units of each listing's price (Berkshire Hathaway converted between Class A and Class B units) × the closing price.
- **Size:** the 10 largest. No buffer.
- **Schedule:** ranked at the close of the second Friday of March, June, September and December, from the 100 largest US listings by the vendor's market capitalization; rebalanced at the close of the third Friday. If either Friday is not a trading day, the last trading day before it.

**Constant Weight.** At each rebalance the target weights are set by full market value at that close. Between rebalances the holdings are traded back to those weights, subject to the band below.

**The thermostat (15%).**
- Each close, the target share in stocks is min(1, 15% ÷ the stock holdings' volatility over the last 21 trading days, annualized with 252 days). The rest is cash, earning nothing.
- If the target differs from the current share in stocks by more than 2 points, every holding is traded to its target (the new share × its weight).
- Otherwise the share is left where it drifted, and a holding is traded back to its weight only when it is more than 0.5% of the portfolio away from it.
- 15% is about the volatility of SPY in an average month (the mean of its 21-day volatility, 2009–2026: 14.7%; in calm months it is lower, so the Joe 10 is then fully invested).

**Costs and taxes.** The SEC fee on sales (0.21 bp); no commission. Shown as in an IRA: no tax. A taxable version is reported separately when the backtest is run, by the method of `research/tax` in TangentAtlas.Backtest, and is not the model's headline.

**Execution.** Every trade at the closing price; total return from adjusted closes.

## 3. Two tests

**The backtest, on TA500.** Once TA500 is built from 1993: the Joe 10 from the first quarter in which the 25 largest companies are all present and correctly identified (judged from the coverage files `index build` writes, before any return is computed), to October 23, 2026. Reported for the whole period, for 1998–2008 and 2009–2026, and in rolling 5-year windows.

**The forward track.** From the September 2026 holdings (ranked September 11, rebalanced September 18, 2026: NVDA, AAPL, GOOGL, MSFT, AMZN, AVGO, META, TSLA, MU, BRK-B; listed in `forward/joe10.py`), starting at 1.0 at the first close after version 1.1 is released and the track is initialized. Updated after every close; reported monthly.

## 4. Benchmarks

- **SPY, fully invested:** the fund most people would otherwise own. The headline comparison, because the Joe 10's volatility target is the index fund's own average.
- **SPY plus cash at the same risk:** SPY with a fixed cash share, set so its volatility over the period equals the Joe 10's. The strict comparison.

## 5. Predictions

**The founder (F2, as in §18):** the constant-volatility personal index does not consistently lose to an index ETF held at the same volatility.

**Claude:**
- **J1.** Over the whole backtest, the Joe 10's annual return exceeds SPY plus cash at the same volatility.
- **J2.** Over the whole backtest, its volatility is below SPY's and its worst drop is smaller than SPY's.
- **J3.** Over 1998–2008 it trails SPY plus cash at the same volatility (the largest companies fell behind).
- **J4.** Forward, after three years, its annual return differs from SPY plus cash at the same volatility by between 0 and +2 points; its volatility is below SPY's.

## 6. What this is not

Hypothetical performance of published rules, before tax, computed from closing prices: not an account, not an offer, not advice. Any figure shown in marketing is labelled as backtested or as hypothetical forward performance.

## 6. Amendment of November 23, 2026 (version 1.3)

Adopted before the December 11, 2026 ranking, the first ranking it could affect. The rules in section 2 are otherwise unchanged.

**1. How "a US company" and "no depositary receipts" are read.** The country is the company's head office, from the address in EODHD's company data; a listing with no address on record is kept. A listing EODHD flags as a depositary receipt (`HomeCategory` ADR) is a depositary receipt, whatever its name says. *Why:* EODHD now reports the country of every listing on a US exchange as the United States (Taiwan Semiconductor included) and leaves "ADR" out of some names, so the code's earlier checks no longer applied the rule as written. Found in a dry run on November 23. The September 2026 holdings already applied the rule as written: Taiwan Semiconductor, then about the 6th largest by value, was left out. *What it changes:* nothing in the rule's meaning; the code now does what the text says.

**2. Seasoning (new).** A listing is ranked only once it has traded for at least 12 months by the ranking date, counted from its first close on record (spin-offs included). This is the S&P 500's 12-month rule for new listings, which S&P kept in June 2026 for the largest IPOs (Nasdaq and others shortened theirs). *Why:* a new listing's reported share count often lags its IPO by a quarter or more (EODHD reported SpaceX at 5.9 billion shares for June 30, 2026 and 12.5 billion for September 30), so its full market value, the ranking's only input, is unreliable at first; and prices around a new listing's first months and its lockup expiry are often unsettled. The founder's reason, stated plainly: he would not buy a new listing in its first months. *What it changes:*
- **The record to date:** nothing. The September 2026 holdings contain no listing younger than 12 months.
- **The backtest:** nothing. From 2009 the backtest ranks S&P 500 members, which already pass S&P's 12-month rule. A check of every quarterly ranking 1993–2026 on the backtest's data found no genuine new listing in the top 10 within its first 12 months; the only flags were share-count errors already excluded as impossible values, a new share class of an old company, and foreign listings.
- **December 2026:** SpaceX (first close June 2026), 7th largest by value at the November 20 close, is not ranked until its first ranking on or after June 2027. Anthropic (first close November 18, 2026, 13th) is not ranked until December 2027. Without this amendment SpaceX would have entered the Joe 10 on December 18, 2026.

**3. What "shares outstanding" means (a clarification; nothing changes).** The shares the company reports outstanding for its listed classes, as in EODHD's quarterly series. Units of an operating partnership that can be exchanged for shares (an "Up-C" structure, as at Interactive Brokers and Carvana) are not counted until they are exchanged: counting them would take judgment about which units count and on what terms, and the rules take the reported figure. Such a company is ranked lower than its value including the units (Interactive Brokers about $32 billion against $121 billion at the November 20 close); the S&P 500 likewise weights these companies by their listed shares.
