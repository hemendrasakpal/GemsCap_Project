from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import pymongo
import statsmodels.api as sm
import statsmodels.tsa.stattools as ts
from statsmodels.tsa.stattools import adfuller
from statsmodels.regression.linear_model import OLS

MONGO_URI = "mongodb://localhost:27017"
DB_NAME = "gemscap"
TICKS_COLL = "ticks"


def fetch_ticks(symbol, since_minutes=60):
    client = pymongo.MongoClient(MONGO_URI)
    coll = client[DB_NAME][TICKS_COLL]
    since = datetime.utcnow() - timedelta(minutes=since_minutes)
    cursor = coll.find({"symbol": symbol.lower(), "ts": {"$gte": since}})
    df = pd.DataFrame(list(cursor))
    if df.empty:
        return df
    df['ts'] = pd.to_datetime(df['ts'])
    df = df.set_index('ts').sort_index()
    return df


def resample_ohlc(df, timeframe='1s'):
    if df.empty:
        return pd.DataFrame()
    ohlc = df['price'].resample(timeframe).ohlc().dropna()
    vol = df['qty'].resample(timeframe).sum().reindex(ohlc.index).fillna(0)
    ohlc['volume'] = vol
    return ohlc


def hedge_ratio_ols(y, x):
    x = sm.add_constant(x)
    model = sm.OLS(y, x).fit()
    return model.params[1], model.params[0], model


def zscore(spread):
    return (spread - spread.mean()) / spread.std(ddof=0)


def adf_test(series):
    result = adfuller(series.dropna(), autolag='AIC')
    return {'adf': result[0], 'pvalue': result[1]}


def compute_pair_analytics(sym_y, sym_x, timeframe='1m', window=60):
    dfy = resample_ohlc(fetch_ticks(sym_y, since_minutes=24 * 60), timeframe)
    dfx = resample_ohlc(fetch_ticks(sym_x, since_minutes=24 * 60), timeframe)
    common_idx = dfy.index.intersection(dfx.index)
    if len(common_idx) < 10:
        return {'error': 'not enough data'}
    py = dfy.loc[common_idx]['close']
    px = dfx.loc[common_idx]['close']
    beta, intercept, model = hedge_ratio_ols(py, px)
    spread = py - beta * px - intercept
    z = zscore(spread)
    adf = adf_test(spread)
    corr = py.rolling(window=window).corr(px).iloc[-1]
    return {
        'beta': float(beta),
        'intercept': float(intercept),
        'last_spread': float(spread.iloc[-1]),
        'last_z': float(z.iloc[-1]),
        'adf': adf,
        'rolling_corr': float(corr),
        'n': int(len(spread))
    }


# --- ENGLE-GRANGER COINTEGRATION ---
def engle_granger_test(y: pd.Series, x: pd.Series):
    """
    Returns (coint_t, pvalue, critical_values)
    """
    # statsmodels coint returns (t_stat, pvalue, crit_vals)
    try:
        t_stat, pvalue, crit_vals = ts.coint(y.dropna(), x.dropna())
        return {'t_stat': float(t_stat), 'pvalue': float(pvalue), 'crit_vals': [float(cv) for cv in crit_vals]}
    except Exception as e:
        return {'error': str(e)}


# --- HALF-LIFE OF MEAN REVERSION ---
def half_life(spread: pd.Series):
    """
    Compute half-life using AR(1) fit: delta_spread = a + b * spread_lag + eps
    half-life = -ln(2)/b
    """
    s = spread.dropna()
    if len(s) < 10:
        return {'error': 'insufficient data'}
    s_lag = s.shift(1).dropna()
    delta_s = s.diff().dropna()
    s_lag = s_lag.loc[delta_s.index]
    X = sm.add_constant(s_lag.values)
    model = OLS(delta_s.values, X).fit()
    b = model.params[1]
    try:
        halflife = -np.log(2) / b
        return {'half_life': float(abs(halflife)), 'b': float(b)}
    except Exception as e:
        return {'error': str(e)}


# --- ROLLING Z-SCORE SPREAD ---
def spread_and_zscore(y: pd.Series, x: pd.Series, window=60):
    """
    Fit simple OLS hedge ratio: y = alpha + beta * x
    spread = y - beta*x - alpha
    return spread series and rolling z-score
    """
    df = pd.concat([y, x], axis=1).dropna()
    df.columns = ['y', 'x']
    X = sm.add_constant(df['x'])
    model = OLS(df['y'], X).fit()
    alpha = float(model.params[0])
    beta = float(model.params[1])
    spread = df['y'] - beta * df['x'] - alpha
    z = (spread - spread.rolling(window).mean()) / (spread.rolling(window).std(ddof=0) + 1e-12)
    return {'alpha': alpha, 'beta': beta, 'spread': spread, 'zscore': z}


# --- Z-SCORE MEAN REVERSION SIGNALS ---
def zscore_signals(zseries: pd.Series, entry=2.0, exit=0.0):
    """
    Generate signals: +1 short spread positive (sell spread) ; -1 long spread negative
    returns DataFrame with signals
    """
    s = zseries.dropna()
    sig = pd.Series(0, index=s.index)
    position = 0
    for i in range(len(s)):
        z = s.iloc[i]
        if position == 0:
            if z > entry:
                position = -1  # short spread
            elif z < -entry:
                position = 1  # long spread
        elif position == 1:
            if z >= -exit:
                position = 0
        elif position == -1:
            if z <= exit:
                position = 0
        sig.iloc[i] = position
    return sig

def correlation_matrix(symbols: list, timeframe='1m', since_minutes=6*60):
    """
    Returns correlation matrix of close prices for list of symbols
    """
    dfs = {}
    for s in symbols:
        df = resample_ohlc(fetch_ticks(s, since_minutes=since_minutes), timeframe=timeframe)
        if df.empty:
            continue
        dfs[s] = df['close'].rename(s)
    if not dfs:
        return {'error': 'no data'}
    combined = pd.concat(dfs.values(), axis=1, join='inner')
    corr = combined.corr()
    return corr.fillna(0).to_dict()