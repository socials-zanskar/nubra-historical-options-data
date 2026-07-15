# Historical Expired Options Data Nubra Python SDK Example

An end-to-end example of fetching historical OHLCV, Greeks, and IV data
for an **expired** NSE options contract using the
[Nubra Python SDK](https://pypi.org/project/nubra-sdk/) (`nubra-sdk`).

Fetching an expired option is trickier than a stock: you first need to know
the *exact* contract symbol that traded, including whether an exchange
holiday shifted the expiry date. This repo shows both halves of that
problem, in two small files:

- **`expiry_resolver.py`** — figures out the real (holiday-adjusted) expiry
  date and builds the exact NSE option trading symbol for it
- **`fetch_expired_option_data.py`** — the end-to-end script: resolves the
  expiry, builds the symbol, fetches OHLCV + Greeks + IV history, and saves
  it to CSV

## Why This Is Tricky

NSE option symbols encode their expiry date directly, in one of two formats:

```
Weekly  : NIFTY2662325000PE     (NIFTY + YY + month-code + DD + strike + CE/PE)
Monthly : NIFTY26MAR25000CE     (NIFTY + YY + MMM + strike + CE/PE)
```

The last weekly expiry of a month is always written in the monthly format.
On top of that, exchange holidays shift the actual expiry to the previous
trading day — and it's the *shifted* date that ends up encoded in the
symbol, not the plain "every Tuesday" scheduled date.

Rather than maintaining a manual NSE holiday calendar, `expiry_resolver.py`
resolves this by probing: it tries the scheduled date's symbol first, and if
that has no historical data, steps back a day (skipping weekends) until it
finds one that does. Resolved expiries are cached to a small JSON file so
the same expiry is never probed twice.

## Requirements

- Python 3.9+
- A Nubra account with API access ([nubra.io](https://nubra.io))
- `nubra-sdk`, `pandas`, `python-dotenv`

```bash
pip install -r requirements.txt
```

## Setup

```bash
cp .env.example .env
```

Fill in your Nubra phone number and MPIN in `.env`.

## Usage

Open `fetch_expired_option_data.py` and edit the config block near the top:

```python
UNDERLYING = "NIFTY"
TRADE_DATE = dt.date(2026, 3, 1)   # find the expiry on/after this date
STRIKE = 24850
OPTION_TYPE = "CE"                 # "CE" or "PE"
INTERVAL = "5m"                    # 1d, 1h, 15m, 5m, ...
LOOKBACK_DAYS = 4
ENV = NubraEnv.PROD                # NubraEnv.PROD or NubraEnv.UAT
```

Then run it:

```bash
python fetch_expired_option_data.py
```

Example output:

```
trade date       : 2026-03-01
scheduled expiry : 2026-03-03 (Tuesday)
actual expiry    : 2026-03-03 (Tuesday)
trading symbol   : NIFTY2630324850CE

192 candles fetched:
                             open   high    low  close  delta  theta  gamma   vega  iv_mid
timestamp
2026-02-27 09:15:00+05:30  118.4  121.0  116.2  119.8   0.48  -9.21   0.01  12.44   14.20
...

Saved to NIFTY2630324850CE.csv
```

## Project Structure

```
.
├── expiry_resolver.py             # holiday-aware expiry resolution + symbol builder
├── fetch_expired_option_data.py   # end-to-end fetch script
├── requirements.txt
├── .env.example
├── LICENSE
└── README.md
```

Running the script also creates two extra files on first run, which are
already excluded via `.gitignore`:

- `expiries.json` — cache of resolved expiry dates
- `*.csv` — the fetched OHLCV/Greeks data for each symbol you fetch

## Notes & Limitations

- Written for NIFTY weekly options by default, but works for any NSE
  index/stock option by changing `UNDERLYING` and `--weekday` equivalent
  in `ExpiryResolver` (pass `weekday=` if the underlying's expiry day
  differs from Tuesday).
- The expiry-resolution probe only looks up to 2 days before the scheduled
  date. That covers ordinary holidays; unusually long market closures would
  need a wider search window.
- Price fields (`open`, `high`, `low`, `close`) are converted from
  exchange-native paise to rupees. Greeks and IV are used as returned by
  the API.

## ⚠️ Disclaimer

This is an educational example for reading Nubra's historical options data
API. It does not place any orders and is not investment advice. Data
availability for older expired contracts depends on Nubra's retention
window — see the historical data docs for current limits.

## License

MIT — see [LICENSE](LICENSE).
