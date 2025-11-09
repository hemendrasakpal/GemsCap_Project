from django.urls import path
from . import views

urlpatterns = [
    path('pair_analytics', views.pair_analytics, name='pair_analytics'),
    path('ohlc', views.get_ohlc, name='ohlc'),
    path('pair_cointegration', views.pair_cointegration, name='pair_cointegration'),
    path('corr_heatmap', views.correlation_heatmap, name='corr_heatmap'),

]
