from django.conf import settings
from django.urls import path, include
from rest_framework import routers

from .apps import CoreApiConfig 
from . import viewsets as vs

router_v1 = routers.DefaultRouter()

router_v1.register(r'city', vs.CityViewSet, basename="city")
router_v1.register(r'country', vs.CountryViewSet, basename="country")
router_v1.register(r'interested/email', vs.InterestedEMailViewSet, basename="interested-email")
router_v1.register(r'profile', vs.ProfileViewSet, basename="profile")
router_v1.register(r'state', vs.StateViewSet, basename="state")
# router_v1.register(r'test', vs.TestViewset, basename="test")

app_name = CoreApiConfig.name

urlpatterns = [

    path('', include(router_v1.urls)),
]

