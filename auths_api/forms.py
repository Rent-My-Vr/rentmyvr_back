from dj_rest_auth.forms import AllAuthPasswordResetForm
from django.contrib.auth import get_user_model
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.conf import settings
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.template.loader import render_to_string
from django.contrib.sites.shortcuts import get_current_site
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


    def save(self, request, **kwargs):
        client_reset_link = request.data['client_reset_link']
        email = self.cleaned_data['email']
        user = UserModel.objects.filter(email=email).first()
        token = account_activation_token.make_token(user)
        pk = urlsafe_base64_encode(force_bytes(user.pk))
        data = {"*****token": token, "id": user.id, "action": user.__class__.PASSWORD_RESET, "channel": "email", "email": user.email, "extra": {}}

        domain = f"{request.scheme}://{request.META.get('HTTP_HOST', 'savvybiz.com')}"
        # If client_reset_link is set, it mean this is client/server request
        activation_link = reverse('auths_api:password-reset-confirm', kwargs={'uidb64': pk, 'token': token}) if client_reset_link else user.password_reset_confirm_link
        html_message = render_to_string('auths/mail_templates/password_reset_email_html.html', {
            'coy_name': settings.COMPANY_NAME.title(),
            'user': user,
            'activation_link': f"{client_reset_link}?link={domain}{activation_link}",
            'domain': domain,
            'project_title': settings.PROJECT_TITLE.title()
        })
        from core.tasks import sendMail
        sendMail.apply_async(kwargs={'subject': UserModel.PASSWORD_RESET, "message": html_message,
                                     "recipients": [f"'{user.full_name}' <{user.email}>"],
                                     "fail_silently": settings.DEBUG, "connection": None})
        cache.delete_pattern(f"access_token_password_{user.id}_email_*")
        cache.set(f"access_token_password_{user.id}_email_{token}", data, timeout=60*60*24)
        return token



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
            session_key = user.send_access_token(settings.AUTH_TOKEN_LENGTH, domain, "email", "Password Reset", {"reset_url": reset_url, "token": temp_key})
            # get_adapter(request).send_mail(
            #     'account/email/password_reset_key', email, context
            # )
            self.data['id'] = user.id
            self.data['session_key'] = session_key
        return self.cleaned_data['email']
