import datetime as dt
import sys

import pandas as pd

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.marketdata.market_data import MarketData

from expiry_resolver import resolve_expiry, next_scheduled_expiry, build_option_symbol

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

UNDERLYING = "NIFTY"
TRADE_DATE = dt.date(2026, 3, 1)
STRIKE = 24850
OPTION_TYPE = "CE"
INTERVAL = "5m"
LOOKBACK_DAYS = 4
ENV = NubraEnv.PROD

PRICE_FIELDS = ["open", "high", "low", "close"]
GREEKS_FIELDS = ["delta", "theta", "gamma", "vega", "iv_mid"]


def fetch_history(market_data, symbol, expiry, lookback_days, interval):
    response = market_data.historical_data({
        "exchange": "NSE",
        "type": "OPT",
        "values": [symbol],
        "fields": PRICE_FIELDS + GREEKS_FIELDS,
        "startDate": f"{expiry - dt.timedelta(days=lookback_days)}T03:30:00.000Z",
        "endDate": f"{expiry}T10:30:00.000Z",
        "interval": interval,
        "intraDay": False,
        "realTime": False,
    })

    if not response.result:
        raise RuntimeError(f"No historical data returned for {symbol}")

    columns = {}
    for chart_data in response.result:
        for symbol_map in chart_data.values:
            for _, chart in symbol_map.items():
                for field in PRICE_FIELDS + GREEKS_FIELDS:
                    points = getattr(chart, field, None) or []
                    points = [p for p in points if p.timestamp is not None and p.value is not None]
                    if not points:
                        continue

                    index = pd.to_datetime(
                        [p.timestamp for p in points], unit="ns", utc=True
                    ).tz_convert("Asia/Kolkata")
                    values = [float(p.value) for p in points]

                    series = pd.Series(values, index=index)
                    if field in PRICE_FIELDS:
                        series = series / 100.0
                    columns[field] = series

    df = pd.DataFrame(columns).sort_index()
    df.index.name = "timestamp"
    return df


def main():
    nubra = InitNubraSdk(ENV, env_creds=True)
    market_data = MarketData(nubra)

    scheduled = next_scheduled_expiry(TRADE_DATE)
    print(f"trade date       : {TRADE_DATE}")
    print(f"scheduled expiry : {scheduled} ({scheduled:%A})")

    actual = resolve_expiry(market_data, scheduled, atm_strike=STRIKE, underlying=UNDERLYING)
    if actual is None:
        print("Could not find a traded expiry near this date. Exiting.")
        return
    print(f"actual expiry    : {actual} ({actual:%A})")

    symbol = build_option_symbol(UNDERLYING, actual, STRIKE, OPTION_TYPE)
    print(f"trading symbol   : {symbol}")

    df = fetch_history(market_data, symbol, actual, LOOKBACK_DAYS, INTERVAL)

    print(f"\n{len(df)} candles fetched:")
    print(df.head(10).to_string())
    print("...")
    print(df.tail(5).to_string())

    out_file = f"{symbol}.csv"
    df.to_csv(out_file)
    print(f"\nSaved to {out_file}")


if __name__ == "__main__":
    main()
