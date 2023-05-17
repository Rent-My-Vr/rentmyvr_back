from django.conf import settings
from django.urls import path, include
from rest_framework import routers

from .apps import DirectoryApiConfig 
from . import viewsets as vs


router_v1 = routers.DefaultRouter()

router_v1.register(r'management', vs.ManagerDirectoryViewSet, basename="management")
router_v1.register(r'office', vs.OfficeViewSet, basename="office")
router_v1.register(r'portfolio', vs.PortfolioViewSet, basename="portfolio")
router_v1.register(r'inquiry/message', vs.InquiryMessageViewSet, basename="inquiry-message")
router_v1.register(r'property', vs.PropertyViewSet, basename="property")
# router_v1.register(r'category', vs.CategoryViewSet, basename="category")
# router_v1.register(r'client', vs.ClientViewSet, basename="client")

app_name = DirectoryApiConfig.name

urlpatterns = [
    path('', include(router_v1.urls)),
]

