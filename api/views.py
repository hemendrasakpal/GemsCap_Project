from rest_framework.decorators import api_view
from rest_framework.response import Response
from analytics.analytics import engle_granger_test, half_life, spread_and_zscore, correlation_matrix
from analytics.analytics import compute_pair_analytics, resample_ohlc, fetch_ticks

@api_view(['GET'])
def pair_analytics(request):
    sy = request.GET.get('y')
    sx = request.GET.get('x')
    tf = request.GET.get('tf', '1m')
    window = int(request.GET.get('window', 60))
    if not sy or not sx:
        return Response({"error": "provide y and x symbol params"}, status=400)
    res = compute_pair_analytics(sy, sx, timeframe=tf, window=window)
    return Response(res)

@api_view(['GET'])
def get_ohlc(request):
    s = request.GET.get('symbol')
    tf = request.GET.get('tf', '1m')
    if not s:
        return Response({"error": "symbol missing"}, status=400)
    df = resample_ohlc(fetch_ticks(s, since_minutes=6*60), timeframe=tf)
    df = df.reset_index()
    out = df.tail(500).to_dict(orient='records')
    return Response(out)

@api_view(['GET'])
def pair_cointegration(request):
    x = request.GET.get('x')
    y = request.GET.get('y')
    tf = request.GET.get('tf', '1m')
    if not x or not y:
        return Response({"error": "provide x and y"}, status=400)
    # fetch resampled close series
    df_x = resample_ohlc(fetch_ticks(x, since_minutes=24*60), timeframe=tf)
    df_y = resample_ohlc(fetch_ticks(y, since_minutes=24*60), timeframe=tf)
    common = df_x.index.intersection(df_y.index)
    if len(common) < 20:
        return Response({"error": "not enough overlapping data"}, status=400)
    series_x = df_x.loc[common]['close']
    series_y = df_y.loc[common]['close']
    coint = engle_granger_test(series_y, series_x)
    # compute spread and z-score
    sp = spread_and_zscore(series_y, series_x, window=int(request.GET.get('window',60)))
    halfl = half_life(sp['spread'])
    # prepare small serializable sample of zscore and spread
    z_sample = sp['zscore'].dropna().tail(500).astype(float).to_list()
    spread_sample = sp['spread'].dropna().tail(500).astype(float).to_list()
    return Response({
        'cointegration': coint,
        'beta': sp['beta'],
        'alpha': sp['alpha'],
        'half_life': halfl,
        'zscore_series': z_sample,
        'spread_series': spread_sample
    })

@api_view(['POST'])
def correlation_heatmap(request):
    # expects JSON body { "symbols": ["btcusdt","ethusdt"], "tf":"1m" }
    body = request.data
    symbols = body.get('symbols', [])
    tf = body.get('tf', '1m')
    if not symbols:
        return Response({"error":"symbols required"}, status=400)
    corr = correlation_matrix(symbols, timeframe=tf)
    return Response({'corr': corr})
