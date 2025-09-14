import json
import pandas as pd, numpy as np, yfinance as yf
from common_screener import (
    get_us_equity_universe, fetch_many, compute_core_score, build_output,
    ffloat, frac_to_pct, is_num
)

PRICE_TO_EARNINGS_MAX = 25.0
DIVIDEND_YIELD_MIN = 2.0
DEBT_TO_EQUITY_MAX = 0.5
ROE_MIN = 15.0
MARKET_CAP_MIN = 2e9

# CoreScore weights
CORE_WEIGHTS = {"P/E":0.25,"DividendYield%":0.20,"ROE%":0.25,"DebtToEquity":0.15,"MarketCap":0.15}
DIRS = {"P/E":False,"DividendYield%":True,"ROE%":True,"DebtToEquity":False,"MarketCap":True}

EXPECTED = ["Ticker","Name","Sector","MarketCap","P/E","Price","DividendYield%","ROE%","DebtToEquity"]
NUMS     = ["MarketCap","P/E","Price","DividendYield%","ROE%","DebtToEquity"]

def _get_live_price(tk, info):
    try:
        fi = getattr(tk, "fast_info", {}) or {}
        p = float(fi.get("last_price"))
        if np.isfinite(p): return p
    except Exception: pass
    try:
        p = float(info.get("currentPrice"))
        if np.isfinite(p): return p
    except Exception: pass
    try:
        h = tk.history(period="1d", interval="1m")
        if not h.empty:
            p = float(h["Close"].dropna().iloc[-1])
            if np.isfinite(p): return p
    except Exception: pass
    return np.nan

def _fetch_one(t:str)->dict:
    try:
        tk = yf.Ticker(t)
        try: info = tk.get_info()
        except: info = getattr(tk, "info", {}) or {}

        price = _get_live_price(tk, info)
        mcap  = ffloat(info.get("marketCap"))
        pe    = ffloat(info.get("trailingPE"))
        roe   = frac_to_pct(info.get("returnOnEquity"))  
        d2e   = ffloat(info.get("debtToEquity"))
        div_y = info.get("dividendYield")
        # normalizing dividend yield
        div_yld = np.nan
        try:
            v = float(div_y)
            div_yld = v * 100.0 if 0 <= v <= 1.0 else v
        except Exception:
            pass

        return {
            "Ticker": t,
            "Name": info.get("shortName") or info.get("longName") or t,
            "Sector": info.get("sector") or "",
            "MarketCap": mcap, "P/E": pe, "Price": price,
            "DividendYield%": div_yld, "ROE%": roe, "DebtToEquity": d2e
        }
    except:
        return {"Ticker": t}

def snowball_checklist(df: pd.DataFrame)->pd.DataFrame:
    checks = {
        "PE_ok":        (df["P/E"] <= PRICE_TO_EARNINGS_MAX),
        "Div_OK":       (df["DividendYield%"] >= DIVIDEND_YIELD_MIN),
        "Debt_OK":      (df["DebtToEquity"] <= DEBT_TO_EQUITY_MAX),
        "ROE_OK":       (df["ROE%"] >= ROE_MIN),
        "MarketCap_OK": (df["MarketCap"] >= MARKET_CAP_MIN)
    }
    for k, v in checks.items(): df[k] = v.fillna(False)
    df["ChecklistScore"] = df[list(checks)].sum(axis=1)
    df["BuffettGate"] = df[list(checks)].all(axis=1)
    return df

def screen_buffett(top_n=15, limit=1000, order="core", include_metric_details=True):
    tickers = get_us_equity_universe(limit)
    print(f"Universe size: {len(tickers)}")
    df = fetch_many(tickers, _fetch_one, EXPECTED, NUMS)
    df = snowball_checklist(df)
    df = compute_core_score(df, CORE_WEIGHTS, DIRS)
    if order == "gate":
        df = df.sort_values(["BuffettGate","ChecklistScore","CoreScore"], ascending=[False,False,False])
    else:
        df = df.sort_values(["CoreScore"], ascending=[False])
    cols = ["Ticker","Name","Sector","CoreScore","ChecklistScore","BuffettGate",
            "MarketCap","P/E","Price","DividendYield%","ROE%","DebtToEquity"]
    return build_output(df, CORE_WEIGHTS, DIRS, cols, top_n, include_metric_details)

if __name__=="__main__":
    print(json.dumps(screen_buffett(), indent=2))
