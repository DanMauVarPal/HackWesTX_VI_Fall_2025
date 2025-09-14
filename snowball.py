import time, math, json, random
import pandas as pd, numpy as np, requests, yfinance as yf
from concurrent.futures import ThreadPoolExecutor, as_completed

# ================= Config =================
SLEEP_BETWEEN_CALLS = (0.02, 0.06)
MAX_WORKERS = 12
HTTP_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123 Safari/537.36"}

# Snowball gates (objective proxies)
PRICE_TO_EARNINGS_MAX = 25.0
DIVIDEND_YIELD_MIN = 2.0
DEBT_TO_EQUITY_MAX = 0.5
ROE_MIN = 15.0
MARKET_CAP_MIN = 2e9

# CoreScore weights
CORE_WEIGHTS = {
    "P/E": 0.25,
    "DividendYield%": 0.20,
    "ROE%": 0.25,
    "DebtToEquity": 0.15,
    "MarketCap": 0.15
}
DIRS = {"P/E": False, "DividendYield%": True, "ROE%": True, "DebtToEquity": False, "MarketCap": True}

EXPECTED_COLS = [
    "Ticker","Name","Sector","MarketCap","P/E","Price","DividendYield%","ROE%","DebtToEquity"
]

FALLBACK_TICKERS = ["AAPL","MSFT","JNJ","KO","PG","WMT","JPM","UNH","DIS","V"]

# ================= Universe =================
def get_sp500_universe(limit=100000) -> list[str]:
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    headers = HTTP_HEADERS
    try:
        r = requests.get(url, headers=headers, timeout=25)
        r.raise_for_status()
        table = pd.read_html(r.text)
        tickers = table[0]["Symbol"].tolist()
        return tickers[:limit]
    except Exception:
        return FALLBACK_TICKERS[:limit]

# ================= Helpers =================
def is_num(x):
    try: return x is not None and not pd.isna(x) and np.isfinite(float(x))
    except: return False

def ffloat(x):
    try:
        if x is None or (isinstance(x, float) and math.isnan(x)): return np.nan
        return float(x)
    except: return np.nan

def normalize_div_yield(x):
    if not is_num(x): return np.nan
    v = float(x)
    if 0 <= v <= 1.0: return v*100.0
    return v

# ================= Yahoo fetch =================
def _fetch_one(t: str) -> dict:
    try:
        tk = yf.Ticker(t)
        try: info = tk.get_info()
        except Exception: info = getattr(tk, "info", {}) or {}

        price   = ffloat(info.get("currentPrice"))
        mcap    = ffloat(info.get("marketCap"))
        pe      = ffloat(info.get("trailingPE"))
        roe     = ffloat(info.get("returnOnEquity"))
        d2e     = ffloat(info.get("debtToEquity"))
        div_yld = normalize_div_yield(info.get("dividendYield"))

        return {
            "Ticker": t,
            "Name": info.get("shortName") or info.get("longName") or t,
            "Sector": info.get("sector") or "",
            "MarketCap": mcap,
            "P/E": pe,
            "Price": price,
            "DividendYield%": div_yld,
            "ROE%": roe,
            "DebtToEquity": d2e
        }
    except Exception:
        return {"Ticker": t}

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

    num_cols = ["MarketCap","P/E","Price","DividendYield%","ROE%","DebtToEquity"]
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

def snowball_checklist(df: pd.DataFrame) -> pd.DataFrame:
    checks = {
        "PE_ok":        (df["P/E"] <= PRICE_TO_EARNINGS_MAX),
        "Div_OK":       (df["DividendYield%"] >= DIVIDEND_YIELD_MIN),
        "Debt_OK":      (df["DebtToEquity"] <= DEBT_TO_EQUITY_MAX),
        "ROE_OK":       (df["ROE%"] >= ROE_MIN),
        "MarketCap_OK": (df["MarketCap"] >= MARKET_CAP_MIN)
    }
    for k, v in checks.items(): df[k] = v.fillna(False)
    df["ChecklistScore"] = df[list(checks)].sum(axis=1)
    df["SnowballGate"] = df[list(checks)].all(axis=1)
    return df

# ================= Public entrypoint =================
def screen_snowball(top_n=15, limit=6000, order="core", include_metric_details=True):
    tickers = get_sp500_universe(limit)
    print(f"Universe size: {len(tickers)}")

    df = fetch_metrics_yf(tickers)
    df = snowball_checklist(df)
    df = compute_core_score(df)

    if order == "gate":
        df = df.sort_values(["SnowballGate","ChecklistScore","CoreScore"], ascending=[False,False,False])
    else:
        df = df.sort_values(["CoreScore"], ascending=[False])

    cols = ["Ticker","Name","Sector","CoreScore","ChecklistScore","SnowballGate",
            "MarketCap","P/E","Price","DividendYield%","ROE%","DebtToEquity"]
    df_out = df[cols].head(int(top_n)).copy()

    out = []
    for _, r in df_out.iterrows():
        row = {c: ("" if pd.isna(r[c]) else (float(r[c]) if c not in ["Ticker","Name","Sector","SnowballGate"] else r[c])) for c in cols}
        if include_metric_details:
            metrics = []
            total = 0.0
            for m, w in CORE_WEIGHTS.items():
                pct = None if pd.isna(r.get(f"Score_{m}")) else round(float(r.get(f"Score_{m}")),1)
                val = None if pd.isna(r.get(m)) else float(r.get(m))
                contrib = None if pct is None else round(pct*w,2)
                total += (contrib or 0)
                metrics.append({"metric":m,"value":val,"percentile_score":pct,"weight":w,"direction":"higher" if DIRS[m] else "lower","weighted_contribution":contrib})
            row["metrics"] = metrics
        out.append(row)
    return out

if __name__ == "__main__":
    print(json.dumps(screen_snowball(top_n=15, limit=6000, order="core", include_metric_details=True), indent=2))
