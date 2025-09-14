# backend/main.py
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

# import your screeners
import sys, os
sys.path.append(os.path.dirname(__file__))  # ensure local import works
from templeton_screener import screen_templeton           # public entrypoint ✔
from klarman_screener import screen_klarman               # public entrypoint ✔

# For Graham, build a small wrapper using its existing helpers
from graham_screener import (
    USE_SAMPLE_TICKERS,
    SAMPLE_TICKERS,
    get_nasdaq_universe,
    fetch_metrics_yf,
    graham_checklist,
    compute_core_score,
)
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

@app.get("/test")
def test():
    return {"ok": True, "msg": "API is alive"}

def screen_graham(top_n=15, limit=200):
    # Recreate the “main” flow as a function that returns JSON-friendly data.
    # (same ingredients the script’s main() uses)
    # - build universe
    tickers = SAMPLE_TICKERS if USE_SAMPLE_TICKERS else get_nasdaq_universe(limit=limit)
    # - fetch metrics
    df = fetch_metrics_yf(tickers)
    # - checklist + core score
    df = graham_checklist(df)
    df = compute_core_score(df)
    # - order like script: Gate, then ChecklistScore, then CoreScore
    df_ranked = df.sort_values(
        ["GrahamGate", "ChecklistScore", "CoreScore"], ascending=[False, False, False]
    )
    cols = [
        "Ticker","Name","Sector",
        "CoreScore","ChecklistScore","GrahamGate",
        "MarketCap","P/E","P/B","PE_x_PB",
        "CurrentRatio","DebtToEquity","ROE%","OperatingMargin%","GrossMargin%","DividendYield%","EPS_ttm"
    ]
    # return top N as plain dicts (JSON serializable)
    out = df_ranked[cols].head(int(top_n)).replace({pd.NA: None}).to_dict(orient="records")
    return out

@app.get("/graham")
def graham(top_n: int = Query(15, ge=1, le=100), limit: int = Query(200, ge=10, le=100000)):
    return screen_graham(top_n=top_n, limit=limit)

@app.get("/templeton")
def templeton(top_n: int = Query(15, ge=1, le=100), limit: int = Query(6000, ge=10, le=100000), order: str = Query("core")):
    # templeton_screener already exposes screen_templeton that returns a JSON-ready list
    return screen_templeton(top_n=top_n, limit=limit, order=order, include_metric_details=True)

@app.get("/klarman")
def klarman(top_n: int = Query(15, ge=1, le=100), limit: int = Query(6000, ge=10, le=100000), order: str = Query("core")):
    # klarman_screener already exposes screen_klarman that returns a JSON-ready list
    return screen_klarman(top_n=top_n, limit=limit, order=order, include_metric_details=True)
