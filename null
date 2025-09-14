# intelligent_investor_screener.py
import time, math, json, random
import pandas as pd, numpy as np, requests, yfinance as yf
from concurrent.futures import ThreadPoolExecutor, as_completed

# ================= Config =================
SLEEP_BETWEEN_CALLS = (0.02, 0.06)
MAX_WORKERS = 12
HTTP_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123 Safari/537.36"}

# Graham-style gates (objective proxies)
PE_MAX = 15.0              # Low P/E
PB_MAX = 1.2               # Low P/B
PRICE_TO_52W_LOW_MAX = 1.20 # Price near 52-week low (margin of safety)
DEBT_TO_EQUITY_MAX = 1.0   # Conservative debt
CURRENT_RATIO_MIN = 1.5    # Liquidity
DIVIDEND_MIN_YIELD = 2.0   # Minimum dividend yield
ROE_MIN = 5.0              # Positive ROE
EARNINGS_GROWTH_MIN = 0.0  # Positive earnings growth

# CoreScore weights
CORE_WEIGHTS = {
    "P/E": 0.25,
    "P/B": 0.20,
    "PriceTo52wLow": 0.15,
    "DividendYield%": 0.15,
    "ROE%": 0.10,
    "DebtToEquity": 0.10,
    "CurrentRatio": 0.05
}

DIRS = {
    "P/E": False,
    "P/B": False,
    "PriceTo52wLow": False,
    "DividendYield%": True,
    "ROE%": True,
    "DebtToEquity": False,
    "CurrentRatio": True
}

EXPECTED_COLS = [
    "Ticker","Name","Sector","MarketCap","P/E","P/B","Price","PriceTo52wLow",
    "DrawdownFromHigh%","DividendYield%","ROE%","DebtToEquity","CurrentRatio"
]

FALLBACK_TICKERS = ["AAPL","MSFT","JNJ","WMT","PG","XOM","KO","PFE","PEP","CVX","DIS","INTC","IBM","VZ","T","JPM","BAC","C","MA","V"]

# ================= Universe =================
def get_nasdaq_universe(limit=100000) -> list[str]:
    urls = [
        "https://ftp.nasdaqtrader.com/dynamic/SymDir/nasdaqtraded.txt",
        "https://ftp.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt",
    ]
    syms = set()
    for url in urls:
        try:
            r = requests.get(url, timeout=25, headers=HTTP_HEADERS)
            r.raise_for_status()
            lines = r.text.strip().splitlines()
            header = lines[0].split("|")
            def idx(name, fallback=None): return header.index(name) if name in header else fallback
            i_sym  = idx("Symbol", idx("ACT Symbol", 0))
            i_etf  = idx("ETF", None)
            i_test = idx("Test Issue", None)
            for ln in lines[1:]:
                parts = ln.split("|")
                if len(parts) <= i_sym: continue
                s = parts[i_sym].strip()
                if not s or any(x in s for x in [".","$","^"," "]): continue
                if i_etf is not None and i_etf < len(parts) and parts[i_etf].strip().upper() == "Y": continue
                if i_test is not None and i_test < len(parts) and parts[i_test].strip().upper() == "Y": continue
                syms.add(s)
        except:
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
        if x is None or (isinstance(x, float) and math.isnan(x)): return np.nan
        return float(x)
    except: return np.nan

def frac_to_pct(x):
    if not is_num(x): return np.nan
    v = float(x)
    return v*100.0 if v <= 2.0 else v

def normalize_div_yield(x):
    if not is_num(x): return np.nan
    v = float(x)
    if 0 <= v <= 1.0: return v*100.0
    if v > 50: return v/100.0
    return v

# ================= Yahoo fetch =================
def _compute_pe(price, eps_ttm):
    if is_num(price) and is_num(eps_ttm) and eps_ttm != 0:
        return float(price) / float(eps_ttm)
    return np.nan

def _compute_pb(price, shares_out, equity_total):
    if is_num(price) and is_num(shares_out) and shares_out > 0 and is_num(equity_total) and equity_total > 0:
        bvps = float(equity_total) / float(shares_out)
        if bvps > 0:
            return float(price) / bvps
    return np.nan

def _fetch_one(t: str) -> dict:
    try:
        tk = yf.Ticker(t)
        try: info = tk.get_info()
        except: info = getattr(tk, "info", {}) or {}
        fi = getattr(tk, "fast_info", {}) or {}

        price   = ffloat(info.get("currentPrice")) or ffloat(fi.get("last_price"))
        mcap    = ffloat(info.get("marketCap")) or ffloat(fi.get("market_cap"))
        shares  = ffloat(info.get("sharesOutstanding")) or ffloat(fi.get("shares"))
        if not is_num(mcap) and is_num(price) and is_num(shares):
            mcap = price * shares

        wk_low  = ffloat(info.get("fiftyTwoWeekLow")) or ffloat(fi.get("year_low"))
        wk_high = ffloat(info.get("fiftyTwoWeekHigh")) or ffloat(fi.get("year_high"))
        pe      = ffloat(info.get("trailingPE"))
        pb      = ffloat(info.get("priceToBook"))
        eps_ttm = ffloat(info.get("trailingEps"))
        d2e     = ffloat(info.get("debtToEquity"))
        curr    = ffloat(info.get("currentRatio"))
        roe     = frac_to_pct(info.get("returnOnEquity"))
        div_yld = normalize_div_yield(info.get("dividendYield"))

        if not is_num(pe): pe = _compute_pe(price, eps_ttm)
        if not is_num(pb):
            try:
                bs = tk.get_balance_sheet()
                equity = None
                for k in ["StockholdersEquity","TotalStockholderEquity","Total Equity Gross Minority Interest","TotalEquityGrossMinorityInterest"]:
                    if k in bs.index: equity = ffloat(bs.loc[k].iloc[0]); break
                pb = _compute_pb(price, shares, equity)
            except: pass

        p_to_low = (price / wk_low) if (is_num(price) and is_num(wk_low) and wk_low > 0) else np.nan
        dd_from_hi = ((wk_high - price) / wk_high * 100.0) if (is_num(price) and is_num(wk_high) and wk_high > 0) else np.nan

        return {
            "Ticker": t,
            "Name": info.get("shortName") or info.get("longName") or t,
            "Sector": info.get("sector") or "",
            "MarketCap": mcap,
            "P/E": pe,
            "P/B": pb,
            "Price": price,
            "PriceTo52wLow": p_to_low,
            "DrawdownFromHigh%": dd_from_hi,
            "DividendYield%": div_yld,
            "ROE%": roe,
            "DebtToEquity": d2e,
            "CurrentRatio": curr
        }
    except: return {"Ticker": t}

def fetch_metrics_yf(tickers: list[str]) -> pd.DataFrame:
    rows = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futs = {ex.submit(_fetch_one, t): t for t in tickers}
        for fut in as_completed(futs):
            rows.append(fut.result())
            time.sleep(random.uniform(*SLEEP_BETWEEN_CALLS))
    df = pd.DataFrame(rows)
    for c in EXPECTED_COLS:
        if c not in df.columns: df[c] = np.nan
    num_cols = ["MarketCap","P/E","P/B","Price","PriceTo52wLow","DrawdownFromHigh%","DividendYield%","ROE%","DebtToEquity","CurrentRatio"]
    for c in num_cols: df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

# ================= Scoring =================
def percentile(series: pd.Series, higher_is_better: bool) -> pd.Series:
    r = series.rank(pct=True, method="average")
    return r*100.0 if higher_is_better else (1.0 - r)*100.0

def compute_core_score(df: pd.DataFrame) -> pd.DataFrame:
    core = pd.Series(0.0, index=df.index)
    wsum = pd.Series(0.0, index=df.index)
    for col, w in CORE_WEIGHTS.items():
        sc = percentile(df[col], DIRS[col])
        df[f"Score_{col}"] = sc
        m = sc.notna()
        core[m] += sc[m]*w
        wsum[m] += w
    df["CoreScore"] = (core / wsum.replace(0, np.nan)).fillna(0).round(1)
    return df

def graham_checklist(df: pd.DataFrame) -> pd.DataFrame:
    checks = {
        "PE_low": (df["P/E"] <= PE_MAX),
        "PB_low": (df["P/B"] <= PB_MAX),
        "Near_52w_low": (df["PriceTo52wLow"] <= PRICE_TO_52W_LOW_MAX),
        "Debt_OK": (df["DebtToEquity"] <= DEBT_TO_EQUITY_MAX),
        "CR_OK": (df["CurrentRatio"] >= CURRENT_RATIO_MIN),
        "Div_OK": (df["DividendYield%"] >= DIVIDEND_MIN_YIELD),
        "ROE_OK": (df["ROE%"] >= ROE_MIN)
    }
    for k, v in checks.items(): df[k] = v.fillna(False)
    df["ChecklistScore"] = df[list(checks)].sum(axis=1)
    df["GrahamGate"] = df[list(checks)].all(axis=1)
    return df

# ================= Public entrypoint =================
def screen_graham(top_n=15, limit=6000, order="core", include_metric_details=True):
    tickers = get_nasdaq_universe(limit)
    print(f"Universe size: {len(tickers)}")
    df = fetch_metrics_yf(tickers)
    df["MarketCap_num"] = pd.to_numeric(df["MarketCap"], errors="coerce")
    df = df[df["MarketCap_num"] > 0].drop(columns=["MarketCap_num"])
    if len(df) == 0:
        df = fetch_metrics_yf(FALLBACK_TICKERS)
        df["MarketCap_num"] = pd.to_numeric(df["MarketCap"], errors="coerce")
        df = df[df["MarketCap_num"] > 0].drop(columns=["MarketCap_num"])
    df = graham_checklist(df)
    df = compute_core_score(df)
    if order == "gate":
        df = df.sort_values(["GrahamGate","ChecklistScore","CoreScore"], ascending=[False,False,False])
    else:
        df = df.sort_values(["CoreScore"], ascending=[False])

    cols = [
        "Ticker","Name","Sector","CoreScore","ChecklistScore","GrahamGate",
        "MarketCap","P/E","P/B","PriceTo52wLow","DividendYield%","ROE%",
        "DebtToEquity","CurrentRatio","DrawdownFromHigh%"
    ]
    df_out = df[cols].head(int(top_n)).copy()
    out = []
    for _, r in df_out.iterrows():
        row = {c: ("" if pd.isna(r[c]) else (float(r[c]) if c not in ["Ticker","Name","Sector","GrahamGate"] else r[c])) for c in cols}
        if include_metric_details:
            metrics = []
            for m, w in CORE_WEIGHTS.items():
                pct = None if pd.isna(r.get(f"Score_{m}")) else round(float(r.get(f"Score_{m}")), 1)
                val = None if pd.isna(r.get(m)) else float(r.get(m))
                contrib = None if pct is None else round(pct * w, 2)
                metrics.append({
                    "metric": m,
                    "value": val,
                    "percentile_score": pct,
                    "weight": w,
                    "direction": "higher" if DIRS[m] else "lower",
                    "weighted_contribution": contrib
                })
            row["metrics"] = metrics
        out.append(row)
    return out

if __name__ == "__main__":
    print(json.dumps(screen_graham(top_n=15, limit=6000, order="core", include_metric_details=True), indent=2))
