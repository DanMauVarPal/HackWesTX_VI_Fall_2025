# klarman_screener.py
import json
import pandas as pd, numpy as np, yfinance as yf
from common_screener import (
    get_us_equity_universe, fetch_many, compute_core_score, build_output,
    ffloat, is_num
)

# Gates
FCF_YIELD_MIN = 5.0
EV_EBITDA_MAX = 8.0
PB_MAX        = 1.2
NET_CASH_TO_MKT_MIN = -10.0
CURRENT_RATIO_MIN   = 1.5
INTEREST_COVER_MIN  = 4.0

# CoreScore
CORE_WEIGHTS = {"FCFYield%":0.30,"EV/EBITDA":0.25,"P/B":0.15,"NetCashToMktCap%":0.15,"CurrentRatio":0.10,"InterestCoverage":0.05}
DIRS = {"FCFYield%":True,"EV/EBITDA":False,"P/B":False,"NetCashToMktCap%":True,"CurrentRatio":True,"InterestCoverage":True}

EXPECTED=["Ticker","Name","Sector","MarketCap","P/B","EV/EBITDA","FCFYield%","NetCashToMktCap%","CurrentRatio","InterestCoverage","Price"]
NUMS    =["MarketCap","P/B","EV/EBITDA","FCFYield%","NetCashToMktCap%","CurrentRatio","InterestCoverage","Price"]

def _stmt_get(df, candidates):
    if df is None or not isinstance(df, pd.DataFrame) or df.empty: return np.nan
    for k in candidates:
        if k in df.index:
            try: return ffloat(df.loc[k].iloc[0])
            except: pass
    return np.nan

def _fetch_one(t:str)->dict:
    try:
        tk=yf.Ticker(t)
        try: info=tk.get_info()
        except: info=getattr(tk,"info",{}) or {}

        price=ffloat(info.get("currentPrice"))
        mcap =ffloat(info.get("marketCap"))
        pb   =ffloat(info.get("priceToBook"))
        ev   =ffloat(info.get("enterpriseValue"))
        ebitda=ffloat(info.get("ebitda"))
        debt=ffloat(info.get("totalDebt")); cash=ffloat(info.get("totalCash"))
        curr=ffloat(info.get("currentRatio"))

        try: ist=tk.get_income_stmt()
        except: ist=None
        try: cfs=tk.get_cashflow()
        except: cfs=None
        try: bs=tk.get_balance_sheet()
        except: bs=None

        if not is_num(ebitda):
            ebitda=_stmt_get(ist,["EBITDA","Ebitda","EarningsBeforeInterestTaxesDepreciationAmortization"])

        if not is_num(ev) and is_num(mcap):
            if is_num(debt) or is_num(cash):
                ev = mcap + (debt or 0.0) - (cash or 0.0)

        fcf = info.get("freeCashflow") or info.get("freeCashFlow")
        fcf = ffloat(fcf)
        if not is_num(fcf):
            fcf = _stmt_get(cfs, ["FreeCashFlow","Free Cash Flow"])
            if not is_num(fcf):
                cfo   = _stmt_get(cfs, ["OperatingCashFlow","CashFlowsFromUsedInOperatingActivities"])
                capex = _stmt_get(cfs, ["CapitalExpenditure","CapitalExpenditures","InvestmentsInPropertyPlantAndEquipment"])
                if is_num(cfo) and is_num(capex): fcf = cfo - abs(capex)

        ebit = _stmt_get(ist, ["EBIT","EarningsBeforeInterestAndTaxes","OperatingIncome"])
        int_exp = abs(_stmt_get(ist, ["InterestExpense","InterestExpenseNonOperating","InterestExpenseIncome"]))

        ev_ebitda = (ev/ebitda) if (is_num(ev) and is_num(ebitda) and ebitda>0) else np.nan
        fcf_yield = (fcf/mcap*100.0) if (is_num(fcf) and is_num(mcap) and mcap>0) else np.nan
        net_cash  = ((cash-debt)/mcap*100.0) if (is_num(cash) and is_num(debt) and is_num(mcap) and mcap>0) else np.nan
        int_cov   = (ebit/int_exp) if (is_num(ebit) and is_num(int_exp) and int_exp>0) else np.nan

        return {
            "Ticker":t, "Name":info.get("shortName") or info.get("longName") or t, "Sector":info.get("sector") or "",
            "MarketCap":mcap,"P/B":pb,"EV/EBITDA":ev_ebitda,"FCFYield%":fcf_yield,
            "NetCashToMktCap%":net_cash,"CurrentRatio":curr,"InterestCoverage":int_cov,"Price":price
        }
    except: return {"Ticker":t}

def klarman_checklist(df: pd.DataFrame)->pd.DataFrame:
    checks={
        "FCF_Positive":(df["FCFYield%"]>=FCF_YIELD_MIN),
        "EVEBITDA_low":(df["EV/EBITDA"]<=EV_EBITDA_MAX),
        "PB_low":(df["P/B"]<=PB_MAX),
        "NetCash_OK":(df["NetCashToMktCap%"]>=NET_CASH_TO_MKT_MIN),
        "CR_OK":(df["CurrentRatio"]>=CURRENT_RATIO_MIN),
        "Interest_OK":(df["InterestCoverage"]>=INTEREST_COVER_MIN),
    }
    for k,v in checks.items(): df[k]=v.fillna(False)
    df["ChecklistScore"]=df[list(checks)].sum(axis=1)
    df["KlarmanGate"]=df[list(checks)].all(axis=1)
    return df

def screen_klarman(top_n=15, limit=1000, order="core", include_metric_details=True):
    tickers=get_us_equity_universe(limit)
    print(f"Universe size: {len(tickers)}")
    df=fetch_many(tickers, _fetch_one, EXPECTED, NUMS)
    df=df[df["MarketCap"].fillna(0)>0]
    df=klarman_checklist(df)
    df=compute_core_score(df, CORE_WEIGHTS, DIRS)
    if order=="gate":
        df=df.sort_values(["KlarmanGate","ChecklistScore","CoreScore"], ascending=[False,False,False])
    else:
        df=df.sort_values(["CoreScore"], ascending=[False])
    cols=["Ticker","Name","Sector","CoreScore","ChecklistScore","KlarmanGate","MarketCap","P/B","EV/EBITDA","FCFYield%","NetCashToMktCap%","CurrentRatio","InterestCoverage","Price"]
    return build_output(df, CORE_WEIGHTS, DIRS, cols, top_n, include_metric_details)

if __name__=="__main__":
    print(json.dumps(screen_klarman(), indent=2))
