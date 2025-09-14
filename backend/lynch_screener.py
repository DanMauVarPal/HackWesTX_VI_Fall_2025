import json
import pandas as pd, numpy as np, yfinance as yf
from common_screener import (
    get_us_equity_universe, fetch_many, compute_core_score, build_output,
    ffloat, is_num, frac_to_pct
)

# Gates (growth at a reasonable price in essence)
PEG_MAX = 1.0
PE_MAX = 25.0
DEBT_TO_EQUITY_MAX = 0.5
MARKET_CAP_MIN = 500e6

# CoreScore weights based on one up on wallstreet
CORE_WEIGHTS = {"P/E":0.25, "PEG":0.25, "ROE%":0.20, "DebtToEquity":0.15, "MarketCap":0.15}
DIRS = {"P/E":False, "PEG":False, "ROE%":True, "DebtToEquity":False, "MarketCap":True}

EXPECTED = ["Ticker","Name","Sector","MarketCap","P/E","Price","PEG","ROE%","DebtToEquity"]
NUMS     = ["MarketCap","P/E","Price","PEG","ROE%","DebtToEquity"]

def _fetch_one(t:str)->dict:
    try:
        tk = yf.Ticker(t)
        try: info = tk.get_info()
        except: info = getattr(tk, "info", {}) or {}
        price = ffloat(info.get("currentPrice"))
        mcap  = ffloat(info.get("marketCap"))
        pe    = ffloat(info.get("trailingPE"))
        roe   = frac_to_pct(info.get("returnOnEquity"))  # convert fraction→%
        d2e   = ffloat(info.get("debtToEquity"))
        growth= ffloat(info.get("earningsGrowth"))       # fraction, e.g., 0.15 = 15%
        peg = np.nan
        if is_num(pe) and is_num(growth) and growth > 0:
            peg = pe / (growth * 100.0)  # growth in %
        return {
            "Ticker": t,
            "Name": info.get("shortName") or info.get("longName") or t,
            "Sector": info.get("sector") or "",
            "MarketCap": mcap, "P/E": pe, "Price": price, "PEG": peg,
            "ROE%": roe, "DebtToEquity": d2e
        }
    except:
        return {"Ticker": t}

def lynch_checklist(df: pd.DataFrame)->pd.DataFrame:
    checks = {
        "PE_ok": (df["P/E"] <= PE_MAX),
        "PEG_ok": (df["PEG"] <= PEG_MAX),
        "ROE_OK": (df["ROE%"] >= 15),
        "Debt_OK": (df["DebtToEquity"] <= DEBT_TO_EQUITY_MAX),
        "MarketCap_OK": (df["MarketCap"] >= MARKET_CAP_MIN)
    }
    for k,v in checks.items(): df[k] = v.fillna(False)
    df["ChecklistScore"] = df[list(checks)].sum(axis=1)
    df["LynchGate"] = df[list(checks)].all(axis=1)
    return df

def screen_lynch(top_n=15, limit=1000, order="core", include_metric_details=True):
    tickers = get_us_equity_universe(limit)
    print(f"Universe size: {len(tickers)}")
    df = fetch_many(tickers, _fetch_one, EXPECTED, NUMS)
    df = lynch_checklist(df)
    df = compute_core_score(df, CORE_WEIGHTS, DIRS)
    if order == "gate":
        df = df.sort_values(["LynchGate","ChecklistScore","CoreScore"], ascending=[False,False,False])
    else:
        df = df.sort_values(["CoreScore"], ascending=[False])
    cols = ["Ticker","Name","Sector","CoreScore","ChecklistScore","LynchGate","MarketCap","P/E","Price","PEG","ROE%","DebtToEquity"]
    return build_output(df, CORE_WEIGHTS, DIRS, cols, top_n, include_metric_details)

if __name__=="__main__":
    print(json.dumps(screen_lynch(), indent=2))
