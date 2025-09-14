# common_screener.py
# Shared utilities for all screeners:
# - Robust SEC-based US ticker universe (HTTPS, cached 24h)
# - Yahoo-friendly symbol normalization ('.' -> '-', trim spaces, drop '^')
# - Filters out non-common securities (warrants/units/rights/preferreds)
# - Threaded fetch helper + core score computation + output shaping

import os, json, time, math, random
import pandas as pd, numpy as np, requests
from concurrent.futures import ThreadPoolExecutor, as_completed

# ================= General config =================
SLEEP_BETWEEN_CALLS = (0.02, 0.06)  # jitter to be gentle on Yahoo endpoints
MAX_WORKERS = 12
HTTP_HEADERS = {
    # Good citizen UA; include a contact per SEC guidance if you can
    "User-Agent": "HackWestX-StockCopilot/1.0 (+contact@example.com) Mozilla/5.0"
}

# ================= Robust requests Session =================
from requests.adapters import HTTPAdapter
try:
    from urllib3.util.retry import Retry
    RETRY = Retry(
        total=5,
        backoff_factor=0.4,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=frozenset(["GET"]),
        raise_on_status=False,
    )
except Exception:  # very old urllib3 compatibility
    from urllib3.util.retry import Retry
    RETRY = Retry(
        total=5,
        backoff_factor=0.4,
        status_forcelist=[429, 500, 502, 503, 504],
        method_whitelist=frozenset(["GET"]),  # deprecated name
        raise_on_status=False,
    )

SESSION = requests.Session()
SESSION.headers.update(HTTP_HEADERS)
SESSION.mount("https://", HTTPAdapter(max_retries=RETRY))
SESSION.mount("http://",  HTTPAdapter(max_retries=RETRY))

# ================= SEC universe (HTTPS) with cache =================
SEC_URLS = [
    "https://www.sec.gov/files/company_tickers.json",
    "https://www.sec.gov/files/company_tickers_exchange.json",
]

# Cache file lives next to this module (more reliable than CWD)
SYMBOL_CACHE = os.path.join(os.path.dirname(__file__), "symbol_cache_us.json")
CACHE_TTL_SECS = 24 * 3600  # 24 hours

# Restrict to major exchanges when the SEC payload includes an exchange field
ALLOWED_EXCHANGES = {"NYSE", "NASDAQ", "NYSE AMERICAN", "NYSEMKT", "NYSE ARCA"}

def _normalize_for_yahoo(sym: str) -> str:
    """Normalize SEC/Nasdaq symbols into Yahoo-friendly format."""
    s = (sym or "").strip().upper()
    s = s.replace(".", "-")  # class shares: BRK.B -> BRK-B
    s = s.replace(" ", "")   # drop spaces
    if "^" in s or not s:    # Yahoo caret products / empty
        return ""
    return s

# Yahoo rarely has fundamentals for these suffixes (warrants/units/rights)
EXCLUDE_SUFFIXES = {"W", "WS", "WT", "WTA", "WTS", "U", "UN", "RT", "R"}

def _looks_like_common(sym: str) -> bool:
    """Heuristic filter to keep common stock and drop warrants/units/rights/preferreds."""
    s = _normalize_for_yahoo(sym)
    if not s:
        return False
    tail = s.split("-")[-1]  # e.g., BRK-B -> "B", BAC-PRA -> "PRA"
    # Exclude warrants/units/rights by explicit suffix list
    if tail in EXCLUDE_SUFFIXES:
        return False
    # Exclude most preferred shares (e.g., "-PRA", "-PRB", "-PRN", "-PA", "-PB")
    if tail.startswith("PR") or (len(tail) <= 3 and tail.startswith("P")):
        return False
    return True

def get_us_equity_universe(limit: int = 100000) -> list[str]:
    """
    Build a de-duped list of US common-stock tickers from SEC HTTPS feeds.
    - Normalizes symbols for Yahoo
    - Filters out warrants/units/rights/preferreds
    - Optionally restricts to major exchanges (when provided)
    - Caches for 24h to reduce repeated pulls
    """
    # 1) Serve fresh cache if available
    try:
        if os.path.exists(SYMBOL_CACHE) and (time.time() - os.path.getmtime(SYMBOL_CACHE) < CACHE_TTL_SECS):
            with open(SYMBOL_CACHE, "r", encoding="utf-8") as f:
                cached = json.load(f)
            syms = [s for s in cached if s]
            print(f"[universe] loaded {len(syms)} tickers from cache")
            return syms[:limit] if limit else syms
    except Exception:
        pass

    # 2) Pull from SEC (both endpoints)
    syms = set()
    for url in SEC_URLS:
        try:
            r = SESSION.get(url, timeout=25)
            r.raise_for_status()
            data = r.json()
            it = data.values() if isinstance(data, dict) else (data if isinstance(data, list) else [])
            for row in it:
                raw = str(row.get("ticker") or "")
                exch = str(row.get("exchange") or "").upper()
                # If exchange info is there, keep major exchanges only
                if exch and ALLOWED_EXCHANGES and exch not in ALLOWED_EXCHANGES:
                    continue
                if _looks_like_common(raw):
                    t = _normalize_for_yahoo(raw)
                    if t:
                        syms.add(t)
        except Exception as e:
            print(f"[universe] SEC fetch failed: {url} -> {type(e).__name__}: {e}")

    out = sorted(syms)

    # 3) Persist cache (best effort)
    try:
        with open(SYMBOL_CACHE, "w", encoding="utf-8") as f:
            json.dump(out, f)
    except Exception:
        pass

    return out[:limit] if limit else out

# Back-compat alias so older screeners still calling get_nasdaq_universe keep working
def get_nasdaq_universe(limit: int = 6000) -> list[str]:
    return get_us_equity_universe(limit=limit)

# ================= Helpers used by screeners =================
def is_num(x):
    try:
        return x is not None and not pd.isna(x) and np.isfinite(float(x))
    except Exception:
        return False

def ffloat(x):
    try:
        if x is None or (isinstance(x, float) and math.isnan(x)):
            return np.nan
        return float(x)
    except Exception:
        return np.nan

def frac_to_pct(x):
    """Convert a fraction (e.g., 0.23) to percent (23.0). Pass-through for already-percent-like values."""
    if not is_num(x): 
        return np.nan
    v = float(x)
    return v * 100.0 if 0 <= v <= 2.0 else v

def normalize_div_yield(x):
    """Yahoo may return 0.023 (2.3%), 2.3, or 230. Normalize to percent."""
    if not is_num(x): 
        return np.nan
    v = float(x)
    if 0 <= v <= 1.0: 
        return v * 100.0
    if v > 50: 
        return v / 100.0
    return v

def percentile(series: pd.Series, higher_is_better: bool) -> pd.Series:
    """Percentile rank (0..100). If higher_is_better=False, invert."""
    r = series.rank(pct=True, method="average")
    return r * 100.0 if higher_is_better else (1.0 - r) * 100.0

def compute_core_score(df: pd.DataFrame, CORE_WEIGHTS: dict, DIRS: dict) -> pd.DataFrame:
    """
    Adds Score_<metric> columns and a blended CoreScore using the provided weights + directions.
    Missing metrics are ignored proportional to the sum of available weights.
    """
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

def fetch_many(tickers, fetch_fn, expected_cols, numeric_cols) -> pd.DataFrame:
    """
    Concurrently call fetch_fn(ticker) across the list.
    Ensures expected columns exist and numeric columns are coerced to numeric.
    """
    rows = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futs = {ex.submit(fetch_fn, t): t for t in tickers}
        for fut in as_completed(futs):
            rows.append(fut.result())
            time.sleep(random.uniform(*SLEEP_BETWEEN_CALLS))
    df = pd.DataFrame(rows)
    for c in expected_cols:
        if c not in df.columns:
            df[c] = np.nan
    for c in numeric_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

def build_output(df: pd.DataFrame, CORE_WEIGHTS: dict, DIRS: dict, cols: list, top_n: int, include_metric_details=True):
    """
    Shapes the final JSON for the frontend: keeps only relevant columns,
    optionally attaches per-metric contributions consistent with the chosen investor style.
    """
    df_out = df[cols].head(int(top_n)).copy()
    out = []
    for _, r in df_out.iterrows():
        row = {
            c: ("" if pd.isna(r[c]) else (float(r[c]) if c not in [
                "Ticker","Name","Sector",
                "GrahamGate","LynchGate","KlarmanGate","BuffettGate","TempletonGate","SorosGate"
            ] else r[c]))
            for c in cols
        }
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

# Optional quick test: print a sample of the universe when running this file directly
if __name__ == "__main__":
    syms = get_us_equity_universe(limit=50)
    print(f"{len(syms)} symbols (sample): {syms[:20]}")
