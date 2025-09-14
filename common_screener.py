# common_screener.py
import os, json, time, math, random
import pandas as pd, numpy as np, requests
from concurrent.futures import ThreadPoolExecutor, as_completed

# ================= General config =================
SLEEP_BETWEEN_CALLS = (0.02, 0.06)
MAX_WORKERS = 12
HTTP_HEADERS = {
    "User-Agent": "HackWestX-StockCopilot/1.0 (+contact@example.com) Mozilla/5.0"
}

# ================= Robust requests Session =================
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
    # very old urllib3
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

# ================= SEC universe w/ cache =================
SEC_URLS = [
    "https://www.sec.gov/files/company_tickers.json",
    "https://www.sec.gov/files/company_tickers_exchange.json",
]
SYMBOL_CACHE = "symbol_cache_us.json"
CACHE_TTL_SECS = 24 * 3600

def _normalize_for_yahoo(sym: str) -> str:
    s = (sym or "").strip().upper()
    s = s.replace(".", "-").replace(" ", "")
    if "^" in s or not s:
        return ""
    return s

def get_us_equity_universe(limit: int = 100000) -> list[str]:
    """
    Returns a de-duped list of US tickers (uppercased, Yahoo-normalized),
    sourced from SEC JSON (HTTPS). Uses a 24h on-disk cache.
    """
    # 1) cache
    try:
        if os.path.exists(SYMBOL_CACHE) and (time.time() - os.path.getmtime(SYMBOL_CACHE) < CACHE_TTL_SECS):
            with open(SYMBOL_CACHE, "r", encoding="utf-8") as f:
                cached = json.load(f)
            syms = [s for s in cached if s]
            print(f"[universe] loaded {len(syms)} tickers from cache")
            return syms[:limit] if limit else syms
    except Exception:
        pass

    # 2) fetch
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
    if not is_num(x): return np.nan
    v = float(x)
    return v * 100.0 if 0 <= v <= 2.0 else v

def normalize_div_yield(x):
    if not is_num(x): return np.nan
    v = float(x)
    if 0 <= v <= 1.0: return v * 100.0
    if v > 50: return v / 100.0
    return v

def percentile(series: pd.Series, higher_is_better: bool) -> pd.Series:
    r = series.rank(pct=True, method="average")
    return r * 100.0 if higher_is_better else (1.0 - r) * 100.0

def compute_core_score(df: pd.DataFrame, CORE_WEIGHTS: dict, DIRS: dict) -> pd.DataFrame:
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
    df_out = df[cols].head(int(top_n)).copy()
    out = []
    for _, r in df_out.iterrows():
        row = {
            c: ("" if pd.isna(r[c]) else (float(r[c]) if c not in ["Ticker","Name","Sector",
                                                                   "GrahamGate","LynchGate","KlarmanGate","BuffettGate","TempletonGate"]
                                          else r[c]))
            for c in cols
        }
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
