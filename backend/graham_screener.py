import time
import json
import math
import pandas as pd
import numpy as np
import requests
import yfinance as yf

# ------------------------------
# Config
# ------------------------------
USE_SAMPLE_TICKERS = True
SAMPLE_TICKERS = ["AAPL","MSFT","JNJ","XOM","KO","INTC","WMT","PG"]  # safe yfinance tickers
MAX_TICKERS_FROM_NASDAQ = 200   # if not using sample, cap for speed
SLEEP_BETWEEN_CALLS = 0.2       # seconds between yfinance calls (rate-limit friendly)

# Graham gates / thresholds
MARKET_CAP_MIN = 2_000_000_000       # $2B
PE_MAX = 15.0
PB_MAX = 1.5
PE_x_PB_MAX = 22.5
CURRENT_RATIO_MIN = 2.0
DEBT_TO_EQUITY_MAX = 1.0
DIVIDEND_MIN_YIELD = 0.0             # >0 means pays dividend
EPS_POSITIVE = True                   # EPS (ttm) > 0

# CoreScore metric weights (must sum ~1; code will renormalize per-row if missing)
CORE_WEIGHTS = {
    "P/E": 0.25,            # lower better
    "P/B": 0.15,            # lower better
    "ROE%": 0.20,           # higher better
    "OperatingMargin%": 0.15, # higher better
    "GrossMargin%": 0.10,     # higher better
    "CurrentRatio": 0.075,  # higher better
    "DebtToEquity": 0.075   # lower better
}

# ------------------------------
# Universe helpers
# ------------------------------
def get_nasdaq_universe(limit=MAX_TICKERS_FROM_NASDAQ) -> list[str]:
    """
    Pulls symbol directory from Nasdaq Trader (Nasdaq + otherlisted), returns a de-duplicated list.
    """
    urls = [
        "https://ftp.nasdaqtrader.com/dynamic/SymDir/nasdaqtraded.txt",
        "https://ftp.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt",
    ]
    syms = set()
    for url in urls:
        try:
            r = requests.get(url, timeout=20)
            r.raise_for_status()
            lines = r.text.strip().splitlines()
            header = lines[0].split("|")
            # detect column index for symbol (usually "Symbol" or "ACT Symbol")
            sym_idx = 0
            if "Symbol" in header:
                sym_idx = header.index("Symbol")
            elif "ACT Symbol" in header:
                sym_idx = header.index("ACT Symbol")
            for line in lines[1:]:
                parts = line.split("|")
                if len(parts) <= sym_idx: 
                    continue
                s = parts[sym_idx].strip()
                # skip test/when-issued etc.
                if not s or any(x in s for x in [".", "$", "^", " "]):
                    continue
                syms.add(s)
        except Exception:
            pass
    syms = sorted(list(syms))
    return syms[:limit]

# ------------------------------
# Yahoo fetch & normalization
# ------------------------------
def fetch_metrics_yf(tickers: list[str]) -> pd.DataFrame:
    """
    For each ticker, fetch a small set of commonly available fields from Yahoo Finance.
    Returns a DataFrame with numeric columns ready for screening/scoring.
    """
    rows = []
    for t in tickers:
        try:
            tk = yf.Ticker(t)
            # yfinance .get_info() (newer) falls back to .info (older) if needed
            try:
                info = tk.get_info()
            except Exception:
                info = getattr(tk, "info", {}) or {}

            # Defensive reads: many fields may be missing
            trailing_pe   = safe_float(info.get("trailingPE"))
            price_to_book = safe_float(info.get("priceToBook"))
            mcap          = safe_float(info.get("marketCap"))
            current_ratio = safe_float(info.get("currentRatio"))
            d_to_e        = safe_float(info.get("debtToEquity"))
            roe           = to_percent(info.get("returnOnEquity"))         # fraction -> %
            op_margin     = to_percent(info.get("operatingMargins"))       # fraction -> %
            gross_margin  = to_percent(info.get("grossMargins"))           # fraction -> %
            div_yield     = to_percent(info.get("dividendYield"))          # fraction -> %
            eps_ttm       = safe_float(info.get("trailingEps"))
            pb = price_to_book
            pe = trailing_pe

            rows.append({
                "Ticker": t,
                "Name": info.get("shortName") or info.get("longName") or t,
                "Sector": info.get("sector") or "",
                "MarketCap": mcap,
                "P/E": pe,
                "P/B": pb,
                "PE_x_PB": pe * pb if is_num(pe) and is_num(pb) else np.nan,
                "CurrentRatio": current_ratio,
                "DebtToEquity": d_to_e,
                "ROE%": roe,
                "OperatingMargin%": op_margin,
                "GrossMargin%": gross_margin,
                "DividendYield%": div_yield,
                "EPS_ttm": eps_ttm,
            })
            time.sleep(SLEEP_BETWEEN_CALLS)
        except Exception:
            # keep going; append a minimal row with only ticker
            rows.append({"Ticker": t})
    df = pd.DataFrame(rows)
    return df

def safe_float(x):
    try:
        if x is None or (isinstance(x, float) and (math.isnan(x))):
            return np.nan
        return float(x)
    except Exception:
        return np.nan

def is_num(x):
    try:
        return x is not None and not pd.isna(x) and np.isfinite(float(x))
    except Exception:
        return False

def to_percent(x):
    """Yahoo returns many ratios as fractions (e.g., 0.18). Convert to 18.0 (%) if numeric."""
    if not is_num(x): 
        return np.nan
    return float(x) * 100.0

# ------------------------------
# Graham checklist & CoreScore
# ------------------------------
def graham_checklist(df: pd.DataFrame) -> pd.DataFrame:
    checks = {}
    checks["Size_OK"]   = (df["MarketCap"] >= MARKET_CAP_MIN)
    checks["PE_OK"]     = (df["P/E"] <= PE_MAX)
    checks["PB_OK"]     = (df["P/B"] <= PB_MAX)
    checks["PEPB_OK"]   = (df["PE_x_PB"] <= PE_x_PB_MAX)
    checks["CR_OK"]     = (df["CurrentRatio"] >= CURRENT_RATIO_MIN)
    checks["DE_OK"]     = (df["DebtToEquity"] < DEBT_TO_EQUITY_MAX)
    checks["Div_OK"]    = (df["DividendYield%"] > DIVIDEND_MIN_YIELD)
    checks["EPS_OK"]    = (df["EPS_ttm"] > 0) if EPS_POSITIVE else pd.Series(True, index=df.index)

    for k, v in checks.items():
        df[k] = v.fillna(False)

    # total checklist score (0..8)
    df["ChecklistScore"] = df[list(checks)].sum(axis=1)
    df["GrahamGate"] = df[["Size_OK","PE_OK","PB_OK","PEPB_OK","CR_OK","DE_OK","EPS_OK"]].all(axis=1)
    return df

def percentile(series: pd.Series, higher_is_better: bool) -> pd.Series:
    # rank pct (0..1); NaNs remain NaN; flip if lower is better
    r = series.rank(pct=True, method="average")
    if higher_is_better:
        return r * 100.0
    else:
        return (1.0 - r) * 100.0

def compute_core_score(df: pd.DataFrame) -> pd.DataFrame:
    # Build per-metric 0..100 subscores
    subs = {}
    dirs = {
        "P/E": False,
        "P/B": False,
        "ROE%": True,
        "OperatingMargin%": True,
        "GrossMargin%": True,
        "CurrentRatio": True,
        "DebtToEquity": False
    }
    for col, w in CORE_WEIGHTS.items():
        if col in df.columns:
            subs[col] = percentile(df[col], dirs[col])

    # weighted sum; renormalize weights row-wise to ignore NaNs
    # start from zeros
    core = pd.Series(0.0, index=df.index)
    wsum = pd.Series(0.0, index=df.index)
    for col, w in CORE_WEIGHTS.items():
        if col in subs:
            s = subs[col]
            mask = s.notna()
            core[mask] = core[mask] + s[mask] * w
            wsum[mask] = wsum[mask] + w

    df["CoreScore"] = (core / wsum.replace(0, np.nan)).fillna(0).round(1)
    return df

# ------------------------------
# Main
# ------------------------------
def main():
    if USE_SAMPLE_TICKERS:
        tickers = SAMPLE_TICKERS
    else:
        tickers = get_nasdaq_universe()

    print(f"Fetching Yahoo metrics for {len(tickers)} tickers...")
    df = fetch_metrics_yf(tickers)

    # Apply Graham checklist and CoreScore
    df = graham_checklist(df)
    df = compute_core_score(df)

    # Final rank: GrahamGate first, then ChecklistScore, then CoreScore
    df_ranked = df.sort_values(["GrahamGate","ChecklistScore","CoreScore"], ascending=[False, False, False])

    cols_to_show = [
        "Ticker","Name","Sector",
        "CoreScore","ChecklistScore","GrahamGate",
        "MarketCap","P/E","P/B","PE_x_PB",
        "CurrentRatio","DebtToEquity","ROE%","OperatingMargin%","GrossMargin%","DividendYield%","EPS_ttm"
    ]
    print("\nTop results:")
    print(df_ranked[cols_to_show].head(12).to_string(index=False))

    # Also save a CSV for your UI / Excel
    df_ranked[cols_to_show].to_csv("graham_scores.csv", index=False)
    print("\nSaved: graham_scores.csv")

if __name__ == "__main__":
    main()