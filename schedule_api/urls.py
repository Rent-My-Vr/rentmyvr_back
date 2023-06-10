from django.conf import settings
from django.urls import path, include, re_path
from rest_framework import routers

from .apps import ScheduleApiConfig 
from . import viewsets as vs

router_v1 = routers.DefaultRouter()

router_v1.register(r'schedule', vs.ProcessingView, basename="schedule")
# router_v1.register(r'transaction', vs.TransactionViewSet, basename="transaction")

app_name = ScheduleApiConfig.name

urlpatterns = [
    path('', include(router_v1.urls)),
]
