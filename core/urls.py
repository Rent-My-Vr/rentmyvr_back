from django.conf import settings
from django.urls import path, re_path

from .apps import CoreConfig 
from . import views

app_name = CoreConfig.name
urlpatterns = [
    path('', views.index, name="index"),
    path('dashboard', views.dashboard, name="dashboard"),

    # path('test/mail/template/', views.test_mail_template, name="test-mail-template"),

    # path('google/authorisaction/', views.google_authorisaction, name='google-authorisaction'),
    # path('google/authorisaction/<email:gmail>/', views.google_authorisaction, name='google-authorisaction-mail'),
    # re_path('google/authorisaction/(?P<gmail>\w+|[\w.%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,4})/', views.google_authorisaction, name='google-authorisaction-mail'),
    # path('google/authorisaction/callback/', views.google_authorisaction_callback, name='google-authorisaction-callback'),
    # path('google/authorisaction/revoke/', views.google_authorisaction_revoke, name='google-authorisaction-revoke'),
]

