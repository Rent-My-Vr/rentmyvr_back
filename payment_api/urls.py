from django.conf import settings
from django.urls import path, include
from rest_framework import routers

from .apps import PaymentApiConfig 
from . import viewsets as vs

router_v1 = routers.DefaultRouter()

router_v1.register(r'price-chart', vs.PriceChartViewSet, basename="price-chart")
# router_v1.register(r'test', vs.TestViewset, basename="test")

app_name = PaymentApiConfig.name

urlpatterns = [

    path('', include(router_v1.urls)),
]

