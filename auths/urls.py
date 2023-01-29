
from django.conf import settings
from django.urls import path, re_path
from rest_framework.authtoken.views import obtain_auth_token

from .views import LogoutView, PasswordChangeView, PasswordChangeDoneView, PasswordResetView, PasswordResetDoneView, \
    PasswordResetConfirmView, PasswordResetCompleteView, LoginView, PasswordChangeForcedView, \
    current_user
from .apps import AuthsConfig 
from . import views

app_name = AuthsConfig.name
urlpatterns = [

    # Session Login
    # url(r'^password/change/$', auth.password_change, {'post_change_redirect': 'auths:password_change_done'}, name='password_change'),
    # url(r'^password/change/done/$', auth.password_change_done, name='password_change_done'),
    # url(r'^password/reset/$', auth.password_reset, {'post_reset_redirect': 'auths:password_reset_done', 'email_template_name': 'auths/mail_templates/password_reset_email.html',
    #                                                    'html_email_template_name': 'auths/mail_templates/password_reset_email_html.html'}, name='password_reset'),
    # url(r'^password/reset/done/$', auth.password_reset_done, name='password_reset_done'),
    # url(r'^password/reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$', auth.password_reset_confirm, {'post_reset_redirect': 'auths:password_reset_complete'},
    #     name='password_reset_confirm'),
    # url(r'^password/reset/complete/$', auth.password_reset_complete, name='password_reset_complete'),

    # url(r'^email/request/(?P<partial_backend_name>[0-9A-Za-z-]+)/(?P<partial_token>[0-9A-Fa-f-]+)/$', views.email_request_form, name='email-request-form'),
    # url(r'^email/verify/(?P<email>[\w.%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,4})/(?P<token>[\wA-Za-z0-9]{' + getattr(settings, EMAIL_TOKEN_LENGTH + '})/$', views.verify_email, name='verify-email'),
    # url(r'^email/resend.gmb$', views.resend_email, name='resend-email'),

    path('login/', LoginView.as_view(), name="login"),
    path('api/token/auth/', obtain_auth_token, name='api-token-auth'),
    path('api/current_user/', current_user, name='api-get-current-user'),
    # TODO: implement such that password change we can copy the email/username
    path('login/<slug:token>/', LoginView.as_view(), name="login"),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('password/change/', PasswordChangeView.as_view(), name='password_change'),
    path('password/change/forced/<int:token>/', PasswordChangeForcedView.as_view(), name='password_change_forced'),
    path('password/change/done/', PasswordChangeDoneView.as_view(), name='password_change_done'),
    path('password/reset/', PasswordResetView.as_view(), name='password_reset'),
    path('password/reset/done/', PasswordResetDoneView.as_view(), name='password_reset_done'),
    re_path(r'^password/reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,60})/$',
        PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('password/reset/complete/', PasswordResetCompleteView.as_view(), name='password_reset_complete'),
    path('activation/token/request/<str:channel>/<str:email>/', views.activation_token_send, name='activation-token-request'),
    path('activation/token/confirm/<int:session_key>/', views.verify_token, name='activation-token-confirm'),
    path('password/reset/token/<int:session_key>/', views.password_reset_by_token, name='password-reset-by-token'),

    path('user/add/', views.user_create, name='user-add'),
    path('user/list/', views.user_create, name='user-list'),
    path('user/detail/<uuid:pk>/', views.user_details, name='user-detail'),
    path('user/edit/<uuid:pk>/', views.user_update, name='user-edit'),
    path('user/delete/<uuid:pk>/', views.user_delete, name='user-delete'),
    path('test/login/', views.test, name='test'),

    path('sign-up/', views.sign_up, name='sign-up'),
    path('sign-up/success/', views.sign_up_acknowledge, name='sign-up-success'),
    # re_path(r'^activate/(?P<uidb64>[0-9A-Za-z_\-]+)/$', views.send_activate, name='activation-send'),
    path('activate/<uuid:uidb64>/', views.activation_send, name='activation-send'),
    re_path(r'^activate/(?P<uuid>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,60})/$',
        views.activate, name='activate'),
    path('email/confirmation/sent/', views.email_confirmation_sent, name='confirmation-email-sent'),
    path('access/denied/', views.accessdenied, name="access-denied"),

    path('loginas/<uuid:user_id>/', views.login_as_user, name='login-as-user'),
    path('loginas-logout/', views.su_logout, name='loginas-logout'),
    
    #url(r'^security/$', views.security_settings, name="security_settings"),
    #url(r'^mfa/configure/$', views.configure_mfa, name="configure_mfa"),
    #url(r'^mfa/enable/$', views.enable_mfa, name="enable_mfa"),
    # url(r'^verify/token/$', views.verify_otp, name="verify_otp"),
    #url(r'^mfa/disable/$', views.disable_mfa, name="disable_mfa"),
]

# if 'rest_framework.authtoken' in settings.INSTALLED_APPS:
#     from rest_framework.authtoken import views as rest_framework_views
#     from auths.views import get_token
