from dj_rest_auth.forms import AllAuthPasswordResetForm
from django.contrib.auth import get_user_model
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.conf import settings
from django.urls import reverse
from django.db.models import Q
from django.utils.encoding import force_bytes
from django.template.loader import render_to_string
from django.contrib.sites.shortcuts import get_current_site
from django.contrib.auth.forms import SetPasswordForm as SPF
from django.core.cache import cache
from django.http import JsonResponse
from auths.utils import account_activation_token, get_domain

from rest_framework.response import Response

if 'allauth' in settings.INSTALLED_APPS:
    from allauth.account import app_settings
    from allauth.account.adapter import get_adapter
    from allauth.account.forms import default_token_generator
    from allauth.account.utils import (user_pk_to_url_str, user_username)
    from allauth.utils import build_absolute_uri


UserModel = get_user_model()

class PasswordResetForm(AllAuthPasswordResetForm):
    
    def clean_email(self):
        """
        Invalid email should not raise error, as this would leak users
        for unit test: test_password_reset_with_invalid_email
        """
        # print(' ---- clean_email() ', self.cleaned_data)
        email = self.cleaned_data["email"]
        email = get_adapter().clean_email(email)
        self.users = UserModel.objects.filter(Q(email=email, is_active=True) | Q(email=email, is_active=False, last_login__isnull=True))
        return self.cleaned_data["email"]


    def save(self, request, **kwargs):
        print(' kwargs:::  ', kwargs)
        print(' Users:::  ', self.users)
        print(' Data:::  ', request.data)
        print(' Clean Data:::  ', self.cleaned_data)
        client_callback_link = request.data.get('client_callback_link', None)
        processing_channel = request.data.get('processing_channel', UserModel.TOKEN if request.data.get('channel') == UserModel.PHONE_CHANNEL else UserModel.LINK)
        extra = {"processing_channel": processing_channel, "client_callback_link": client_callback_link}
        # If client_callback_link is set, it mean this is client/server request
        
        print(self.users)
        session_key = None
        x=0
        for user in self.users:
            if session_key:
                break
            session_key = user.send_access_token(get_domain(request), request.data.get('action'), request.data.get('channel'), extra=extra)
            x += 1
            print('..........', session_key, '\n\n')
            
        print('---session_key: ', session_key)
        return session_key



    def save_(self, request, **kwargs):
        current_site = get_current_site(request)
        email = self.cleaned_data['email']
        token_generator = kwargs.get('token_generator', default_token_generator)

        for user in self.users:

            temp_key = token_generator.make_token(user)

            # save it to the password reset model
            # password_reset = PasswordReset(user=user, temp_key=temp_key)
            # password_reset.save()

            # send the password reset email
            path = reverse(
                'auths_api:password-reset-confirm',
                args=[user_pk_to_url_str(user), temp_key],
            )

            if getattr(settings, 'REST_AUTH_PW_RESET_USE_SITES_DOMAIN', False) is True:
                reset_url = build_absolute_uri(None, path)
            else:
                reset_url = build_absolute_uri(request, path)

            context = {
                'current_site': current_site,
                'user': user,
                'password_reset_url': reset_url,
                'request': request,
            }
            
            if app_settings.AUTHENTICATION_METHOD != app_settings.AuthenticationMethod.EMAIL:
                context['username'] = user_username(user)

            domain = get_domain(request)
            session_key = user.send_access_token(domain, UserModel.PASSWORD_RESET, UserModel.EMAIL_CHANNEL, template='auths/mail_templates/password_reset_email_html.html')
            # get_adapter(request).send_mail(
            #     'account/email/password_reset_key', email, context
            # )
            self.data['id'] = user.id
            self.data['session_key'] = session_key
        return self.cleaned_data['email']


class SetPasswordForm(SPF):
    """
    A form that lets a user change set their password without entering the old password
    """
    def save(self, commit=True):
        print('++++++++ :::: SetPasswordForm().save()', self.user)
        self.user.is_active = True
        self.user.force_password_change = False
        if hasattr(self.user, "email_verified"):
            self.user.email_verified = True
        password = self.cleaned_data["new_password1"]
        self.user.set_password(password)
        if commit:
            self.user.save()
        return self.user

