# graham_screener.py
import json
import pandas as pd, numpy as np, yfinance as yf
from common_screener import (
    get_us_equity_universe, fetch_many, compute_core_score, build_output,
    ffloat, frac_to_pct, normalize_div_yield, is_num
)

# Gates
PE_MAX=15.0; PB_MAX=1.2; PRICE_TO_52W_LOW_MAX=1.20
DEBT_TO_EQUITY_MAX=1.0; CURRENT_RATIO_MIN=1.5
DIVIDEND_MIN_YIELD=2.0; ROE_MIN=5.0

# CoreScore
CORE_WEIGHTS = {"P/E":0.25,"P/B":0.20,"PriceTo52wLow":0.15,"DividendYield%":0.15,"ROE%":0.10,"DebtToEquity":0.10,"CurrentRatio":0.05}
DIRS = {"P/E":False,"P/B":False,"PriceTo52wLow":False,"DividendYield%":True,"ROE%":True,"DebtToEquity":False,"CurrentRatio":True}

EXPECTED=["Ticker","Name","Sector","MarketCap","P/E","P/B","Price","PriceTo52wLow","DrawdownFromHigh%","DividendYield%","ROE%","DebtToEquity","CurrentRatio"]
NUMS    =["MarketCap","P/E","P/B","Price","PriceTo52wLow","DrawdownFromHigh%","DividendYield%","ROE%","DebtToEquity","CurrentRatio"]

def _compute_pe(price, eps_ttm):
    return (float(price)/float(eps_ttm)) if (is_num(price) and is_num(eps_ttm) and eps_ttm!=0) else np.nan

def _compute_pb(price, shares_out, equity_total):
    try:
        if is_num(price) and is_num(shares_out) and shares_out>0 and is_num(equity_total) and equity_total>0:
            bvps=float(equity_total)/float(shares_out)
            return (float(price)/bvps) if bvps>0 else np.nan
    except: pass
    return np.nan

def _fetch_one(t:str)->dict:
    try:
        tk=yf.Ticker(t)
        try: info=tk.get_info()
        except: info=getattr(tk,"info",{}) or {}
        fi=getattr(tk,"fast_info",{}) or {}

        price=ffloat(info.get("currentPrice")) or ffloat(fi.get("last_price"))
        mcap= ffloat(info.get("marketCap"))    or ffloat(fi.get("market_cap"))
        shares=ffloat(info.get("sharesOutstanding")) or ffloat(fi.get("shares"))
        if not is_num(mcap) and is_num(price) and is_num(shares):
            mcap=price*shares

        wk_low= ffloat(info.get("fiftyTwoWeekLow"))  or ffloat(fi.get("year_low"))
        wk_high=ffloat(info.get("fiftyTwoWeekHigh")) or ffloat(fi.get("year_high"))
        pe=ffloat(info.get("trailingPE"))
        pb=ffloat(info.get("priceToBook"))
        eps_ttm=ffloat(info.get("trailingEps"))
        d2e=ffloat(info.get("debtToEquity"))
        curr=ffloat(info.get("currentRatio"))
        roe=frac_to_pct(info.get("returnOnEquity"))
        div_yld=normalize_div_yield(info.get("dividendYield"))

        if not is_num(pe): pe=_compute_pe(price, eps_ttm)
        if not is_num(pb):
            try:
                bs=tk.get_balance_sheet()
                equity=None
                for k in ["StockholdersEquity","TotalStockholderEquity","Total Equity Gross Minority Interest","TotalEquityGrossMinorityInterest"]:
                    if k in bs.index:
                        equity=ffloat(bs.loc[k].iloc[0]); break
                pb=_compute_pb(price, shares, equity)
            except: pass

        p_to_low=(price/wk_low) if (is_num(price) and is_num(wk_low) and wk_low>0) else np.nan
        dd_from_hi=((wk_high-price)/wk_high*100.0) if (is_num(price) and is_num(wk_high) and wk_high>0) else np.nan

        return {
            "Ticker":t, "Name":info.get("shortName") or info.get("longName") or t, "Sector":info.get("sector") or "",
            "MarketCap":mcap, "P/E":pe, "P/B":pb, "Price":price, "PriceTo52wLow":p_to_low,
            "DrawdownFromHigh%":dd_from_hi, "DividendYield%":div_yld, "ROE%":roe,
            "DebtToEquity":d2e, "CurrentRatio":curr
        }
    except: return {"Ticker":t}

def graham_checklist(df: pd.DataFrame)->pd.DataFrame:
    checks={
        "PE_low":(df["P/E"]<=PE_MAX),"PB_low":(df["P/B"]<=PB_MAX),
        "Near_52w_low":(df["PriceTo52wLow"]<=PRICE_TO_52W_LOW_MAX),
        "Debt_OK":(df["DebtToEquity"]<=DEBT_TO_EQUITY_MAX),
        "CR_OK":(df["CurrentRatio"]>=CURRENT_RATIO_MIN),
        "Div_OK":(df["DividendYield%"]>=DIVIDEND_MIN_YIELD),
        "ROE_OK":(df["ROE%"]>=ROE_MIN)
    }
    for k,v in checks.items(): df[k]=v.fillna(False)
    df["ChecklistScore"]=df[list(checks)].sum(axis=1)
    df["GrahamGate"]=df[list(checks)].all(axis=1)
    return df

def screen_graham(top_n=15, limit=1000, order="core", include_metric_details=True):
    tickers=get_us_equity_universe(limit)
    print(f"Universe size: {len(tickers)}")
    df=fetch_many(tickers, _fetch_one, EXPECTED, NUMS)
    df=df[df["MarketCap"].fillna(0)>0]
    df=graham_checklist(df)
    df=compute_core_score(df, CORE_WEIGHTS, DIRS)
    if order=="gate":
        df=df.sort_values(["GrahamGate","ChecklistScore","CoreScore"], ascending=[False,False,False])
    else:
        df=df.sort_values(["CoreScore"], ascending=[False])
    cols=["Ticker","Name","Sector","CoreScore","ChecklistScore","GrahamGate","MarketCap","P/E","P/B","PriceTo52wLow","DividendYield%","ROE%","DebtToEquity","CurrentRatio","DrawdownFromHigh%"]
    return build_output(df, CORE_WEIGHTS, DIRS, cols, top_n, include_metric_details)

if __name__=="__main__":
    print(json.dumps(screen_graham(), indent=2))
