import logging
from itertools import zip_longest
from urllib.parse import quote
from random import randint

import unicodedata

from django.conf import settings
from django.core.cache import cache
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.contrib.sites.shortcuts import get_current_site

log = logging.getLogger("{}.*".format(__package__))
log.setLevel(settings.LOGGING_LEVEL)


class TokenGenerator(PasswordResetTokenGenerator):

    def check_token(self, user, action, token, channel="email", session_key=""):
        data = cache.get(f"access_token_{user.id}_{action}_{channel}_{session_key}")
        # print('\n\n +++++++++ ******* ++++++++ Data:  ', data)
        # print(f"access_token_{user.id}_{action}_{channel}_{session_key}")
        # print((data and token == data['token']) or data == token)
        # print(token)
        if (data and token == data['token']) or data == token:
            cache.delete_pattern(f"access_token_{user.id}_{action}_{channel}_*")
            return data
        else:
            return super().check_token(user, str(token))


    def persist(self, user, action, channel, session_key, data=None, token_length=getattr(settings, 'AUTH_TOKEN_LENGTH', 6), timeout=60*60):
        data = data if data else str(random_with_N_digits(token_length))
        cache.delete_pattern(f"access_token_{user.id}_{action}_{channel}_*")
        cache.set(f"access_token_{user.id}_{action}_{channel}_{session_key}", data, timeout=timeout)
        if timeout != 600:
            print('***Key:   ==> ', f"access_token_{user.id}_{action}_{channel}_{session_key}")
            print('***Data:   ==> ', cache.get(f"access_token_{user.id}_{action}_{channel}_{session_key}"))
        return data


    def _make_hash_value(self, user, timestamp):
        # Ensure results are consistent across DB backends
        # login_timestamp = '' if user.last_login is None else user.last_login.replace(microsecond=0, tzinfo=None)
        return (str(user.pk) + str(timestamp) + str(user.is_active))


account_activation_token = TokenGenerator()

def  get_domain(request):
    if hasattr(request, "stream") and request.stream:
        return request.stream._current_scheme_host
    if hasattr(request, "_stream") and request._stream and hasattr(request._stream, "_current_scheme_host"):
        return request._stream._current_scheme_host
    if hasattr(request, "scheme"):
        return f"{request.scheme}://{request.META['HTTP_HOST']}"
    if settings.BACK_SERVER:
        return settings.BACK_SERVER
    
    return get_current_site(request)

def build_uri(secret, name, initial_count=None, issuer_name=None):
    """
    Returns the provisioning URI for the OTP; works for either TOTP or HOTP.

    This can then be encoded in a QR Code and used to provision the Google
    Authenticator app.

    For module-internal use.

    See also:
        http://code.google.com/p/google-authenticator/wiki/KeyUriFormat

    @param [String] the hotp/totp secret used to generate the URI
    @param [String] name of the account
    @param [Integer] initial_count starting counter value, defaults to None.
        If none, the OTP type will be assumed as TOTP.
    @param [String] the name of the OTP issuer; this will be the
        organization title of the OTP entry in Authenticator
    @return [String] provisioning uri
    """
    # initial_count may be 0 as a valid param
    is_initial_count_present = (initial_count is not None)

    otp_type = 'hotp' if is_initial_count_present else 'totp'
    base = 'otpauth://%s/' % otp_type

    if issuer_name:
        issuer_name = quote(issuer_name)
        base += '%s:' % issuer_name

    uri = '%(base)s%(name)s?secret=%(secret)s' % {
        'name': quote(name, safe='@'),
        'secret': secret,
        'base': base,
    }

    if is_initial_count_present:
        uri += '&counter=%s' % initial_count

    if issuer_name:
        uri += '&issuer=%s' % issuer_name

    return uri


def _compare_digest(s1, s2):
    differences = 0
    for c1, c2 in zip_longest(s1, s2):
        if c1 is None or c2 is None:
            differences = 1
            continue
        differences |= ord(c1) ^ ord(c2)
    return differences == 0

try:
    # Python 3.3+ and 2.7.7+ include a timing-attack-resistant
    # comparison function, which is probably more reliable than ours.
    # Use it if available.
    from hmac import compare_digest

except ImportError:
    compare_digest = _compare_digest


def strings_equal(s1, s2):
    """
    Timing-attack resistant string comparison.

    Normal comparison using == will short-circuit on the first mismatching
    character. This avoids that by scanning the whole string, though we
    still reveal to a timing attack whether the strings are the same
    length.
    """

    s1 = unicodedata.normalize('NFKC', str(s1))
    s2 = unicodedata.normalize('NFKC', str(s2))
    return compare_digest(s1, s2)


def client2str(c_str):
    "2690895513::Chrome 67.0.3396.99::Windows 8.1::1366x768::1366x728::Unknown Windows Device::en-US::West Africa Standard Time"
    paths = c_str.split("::")
    son = {}
    son['fingerprint'] = paths[0]
    son['browser'] = paths[1].split(" ")[0]
    son['browser_version'] = paths[1].split(" ")[1]
    son['os'] = paths[2].split(" ")[0]
    son['os_version'] = paths[2].split(" ")[1]
    son['current_resolution'] = paths[3]
    son['available_resolution'] = paths[4]
    son['device'] = paths[5]
    son['language'] = paths[6]
    son['timezone'] = paths[7]

    return son

def random_with_N_digits(n):
    range_start = 10**(n-1)
    range_end = (10**n)-1
    return randint(range_start, range_end)