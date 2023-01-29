import logging
from urllib.parse import urlparse

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, logout
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.core import mail
from social_core import exceptions

from social_core.exceptions import InvalidEmail, AuthAlreadyAssociated, AuthCanceled
from social_core.pipeline.partial import partial
from social_core.backends.google import GooglePlusAuth
from social_core.backends.utils import load_backends
from social_core.pipeline.social_auth import social_user
from social_django.middleware import SocialAuthExceptionMiddleware
from social_django.models import UserSocialAuth, Code

log = logging.getLogger(f"{__package__}.*")
log.setLevel(settings.LOGGING_LEVEL)


UserModel = get_user_model()


def get_profile_picture(backend, strategy, details, response, user=None, *args, **kwargs):
    url = None
    messages.success(strategy.request, "<div class='text-center'>Hello {} {}</div>".format(user.first_name, user.last_name), "<h3 style='color:white'>{} <i>READY TO ROCK!</i></h3>".format('<img style="border-radius: 50%;width:50px;height:50px;" src="https://s3-us-west-1.amazonaws.com/cdn-savvybiz/static/img/SavvyBiz-logo-Icon.png">'))
    # messages.success(strategy.request, "Hello {}, you are welcome to SavvyBiz".format(user.first_name),"<h4 style='color:white'>🤹 READY TO ROCK!</h4>")
    try:
        if backend.name == 'facebook': 
            url = f"https://graph.facebook.com/{response['id']}/picture?type=large"
            # print "Gender: "+response.get('gender')
            # print "Link: "+response.get('link')
            # print "Timezone: "+response.get('timezone')
        elif backend.name == 'twitter':
            url = response.get('profile_image_url', '').replace('_normal','')
        elif backend.name == 'google-oauth2':
            url = response['image'].get('url', "")
            size = url.split('=')[-1]
            url = url.replace('={}'.format(size), '=240')
        elif backend.name == 'github':
            url = response['avatar_url']

        if url:
            user.avatar_url = url
            user.save()
    except Exception as err:
        log.error("***Error: {}".format(err))


# @partial
# def auth_logout(strategy, *args, **kwargs):
#     request = strategy.request
#     logout(strategy.request)


@partial
def require_email(strategy, details, user=None, is_new=False, *args, **kwargs):
    if kwargs.get('ajax') or user and user.email:
        return
    elif is_new and not details.get('email'):
        email = strategy.request_data().get('email')
        if email:
            details['email'] = email
        else:
            current_partial = kwargs.get('current_partial')
            # return strategy.redirect('/email?partial_token={0}'.format(current_partial.token))
            # details['force_mail_validation']=True
            # strategy.REQUIRES_EMAIL_VALIDATION = True
            return strategy.redirect(f'/Email Required?partial_token={current_partial.token}')
            # return {strategy: strategy.redirect('/Email Required?partial_token={0}'.format(current_partial.token)), force_mail_validation: True}


@partial
def force_mail_validation(backend, details, user=None, is_new=False, *args, **kwargs):
    # usa = UserSocialAuth(provider=backend.name, uid=2)

    # ONLY Allow this line if you do NOT want users to Create Account from Social Auth
    if UserModel.objects.filter(email=details['email']).count() == 0:
        error_message = messages.warning(kwargs['request'], f"Hi <b>{details['first_name']}</b>, user with email "{details['email']}" does not exists. <Please login with your password", "Access Denied")
        return HttpResponseRedirect(reverse('auths:login', error_message))

    existing_usa = UserSocialAuth.objects.filter(provider=backend.name, uid=kwargs.get('uid')).count()
    new_association = kwargs.get('new_association')
    data = backend.strategy.request_data()
    if new_association and 'verification_code' not in data and existing_usa == 0:
        current_partial = kwargs.get('current_partial')
        backend.strategy.send_email_validation(backend, details['email'], current_partial.token)
        backend.strategy.session_set('email_validation_address', details['email'])
        url = f"{backend.strategy.setting('EMAIL_VALIDATION_URL')}?email={details['email']}"
        return backend.strategy.redirect(backend.strategy.request.build_absolute_uri(url))
    elif new_association and 'verification_code' in data:
        backend.REQUIRES_EMAIL_VALIDATION = True
    return


def send_validation(strategy, backend, code, partial_token):
    url = f"{reverse('social:complete', args=(backend.name,))}?verification_code={code.code}&partial_token={partial_token}"
    url = strategy.request.build_absolute_uri(url)
    log.info(url)
    o = urlparse(url)
    user = UserModel.objects.filter().first()
    html_message = render_to_string('auths/mail_templates/activation.html', {
        'project_title': settings.PROJECT_NAME.title(),
        'firstName': user.first_name,
        'lastName': user.last_name,
        'validation_url': url,
        'domain': f"{o.scheme}://{o.netloc}",
    })

    from core.tasks import sendMail
    # sendMail(subject, message, recipients, fail_silently=settings.DEBUG, html_message=None, channel=None,
    #              connection_label=None, fromm=None, reply_to=None, cc=None, bcc=None, files=None):

    sendMail.apply_async(kwargs={'subject': "{} Account Activation".format(settings.COY_NAME), 'message': html_message,
                                 'recipients': [code.email], 'fail_silently': settings.DEBUG,
                                 'html_message': html_message, 'channel': None, 'connection': None})


@partial
def mail_validation_member(backend, details, is_new=False, *args, **kwargs):
    requires_validation = backend.REQUIRES_EMAIL_VALIDATION or backend.setting('FORCE_EMAIL_VALIDATION', False)
    send_validation = details.get('email') and (is_new or backend.setting('PASSWORDLESS', False))
    data = backend.strategy.request_data()
    if requires_validation and send_validation:
        data = backend.strategy.request_data()
        if 'verification_code' in data:
            backend.strategy.session_pop('email_validation_address')
            if not backend.strategy.validate_email(details['email'], data['verification_code']):
                raise InvalidEmail(backend)
            else:
                try:
                    me = UserModel.objects.filter(email=details['email']).first()
                    me.email_verified = True
                    me.save()
                except Exception as err:
                    log.error(f"***Error updating User's Email Verification Status: {err}")
        else:
            current_partial = kwargs.get('current_partial')
            backend.strategy.send_email_validation(backend, details['email'], current_partial.token)
            backend.strategy.session_set('email_validation_address', details['email'])
            return backend.strategy.redirect(backend.strategy.setting('EMAIL_VALIDATION_URL'))


def is_authenticated(user):
    if callable(user.is_authenticated):
        return user.is_authenticated()
    else:
        return user.is_authenticated


def associations(user, strategy):
    user_associations = strategy.storage.user.get_social_auth_for_user(user)
    if hasattr(user_associations, 'all'):
        user_associations = user_associations.all()
    return list(user_associations)


def common_context(authentication_backends, strategy, user=None, plus_id=None, **extra):
    """Common view context"""
    context = {
        'user': user,
        'available_backends': load_backends(authentication_backends),
        'associated': {}
    }

    if user and is_authenticated(user):
        context['associated'] = dict((association.provider, association) for association in associations(user, strategy))

    if plus_id:
        context['plus_id'] = plus_id
        context['plus_scope'] = ' '.join(GooglePlusAuth.DEFAULT_SCOPE)

    return dict(context, **extra)


def url_for(name, **kwargs):
    if name == 'social:begin':
        url = '/login/{backend}/'
    elif name == 'social:complete':
        url = '/complete/{backend}/'
    elif name == 'social:disconnect':
        url = '/disconnect/{backend}/'
    elif name == 'social:disconnect_individual':
        url = '/disconnect/{backend}/{association_id}/'
    else:
        url = name
    return url.format(**kwargs)


def get_username_lower(strategy, details, backend, user=None, *args, **kwargs):
    from social_core.pipeline.user import get_username
    return {'username': get_username(strategy, details, backend, user=None, *args, **kwargs)['username'].lower()}


def check_email_exists(request, backend, details, uid, user=None, *args, **kwargs):
    email = details.get('email', '')
    provider = backend.name

    # check if social user exists to allow logging in (not sure if this is necessary)
    social = backend.strategy.storage.user.get_social_auth(provider, uid)
    # check if given email is in use
    count = UserModel.objects.filter(email=email).count()

    error_message = messages.error(request, 'Sorry User With That Email Already Exists')

    # user is not logged in, social profile with given uid doesn't exist
    # and email is in use
    if not user and not social and count:
        return HttpResponseRedirect(reverse('auths:login', error_message))


def associate_user(backend, uid, user=None, social=None, *args, **kwargs):
    if user and not social:
        try:
            if getattr(settings, 'SOCIAL_AUTH_ASSOCIATE_BY_MAIL', False) and user.email != uid:
                logout(backend.strategy.request)
                messages.warning(backend.strategy.request, f"User {user.email} auto signed out, please try again")
                status = Code.objects.filter(email=uid).delete()
                return HttpResponseRedirect(reverse('auths:login'))
            social = backend.strategy.storage.user.create_social_auth(user, uid, backend.name)
        except Exception as err:
            if not backend.strategy.storage.is_integrity_error(err):
                raise
            # Protect for possible race condition, those bastard with FTL
            # clicking capabilities, check issue #131:
            #   https://github.com/omab/django-social-auth/issues/131
            return social_user(backend, uid, user, *args, **kwargs)
        else:
            return {'social': social,
                    'user': social.user,
                    'new_association': True}


class SocialAuthExceptionMiddleware(SocialAuthExceptionMiddleware):
    """Redirect users to desired-url when AuthAlreadyAssociated exception occurs."""
    def process_exception(self, request, exception):
        if isinstance(exception, AuthAlreadyAssociated):
            if request.backend.name == 'google-oauth2':
                message = "This google account is already in use."
                messages.warning(request, message)
                if message in str(exception):
                    # User is redirected to any url you want "
                    return redirect(reverse("auths:login"))
        elif isinstance(exception, AuthCanceled):
            messages.warning(request, "Login process cancelled!!!")
            return redirect(reverse("auths:login"))


class MySocialAuthExceptionMiddleware(SocialAuthExceptionMiddleware):
    def process_exception(self, request, exception):
        if hasattr(exceptions, exception.__class__.__name__):
            # Here you can handle the exception as you wish
            log.warning(exception.__class__.__name__)
            return HttpResponse(f"Exception {exception} while processing your social account.")
        else:
            return super(MySocialAuthExceptionMiddleware, self).process_exception(request, exception)














