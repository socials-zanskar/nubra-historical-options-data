import datetime as dt
import json
from pathlib import Path

MONTH_CODE = {
    1: "1", 2: "2", 3: "3", 4: "4", 5: "5", 6: "6",
    7: "7", 8: "8", 9: "9", 10: "O", 11: "N", 12: "D",
}


def last_weekday_of_month(year, month, weekday=1):
    if month == 12:
        first_of_next_month = dt.date(year + 1, 1, 1)
    else:
        first_of_next_month = dt.date(year, month + 1, 1)

    day = first_of_next_month - dt.timedelta(days=1)
    while day.weekday() != weekday:
        day -= dt.timedelta(days=1)
    return day


def next_scheduled_expiry(trade_date, weekday=1):
    days_ahead = (weekday - trade_date.weekday()) % 7
    return trade_date + dt.timedelta(days=days_ahead)


def build_option_symbol(underlying, expiry, strike, option_type, weekday=1):
    if expiry == last_weekday_of_month(expiry.year, expiry.month, weekday):
        return f"{underlying}{expiry:%y%b}".upper() + f"{strike}{option_type}"
    month_code = MONTH_CODE[expiry.month]
    return f"{underlying}{expiry:%y}{month_code}{expiry.day:02d}{strike}{option_type}"


def load_cache(cache_file):
    path = Path(cache_file)
    if path.exists():
        return json.loads(path.read_text())
    return {}


def save_cache(cache_file, cache):
    Path(cache_file).write_text(json.dumps(cache, indent=2))


def has_data(market_data, symbol, near_date):
    try:
        response = market_data.historical_data({
            "exchange": "NSE",
            "type": "OPT",
            "values": [symbol],
            "fields": ["close"],
            "startDate": f"{near_date - dt.timedelta(days=1)}T00:00:00.000Z",
            "endDate": f"{near_date + dt.timedelta(days=1)}T00:00:00.000Z",
            "interval": "1d",
            "intraDay": False,
            "realTime": False,
        })
    except Exception:
        return False

    for chart_data in response.result or []:
        for symbol_map in chart_data.values or []:
            for _, chart in symbol_map.items():
                if chart.close:
                    return True
    return False


def resolve_expiry(market_data, scheduled, atm_strike, underlying="NIFTY", weekday=1, cache_file="expiries.json"):
    cache = load_cache(cache_file)
    key = scheduled.isoformat()
    if key in cache:
        cached = cache[key]
        return dt.date.fromisoformat(cached) if cached else None

    for days_back in range(3):
        candidate = scheduled - dt.timedelta(days=days_back)
        if candidate.weekday() >= 5:
            continue
        symbol = build_option_symbol(underlying, candidate, atm_strike, "CE", weekday)
        if has_data(market_data, symbol, candidate):
            cache[key] = candidate.isoformat()
            save_cache(cache_file, cache)
            return candidate

    cache[key] = None
    save_cache(cache_file, cache)
    return None
