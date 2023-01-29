from django.conf import settings
from django.urls import path, include
from rest_framework import routers

from .apps import NotificationsApiConfig 
from . import viewsets as vs

router_v1 = routers.DefaultRouter()

router_v1.register(r'notifications', vs.NotificationViewSet, basename="notifications")

app_name = NotificationsApiConfig.name

urlpatterns = [

    path('', include(router_v1.urls)),
]

