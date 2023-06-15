"""supertool_back URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

import notifications.urls

from rest_framework.documentation import include_docs_urls
from rest_framework.authentication import SessionAuthentication, TokenAuthentication

schema_view = get_schema_view(
   openapi.Info(
      title=f"{settings.COMPANY_NAME} API",
      default_version='v0.1',
      description=f"{settings.COMPANY_NAME} Restful API",
      terms_of_service="https://www.google.com/policies/terms/",
      contact=openapi.Contact(email="contact@maintenancets.local"),
      license=openapi.License(name="BSD License"),
   ),
   public=True,
   permission_classes=[permissions.AllowAny],
)

# urlpatterns = [
#    re_path(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
#    re_path(r'^swagger/$', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
#    re_path(r'^redoc/$', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
# ]

urlpatterns = [
    path('__debug__/', include('debug_toolbar.urls')),
    path('access/', admin.site.urls),
    path('accounts/', include('auths.urls')),
    path('api/accounts/', include('auths_api.urls')),
    # path('api/accounts/dj-rest/', include('dj_rest_auth.urls')),

    path('api/accounts/registration/', include('dj_rest_auth.registration.urls')),
    path('api/accounts/social/', include('allauth.urls')),

    path('api/doc/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    # path('api/doc/', include_docs_urls(title='Rent MyVR API Doc', public=False,
    #                              authentication_classes=[SessionAuthentication])),

    # path('api/inbox/notifications/', include(notifications.urls, namespace='notifications')),
    path('api/inbox/', include('notifications_api.urls', namespace='notifications-api')),
    
    path('', include('core.urls')),
    path('api/core/', include('core_api.urls')),

    path('directory/', include('directory.urls')),
    path('api/directory/', include('directory_api.urls')),

    path('payment/', include('payment.urls')),
    path('api/payment/', include('payment_api.urls')),

    path('schedule/', include('schedule.urls')),
    path('api/schedule/', include('schedule_api.urls')),
]

if settings.DEBUG:
    urlpatterns = urlpatterns + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    
admin.site.site_header = f"{settings.COMPANY_NAME} Admin"  
admin.site.site_title  = f"{settings.COMPANY_NAME} Admin"
admin.site.index_title = f"{settings.COMPANY_NAME} Modules"
