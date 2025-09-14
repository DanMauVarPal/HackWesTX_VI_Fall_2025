# klarman_screener.py
import time, math, json, random
import pandas as pd, numpy as np, requests, yfinance as yf
from concurrent.futures import ThreadPoolExecutor, as_completed

# ================= Config =================
SLEEP_BETWEEN_CALLS = (0.02, 0.06)
MAX_WORKERS = 12
HTTP_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123 Safari/537.36"}

# Klarman gates (margin of safety proxies)
FCF_YIELD_MIN = 5.0          # %
EV_EBITDA_MAX = 8.0
PB_MAX = 1.2
NET_CASH_TO_MKT_MIN = -10.0  # % (prefer >=0; tolerate mild net debt)
CURRENT_RATIO_MIN = 1.5
INTEREST_COVER_MIN = 4.0

# CoreScore weights (cash flows & balance sheet first)
CORE_WEIGHTS = {
    "FCFYield%": 0.30, "EV/EBITDA": 0.25, "P/B": 0.15,
    "NetCashToMktCap%": 0.15, "CurrentRatio": 0.10, "InterestCoverage": 0.05
}
DIRS = {  # True => higher is better
    "FCFYield%": True, "EV/EBITDA": False, "P/B": False,
    "NetCashToMktCap%": True, "CurrentRatio": True, "InterestCoverage": True
}

EXPECTED_COLS = [
    "Ticker","Name","Sector","MarketCap","P/B","EV/EBITDA","FCFYield%",
    "NetCashToMktCap%","CurrentRatio","InterestCoverage","Price"
]

# Guaranteed fallback list so you always get results
FALLBACK_TICKERS = [
    "AAPL","MSFT","NVDA","AMZN","META","GOOGL","GOOG","BRK-B","TSLA","JPM","V","MA","UNH","HD",
    "XOM","CVX","KO","PEP","PG","WMT","COST","MCD","DIS","INTC","AMD","AVGO","NFLX","ORCL",
    "PFE","JNJ","MRK","ABBV","TMO","NKE","IBM","QCOM","TXN","CSCO","ADBE","CRM","LIN","BAC",
    "GS","MS","C","CAT","DE","GE","BA","LMT","RTX","T","VZ","UPS","LOW","SBUX","BKNG","DUK"
]

# ================= Universe =================
def get_nasdaq_universe(limit=6000) -> list[str]:
    urls = [
        "https://ftp.nasdaqtrader.com/dynamic/SymDir/nasdaqtraded.txt",
        "https://ftp.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt",
    ]
    syms=set()
    for url in urls:
        try:
            r=requests.get(url,timeout=25,headers=HTTP_HEADERS); r.raise_for_status()
            lines=r.text.strip().splitlines(); header=lines[0].split("|")
            def idx(name, fallback=None): return header.index(name) if name in header else fallback
            i_sym=idx("Symbol", idx("ACT Symbol", 0))
            i_etf=idx("ETF", None); i_test=idx("Test Issue", None)
            for ln in lines[1:]:
                p=ln.split("|"); 
                if len(p)<=i_sym: continue
                s=p[i_sym].strip()
                if not s or any(x in s for x in [".","$","^"," "]): continue
                if i_etf is not None and i_etf < len(p) and p[i_etf].strip().upper()=="Y": continue
                if i_test is not None and i_test < len(p) and p[i_test].strip().upper()=="Y": continue
                syms.add(s)
        except Exception:
            pass
    out = sorted(list(syms))[:limit]
    if not out:
        out = FALLBACK_TICKERS[: min(limit, len(FALLBACK_TICKERS))]
    return out

# ================= Helpers =================
def is_num(x):
    try: return x is not None and not pd.isna(x) and np.isfinite(float(x))
    except: return False

def ffloat(x):
    try:
        if x is None or (isinstance(x,float) and math.isnan(x)): return np.nan
        return float(x)
    except: return np.nan

# ================= Yahoo fetch (robust) =================
def _get_stmt_value(df, candidates):
    """Safely get first available row value from a yfinance statement DF."""
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return np.nan
    for k in candidates:
        if k in df.index:
            try: return ffloat(df.loc[k].iloc[0])
            except Exception: pass
    return np.nan

def _fetch_one(t: str) -> dict:
    """Fetch one ticker using get_info + fast_info + statements as fallbacks."""
    try:
        tk = yf.Ticker(t)
        try: info = tk.get_info()
        except Exception: info = getattr(tk, "info", {}) or {}
        fi = getattr(tk, "fast_info", {}) or {}

        price   = ffloat(info.get("currentPrice")) or ffloat(fi.get("last_price"))
        mcap    = ffloat(info.get("marketCap"))    or ffloat(fi.get("market_cap"))
        shares  = ffloat(info.get("sharesOutstanding")) or ffloat(fi.get("shares"))
        if not is_num(mcap) and is_num(price) and is_num(shares):
            mcap = price * shares

        pb      = ffloat(info.get("priceToBook"))
        ev      = ffloat(info.get("enterpriseValue")) or np.nan
        ebitda  = ffloat(info.get("ebitda"))
        total_debt = ffloat(info.get("totalDebt"))
        total_cash = ffloat(info.get("totalCash"))
        curr_ratio = ffloat(info.get("currentRatio"))

        # Statements for missing items
        try: ist = tk.get_income_stmt()
        except Exception: ist = None
        try: cfs = tk.get_cashflow()
        except Exception: cfs = None
        try: bs = tk.get_balance_sheet()
        except Exception: bs = None

        # EBITDA
        if not is_num(ebitda):
            ebitda = _get_stmt_value(ist, ["EBITDA","Ebitda","EarningsBeforeInterestTaxesDepreciationAmortization"])

        # Enterprise Value (recompute if missing and we have MktCap + Debt/Cash)
        if not is_num(ev) and is_num(mcap):
            if is_num(total_debt) or is_num(total_cash):
                ev = mcap + (total_debt or 0.0) - (total_cash or 0.0)

        # FCF (prefer info['freeCashflow'], then Cashflow['FreeCashFlow'], else CFO - CapEx)
        fcf = ffloat(info.get("freeCashflow") or info.get("freeCashFlow"))
        if not is_num(fcf):
            fcf = _get_stmt_value(cfs, ["FreeCashFlow","Free Cash Flow"])
            if not is_num(fcf):
                cfo = _get_stmt_value(cfs, ["OperatingCashFlow","CashFlowsFromUsedInOperatingActivities"])
                capex = _get_stmt_value(cfs, ["CapitalExpenditure","CapitalExpenditures","InvestmentsInPropertyPlantAndEquipment"])
                if is_num(cfo) and is_num(capex):
                    fcf = cfo - abs(capex)

        # Interest coverage = EBIT / InterestExpense
        ebit = _get_stmt_value(ist, ["EBIT","EarningsBeforeInterestAndTaxes","OperatingIncome"])
        interest_exp = abs(_get_stmt_value(ist, ["InterestExpense","InterestExpenseNonOperating","InterestExpenseIncome"]))

        ev_ebitda = (ev/ebitda) if (is_num(ev) and is_num(ebitda) and ebitda>0) else np.nan
        fcf_yield_pct  = (fcf/mcap*100.0) if (is_num(fcf) and is_num(mcap) and mcap>0) else np.nan
        net_cash_pct   = ((total_cash-total_debt)/mcap*100.0) if (is_num(total_cash) and is_num(total_debt) and is_num(mcap) and mcap>0) else np.nan
        int_cov        = (ebit/interest_exp) if (is_num(ebit) and is_num(interest_exp) and interest_exp>0) else np.nan

        return {
            "Ticker": t,
            "Name": info.get("shortName") or info.get("longName") or t,
            "Sector": info.get("sector") or "",
            "MarketCap": mcap,
            "P/B": pb,
            "EV/EBITDA": ev_ebitda,
            "FCFYield%": fcf_yield_pct,
            "NetCashToMktCap%": net_cash_pct,
            "CurrentRatio": curr_ratio,
            "InterestCoverage": int_cov,
            "Price": price
        }
    except Exception:
        return {"Ticker": t}

def fetch_metrics_yf(tickers:list[str])->pd.DataFrame:
    rows=[]
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futs = {ex.submit(_fetch_one, t): t for t in tickers}
        for fut in as_completed(futs):
            rows.append(fut.result())
            time.sleep(random.uniform(*SLEEP_BETWEEN_CALLS))
    df=pd.DataFrame(rows)

    for c in EXPECTED_COLS:
        if c not in df.columns: df[c]=np.nan

    num_cols = ["MarketCap","P/B","EV/EBITDA","FCFYield%","NetCashToMktCap%","CurrentRatio","InterestCoverage","Price"]
    for c in num_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    return df

# ============ Scoring ============
def percentile(series: pd.Series, higher_is_better: bool)->pd.Series:
    r=series.rank(pct=True,method="average")
    return r*100.0 if higher_is_better else (1.0-r)*100.0

def compute_core_score(df: pd.DataFrame)->pd.DataFrame:
    core=pd.Series(0.0,index=df.index); wsum=pd.Series(0.0,index=df.index)
    for col,w in CORE_WEIGHTS.items():
        sc=percentile(df[col], DIRS[col])
        df[f"Score_{col}"]=sc
        m=sc.notna(); core[m]+=sc[m]*w; wsum[m]+=w
    df["CoreScore"]=(core/wsum.replace(0,np.nan)).fillna(0).round(1)
    return df

def klarman_checklist(df: pd.DataFrame)->pd.DataFrame:
    checks={
        "FCF_Positive": (df["FCFYield%"]>=FCF_YIELD_MIN),
        "EVEBITDA_low": (df["EV/EBITDA"]<=EV_EBITDA_MAX),
        "PB_low": (df["P/B"]<=PB_MAX),
        "NetCash_OK": (df["NetCashToMktCap%"]>=NET_CASH_TO_MKT_MIN),
        "CR_OK": (df["CurrentRatio"]>=CURRENT_RATIO_MIN),
        "Interest_OK": (df["InterestCoverage"]>=INTEREST_COVER_MIN),
    }
    for k,v in checks.items(): df[k]=v.fillna(False)
    df["ChecklistScore"]=df[list(checks)].sum(axis=1)
    df["KlarmanGate"]=df[list(checks)].all(axis=1)
    return df

# ============ Public entrypoint ============
def screen_klarman(top_n=15, limit=6000, order="core", include_metric_details=True):
    """
    Returns top N ordered by:
      - order="core": CoreScore desc (default)
      - order="gate": KlarmanGate, ChecklistScore, CoreScore
    Each item includes metric breakdown with value, percentile, weight, direction,
    and weighted contribution (percentile * weight).
    """
    tickers = get_nasdaq_universe(limit)
    print(f"Universe size: {len(tickers)}")

    df = fetch_metrics_yf(tickers)
    df["MarketCap_num"] = pd.to_numeric(df["MarketCap"], errors="coerce")
    df = df[df["MarketCap_num"] > 0].drop(columns=["MarketCap_num"])
    print(f"Have MarketCap>0 for: {len(df)} tickers")

    if len(df)==0:
        df = fetch_metrics_yf(FALLBACK_TICKERS)
        df["MarketCap_num"] = pd.to_numeric(df["MarketCap"], errors="coerce")
        df = df[df["MarketCap_num"] > 0].drop(columns=["MarketCap_num"])

    df = klarman_checklist(df)
    df = compute_core_score(df)

    if order=="gate":
        df=df.sort_values(["KlarmanGate","ChecklistScore","CoreScore"],ascending=[False,False,False])
    else:
        df=df.sort_values(["CoreScore"],ascending=[False])

    cols=["Ticker","Name","Sector","CoreScore","ChecklistScore","KlarmanGate",
          "MarketCap","P/B","EV/EBITDA","FCFYield%","NetCashToMktCap%","CurrentRatio","InterestCoverage","Price"]
    df_out=df[cols].head(int(top_n)).copy()

    out=[]
    for _,r in df_out.iterrows():
        row={c:("" if pd.isna(r[c]) else (float(r[c]) if c not in ["Ticker","Name","Sector","KlarmanGate"] else r[c])) for c in cols}
        if include_metric_details:
            metrics=[]
            for m,w in CORE_WEIGHTS.items():
                pct = None if pd.isna(r.get(f"Score_{m}")) else round(float(r.get(f"Score_{m}")),1)
                val = None if pd.isna(r.get(m)) else float(r.get(m))
                contrib = None if pct is None else round(pct*w,2)
                metrics.append({
                    "metric": m,
                    "value": val,
                    "percentile_score": pct,
                    "weight": w,
                    "direction": "higher" if DIRS[m] else "lower",
                    "weighted_contribution": contrib
                })
            row["metrics"]=metrics
        out.append(row)
    return out

if __name__=="__main__":
    print(json.dumps(screen_klarman(top_n=15, limit=6000, order="core", include_metric_details=True), indent=2))