from django.conf import settings
from django.urls import path, include
from rest_framework import routers

from .apps import CoreApiConfig 
from . import viewsets as vs

router_v1 = routers.DefaultRouter()

# router_v1.register(r'email', vs.EMailerViewset, basename="email")
router_v1.register(r'interested/email', vs.InterestedEMailViewSet, basename="interested-email")
# router_v1.register(r'category', vs.CategoryViewSet, basename="category")
# router_v1.register(r'client', vs.ClientViewSet, basename="client")
# router_v1.register(r'expense', vs.ExpenseViewSet, basename="expense")
# router_v1.register(r'profile', vs.ProfileViewSet, basename="profile")
# router_v1.register(r'project', vs.ProjectViewSet, basename="project")
# router_v1.register(r'protected', vs.TestProtectedViewset, basename="test-protected")
# router_v1.register(r'report', vs.WorkReportViewSet, basename="report")
# router_v1.register(r'specifier', vs.SpecifierViewSet, basename="specifier")
# router_v1.register(r'status', vs.WorkStatusViewSet, basename="status")
# router_v1.register(r'tag', vs.TagViewSet, basename="tag")
# router_v1.register(r'template/activity', vs.WorkActivityTemplateViewSet, basename="activity-template")
# router_v1.register(r'test', vs.TestViewset, basename="test")

app_name = CoreApiConfig.name

urlpatterns = [

    path('', include(router_v1.urls)),
]

