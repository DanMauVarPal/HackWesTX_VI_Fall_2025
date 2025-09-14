# soros_screener.py
import time, math, json, random
import pandas as pd, numpy as np, requests, yfinance as yf
from concurrent.futures import ThreadPoolExecutor, as_completed

# ================= Config =================
SLEEP_BETWEEN_CALLS = (0.02, 0.06)
MAX_WORKERS = 12
HTTP_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123 Safari/537.36"}

# Soros-style variables (focus on trend, volatility, momentum)
PRICE_MOMENTUM_DAYS = 50
VOLATILITY_DAYS = 30
PEAK_DRAWUP_MAX = 1.20    # recent price vs 50-day high
PEAK_DRAWDOWN_MAX = 0.30  # recent price vs 52-week high
VOLUME_SPIKE_MIN = 1.5     # current volume vs avg volume
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70

# CoreScore weights for Soros-style metrics
CORE_WEIGHTS = {
    "Momentum%": 0.25,
    "Volatility%": 0.15,
    "DrawupRatio": 0.20,
    "Drawdown%": 0.20,
    "VolumeSpike": 0.10,
    "RSI": 0.10
}

# Directions: True means higher is better
DIRS = {
    "Momentum%": True,
    "Volatility%": False,
    "DrawupRatio": False,
    "Drawdown%": False,
    "VolumeSpike": True,
    "RSI": True
}

EXPECTED_COLS = [
    "Ticker","Name","Sector","Price","Momentum%","Volatility%","DrawupRatio",
    "Drawdown%","VolumeSpike","RSI"
]

# Fallback tickers
FALLBACK_TICKERS = ["AAPL","MSFT","GOOGL","AMZN","NVDA","META","TSLA","JPM"]

# ================= Helpers =================
def is_num(x):
    try:
        return x is not None and not pd.isna(x) and np.isfinite(float(x))
    except:
        return False

def ffloat(x):
    try:
        if x is None or (isinstance(x, float) and math.isnan(x)):
            return np.nan
        return float(x)
    except:
        return np.nan

# ================= Yahoo fetch =================
def _fetch_soros(ticker: str) -> dict:
    try:
        tk = yf.Ticker(ticker)
        hist = tk.history(period="3mo")  # use last 3 months for trend metrics
        if len(hist) < 2:
            return {"Ticker": ticker}

        price_now = ffloat(hist["Close"].iloc[-1])
        price_prev = ffloat(hist["Close"].iloc[-PRICE_MOMENTUM_DAYS]) if len(hist) > PRICE_MOMENTUM_DAYS else ffloat(hist["Close"].iloc[0])
        momentum = ((price_now - price_prev) / price_prev) * 100.0 if is_num(price_now) and is_num(price_prev) else np.nan

        volatility = hist["Close"].pct_change().rolling(VOLATILITY_DAYS).std().iloc[-1] * 100 if len(hist) >= VOLATILITY_DAYS else np.nan

        drawup_ratio = price_now / hist["Close"].rolling(PRICE_MOMENTUM_DAYS).max().iloc[-1] if len(hist) >= PRICE_MOMENTUM_DAYS else np.nan
        drawdown = (hist["Close"].max() - price_now) / hist["Close"].max() * 100

        avg_vol = hist["Volume"].mean()
        vol_spike = hist["Volume"].iloc[-1] / avg_vol if avg_vol > 0 else np.nan

        # RSI calculation
        delta = hist["Close"].diff()
        gain = delta.clip(lower=0)
        loss = -1 * delta.clip(upper=0)
        avg_gain = gain.rolling(14).mean().iloc[-1]
        avg_loss = loss.rolling(14).mean().iloc[-1]
        rsi = 100 - (100 / (1 + avg_gain / avg_loss)) if avg_loss != 0 else 100

        info = tk.info if hasattr(tk, "info") else {}
        return {
            "Ticker": ticker,
            "Name": info.get("shortName") or info.get("longName") or ticker,
            "Sector": info.get("sector") or "",
            "Price": price_now,
            "Momentum%": momentum,
            "Volatility%": volatility,
            "DrawupRatio": drawup_ratio,
            "Drawdown%": drawdown,
            "VolumeSpike": vol_spike,
            "RSI": rsi
        }
    except Exception as e:
        return {"Ticker": ticker}

def fetch_metrics_soros(tickers: list[str]) -> pd.DataFrame:
    rows = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futs = {ex.submit(_fetch_soros, t): t for t in tickers}
        for fut in as_completed(futs):
            rows.append(fut.result())
            time.sleep(random.uniform(*SLEEP_BETWEEN_CALLS))
    df = pd.DataFrame(rows)
    for c in EXPECTED_COLS:
        if c not in df.columns:
            df[c] = np.nan
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

# ================= Public entrypoint =================
def screen_soros(top_n=15, limit=1000, order="core"):
    tickers = FALLBACK_TICKERS[:limit]
    df = fetch_metrics_soros(tickers)
    df = compute_core_score(df)
    df = df.sort_values("CoreScore", ascending=False) if order=="core" else df
    return df.head(top_n).to_dict(orient="records")

if __name__ == "__main__":
    print(json.dumps(screen_soros(top_n=15), indent=2))
