import datetime

from django.conf import settings
from django.shortcuts import resolve_url
from django.contrib.auth import REDIRECT_FIELD_NAME as redirect_field_name, logout
from django.urls import reverse

from .models import is_mfa_enabled

try:
    from django.utils.deprecation import MiddlewareMixin
except ImportError:  # Django < 1.10
    # Works perfectly for everyone using MIDDLEWARE_CLASSES
    MiddlewareMixin = object


class MfaMiddleware(MiddlewareMixin):

    def process_request(self, request):
        if request.user.is_authenticated and is_mfa_enabled(request.user) and request.path not in reverse("auths:logout"):
            if not request.session.get('verfied_otp'):
                current_path = request.path
                if current_path != reverse("auths:verify_otp"):
                    path = request.get_full_path()
                    resolved_login_url = resolve_url(reverse("auths:verify_otp"))
                    from django.contrib.auth.views import redirect_to_login
                    return redirect_to_login(path, resolved_login_url, redirect_field_name)
        return None


class SessionIdleTimeout:

    # I can use this to implement remember me at the server side but the issue is that it works
    # independent of what the browser does which could be contradictory
    # setting.py
    # TIME = 60*60  # 1 hour
    # SESSION_SERIALIZER = 'django.contrib.sessions.serializers.PickleSerializer'
    # SESSION_EXPIRE_AT_BROWSER_CLOSE = True
    # SESSION_COOKIE_AGE = TIME    # change expired session
    # SESSION_IDLE_TIMEOUT = TIME  # logout
    def process_request(self, request):
        if request.user.is_authenticated():
            current_datetime = datetime.datetime.now()
            if ('last_accessed' in request.session):
                last = (current_datetime - request.session['last_accessed']).seconds
                if last > settings.SESSION_IDLE_TIMEOUT:
                    logout(request)
            else:
                request.session['last_accessed'] = current_datetime
        return None