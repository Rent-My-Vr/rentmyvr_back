from django.conf import settings
from django.urls import path, include
from rest_framework import routers

from .apps import CoreApiConfig 
from . import viewsets as vs

router_v1 = routers.DefaultRouter()

router_v1.register(r'company', vs.CompanyViewSet, basename="company")
router_v1.register(r'city', vs.CityViewSet, basename="city")
router_v1.register(r'contact', vs.ContactViewSet, basename="contact")
router_v1.register(r'country', vs.CountryViewSet, basename="country")
router_v1.register(r'invitation', vs.InvitationViewSet, basename="invitation")
router_v1.register(r'profile', vs.ProfileViewSet, basename="profile")
router_v1.register(r'state', vs.StateViewSet, basename="state")
# router_v1.register(r'test', vs.TestViewset, basename="test")

app_name = CoreApiConfig.name

urlpatterns = [

    path('', include(router_v1.urls)),
]

