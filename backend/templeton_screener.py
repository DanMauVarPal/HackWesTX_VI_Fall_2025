# templeton_screener.py
import sys, os, time, math, json, random
import pandas as pd, numpy as np, requests, yfinance as yf
from concurrent.futures import ThreadPoolExecutor, as_completed

# ================= Universe sources (HTTPS) =================
SEC_URLS = [
    "https://www.sec.gov/files/company_tickers.json",
    "https://www.sec.gov/files/company_tickers_exchange.json",
]

# Cache for the SEC ticker list
SYMBOL_CACHE = "symbol_cache_us.json"   # saved in working dir
CACHE_TTL_SECS = 24 * 3600              # reuse for 24h

def _normalize_for_yahoo(sym: str) -> str:
    """Convert raw exchange/SEC symbols to Yahoo format."""
    s = (sym or "").strip().upper()
    s = s.replace(".", "-").replace(" ", "")
    if "^" in s or not s:
        return ""
    return s

# ================= Config =================
SLEEP_BETWEEN_CALLS = (0.02, 0.06)   # jitter between Yahoo calls (rate-limit friendly)
MAX_WORKERS = 12
HTTP_HEADERS = {
    "User-Agent": "HackWestX-StockCopilot/1.0 (+contact@example.com) Mozilla/5.0"
}

# Templeton gates (objective proxies)
PE_MAX = 12.0
PB_MAX = 1.5
PRICE_TO_52W_LOW_MAX = 1.30
DEBT_TO_EQUITY_MAX = 1.5
CURRENT_RATIO_MIN = 1.5
DIVIDEND_MIN_YIELD = 0.0
EARNINGS_GROWTH_MIN = -5.0

# CoreScore weights & directions (higher better = True)
CORE_WEIGHTS = {
    "P/E": 0.20,
    "P/B": 0.15,
    "PriceTo52wLow": 0.20,
    "DividendYield%": 0.10,
    "ROE%": 0.15,
    "DebtToEquity": 0.10,
    "EarningsGrowth%": 0.10
}
DIRS = {
    "P/E": False, "P/B": False, "PriceTo52wLow": False,
    "DividendYield%": True, "ROE%": True, "DebtToEquity": False, "EarningsGrowth%": True
}

EXPECTED_COLS = [
    "Ticker","Name","Sector","MarketCap","P/E","P/B","Price","PriceTo52wLow",
    "DrawdownFromHigh%","DividendYield%","ROE%","DebtToEquity","CurrentRatio","EarningsGrowth%"
]

# ================= Robust requests Session =================
from requests.adapters import HTTPAdapter
try:
    from urllib3.util.retry import Retry  # modern urllib3
    RETRY = Retry(
        total=5,
        backoff_factor=0.4,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=frozenset(["GET"]),
        raise_on_status=False,
    )
except Exception:
    from urllib3.util.retry import Retry  # compat
    RETRY = Retry(
        total=5,
        backoff_factor=0.4,
        status_forcelist=[429, 500, 502, 503, 504],
        method_whitelist=frozenset(["GET"]),
        raise_on_status=False,
    )

SESSION = requests.Session()
SESSION.headers.update(HTTP_HEADERS)
SESSION.mount("https://", HTTPAdapter(max_retries=RETRY))
SESSION.mount("http://",  HTTPAdapter(max_retries=RETRY))

# ================= SEC universe with 24h cache =================
def get_us_equity_universe(limit=100000) -> list[str]:
    # 1) use cache if fresh
    try:
        if os.path.exists(SYMBOL_CACHE) and (time.time() - os.path.getmtime(SYMBOL_CACHE) < CACHE_TTL_SECS):
            with open(SYMBOL_CACHE, "r", encoding="utf-8") as f:
                cached = json.load(f)
            syms = [s for s in cached if s]
            print(f"[universe] loaded {len(syms)} tickers from cache")
            return syms[:limit] if limit else syms
    except Exception:
        pass

    # 2) pull from SEC
    syms = set()
    for url in SEC_URLS:
        try:
            r = SESSION.get(url, timeout=25)
            r.raise_for_status()
            data = r.json()
            it = data.values() if isinstance(data, dict) else (data if isinstance(data, list) else [])
            for row in it:
                t = _normalize_for_yahoo(str(row.get("ticker") or ""))
                if t:
                    syms.add(t)
        except Exception as e:
            print(f"[universe] SEC fetch failed: {url} -> {type(e).__name__}: {e}")

    out = sorted(syms)

    # 3) write/update cache
    try:
        with open(SYMBOL_CACHE, "w", encoding="utf-8") as f:
            json.dump(out, f)
    except Exception:
        pass

    return out[:limit] if limit else out

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
    return v*100.0 if 0 <= v <= 2.0 else v

def normalize_div_yield(x):
    if not is_num(x): return np.nan
    v = float(x)
    if 0 <= v <= 1.0: return v*100.0
    if v > 50: return v/100.0
    return v

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

def _get_live_price(tk, info):
    # 1) fast_info
    try:
        fi = getattr(tk, "fast_info", {}) or {}
        p = float(fi.get("last_price"))
        if np.isfinite(p): return p
    except Exception:
        pass
    # 2) info
    try:
        p = float(info.get("currentPrice"))
        if np.isfinite(p): return p
    except Exception:
        pass
    # 3) 1-day intraday last
    try:
        h = tk.history(period="1d", interval="1m")
        if not h.empty:
            p = float(h["Close"].dropna().iloc[-1])
            if np.isfinite(p): return p
    except Exception:
        pass
    return np.nan

# ================= Yahoo fetch =================
def _fetch_one(t: str) -> dict:
    try:
        tk = yf.Ticker(t)
        try: info = tk.get_info()
        except Exception: info = getattr(tk, "info", {}) or {}

        fi = getattr(tk, "fast_info", {}) or {}
        price   = _get_live_price(tk, info)
        mcap    = ffloat(info.get("marketCap"))    or ffloat(fi.get("market_cap"))
        shares  = ffloat(info.get("sharesOutstanding")) or ffloat(fi.get("shares"))
        if not is_num(mcap) and is_num(price) and is_num(shares):
            mcap = price * shares

        wk_low  = ffloat(info.get("fiftyTwoWeekLow"))  or ffloat(fi.get("year_low"))
        wk_high = ffloat(info.get("fiftyTwoWeekHigh")) or ffloat(fi.get("year_high"))
        pe      = ffloat(info.get("trailingPE"))
        pb      = ffloat(info.get("priceToBook"))
        eps_ttm = ffloat(info.get("trailingEps"))
        d2e     = ffloat(info.get("debtToEquity"))
        curr    = ffloat(info.get("currentRatio"))
        roe     = frac_to_pct(info.get("returnOnEquity"))
        div_yld = normalize_div_yield(info.get("dividendYield"))
        earn_g  = frac_to_pct(info.get("earningsGrowth"))

        if not is_num(pe): pe = _compute_pe(price, eps_ttm)

        if not is_num(div_yld):
            # Prefer get_dividends(); fall back to .dividends
            try:
                divs = tk.get_dividends()
            except Exception:
                divs = getattr(tk, "dividends", None)
            if divs is not None and len(divs) > 0 and is_num(price):
                ttm_div = float(divs.tail(4).sum())
                if ttm_div > 0: div_yld = (ttm_div / float(price)) * 100.0

        if not is_num(pb):
            try:
                bs = tk.get_balance_sheet()
                equity = None
                for k in ["StockholdersEquity","TotalStockholderEquity",
                          "Total Equity Gross Minority Interest","TotalEquityGrossMinorityInterest"]:
                    if k in bs.index:
                        equity = ffloat(bs.loc[k].iloc[0]); break
                pb = _compute_pb(price, shares, equity)
            except Exception:
                pass

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
            "CurrentRatio": curr,
            "EarningsGrowth%": earn_g,
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
    num_cols = ["MarketCap","P/E","P/B","Price","PriceTo52wLow","DrawdownFromHigh%","DividendYield%","ROE%","DebtToEquity","CurrentRatio","EarningsGrowth%"]
    for c in num_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")
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

def templeton_checklist(df: pd.DataFrame) -> pd.DataFrame:
    checks = {
        "PE_low":        (df["P/E"] <= PE_MAX),
        "PB_low":        (df["P/B"] <= PB_MAX),
        "Near_52w_low":  (df["PriceTo52wLow"] <= PRICE_TO_52W_LOW_MAX),
        "Debt_OK":       (df["DebtToEquity"] <= DEBT_TO_EQUITY_MAX),
        "CR_OK":         (df["CurrentRatio"] >= CURRENT_RATIO_MIN),
        "Div_OK":        (df["DividendYield%"] >= DIVIDEND_MIN_YIELD),
        "Growth_OK":     (df["EarningsGrowth%"] > EARNINGS_GROWTH_MIN),
    }
    for k, v in checks.items():
        df[k] = v.fillna(False)
    df["ChecklistScore"] = df[list(checks)].sum(axis=1)
    df["TempletonGate"]  = df[list(checks)].all(axis=1)
    return df

# ================= Public entrypoint =================
def screen_templeton(top_n=15, limit=6000, order="core", include_metric_details=True):
    tickers = get_us_equity_universe(limit)
    print(f"Universe size: {len(tickers)}")
    if not tickers:
        print("Universe empty (Nasdaq/SEC not reachable).")
        return []

    df = fetch_metrics_yf(tickers)
    df["MarketCap_num"] = pd.to_numeric(df["MarketCap"], errors="coerce")
    df = df[df["MarketCap_num"] > 0].drop(columns=["MarketCap_num"])
    print(f"Have MarketCap>0 for: {len(df)} tickers")
    if df.empty:
        print("No valid Yahoo metrics for universe. Returning empty result.")
        return []

    df = templeton_checklist(df)
    df = compute_core_score(df)

    if order == "gate":
        df = df.sort_values(["TempletonGate","ChecklistScore","CoreScore"], ascending=[False,False,False])
    else:
        df = df.sort_values(["CoreScore"], ascending=[False])

    cols = [
        "Ticker","Name","Sector","CoreScore","ChecklistScore","TempletonGate",
        "MarketCap","Price","P/E","P/B","PriceTo52wLow","DividendYield%","ROE%",
        "DebtToEquity","CurrentRatio","EarningsGrowth%","DrawdownFromHigh%"
    ]
    df_out = df[cols].head(int(top_n)).copy()

    out = []
    for _, r in df_out.iterrows():
        row = {c: ("" if pd.isna(r[c]) else (float(r[c]) if c not in ["Ticker","Name","Sector","TempletonGate"] else r[c])) for c in cols}
        if include_metric_details:
            metrics = []
            for m, w in CORE_WEIGHTS.items():
                pct = None if pd.isna(r.get(f"Score_{m}")) else round(float(r.get(f"Score_{m}")), 1)
                val = None if pd.isna(r.get(m)) else float(r.get(m))
                contrib = None if pct is None else round(pct * w, 2)
                metrics.append({
                    "metric": m, "value": val, "percentile_score": pct,
                    "weight": w, "direction": "higher" if DIRS[m] else "lower",
                    "weighted_contribution": contrib
                })
            row["metrics"] = metrics
        out.append(row)
    return out

if __name__ == "__main__":
    # Allow quick override from CLI: python templeton_screener.py 10 800
    top_n = int(sys.argv[1]) if len(sys.argv) > 1 else 15
    limit  = int(sys.argv[2]) if len(sys.argv) > 2 else 6000
    print(json.dumps(screen_templeton(top_n=top_n, limit=limit, order="core", include_metric_details=True), indent=2))