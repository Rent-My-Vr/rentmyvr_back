from django.urls import path, re_path, include
from rest_framework import routers
from rest_framework.schemas import get_schema_view
from dj_rest_auth.registration.views import SocialAccountListView, SocialAccountDisconnectView


from auths_api import viewsets
from .apps import AuthsApiConfig

router_v1 = routers.DefaultRouter()

router_v1.register(r'group', viewsets.SavvybizGroupViewSet, basename='group')
router_v1.register(r'permission', viewsets.PermissionViewSet, basename='permission')
# router_v1.register(r'auth', viewsets.AuthViewSet, basename='auth')
router_v1.register(r'user', viewsets.UserViewSet, basename='user')
router_v1.register(r'activation', viewsets.ActivationRequestView, basename='activation')
# router_v1.register(r'password/rest', viewsets.PasswordResetView, basename='password-reset')

schema_view = get_schema_view(title=AuthsApiConfig.verbose_name)



app_name = AuthsApiConfig.name
urlpatterns = [
    path('', include(router_v1.urls)),

    path('ws/auth/token/', viewsets.WsAuthTokenView.as_view(), name='ws-token'),
    path('login/', viewsets.LoginView.as_view(), name='login'),
    path('logout/', viewsets.LogoutView.as_view(), name='logout'),
    path('password/reset/', viewsets.PasswordResetView.as_view(), name='password-reset-send'),
    path('password/change/', viewsets.PasswordChange.as_view(), name='password-change'),
    # path('password/reset/confirm/', viewsets.PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
    re_path(r'^password/reset/confirm/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,60})/',
        viewsets.PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
    re_path(r'^password/reset/confirm/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<session_key>\d+)/',
        viewsets.PasswordResetConfirmView.as_view(), name='password-reset-confirm-token'),

    path('social/facebook/login/', viewsets.FacebookLogin.as_view(), name='facebook-login'),
    path('social/facebook/connect/', viewsets.FacebookConnect.as_view(), name='facebook-connect'),
    path('social/google/login/', viewsets.GoogleLogin.as_view(), name='google-login'),
    path('social/google/connect/', viewsets.GoogleConnect.as_view(), name='google-connect'),
    path('social/apple/login/', viewsets.AppleLogin.as_view(), name='apple-login'),
    path('social/apple/connect/', viewsets.AppleConnect.as_view(), name='apple-connect'),
    
]

urlpatterns += [
    path('social/accounts/', SocialAccountListView.as_view(), name='social_account_list'),
    path('social/accounts/<int:pk>/disconnect/', SocialAccountDisconnectView.as_view(), 
        name='social_account_disconnect')
]
