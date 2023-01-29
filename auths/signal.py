import logging
# from django.contrib.auth.models import User
from django.conf import settings
from django.db.models.signals import post_save, post_delete
from django.contrib.auth import user_login_failed, user_logged_in, user_logged_out, get_user_model
from django.dispatch import receiver
from django.urls import reverse
from django.utils import timezone
from auths.utils import client2str
# from allauth.account.signals import user_logged_in, user_logged_out, user_signed_up, password_set, password_changed, password_reset, email_confirmed, email_confirmation_sent, email_changed, email_added, email_removed
from allauth.socialaccount.signals import pre_social_login, social_account_added, social_account_updated, social_account_removed

from .models import Audit

log = logging.getLogger(f"{__package__}.*")
log.setLevel(settings.LOGGING_LEVEL)

User  = get_user_model()

@receiver(post_save, sender=User)
def created_user(sender, instance, created, **kwargs):
    pass
    # if created:
    #     Assigned.create_assigned(sender.pk, Assigned.PROFILE, sender.company, sender.updated_by_id)
    # else:
    #     pass
    #     print(kwargs)


@receiver(post_delete, sender=User)
def deleted_user(sender, instance, **kwargs):
    pass
    # try:
    #     Assigned.objects.filter(data_id=sender.pk, data_type=Assigned.PROFILE).delete()
    # except Exception:
    #     pass


# def post_save_receiver(sender, instance, created, **kwargs):
#     print ("----User Saved----")

# post_save.connect(post_save_receiver, sender=settings.AUTH_USER_MODEL)





def auth_audit_log(c, request, user, username, auth_status, backend, session_status=Audit.ANONYMOUS,
                   session_key=None, last_seen=None):
    log.info(f"\n\nClient: {c}\n\n")
    audit = Audit.objects.create(ip=request.META.get('REMOTE_ADDR'), session_key=session_key, username=username,
                                 user=user, fingerprint=c['fingerprint'], browser=c['browser'],
                                 browser_version=c['browser_version'], auth_status=auth_status, auth_backend=backend,
                                 session_status=session_status, last_seen=last_seen, os=c['os'],
                                 os_version=c['os_version'], current_resolution=c['current_resolution'],
                                 available_resolution=c['available_resolution'], device=c['device'],
                                 language=request.META.get('HTTP_ACCEPT_LANGUAGE'), timezone=c['timezone'])
    return audit



def get_login_backend(path=None, backend_path=None):
    if path:
        if reverse(settings.LOGIN_URL) == path:
            return Audit.PASSWORD
        else:
            try:
                backends = []
                for b in Audit.AUTH_BACKEND:
                    backends.append(b[0])
                backends.pop(0)
                auth_backend = path.split("/")[4].title()
                if auth_backend in backends:
                    return auth_backend
                else:
                    return None
            except IndexError:
                return None
    else:
        paths = backend_path.split(".")
        if len(paths) in [4, 5]:
            if backend_path in ['django.contrib.auth.backends.ModelBackend', 'auths.overrides.auth_backend.SDBackend']:
                return Audit.PASSWORD
            backends = []
            for b in Audit.AUTH_BACKEND:
                backends.append(b[0])
            backends.pop(0)
            auth_backend = paths[2].title()
            if auth_backend in backends:
                return auth_backend
            else:
                return None
        else:
            return None


@receiver(user_logged_in)
def user_logged_in_callback(sender, request, user, **kwargs):
    """DJango Clears Session after a successful Login, however, backend for auth, user id, user hash will be saved"""
    log.info("***********------Logged In user_logged_in_callback -------*************")
    backend = get_login_backend(None, request.session['_auth_user_backend'])

    # print request.session.session_key
    # for k in request.session.keys():
    #     print k+":\t\t"+request.session[k]

    return
    if not backend:
        return

    stop = False

    try:
        client_id = request.POST['client_id']
    except KeyError:
        if not request.session._get_session_key():
            stop = True
        request.session._get_or_create_session_key()
        try:
            client_id = request.session['client_id']
            request.session.modified = True
        except Exception as e:
            stop = True

    if not stop:
        user.failed_attempts = 0

        c = client2str(client_id)
        if len(c) > 7:
            audit = auth_audit_log(c, request, user, (user.username or user.email), Audit.SUCCESSFUL, backend,
                                Audit.ACTIVE, request.session.session_key)
            user.last_login_signature = audit
            previous = Audit.objects.filter(fingerprint=audit.fingerprint, user=user, auth_backend=audit.auth_backend,
                                            auth_status=Audit.SUCCESSFUL).count()
            # if previous == 1:
            #     from core import notification
            # notify.send(audit, recipient=user, verb=notification.logged_smsg)
        else:
            # You can logged this user immediately from here
            pass

        print("*************------------")
        user.save()


@receiver(user_logged_out)
def user_logged_out_callback(sender, request, user, **kwargs):
    log.info("***********------Logged Out user_logged_out_callback -------*************")
    # messages.info(request, 'Bye {}, we hope to see again soon'.format(user.first_name if user else "Friend"))
    audit = Audit.objects.filter(session_key=request.session.session_key).exclude(session_key__isnull=True
                                                                                  ).order_by('-created').first()
    if audit:
        audit.session_key = None
        audit.session_status = Audit.LOGGED_OUT
        audit.last_seen = timezone.now()
        audit.save()


@receiver(user_login_failed)
def user_login_failed_callback(sender, credentials, **kwargs):
    # return kwargs['request'].session.flush()
    log.info("Login Fail...............................................")
    log.info(kwargs)
    if kwargs['request']:
        backend = get_login_backend(kwargs['request'].path)
        print(backend)
        try:
            client_id = kwargs['request'].POST['client_id']
        except KeyError:
            kwargs['request'].session._get_or_create_session_key()
            try:
                client_id = kwargs['request'].session['client_id']
                kwargs['request'].session.modified = True
            except KeyError as err:
                log.error("***Error setting the session: {}".format(err))
                return

        c = client2str(client_id)
        if len(c) < 6:
            return

        try:
            user = User.objects.get(username=credentials['username'])
            user.last_failed_attempt = timezone.now()
            user.failed_attempts += 1
            user.save()
        except User.DoesNotExist:
            user = None

        auth_audit_log(c, kwargs['request'], user, credentials['username'], Audit.FAILED, backend)

        # r=kwargs['request']
        # log.info("Scheme:\t%s" % r.scheme)
        # log.info("layout:\t%s" % r.layout)
        # log.info("path:\t%s" % r.path)
        # log.info("path_info:\t%s" % r.path_info)
        # log.info("method:\t%s" % r.method)
        # log.info("encoding:\t%s" % r.encoding)
        # log.info("content_type:\t%s" % r.content_type)
        # log.info("content_params:\t%s" % r.content_params)
        # log.info('HTTP_ACCEPT:\t%s' % r.META.get('HTTP_ACCEPT'))
        # log.info('REMOTE_ADDR\t%s' % r.META.get('REMOTE_ADDR'))
        # log.info('HTTP_ACCEPT_ENCODING\t%s' % r.META.get('HTTP_ACCEPT_ENCODING'))
        # log.info('HTTP_ACCEPT_LANGUAGE\t%s' % r.META.get('HTTP_ACCEPT_LANGUAGE'))
        # log.info('HTTP_HOST\t%s' % r.META.get('HTTP_HOST'))
        # log.info('HTTP_REFERER\t%s' % r.META.get('HTTP_REFERER'))
        # log.info('HTTP_USER_AGENT\t%s' % r.META.get('HTTP_USER_AGENT'))
        # log.info('QUERY_STRING\t%s' % r.META.get('QUERY_STRING'))
        # log.info('REMOTE_ADDR\t%s' % r.META.get('REMOTE_ADDR'))
        # log.info('REMOTE_HOST\t%s' % r.META.get('REMOTE_HOST'))
        # log.info('REMOTE_USER\t%s' % r.META.get('REMOTE_USER'))
        # log.info('REQUEST_METHOD\t%s' % r.META.get('REQUEST_METHOD'))
        # log.info('SERVER_NAME\t%s' % r.META.get('SERVER_NAME'))
        # log.info('SERVER_PORT\t%s' % r.META.get('SERVER_PORT'))
        # log.info('HTTP_USER_AGENT\t%s' % r.META.get('HTTP_USER_AGENT'))

