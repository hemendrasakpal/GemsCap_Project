from django.urls import path
from . import views

urlpatterns = [
    path('pair_analytics', views.pair_analytics, name='pair_analytics'),
    path('ohlc', views.get_ohlc, name='ohlc'),
]
