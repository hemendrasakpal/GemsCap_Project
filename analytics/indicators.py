# analytics/indicators.py
import pandas as pd


def sma(series: pd.Series, window: int):
    return series.rolling(window).mean()


def ema(series: pd.Series, span: int):
    return series.ewm(span=span, adjust=False).mean()


def sma_ema_bundle(df: pd.DataFrame, close_col='close', sma_windows=(20, 50), ema_spans=(12, 26)):
    out = {}
    s = df[close_col]
    for w in sma_windows:
        out[f'sma_{w}'] = sma(s, w)
    for sp in ema_spans:
        out[f'ema_{sp}'] = ema(s, sp)
    return pd.DataFrame(out)


def rsi(series: pd.Series, period: int = 14):
    delta = series.diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    ma_up = up.ewm(alpha=1 / period, adjust=False).mean()
    ma_down = down.ewm(alpha=1 / period, adjust=False).mean()
    rs = ma_up / (ma_down + 1e-12)
    return 100 - (100 / (1 + rs))


def macd(series: pd.Series, fast=12, slow=26, signal=9):
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


def bollinger_bands(series: pd.Series, window=20, n_std=2):
    ma = series.rolling(window).mean()
    std = series.rolling(window).std(ddof=0)
    upper = ma + n_std * std
    lower = ma - n_std * std
    return ma, upper, lower


def vwap(df: pd.DataFrame, price_col='close', volume_col='volume'):
    pv = df[price_col] * df[volume_col]
    cum_pv = pv.cumsum()
    cum_vol = df[volume_col].cumsum()
    return cum_pv / (cum_vol + 1e-12)


def atr(df: pd.DataFrame, n=14, high_col='high', low_col='low', close_col='close'):
    high = df[high_col]
    low = df[low_col]
    close = df[close_col]
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / n, adjust=False).mean()
    return atr


# Utility: rolling z-score for a series
def rolling_zscore(series: pd.Series, window: int):
    roll_mean = series.rolling(window).mean()
    roll_std = series.rolling(window).std(ddof=0)
    return (series - roll_mean) / (roll_std + 1e-12)

def detect_rsi_divergence(df: pd.DataFrame, rsi_col='rsi', price_col='close', lookback=30):
    """
    Simple heuristic:
    - bullish divergence: price makes lower low while RSI makes higher low within lookback window
    - bearish divergence: price makes higher high while RSI makes lower high
    Returns dict with latest flag and indices
    """
    s_price = df[price_col].dropna()
    s_rsi = df[rsi_col].dropna()
    if len(s_price) < lookback or len(s_rsi) < lookback:
        return {'error': 'insufficient data'}
    recent_price = s_price[-lookback:]
    recent_rsi = s_rsi.reindex(recent_price.index)
    # highs/lows
    price_low_idx = recent_price.idxmin()
    price_high_idx = recent_price.idxmax()
    rsi_low_idx = recent_rsi.idxmin()
    rsi_high_idx = recent_rsi.idxmax()
    result = {'bullish_divergence': False, 'bearish_divergence': False}
    # bullish: price low is lower than previous low but RSI low is higher (i.e. price lower low, rsi higher low)
    if recent_price.iloc[-1] < recent_price.iloc[0] and recent_rsi.iloc[-1] > recent_rsi.iloc[0]:
        result['bullish_divergence'] = True
    if recent_price.iloc[-1] > recent_price.iloc[0] and recent_rsi.iloc[-1] < recent_rsi.iloc[0]:
        result['bearish_divergence'] = True
    return result
