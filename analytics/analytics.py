import pandas as pd
import numpy as np
from statsmodels.tsa.stattools import adfuller
import statsmodels.api as sm
import pymongo
from datetime import datetime, timedelta

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
    dfy = resample_ohlc(fetch_ticks(sym_y, since_minutes=24*60), timeframe)
    dfx = resample_ohlc(fetch_ticks(sym_x, since_minutes=24*60), timeframe)
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
