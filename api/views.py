from rest_framework.decorators import api_view
from rest_framework.response import Response
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
