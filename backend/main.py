# backend/main.py
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
# ---------- Stable schema helpers ----------
from typing import Any, Dict, List, Optional

# wherever you define the standard columns
STANDARD_COLUMNS = [
    "Ticker","Name","Sector",
    "Price",                     # <-- add this
    "CoreScore","ChecklistScore","Gate",
    "MarketCap","P/E","P/B","DividendYield%",
    "CurrentRatio","DebtToEquity","ROE%","OperatingMargin%","GrossMargin%","EPS_ttm",
]

def pick(d, *keys):
    for k in keys:
        v = d.get(k)
        if v not in (None, "", "NaN"):  # light sanity
            return v
    return None

def metric_value(row, key):
    ms = row.get("metrics")
    if isinstance(ms, list):
        for m in ms:
            if isinstance(m, dict) and m.get("metric") == key:
                return m.get("value")
    return None

def normalize_row(strategy, row):
    return {
        "Ticker": pick(row,"Ticker","ticker","symbol"),
        "Name": pick(row,"Name","company","shortName"),
        "Sector": pick(row,"Sector","sector"),
        # NEW: Price (prefer quotes; last/close as fallbacks; finally metrics if you ever add them)
        "Price": pick(row,"Price","price","regularMarketPrice","RegularMarketPrice","Close","AdjClose","last","Last")
                 or metric_value(row,"Price") or metric_value(row,"RegularMarketPrice"),
        "CoreScore": pick(row,"CoreScore","Score","core_score"),
        "ChecklistScore": pick(row,"ChecklistScore","checklist_score"),
        "Gate": bool(pick(row,"Gate",f"{strategy}_gate",f"{strategy.capitalize()}Gate")),
        "MarketCap": pick(row,"MarketCap","marketCap","cap"),
        "P/E": pick(row,"P/E","PE","trailingPE"),
        "P/B": pick(row,"P/B","PB","priceToBook"),
        "DividendYield%": pick(row,"DividendYield%","dividendYield%","dividendYield"),
        "CurrentRatio": pick(row,"CurrentRatio","currentRatio"),
        "DebtToEquity": pick(row,"DebtToEquity","debtToEquity"),
        "ROE%": pick(row,"ROE%","returnOnEquity%","roe%"),
        "OperatingMargin%": pick(row,"OperatingMargin%","operatingMargin%","operatingMargin"),
        "GrossMargin%": pick(row,"GrossMargin%","grossMargin%","grossMargins"),
        "EPS_ttm": pick(row,"EPS_ttm","trailingEps","eps_ttm"),
        "metrics": row.get("metrics"),
    }

# --------- JSON sanitizer: replace NaN/±inf with None; numpy/pandas -> native -----
import math
from typing import Any
try:
    import numpy as np
except Exception:
    np = None  # type: ignore
try:
    import pandas as pd
except Exception:
    pd = None  # type: ignore

def to_json_safe(obj: Any) -> Any:
    # floats
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    # numpy scalars
    if np is not None and isinstance(obj, (np.floating,)):
        v = float(obj)
        return None if (math.isnan(v) or math.isinf(v)) else v
    if np is not None and isinstance(obj, (np.integer,)):
        return int(obj)
    # pandas timestamps
    if pd is not None and isinstance(obj, getattr(pd, "Timestamp", ())):
        return obj.isoformat()
    # pandas containers / numpy arrays
    if pd is not None and isinstance(obj, (getattr(pd, "Series", ()), getattr(pd, "Index", ()))):
        obj = obj.tolist()
    if np is not None and isinstance(obj, (np.ndarray,)):
        obj = obj.tolist()
    # containers
    if isinstance(obj, dict):
        return {k: to_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [to_json_safe(v) for v in obj]
    # everything else unchanged (str, int, bool, None, etc.)
    return obj
# -----------------------------------------------------------------------------------

def normalize_row(strategy: str, row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map whatever the screener returns into a consistent row dict.
    We keep raw metrics (if present) under 'metrics' for drilldown.
    """
    # Common synonyms used across the three screeners
    out = {
        "Ticker":        pick(row, "Ticker", "ticker", "symbol"),
        "Name":          pick(row, "Name", "Company", "company", "shortName"),
        "Sector":        pick(row, "Sector", "sector"),
        "CoreScore":     pick(row, "CoreScore", "core_score", "Score", "score"),
        "ChecklistScore":pick(row, "ChecklistScore", "checklist_score"),
        "Gate":          pick(row, f"{strategy.capitalize()}Gate", "Gate", "gate", f"{strategy}_gate"),
        "MarketCap":     pick(row, "MarketCap", "marketCap", "cap"),
        "P/E":           pick(row, "P/E", "PE", "trailingPE"),
        "P/B":           pick(row, "P/B", "PB", "priceToBook"),
        "DividendYield%":pick(row, "DividendYield%", "dividendYield%", "dividendYield"),
        "CurrentRatio":  pick(row, "CurrentRatio", "currentRatio"),
        "DebtToEquity":  pick(row, "DebtToEquity", "debtToEquity"),
        "ROE%":          pick(row, "ROE%", "roe%", "returnOnEquity%"),
        "OperatingMargin%": pick(row, "OperatingMargin%", "operatingMargin%", "operatingMargin"),
        "GrossMargin%":     pick(row, "GrossMargin%", "grossMargin%", "grossMargins"),
        "EPS_ttm":       pick(row, "EPS_ttm", "eps_ttm", "EPS", "trailingEps"),
        # keep everything the screener provided for detail views
        "metrics":       row.get("metrics", None),
    }
    return out

def normalize_result(strategy: str, rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    norm = [normalize_row(strategy, r) for r in rows]
    return {
        "strategy": strategy,
        "schema_version": 1,
        "columns": STANDARD_COLUMNS,
        "count": len(norm),
        "rows": norm,
        "meta": {"source": "yahoo+sec+internal", "ts": __import__("time").time()},
    }

from fastapi import HTTPException
def _wrap_endpoint(fetch_fn, strategy: str, **kwargs):
    try:
        data = fetch_fn(**kwargs)
        if not isinstance(data, list):
            # some screeners may return dict with 'results'
            data = data.get("results", [])
        return normalize_result(strategy, data)
    except HTTPException:
        raise
    except Exception as e:
        # Return a 500 with a concise, user-facing message
        raise HTTPException(status_code=500, detail=f"{strategy} screener error: {e}")
# -------------------------------------------

# import your screeners
import sys, os
sys.path.append(os.path.dirname(__file__))  # ensure local import works
from templeton_screener import screen_templeton           # public entrypoint ✔
from klarman_screener import screen_klarman               # public entrypoint ✔
from buffett_screener import screen_buffett   # :contentReference[oaicite:0]{index=0}
from lynch_screener import screen_lynch       # :contentReference[oaicite:1]{index=1}
from soros_screener import screen_soros       # :contentReference[oaicite:2]{index=2}

# For Graham, build a small wrapper using its existing helpers
# Flexible import: work with any recent graham_screener shape
import importlib
_gs = importlib.import_module("graham_screener")

gs_get_universe      = getattr(_gs, "get_nasdaq_universe", None)
gs_fetch_metrics     = getattr(_gs, "fetch_metrics_yf", None)
gs_checklist         = getattr(_gs, "graham_checklist", None)
gs_compute_core      = getattr(_gs, "compute_core_score", None)
gs_screen_graham_fn  = getattr(_gs, "screen_graham", None)

import pandas as pd

app = FastAPI(title="Value Screeners API")

# Allow your Flutter app to call this locally (Android emulator uses 10.0.2.2)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # lock this down later if you want
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def screen_graham(top_n=15, limit=200):
    """
    Returns a list[dict] of rows suitable for normalize_result(...).
    Prefers a native screen_graham(...) if the module provides one.
    Otherwise reconstructs the classic pipeline (universe -> metrics -> checklist -> score).
    """
    # 1) If the module provides a ready screen function, prefer it.
    if callable(gs_screen_graham_fn):
        try:
            # Try the richer signature first
            result = gs_screen_graham_fn(top_n=top_n, limit=limit, order="core", include_metric_details=True)  # type: ignore
        except TypeError:
            # Fallback: maybe it only accepts (top_n, limit)
            result = gs_screen_graham_fn(top_n=top_n, limit=limit)  # type: ignore

        # Some implementations return {"rows":[...]} already; others return list[dict]
        if isinstance(result, dict) and "rows" in result:
            return result["rows"]
        return result

    # 2) Otherwise, rebuild the classic flow using the module’s helpers.
    missing = [name for name, fn in {
        "get_nasdaq_universe": gs_get_universe,
        "fetch_metrics_yf":    gs_fetch_metrics,
        "graham_checklist":    gs_checklist,
        "compute_core_score":  gs_compute_core,
    }.items() if not callable(fn)]
    if missing:
        raise RuntimeError(f"graham_screener is missing required functions: {', '.join(missing)}")

    # universe -> metrics -> checklist -> score
    tickers = gs_get_universe(limit=limit)  # type: ignore
    import pandas as pd  # local import to avoid hard dependency at import time
    df = gs_fetch_metrics(tickers)          # type: ignore
    df = gs_checklist(df)                   # type: ignore
    df = gs_compute_core(df)                # type: ignore

    # sort with whatever columns exist
    sort_cols = [c for c in ["GrahamGate", "ChecklistScore", "CoreScore"] if c in df.columns]
    df_ranked = df.sort_values(sort_cols, ascending=[False]*len(sort_cols)) if sort_cols else df

    # choose available columns (be forgiving if names shifted)
    preferred_cols = [
        "Ticker","Name","Sector",
        "CoreScore","ChecklistScore","GrahamGate",
        "MarketCap","P/E","P/B","PE_x_PB",
        "CurrentRatio","DebtToEquity","ROE%","OperatingMargin%","GrossMargin%","DividendYield%","EPS_ttm",
    ]
    cols = [c for c in preferred_cols if c in df_ranked.columns]
    rows = df_ranked[cols].head(int(top_n)).to_dict(orient="records")

    # Leave final NaN/±inf cleanup to your to_json_safe wrapper at return time
    return rows


@app.get("/graham")
def graham(top_n: int = Query(15, ge=1, le=100), limit: int = Query(200, ge=10, le=100000)):
    rows = screen_graham(top_n=top_n, limit=limit)
    payload = normalize_result("graham", rows)
    print(payload)
    return to_json_safe(payload)


@app.get("/templeton")
def templeton(top_n: int = Query(15, ge=1, le=100), limit: int = Query(200, ge=10, le=100000), order: str = Query("core")):
    payload = _wrap_endpoint(screen_templeton, "templeton",
                             top_n=top_n, limit=limit, order=order, include_metric_details=True)
    print(payload)
    return to_json_safe(payload)

@app.get("/klarman")
def klarman(top_n: int = Query(15, ge=1, le=100), limit: int = Query(200, ge=10, le=100000), order: str = Query("core")):
    payload = _wrap_endpoint(screen_klarman, "klarman",
                             top_n=top_n, limit=limit, order=order, include_metric_details=True)
    print(payload)
    return to_json_safe(payload)
@app.get("/buffett")
def buffett(top_n: int = Query(15, ge=1, le=100), limit: int = Query(200, ge=10, le=100000), order: str = Query("core")):
    payload = _wrap_endpoint(screen_buffett, "buffett",
                             top_n=top_n, limit=limit, order=order, include_metric_details=True)
    print(payload)
    return to_json_safe(payload)

@app.get("/lynch")
def lynch(top_n: int = Query(15, ge=1, le=100), limit: int = Query(200, ge=10, le=100000), order: str = Query("core")):
    payload = _wrap_endpoint(screen_lynch, "lynch",
                             top_n=top_n, limit=limit, order=order, include_metric_details=True)
    print(payload)
    return to_json_safe(payload)

@app.get("/soros")
def soros(top_n: int = Query(15, ge=1, le=100), limit: int = Query(200, ge=10, le=100000), order: str = Query("core")):
    # soros uses price history heavily; keep limit moderate for speed
    payload = _wrap_endpoint(screen_soros, "soros",
                             top_n=top_n, limit=limit, order=order, include_metric_details=True)
    print(payload)
    return to_json_safe(payload)
