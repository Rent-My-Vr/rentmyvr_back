import logging
import json
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import Permission, UserManager
from django.db.models import Q
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode
from django.utils.safestring import mark_safe
from rest_framework.authtoken.management.commands import drf_create_token

from rest_framework import exceptions

from auths.custom_exception import ActivationRequired
from auths.utils import get_domain
from auths_api.serializers import UserSerializer


UserModel = get_user_model()

log = logging.getLogger(f"{__package__}.*")
log.setLevel(settings.LOGGING_LEVEL)

# log.info("Info ({}): *****Testing****....".format(logging.INFO))
# log.warning("Warning ({}): *****Testing****....".format(logging.WARNING))
# log.debug("Debug ({}): *****Testing****....".format(logging.DEBUG))
# log.error("Error ({}): *****Testing****....".format(logging.ERROR))


"""
Also Copy 'django.contrib.auth.backends.ModelBackend' class ONLY for your version and inject whatever
"""


class SDBackend(ModelBackend):
    err_msg = None
    """
    Authenticates against settings.AUTH_USER_MODEL.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(UserModel.USERNAME_FIELD)
        try:
            if getattr(settings, "AUTH_SIGN_IN_BY", "username") == "email":
                UserModel.USERNAME_FIELD = 'email'
                user = UserModel.objects.get(email=username)
            else:
                UserModel.USERNAME_FIELD = 'username'
                user = UserModel.objects.get(username=username)
            # user = UserModel._default_manager.get_by_natural_key(username)
        except UserModel.DoesNotExist:
            # Run the default password hasher once to reduce the timing
            # difference between an existing and a non-existing user (#20760).
            UserModel().set_password(password)
        else:
            if user.check_password(password):
                result = allow_login(user, request)
                request.msg_error = result
                # print(result)

                # is_json =  request.content_type == 'application/json'
                # verification_msg = f"""Hi {user.first_name}, to proceed please check your email for Account Activation.<br>👉 <a href="{reverse('auths:send-mail-activation', args=(user.pk,))}" class="text-primary" title="Resend Actvation Link">Resend Activation link</a> 👈"""
                # if hasattr(user, "email_verified"):
                #     if getattr(settings, 'AUTH_ACTIVATION_REQUIRED', True) and not user.email_verified and not user.is_superuser:
                #         # TODO: Check if `request.accepted_media_type` exists and is == `application/json` (API login) b4 setting this
                #         messages.warning(request, verification_msg, extra_tags='Account Activation Required!')
                #         return None
                # elif getattr(settings, 'AUTH_ACTIVATION_REQUIRED', True) and not user.is_active and not user.last_login:
                #     messages.warning(request, verification_msg, extra_tags='Authentication Failed')
                #     return None
                # if self.user_can_authenticate(user):
                #     pass
                #     # TODO: Call this as Async Task
                #     # for queue in Queue.get_profile_queues(user.user_profile):
                #     #     is_valid = check_email_connection(queue)
                #     #     if not is_valid:
                #     #         messages.warning(request, "Failed accessing <strong>{}<strong> <br> <div class='d-flex justify-content-around'>"
                #     #                                   "<button class='btn btn-link clear' style='text-decoration: none;'>❌ Dismiss</button>"
                #     #                                   "<button class='btn btn-link disable-email' style='text-decoration: none;' data-queue-id='{}'>✔️ Do not show again</button>"
                #     #                                   "</div>".format(queue.channel, queue.pk))

                    
                #     if not is_json:
                #         messages.success(request, f"<div class='text-center'>Hello {user.full_name or user.username or user.email, settings.DEFAULT_COY_NAME}</div>", 
                #         f"""<h3 style='color:white'>{'<img style="border-radius: 50%;width:50px;height:50px;" src="https://s3-us-west-1.amazonaws.com/cdn-savvybiz/static/img/SavvyBiz-logo-Icon.png">'} <i>READY TO ROCK!</i></h3>""")

                #         messages.success(request, "true", "clear-local")
                #         # messages.success(request, f"Hello {user.first_name or user.last_name or user.username or user.email}, <br>You are welcome to {settings.COY_NAME}","<h4 style='color:white'>🤹 READY TO ROCK!</h4>")
                #         return user
                #     else:
                #         return json.dumps(user.__dict__)
            else:
                if hasattr(user, 'failed_attempts'):
                    user.failed_attempts = user.failed_attempts + 1
                    user.save()
                if hasattr(user, 'last_login') and hasattr(user, 'email_verified'):
                    if not user.is_active and user.last_login is None and not user.email_verified:
                        msg = f"""Hello {user}, please make sure you type the {UserModel.USERNAME_FIELD} " \
                              "and password correctly. Default password should be part of your activation email. " \
                              "<a href='{reverse('auths:send-mail-activation', args=(user.pk,))}' title='Click to Generate Activation Link'><u>Regenerate New Email</u></a>"""
                        messages.warning(request, mark_safe(msg), extra_tags='Authentication Failed')

    def user_can_authenticate(self, user):
        """
        Reject users with is_active=False. Custom user models that don't have
        that attribute are allowed.
        """
        is_active = getattr(user, 'is_active', None)
        return is_active or is_active is None

    def _get_user_permissions(self, user_obj):
        return user_obj.user_permissions.all()

    def _get_group_permissions(self, user_obj):
        # user_groups_field = get_user_model()._meta.get_field('groups')
        # user_groups_query = 'group__%s' % user_groups_field.related_query_name()
        # return Permission.objects.filter(**{user_groups_query: user_obj})
            return user_obj.permissions()

    def _get_permissions(self, user_obj, obj, from_name):
        """
        Returns the permissions of `user_obj` from `from_name`. `from_name` can
        be either "group" or "user" to return permissions from
        `_get_group_permissions` or `_get_user_permissions` respectively.
        """
        if not user_obj.is_active or user_obj.is_anonymous or obj is not None:
            return set()

        perm_cache_name = '_%s_perm_cache' % from_name
        if not hasattr(user_obj, perm_cache_name):
            if user_obj.is_superuser:
                perms = Permission.objects.all()
            else:
                perms = getattr(self, '_get_%s_permissions' %from_name)(user_obj)
            perms = perms.values_list('content_type__app_label', 'codename').order_by()
            setattr(user_obj, perm_cache_name, set("%s.%s" % (ct, name) for ct, name in perms))
        return getattr(user_obj, perm_cache_name)

    def get_user_permissions(self, user_obj, obj=None):
        """
        Returns a set of permission strings the user `user_obj` has from their
        `user_permissions`.
        """
        return self._get_permissions(user_obj, obj, 'user')

    def get_group_permissions(self, user_obj, obj=None):
        """
        Returns a set of permission strings the user `user_obj` has from the
        groups they belong.
        """
        return self._get_permissions(user_obj, obj, 'group')

    def get_all_permissions(self, user_obj, obj=None):
        if not user_obj.is_active or user_obj.is_anonymous or obj is not None:
            return set()
        if not hasattr(user_obj, '_perm_cache'):
            user_obj._perm_cache = self.get_user_permissions(user_obj)
            user_obj._perm_cache.update(self.get_group_permissions(user_obj))
        return user_obj._perm_cache

    def has_perm(self, user_obj, perm, obj=None):
        if not user_obj.is_active:
            return False
        return perm in self.get_all_permissions(user_obj, obj)

    def has_module_perms(self, user_obj, app_label):
        """
        Returns True if user_obj has any permissions in the given app_label.
        """
        if not user_obj.is_active:
            return False
        for perm in self.get_all_permissions(user_obj):
            if perm[:perm.index('.')] == app_label:
                return True
        return False

    def get_user(self, user_id):
        try:
            user = UserModel._default_manager.get(pk=user_id)
        except UserModel.DoesNotExist:
            return None
        return user if self.user_can_authenticate(user) else None


def user_can_authenticate(user):
    """
    Reject users with is_active=False. Custom user models that don't have
    that attribute are allowed.
    """
    is_active = getattr(user, 'is_active', None)
    return is_active or is_active is None

def allow_login(user, request):
    is_json =  request.content_type == 'application/json'

    domain = get_domain(request)
    if is_json:
        resend_url = f"{domain}{reverse('auths_api:activation-send', args=(user.pk,))}"
        
    else:
        resend_url = f"{domain}{reverse('auths:activation-send', args=(user.pk,))}"
        
    verification_msg = f"""Hi {user.first_name}, to proceed please check your email for Account Activation.<br>👉 <a href="{resend_url}" class="text-primary" title="Resend Actvation Link">Resend Activation link</a> 👈"""
    verification = {
            "type": "Activation Required", 
            "resend_url": f'{resend_url}?action=Account Activation&channel=email', 
            "activation_url": "", 
            "title": "Resend Link",
            "message":  f"Hi {user.first_name}, to proceed please check your email for Account Activation"}
    
    if hasattr(user, "email_verified"):
        if getattr(settings, 'AUTH_ACTIVATION_REQUIRED', True) and not user.email_verified and not user.is_superuser:
            # Email is not Verified
            # TODO: Deceidex

            session_key = user.send_access_token(settings.AUTH_TOKEN_LENGTH, domain, "email")
            # user.send_activation_link(domain)

            verification['activation_url'] = f"{domain}{reverse('auths_api:activation-activate', args=(user.pk, session_key))}"

            if is_json:
                raise exceptions.ValidationError(verification)
            else:
                messages.warning(request, verification_msg, extra_tags='Account Activation Required!')
                return None
    elif getattr(settings, 'AUTH_ACTIVATION_REQUIRED', True) and not user.is_active and not user.last_login:
        session_key = user.send_access_token(settings.AUTH_TOKEN_LENGTH, domain, "email")
        # user.send_activation_link(domain)

        verification['activation_url'] = f"{domain}{reverse('auths_api:activation-activate', args=(user.pk, session_key))}"
        if is_json:
            raise exceptions.ValidationError(verification)
        else:
            messages.warning(request, verification_msg, extra_tags='Authentication Failed')
            return None

    # verification['activation_url'] = f"{domain}{reverse('auths_api:activation-activate', args=(user.pk, session_key))}"
    
    if user_can_authenticate(user):
        pass
        # TODO: Call this as Async Task
        # for queue in Queue.get_profile_queues(user.user_profile):
        #     is_valid = check_email_connection(queue)
        #     if not is_valid:
        #         messages.warning(request, "Failed accessing <strong>{}<strong> <br> <div class='d-flex justify-content-around'>"
        #                                   "<button class='btn btn-link clear' style='text-decoration: none;'>❌ Dismiss</button>"
        #                                   "<button class='btn btn-link disable-email' style='text-decoration: none;' data-queue-id='{}'>✔️ Do not show again</button>"
        #                                   "</div>".format(queue.channel, queue.pk))

        
        if is_json:
            # raise exceptions.ValidationError(verification)
            return UserSerializer(user).data
        else:
            messages.success(request, f"<div class='text-center'>Hello {user.full_name or user.username or user.email, settings.DEFAULT_COY_NAME}</div>", 
            f"""<h3 style='color:white'>{'<img style="border-radius: 50%;width:50px;height:50px;" src="https://s3-us-west-1.amazonaws.com/cdn-savvybiz/static/img/SavvyBiz-logo-Icon.png">'} <i>READY TO ROCK!</i></h3>""")

            messages.success(request, "true", "clear-local")
            # messages.success(request, f"Hello {user.first_name or user.last_name or user.username or user.email}, <br>You are welcome to {settings.COY_NAME}","<h4 style='color:white'>🤹 READY TO ROCK!</h4>")
            return user
    else:
        print("Account is diabled*******")


class SuBackend(object):
    supports_inactive_user = False

    def authenticate(self, request=None, su=False, user_id=None, **kwargs):
        print("SuBackend.authenticate", user_id)
        if not su:
            print('not su')
            return None
        try:
            user = UserModel.objects.get(pk=user_id)
            print('user', user)
        except (UserModel.DoesNotExist, ValueError):
            import traceback
            traceback.print_exc()
            return None
        print(user)
        return user

    def get_user(self, user_id):
        print('SuBackend.get_user')
        try:
            return UserModel._default_manager.get(pk=user_id)
        except UserModel.DoesNotExist:
            print('SuBackend.get_user None')
            return None
#
