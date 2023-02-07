from django.conf import settings
from django.urls import path, include
from rest_framework import routers

from .apps import DirectoryConfig 
from . import views

router_v1 = routers.DefaultRouter()

# router_v1.register(r'email', vs.EMailerViewset, basename="email")
# router_v1.register(r'interested/email', vs.InterestedEMailViewSet, basename="interested-email")

app_name = DirectoryConfig.name

urlpatterns = [

    # path('', include(router_v1.urls)),
]

