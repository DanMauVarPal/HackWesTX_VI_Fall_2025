# soros_screener.py
import sys, os, json, time, math, random
import pandas as pd, numpy as np, requests, yfinance as yf
from concurrent.futures import ThreadPoolExecutor, as_completed

# ================= Config =================
SLEEP_BETWEEN_CALLS = (0.05, 0.15)   # gentler pacing (yahoo rate limits)
MAX_WORKERS = 6                      # momentum uses history() -> keep moderate
HTTP_HEADERS = {
    "User-Agent": "HackWestX-StockCopilot/1.0 (+contact@example.com) Mozilla/5.0"
}

# SEC symbol feed cache
SEC_URLS = [
    "https://www.sec.gov/files/company_tickers.json",
    "https://www.sec.gov/files/company_tickers_exchange.json",
]
SYMBOL_CACHE = "symbol_cache_us.json"
CACHE_TTL_SECS = 24*3600

# ===== Soros-style CoreScore weights & directions =====
# Higher-is-better? True/False in DIRS
CORE_WEIGHTS = {
    "Mom12m%":        0.35,
    "Mom3m%":         0.20,
    "Trend200%":      0.15,   # price vs SMA200
    "Trend50%":       0.10,   # price vs SMA50
    "Volatility20d%": 0.10,   # lower is better
    "MaxDrawdown%":   0.05,   # lower is better (less negative)
    "DollarVol20d":   0.05,   # liquidity bonus
}
DIRS = {
    "Mom12m%":        True,
    "Mom3m%":         True,
    "Trend200%":      True,
    "Trend50%":       True,
    "Volatility20d%": False,
    "MaxDrawdown%":   False,
    "DollarVol20d":   True,
}

EXPECTED_COLS = [
    "Ticker","Name","Sector","Price",
    "Mom12m%","Mom3m%","Trend200%","Trend50%","Volatility20d%","MaxDrawdown%","DollarVol20d"
]

# ================= Robust requests Session (for SEC) =================
from requests.adapters import HTTPAdapter
try:
    from urllib3.util.retry import Retry
    RETRY = Retry(
        total=5, backoff_factor=0.4,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=frozenset(["GET"]),
        raise_on_status=False,
    )
except Exception:
    # compat for older urllib3
    from urllib3.util.retry import Retry
    RETRY = Retry(
        total=5, backoff_factor=0.4,
        status_forcelist=[429, 500, 502, 503, 504],
        method_whitelist=frozenset(["GET"]),
        raise_on_status=False,
    )

SESSION = requests.Session()
SESSION.headers.update(HTTP_HEADERS)
SESSION.mount("https://", HTTPAdapter(max_retries=RETRY))
SESSION.mount("http://",  HTTPAdapter(max_retries=RETRY))

# ================= Universe (SEC, cached) =================
def _normalize_for_yahoo(sym: str) -> str:
    s = (sym or "").strip().upper()
    s = s.replace(".", "-").replace(" ", "")
    return "" if "^" in s or not s else s

def get_us_equity_universe(limit=100000) -> list[str]:
    # try cache
    try:
        if os.path.exists(SYMBOL_CACHE) and (time.time() - os.path.getmtime(SYMBOL_CACHE) < CACHE_TTL_SECS):
            with open(SYMBOL_CACHE, "r", encoding="utf-8") as f:
                cached = json.load(f)
            syms = [s for s in cached if s]
            return syms[:limit] if limit else syms
    except Exception:
        pass

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

def _get_info_safe(tk):
    try: return tk.get_info()
    except Exception: return getattr(tk, "info", {}) or {}

def _get_live_price(tk, info):
    # 1) fast_info
    try:
        fi = getattr(tk, "fast_info", {}) or {}
        p = float(fi.get("last_price"))
        if np.isfinite(p): return p
    except Exception: pass
    # 2) info
    try:
        p = float(info.get("currentPrice"))
        if np.isfinite(p): return p
    except Exception: pass
    # 3) 1d intraday last
    try:
        h = tk.history(period="1d", interval="1m")
        if not h.empty:
            p = float(h["Close"].dropna().iloc[-1])
            if np.isfinite(p): return p
    except Exception: pass
    return np.nan

# ================= Yahoo fetch (momentum/vol) =================
def _fetch_one_soros(t: str) -> dict:
    try:
        tk = yf.Ticker(t)
        info = _get_info_safe(tk)

        # 1y daily data (enough for 200d SMA + 12m momentum)
        h = tk.history(period="1y", interval="1d", auto_adjust=False, prepost=False, actions=False)
        if h is None or h.empty or "Close" not in h:
            return {"Ticker": t}

        closes = h["Close"].dropna()
        vols   = h["Volume"].fillna(0)

        if closes.empty:
            return {"Ticker": t}

        price = float(closes.iloc[-1])

        # Momentum
        mom12 = (price / float(closes.iloc[0]) - 1.0) if len(closes) >= 2 else np.nan
        mom3  = (price / float(closes.iloc[-63]) - 1.0) if len(closes) >= 64 else np.nan  # ~3 months

        # Trend: % above SMAs
        sma200 = float(closes.rolling(200).mean().iloc[-1]) if len(closes) >= 200 else np.nan
        sma50  = float(closes.rolling(50).mean().iloc[-1])  if len(closes) >= 50  else np.nan
        trend200 = (price / sma200 - 1.0) if is_num(sma200) and sma200 > 0 else np.nan
        trend50  = (price / sma50  - 1.0) if is_num(sma50)  and sma50  > 0 else np.nan

        # Volatility: 20d annualized stdev of daily returns
        rets = closes.pct_change().dropna()
        vol20 = (rets.tail(20).std() * np.sqrt(252)) if len(rets) >= 20 else np.nan

        # Max drawdown over ~1y
        if len(closes) >= 20:
            running_max = closes.cummax()
            drawdowns = (closes / running_max - 1.0)
            maxdd = float(drawdowns.min())  # negative fraction, e.g., -0.35
        else:
            maxdd = np.nan

        # Liquidity: 20d avg dollar volume
        if len(closes) >= 20 and "Volume" in h:
            dv20 = float((closes.tail(20) * vols.tail(20)).mean())
        else:
            dv20 = np.nan

        # name/sector (best-effort)
        name = info.get("shortName") or info.get("longName") or t
        sector = info.get("sector") or ""

        return {
            "Ticker": t,
            "Name": name,
            "Sector": sector,
            "Price": price,
            "Mom12m%": (mom12 * 100.0) if is_num(mom12) else np.nan,
            "Mom3m%":  (mom3  * 100.0) if is_num(mom3)  else np.nan,
            "Trend200%": (trend200 * 100.0) if is_num(trend200) else np.nan,
            "Trend50%":  (trend50  * 100.0) if is_num(trend50)  else np.nan,
            "Volatility20d%": (vol20 * 100.0) if is_num(vol20) else np.nan,
            "MaxDrawdown%":   (maxdd * 100.0) if is_num(maxdd) else np.nan,
            "DollarVol20d": dv20,
        }
    except Exception:
        return {"Ticker": t}

def fetch_metrics_soros(tickers: list[str]) -> pd.DataFrame:
    rows = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futs = {ex.submit(_fetch_one_soros, t): t for t in tickers}
        for fut in as_completed(futs):
            rows.append(fut.result())
            time.sleep(random.uniform(*SLEEP_BETWEEN_CALLS))
    df = pd.DataFrame(rows)

    # ensure expected cols exist
    for c in EXPECTED_COLS:
        if c not in df.columns:
            df[c] = np.nan

    num_cols = [c for c in EXPECTED_COLS if c not in ["Ticker","Name","Sector"]]
    for c in num_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    return df

# ================= Scoring =================
def percentile(series: pd.Series, higher_is_better: bool) -> pd.Series:
    r = series.rank(pct=True, method="average")
    return r * 100.0 if higher_is_better else (1.0 - r) * 100.0

def compute_core_score(df: pd.DataFrame) -> pd.DataFrame:
    core = pd.Series(0.0, index=df.index)
    wsum = pd.Series(0.0, index=df.index)
    for col, w in CORE_WEIGHTS.items():
        sc = percentile(df[col], DIRS[col])
        df[f"Score_{col}"] = sc
        m = sc.notna()
        core[m] += sc[m] * w
        wsum[m] += w
    df["CoreScore"] = (core / wsum.replace(0, np.nan)).fillna(0).round(1)
    return df

# ================= Public entrypoint =================
def screen_soros(top_n=15, limit=600, order="core", include_metric_details=True):
    # Momentum uses history() heavily — keep limit moderate to avoid throttling
    tickers = get_us_equity_universe(limit)
    print(f"Universe size: {len(tickers)}")
    if not tickers:
        print("Universe empty (SEC not reachable).")
        return []

    df = fetch_metrics_soros(tickers)
    df = compute_core_score(df)

    df = df.sort_values(["CoreScore"], ascending=[False])

    cols = [
        "Ticker","Name","Sector","CoreScore",
        "Price","Mom12m%","Mom3m%","Trend200%","Trend50%",
        "Volatility20d%","MaxDrawdown%","DollarVol20d"
    ]
    df_out = df[cols].head(int(top_n)).copy()

    out = []
    for _, r in df_out.iterrows():
        row = {c: ("" if pd.isna(r[c]) else (float(r[c]) if c not in ["Ticker","Name","Sector"] else r[c])) for c in cols}
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
    top_n = int(sys.argv[1]) if len(sys.argv) > 1 else 15
    limit  = int(sys.argv[2]) if len(sys.argv) > 2 else 600   # keep moderate for history()
    print(json.dumps(screen_soros(top_n=top_n, limit=limit), indent=2))
