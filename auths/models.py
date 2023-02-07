import logging
import random
import string
import uuid
import pytz
import base64
import pickle
import jsonpickle
from django.conf import settings
from django.contrib import auth
from django.contrib.auth import get_user_model
from django.contrib.auth.base_user import AbstractBaseUser as DjangoAbstractBaseUser, BaseUserManager as DjangoBaseUserManager
from django.contrib.auth.models import User as AuthUser, Permission, AbstractUser as DjangoAbstractUser, Group
from django.contrib.auth.validators import UnicodeUsernameValidator, ASCIIUsernameValidator
from django.contrib.sessions.base_session import AbstractBaseSession
from django.contrib.sites.models import Site
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.db import models
from django.db.models import Q
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone, encoding
from django.utils.translation import gettext_lazy as _
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.forms.fields import DateTimeField

from rest_framework.authtoken.models import Token


from auths.custom_exception import PermissionRequired, CompanyRequired
from auths.utils import account_activation_token
from auths import permission_utils

from google.oauth2.credentials import Credentials
from google.auth.exceptions import RefreshError, TransportError
from google.auth.transport.requests import Request

from .utils import random_with_N_digits

log = logging.getLogger(f"{__package__}.*")
log.setLevel(settings.LOGGING_LEVEL)


class CredentialsField(models.Field):
    """Django ORM field for storing OAuth2 Credentials."""

    def __init__(self, *args, **kwargs):
        if 'null' not in kwargs:
            kwargs['null'] = True
        super(CredentialsField, self).__init__(*args, **kwargs)

    def get_internal_type(self):
        return 'BinaryField'

    def from_db_value(self, value, expression, connection):
        """Overrides ``models.Field`` method. This converts the value
        returned from the database to an instance of this class.
        """
        return self.to_python(value)

    def to_python(self, value):
        """Overrides ``models.Field`` method. This is used to convert
        bytes (from serialization etc) to an instance of this class"""
        if value is None:
            return None
        elif isinstance(value, Credentials):
            return value
        else:
            try:
                return jsonpickle.decode(
                    base64.b64decode(encoding.smart_bytes(value)).decode())
            except ValueError:
                return pickle.loads(
                    base64.b64decode(encoding.smart_bytes(value)))

    def get_prep_value(self, value):
        """Overrides ``models.Field`` method. This is used to convert
        the value from an instances of this class to bytes that can be
        inserted into the database.
        """
        if value is None:
            return None
        else:
            return encoding.smart_str(
                base64.b64encode(jsonpickle.encode(value).encode()))

    def value_to_string(self, obj):
        """Convert the field value from the provided model to a string.

        Used during model serialization.

        Args:
            obj: db.Model, model object

        Returns:
            string, the serialized field value
        """
        # value = self._get_val_from_obj(obj)
        value = self.value_from_object(obj)
        return self.get_prep_value(value)


# class BaseUserManager(BUM):
#     """
#     A custom user manager to deal with emails as unique identifiers for auth
#     instead of usernames. The default that's used is "UserManager"
#     """
#     def _create_user(self, email, password, **extra_fields):
#         """
#         Creates and saves a User with the given email and password.
#         """
#         if not email:
#             raise ValueError('The Email must be set')
#         email = self.normalize_email(email).lower()
#         user = self.model(email=email, **extra_fields)
#         user.set_password(password)
#         user.save()
#         return user
#
#     def create_superuser(self, email, password, **extra_fields):
#         extra_fields.setdefault('is_staff', True)
#         extra_fields.setdefault('is_superuser', True)
#         extra_fields.setdefault('is_active', True)
#
#         if extra_fields.get('is_staff') is not True:
#             raise ValueError('Superuser must have is_staff=True.')
#         if extra_fields.get('is_superuser') is not True:
#             raise ValueError('Superuser must have is_superuser=True.')
#         return self._create_user(email, password, **extra_fields)
#
#
# class User(AbstractBaseUser, PermissionsMixin):
#     email = models.EmailField(unique=True, null=True)
#
#     is_staff = models.BooleanField(_('staff status'), default=False, help_text=_('Designates whether the user can log into this site as a staff'),)
#     is_active = models.BooleanField(_('active'), default=True, help_text=_('Designates whether this user should be treated as active. ' 'Unselect this instead of deleting accounts.'), )
#     USERNAME_FIELD = 'email'
#     objects = BaseUserManager()
#
#     def __str__(self):
#         return self.get_full_name()
#
#     def get_full_name(self):
#         if (self.first_name is None or self.first_name == "") and (self.last_name is None or self.last_name == ""):
#             return "{} {}".format(self.first_name, self.last_name)
#         else:
#             return self.email if User.USERNAME_FIELD == 'email' else self.username
#
#     def get_short_name(self):
#         if self.first_name is None or self.first_name == "":
#             return self.first_name
#         else:
#             return self.email if User.USERNAME_FIELD == 'email' else self.username


# ****************************** CUSTOM SECURITY IMPLEMENTATION ******************************


# class UserManager_(UserManager):


class CustomGroupManager(models.Manager):
    use_in_migrations = True

    def get_by_natural_key(self, name):
        return self.get(name=name)

    def get_queryset(self):
        return super(CustomGroupManager, self).get_queryset()


class UserManager(DjangoBaseUserManager):
    use_in_migrations = True

    def _create_user(self, password, email, username=None, phone=None, **extra_fields):
        """Creates and saves a User with the given username, email and password."""
        if not username and getattr(settings, "AUTH_SIGN_IN_BY", "username") == 'username':
            raise ValueError('The username must be set')
        if not phone and getattr(settings, "AUTH_REQUIRE_PHONE", False):
            raise ValueError('Did you forgot the phone number')
        if not email:
            raise ValueError('Users must have a valid email address')

        # TODO: Fix this
        # db_user = User.objects.filter(Q(phone=phone) | Q(email=email))
        # if len(db_user) > 0:
        #     if db_user.phone == phone:
        #         raise ValueError('Phone number is already in use')
        #     else:
        #         raise ValueError('Email number is already in use')

        print(' ++++ password: ', password)
        email = self.normalize_email(email)
        username = self.model.normalize_username(username)
        user = self.model(username=username, email=email, phone=phone, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, password, email, username=None, phone=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(password, email, username, phone, **extra_fields)

    def create_superuser(self, password, email, username=None, phone=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(password, email, username, phone, **extra_fields)


# def avatar_path(instance, filename):
#     from core.utils import ensure_path_exists
#     path = settings.GENERAL_UPLOAD_PATH.format(company_id=instance.company.pk, path='/avatar/')
#     ensure_path_exists(path)
#     import os
#     return os.path.join(path, filename)


# class User(AbstractUser):
class AbstractUser(DjangoAbstractUser):
    """
    An abstract base class implementing a fully featured User model with
    admin-compliant permissions.

    Username and password are required. Other fields are optional.
    """
    # gauth_key = models.CharField(max_length=16, null=True, blank=None, default=None)

    # HI = "Pacific/Honolulu"
    # AK = "America/Juneau"
    # PAC = "America/Los_Angeles"
    # AZ = "America/Phoenix"
    # MTN = "America/Denver"
    # CEN = "America/Chicago"
    # EAS = "America/New_York"
    # ATL = "Atlantic/Bermuda"
    # ASK = "Asia/Kolkata" # Temporarily added.
    # TZONES = ((HI, "HI"), (AK, "AK"), (PAC, "PAC"), (AZ, "AZ"), (MTN, "MTN"), (CEN, "CEN"), (EAS, "EAS"), (ATL, "ATL"), (ASK, "ASK"))

    BASIC = 'basic'
    ADMIN = 'admin'
    POSITIONS = ((BASIC, _('Basic')), (ADMIN, _('Admin')))
    BOOL_CHOICES = ((True, 'Active'), (False, 'Inactive'))

    username_validator = UnicodeUsernameValidator()
    if getattr(settings, "AUTH_SIGN_IN_BY", "username") == "username":
        email = models.EmailField(_('email address'), unique=True, max_length=128, null=True, blank=True,
                                  help_text=_('Required valid email with 128 characters or fewer'), default=None,
                                  error_messages={'unique': _("A user with that email already exists.")})
        username = models.CharField(_('username'), unique=True, max_length=20, validators=[username_validator],
                                    help_text=_('Required 20 characters or fewer. Letters, digits and @/./+/-/_ only.'),
                                    error_messages={'unique': _("A user with that username already exists.")})
    else:
        email = models.EmailField(_('email address'), unique=True, max_length=128,
                                  help_text=_('Required valid email with 128 characters or fewer'),
                                  error_messages={'unique': _("A user with that email already exists.")})
        username = models.CharField(_('username'), max_length=20, validators=[username_validator],
                                    help_text=_('Required 20 characters or fewer. Letters, digits and @/./+/-/_ only.'),
                                    null=True, blank=True, default=None)
    if getattr(settings, "AUTH_REQUIRE_PHONE", False):
        phone = models.CharField(_('phone number'), max_length=15)
    else:
        phone = models.CharField(_('phone number'), max_length=15, blank=True, null=True, default=None)

    is_active = models.BooleanField(_('status'), choices=BOOL_CHOICES, default=True)
    email_verified = models.BooleanField(_('email verified'), default=False)
    phone_verified = models.BooleanField(_('phone verified'), default=False)
    # remember_me = models.BooleanField(_('remember me'), default=False)
    position = models.CharField(max_length=32, verbose_name="position", choices=POSITIONS, default=BASIC)
    is_manager = models.BooleanField(_('manager'), help_text="This is company's superuser", default=False)
    last_login_signature = models.ForeignKey('Audit', related_name='signatures', on_delete=models.SET_NULL,
                                             related_query_name='signature', null=True, default=None, blank=True)
    failed_attempts = models.IntegerField(_('failed attempts'), default=0)
    last_password_change = models.DateTimeField(_('last password change'), null=True, blank=True, default=None)
    force_password_change = models.BooleanField(_('force password change'), default=True)
    # avatar_image = models.ImageField(_("Avatar"), upload_to=avatar_path, blank=True, null=True, default=None,
    #                                  storage=PrivateMediaStorage())
    # avatar_image = models.ImageField(blank=True, null=True, default=None)
    # avatar_thumbnail = models.ImageField(blank=True, null=True, default=None)
    # avatar_url = models.URLField(null=True, blank=True, default=None)
    # timezone = models.CharField(_('timezone'), max_length=128, blank=True, null=True, default="America/Denver")
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cert = CredentialsField(null=True, default=None, blank=True)
    groups = models.ManyToManyField('auths.CustomGroup', verbose_name=_('groups'), blank=True,
                                    help_text=_('The groups this user belongs to. A user will get all permissions '
                                                'granted to each of their groups.'), related_name="user_set",
                                    related_query_name="user")
    remember = models.IntegerField(_('Remember me'), default=0)
    objects = UserManager()

    EMAIL_FIELD = 'email'
    USERNAME_FIELD = getattr(settings, "AUTH_SIGN_IN_BY", "username")
    REQUIRED_FIELDS = []
    if getattr(settings, "AUTH_SIGN_IN_BY", "username") != 'email':
        # This must contain all required fields on ur user model, but shouldn't contain de USERNAME_FIELD/password as these fields 'll always be prompted for.
        REQUIRED_FIELDS.append(EMAIL_FIELD)
    if getattr(settings, "AUTH_REQUIRE_PHONE", False):
        REQUIRED_FIELDS.append('phone')

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')
        abstract = True

    def has_perms(self, perm_list, obj=None):
        """
        Return True if the user has each of the specified permissions. If
        object is passed, check if the user has all required perms for it.
        """
        return all(self.has_perm(perm, obj) for perm in perm_list)

    def has_perm(self, perm, obj=None):
        """
        Return True if the user has the specified permission. Query all
        available auth backends, but return immediately if any backend returns
        True. Thus, a user who has permission from a single auth backend is
        assumed to have permission in general. If an object is provided, check
        permissions for that object.
        """
        # Active superusers have all permissions.
        if self.is_active and (self.is_superuser or self.is_manager):
            return True

        return _user_has_perm(self, perm, obj)

    # def has_perms(self, perm_list, obj=None):
    #     """
    #     Return True if the user has each of the specified permissions. If
    #     object is passed, check if the user has all required perms for it.
    #     """
    #     return all(self.has_perm(perm, obj) for perm in perm_list)

    def has_module_perms(self, app_label):
        """
        Return True if the user has any permissions in the given app label.
        Use similar logic as has_perm(), above.
        """
        # Active superusers have all permissions.
        if self.is_active and self.is_superuser:
            return True

        return _user_has_module_perms(self, app_label)

    def has_app(self, app):
        """
        Return True if the user's company subscribed for the specified module.
        """

        # Active superusers have all permissions but
        if self.is_active and self.is_superuser and self.company.id == self.user_profile.company_id:
            return True

    def check_validity(self):
        # if self.cert and self.cert.valid:
        #     return True
        try:
            try:
                if self.cert:
                    try:
                        self.cert.refresh(Request())
                    except TransportError:
                        return False
                else:
                    return False
            except RefreshError as e:
                print(e)
                return False
            return self.cert.valid
        except AttributeError:
            return False
    


# content_type = ContentType.objects.get_for_model(User)
# permission = Permission.objects.create(
#     codename='can_make_user_super',
#     name='Can Promote User to Super User',
#     content_type=content_type,
# )

def _user_has_perm(user, perm, obj):
    """
    A backend can raise `PermissionDenied` to short-circuit permission checking.
    """
    for backend in auth.get_backends():
        if not hasattr(backend, 'has_perm'):
            continue
        try:
            if backend.has_perm(user, perm, obj):
                return True
        except PermissionDenied:
            return False
    return False


def _user_has_module_perms(user, app_label):
    """
    A backend can raise `PermissionDenied` to short-circuit permission checking.
    """
    for backend in auth.get_backends():
        if not hasattr(backend, 'has_module_perms'):
            continue
        try:
            if backend.has_module_perms(user, app_label):
                return True
        except PermissionDenied:
            return False
    return False


class User(AbstractUser):
    ACCOUNT_ACTIVATION = "Account Activation"
    NEW_REG_PASS_SET = "New Reg Password Set"
    PASSWORD_RESET = "Password Reset"
    VERIFY_EMAIL = "Verify Email"
    VERIFY_PHONE = "Verify Phone"
    
    EMAIL_CHANNEL = 'email'
    PHONE_CHANNEL = 'phone'

    """
    Concrete class of AbstractUser.
    Use this if you don't need to extend User.
    """
    blacklist_permissions = models.ManyToManyField(Permission, verbose_name=_('user permissions blacklist'),
                                                   blank=True, help_text=_('Specific permissions for this user.'),
                                                   related_name="user_blacklist", related_query_name="userb")

    @property
    def activation_link(self):
        return reverse('auths:activate', kwargs={'uuid': self.pk, 'token': account_activation_token.make_token(self)})

    def activation_link_by_code(self):
        return reverse('auths:activate', kwargs={'uuid': self.pk, 'token': account_activation_token.make_token(self)})

    @property
    def password_reset_confirm_link(self):
        pk = urlsafe_base64_encode(force_bytes(self.pk))
        return reverse('auths:password_reset_confirm', kwargs={'uidb64': pk, 'token': account_activation_token.make_token(self)})

    def send_activation_link(self, domain, password=None):
        html_message = render_to_string('auths/mail_templates/welcome_activate.html',
                                        {'project_title': settings.PROJECT_TITLE.title(), 'first_name': self.first_name,
                                         'activation_link': f"{domain}{self.activation_link}",
                                         'domain': domain, 'password': password or ""})
        log.info(f"*****{self.email} Activation link is {domain}{self.activation_link}")
        from core.tasks import sendMail
        # sendMail(subject, message, recipients, fail_silently=settings.DEBUG, connection=None, cc=None, bcc=None, files=None, use_signature=None, context_data=None)
        sendMail.apply_async(kwargs={'subject': User.ACCOUNT_ACTIVATION, 'message': html_message,
                                     'recipients': [f'"{self.full_name}" <{self.email}>'],
                                     'fail_silently': settings.DEBUG,
                                     'connection': None})

        return True

    def send_password_reset_link(self, domain):
        print("======send_password_reset_link()")
        print(domain)
        
        html_message = render_to_string('auths/mail_templates/welcome_set_password.html', {
            'first_name': self.first_name,
            'activation_link': f"{domain}{self.password_reset_confirm_link}",
            'domain': domain,
            'project_title': settings.PROJECT_TITLE.title()
        })
        from core.tasks import sendMail
        sendMail.apply_async(kwargs={'subject': User.ACCOUNT_ACTIVATION, "message": html_message,
                                     "recipients": [f"'{self.full_name}' <{self.email}>"],
                                     "fail_silently": settings.DEBUG, "connection": None})

    def send_registration_password(self, domain, client_reset_link):
        token = account_activation_token.make_token(self)
        pk = urlsafe_base64_encode(force_bytes(self.pk))
        
        data = {"token": token, "id": self.id, "action": User.NEW_REG_PASS_SET, "channel": "email", "email": self.email, "extra": {}}

        # If client_reset_link is set, it mean this is client/server request
        activation_link = reverse('auths_api:password-reset-confirm', kwargs={'uidb64': pk, 'token': token}) if client_reset_link else self.password_reset_confirm_link
        html_message = render_to_string('auths/mail_templates/welcome_set_password.html', {
            'coy_name': settings.COMPANY_NAME.title(),
            'first_name': self.first_name,
            'activation_link': f"{client_reset_link}?link={domain}{activation_link}",
            'domain': domain,
            'project_title': settings.PROJECT_TITLE.title()
        })
        from core.tasks import sendMail
        sendMail.apply_async(kwargs={'subject': User.ACCOUNT_ACTIVATION, "message": html_message,
                                     "recipients": [f"'{self.full_name}' <{self.email}>"],
                                     "fail_silently": settings.DEBUG, "connection": None})
        cache.delete_pattern(f"access_token_password_{self.id}_email_*")
        cache.set(f"access_token_password_{self.id}_email_{token}", data, timeout=60*60*24)
        return token

    def send_access_token(self, token_length, domain, channel=EMAIL_CHANNEL, action=VERIFY_EMAIL, extra={}):
        token = random_with_N_digits(token_length)
        session_key = random_with_N_digits(12)
        # TODO: TO use this for multiple purpose
        data = {"token": token, "id": self.id, "action": action, "channel": channel, "extra": extra} 

        # user = UserModel.objects.filter(id=settings.EMAIL_PROCESSOR_ID).first()
        if channel.lower() == User.EMAIL_CHANNEL:
            html_message = render_to_string('auths/mail_templates/token.html', {
                'first_name': self.first_name,
                'activation_link': f"{domain}{self.password_reset_confirm_link}",
                # 'domain': domain,
                'token': token,
                'project_title': settings.PROJECT_TITLE.title()
            })

            from core.tasks import sendMail
            sendMail.apply_async(kwargs={'subject': User.ACCOUNT_ACTIVATION, "message": html_message,
                                        "recipients": [f"'{self.full_name}' <{self.email}>"],
                                        "fail_silently": settings.DEBUG, "connection": None})

            print(f"access_token_{self.id}_{User.EMAIL_CHANNEL}_{session_key}")
            cache.delete_pattern(f"access_token_{self.id}_{User.EMAIL_CHANNEL}_*")
            cache.set(f"access_token_{self.id}_{User.EMAIL_CHANNEL}_{session_key}", data, timeout=60*10)
            return session_key

    def __str__(self):
        return self.full_name or ""

    @property
    def from_database(self):
        return not self._state.adding

    @property
    def fullname(self):
        return self.full_name

    @property
    def full_name(self):
        if (self.first_name is None or self.first_name.strip() == "") and \
                (self.last_name is None or self.last_name.strip() == ""):
            return self.email if User.USERNAME_FIELD == 'email' and self.email.strip() != '' else self.username
        else:
            return "{} {}".format(self.first_name, self.last_name)

    @property
    def company(self):
        # from core.models import Company
        if self.user_profile.company.name == settings.COY_NAME:
            return cache.get(f"staff-assumed-company-{self.pk}", None) or self.user_profile.company
        else:
            return self.user_profile.company

    @property
    def companies(self):
        from core.models import Company
        if self.user_profile.company.name == settings.COY_NAME:
            return Company.companies()
        else:
            c = self.company
            return [(c.pk, c)]

    @property
    def our_users(self):
        if self.company:
            users = User.objects.filter(user_profile__company=self.company, is_active=True)
            if not (self.user_profile.company.name == settings.COY_NAME):
                users.exclude(Q(is_staff=True) | Q(is_superuser=True))
            return users
        else:
            return []

    def password_generator(self, size=8, chars=string.ascii_letters + string.digits):
        """
        Returns a string of random characters, useful in generating temporary
        passwords for automated password resets.

        size: default=8; override to provide smaller/larger passwords
        chars: default=A-Za-z0-9; override to provide more/less diversity

        Credit: Ignacio Vasquez-Abrams
        Source: http://stackoverflow.com/a/2257449
        """
        return ''.join(random.choice(chars) for i in range(size))

    def get_short_name(self):
        if self.first_name is None or self.first_name.strip() == "":
            if self.last_name is None or self.last_name.strip() == "":
                return self.email if User.USERNAME_FIELD == 'email' else self.username
            else:
                return self.last_name
        else:
            return self.first_name

    def email_user(self, subject, message, from_email=None, **kwargs):
        from core.tasks import sendMail
        # sendMail(subject, message, recipients, fail_silently=settings.DEBUG, html_message=None, channel=None, connection_label=None, reply_to=None, cc=None, bcc=None, files=None)
        # (subject, message, recipients, fail_silently =settings.DEBUG, html_message=None, channel=None, connection_label=None, reply_to=None, cc=None, bcc=None, files=None)

        sendMail.apply_async(kwargs={**{"subject": subject, "message": message,  "connection": None,
                                        "recipients": self.email}, **kwargs})
        return

    @property
    def profile_pic_url(self):
        # get_current_site(request).domain)
        if self.avatar_image:
            return self.avatar_image.url
        return self.avatar_url or f"{settings.STATIC_URL}{'img/default-profile-icon.png'}"

    @property
    def get_avatar_thumbnail(self):
        if self.avatar_image:
            try:
                return self.avatar_thumbnail.url
            except ValueError:
                from core.utils import make_thumbnail
                if not make_thumbnail(self.avatar_thumbnail, self.avatar_image, settings.THUMBNAIL_IMAGE_SIZE, 'thumb'):
                    return None
            return self.get_avatar_thumbnail
        else:
            return self.profile_pic_url

    def localize_time(self, datetime, set_format=False, or_use_company_tz=False):
        # try:
        #     timezone.activate(pytz.timezone(self.timezone))
        #     datetime = timezone.localtime(datetime)
        # except Exception as err:
        #     log.warning(err)
        #     raise InvalidTimezoneException("User's Timezone is required")
        if datetime:
            datetime = DateTimeField().clean(datetime) if isinstance(datetime, str) else datetime

            tzone = self.timezone if self.timezone else self.company.timezone if or_use_company_tz & self.company.timezone else None
            if tzone:
                # https://www.peterbe.com/plog/django-forms-and-making-datetime-inputs-localized
                from core.utils import is_timezone_aware
                if is_timezone_aware(datetime):
                    datetime = datetime.astimezone(pytz.timezone(tzone.utc))
                else:
                    datetime = datetime.replace(tzinfo=None)  # Make it native
                    # This user's timezone
                    user_tz = pytz.timezone(tzone.utc)
                    # Localize the date for this user
                    datetime = user_tz.localize(datetime)
            else:
                pass
                # TODO: Try figure out how best to handle situation when the `tzone` is NOT set
            if set_format:
                return datetime.strftime(f"{self.company.date_format_python()} %I:%M %p") if datetime else ""
        return datetime

    def utc_time(self, datetime, set_format=False):
        if datetime:
            datetime = DateTimeField().clean(
                datetime) if isinstance(datetime, str) else datetime
            # https://www.peterbe.com/plog/django-forms-and-making-datetime-inputs-localized
            from core.utils import is_timezone_aware
            if is_timezone_aware(datetime):
                datetime = datetime.astimezone(pytz.timezone("UTC"))
            else:
                datetime = datetime.replace(tzinfo=None)  # Make it native
                datetime = pytz.timezone("UTC").localize(datetime)  # Localize the date for this user
            if set_format:
                return datetime.strftime(f"{self.company.date_format_python()} %I:%M %p") if datetime else ""
        return datetime

    @property
    def permissions_csv(self):
        perms = self.user_permissions.all().values_list('id', flat=True)
        perms_str = ",".join([str(i) for i in perms])
        return perms_str

    @property
    def blacklist_permissions_csv(self):
        blacklist_perms = self.blacklist_permissions.all().values_list('id', flat=True)
        blacklist_perms_str = ",".join([str(i) for i in blacklist_perms])
        return blacklist_perms_str

    # TODO: Remove duplicates for when user is different groups with common permission
    def permissions(self, code_list=False):
        if self.is_superuser:
            if code_list:
                return Permission.objects.all().values_list('codename', flat=True)
            else:
                return Permission.objects.all()
        if code_list:
            return self.user_permissions.all().values_list('codename', flat=True) | \
                   Permission.objects.filter(group__user=self).values_list('codename', flat=True)
        else:
            bl = [i.id for i in self.blacklist_permissions.all()]
            defaults = permission_utils.default_perms()
            default_ids = [i.id for i in defaults]
            bl = [i for i in bl if i not in default_ids]

            perms = Permission.objects.filter(Q(group__in=self.groups.all()), Q(id__in=default_ids)).exclude(id__in=bl)
            #return [p for p in perms if p.id not in bl]
            return perms

    def has_model_permissions(self, model, perms, raise_exception=False):
        """
        Checks if instance (User or Group) has the permission listed in the 'perms' list
        :param model: Model been checked against (Not Instance) eg. Profile for Profile Model
        :param perms: List of permissions to check for eg. ['read', 'add', 'delete']
        :param raise_exception: Raise PermissionRequired Exception if one or more permission is not Found
        :return:
        """
        perm = "{}.{{}}_{}".format(model.__module__.split(".")[0], model.__name__.lower())

        for p in perms:
            if not self.has_perm(perm.format(p)):
                if raise_exception:
                    raise PermissionRequired(f"Permission '{perm.format(p)}' not found for {self}")
                return False
        return True

    @property
    def editable_together(self):
        return []

    # def save(self, *args, **kwargs):
    #     major = kwargs.pop('major', False)
    #     updated_by = kwargs.pop('updated_by', False)
    #     created = True
    #     if self.pk is not None:
    #         created = False
    #         self._original = self.__class__.objects.get(pk=self.pk).to_dict()
    #         diff = self.diff()
    #         if diff:
    #             diff['batch_id'] = self._batch_id if hasattr(self, "_batch_id") else None
    #             self.log_changes(updated_by, diff, change_type=1, major=major)
    #     super(self.__class__, self).save(*args, **kwargs)
    #     self._original = self.to_dict()
    #     if created:
    #         self._original['batch_id'] = self._batch_id if hasattr(self, "_batch_id") else None
    #         self.log_changes(updated_by, self._original, change_type=0, major=major)

    # def save(self, *args, **kwargs):
    #     created = False
    #     if self.pk is None:
    #         created = True
    #     super(User, self).save(*args, **kwargs)
    #     if created and self.pk:
    #         from core.models import Assigned
    #         Assigned.create_assigned(self.pk, self.__class__.__name__, self.company, self.updated_by_id)

    class Meta:  # noqa: D101
        abstract = False
        app_label = 'auths'
        swappable = 'AUTH_USER_MODEL'
        db_table = 'auths_user'

    def get_admin_url(self):
        return reverse(f'admin:{self._meta.app_label}_{self._meta.model_name}_change', args=(self.pk,))

    @classmethod
    def get_add_url(cls):
        return reverse('auths:user-add')

    @classmethod
    def get_list_url(cls):
        return reverse('auths:user-list')

    def get_absolute_url(self):
        return reverse('auths:user-detail', kwargs={'pk': self.pk})

    def get_update_url(self):
        return reverse('auths:user-edit', kwargs={'pk': self.pk})

    def get_delete_url(self):
        return reverse('auths:user-delete', kwargs={'pk': self.pk})

    def get_disable_url(self):
        return reverse('auths:user-disable', kwargs={'pk': self.pk})


class Audit(models.Model):
    FAILED = 'Failed'
    SUCCESSFUL = 'Successful'
    STATUS = ((FAILED, _('Failed')), (SUCCESSFUL, _('Successful')),)

    ACTIVE = 'Active'
    ANONYMOUS = 'Anonymous'
    LOGGED_OUT = 'Logged Out'
    INVALIDATED = 'Invalidated'
    EXPIRED = 'Expired'
    SESSION_STATUS = (
        (ACTIVE, _('Active')),
        (ANONYMOUS, _('Anonymous')),
        (EXPIRED, _('Expired')),
        (INVALIDATED, _('Invalidated')),
        (LOGGED_OUT, _('Logged Out')),
    )

    PASSWORD = 'Password'
    FACEBOOK = 'Facebook'
    GOOGLE = 'Google'
    TWITTER = 'Twitter'
    YAHOO = 'Yahoo'
    LINKEDIN = 'LinkedIn'
    INSTAGRAM = 'Instagram'
    AMAZON = 'Amazon'
    DROPBOX = 'Dropbox'
    GITHUB = 'Github'
    GITLAB = 'GitLab'
    STACKOVERFLOW = 'Stackoverflow'
    AUTH_BACKEND = [
        (PASSWORD, _('Password')),
        (FACEBOOK, _('Facebook')),
        (GOOGLE, _('Google')),
        (TWITTER, _('Twitter')),
        (YAHOO, _('Yahoo')),
        (LINKEDIN, _('LinkedIn')),
        (INSTAGRAM, _('Instagram')),
        (AMAZON, _('Amazon')),
        (DROPBOX, _('Dropbox')),
        (GITHUB, _('Github')),
        (GITLAB, _('GitLab')),
        (STACKOVERFLOW, _('Stackoverflow'))
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ip = models.GenericIPAddressField(_('ip address'), null=True, blank=True,)
    session_key = models.CharField(_('session key'), max_length=40, null=True, blank=True, default=None)
    created = models.DateTimeField(_('created'), auto_now_add=True, editable=True)
    last_seen = models.DateTimeField(_('last seen'), null=True, blank=True, default=None)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, default=None)
    username = models.CharField(_('username'), max_length=254)
    fingerprint = models.CharField(_('fingerprint'), max_length=32)
    auth_backend = models.CharField(_('authenticated via'), max_length=14, choices=AUTH_BACKEND, default=PASSWORD)
    auth_status = models.CharField(_('authentication status'), max_length=10, choices=STATUS, default=SUCCESSFUL)
    session_status = models.CharField(_('session status'), max_length=12, choices=SESSION_STATUS, default=ANONYMOUS)
    browser = models.CharField(_('browser'), max_length=16, null=True, blank=True,)
    browser_version = models.CharField(_('browser version'), max_length=16, blank=True, null=True)
    os = models.CharField(_('operating system (OS)'), max_length=16, blank=True, null=True)
    os_version = models.CharField(_('OS version'), max_length=16, blank=True, null=True)
    current_resolution = models.CharField(_('current resolution'), max_length=16, blank=True, null=True)
    available_resolution = models.CharField(_('available resolution'), max_length=16, blank=True, null=True)
    device = models.CharField(_('device'), max_length=32, blank=True, null=True)
    language = models.CharField(_('language'), max_length=254, blank=True, null=True)
    timezone = models.CharField(_('timezone'), max_length=64, blank=True, null=True)

    def get_admin_url(self):
        return reverse(f'admin:{self._meta.app_label}_{self._meta.model_name}_change', args=(self.pk,))

    def __str__(self):
        return f'{self.os} - {self.browser} - {self.ip}'

    class Meta:
        db_table = 'account_audit'


# class CustomSession(SessionStore):
class AuthSession(AbstractBaseSession):
    # The example below shows a custom database-backed session engine that includes an additional database column to
    # store an account ID (thus providing an option to query the database for all active sessions for an account):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, default=None)

    @classmethod
    def get_session_store_class(cls):
        from auths.overrides.cached_db import SessionStore
        return SessionStore

    class Meta:
        db_table = 'account_auth_session'


class PasswordHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    harsh = models.CharField(max_length=128)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'account_password_history'


UserModel = get_user_model()


class CustomGroup(Group):
    if settings.IS_MULTITENANT:
        company = models.ForeignKey("core.Company", on_delete=models.CASCADE)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, blank=True, null=True, default=None,
                               related_name="children")
    is_default = models.BooleanField(_('is default'), default=False)
    updated_by = models.ForeignKey(UserModel, on_delete=models.CASCADE, blank=True, null=True)
    parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True, default=None)

    def __init__(self, *args, **kwargs):
        super(Group, self).__init__(*args, **kwargs)
        cmp_id = str(self.company_id) if self.company_id else ""

        if self.name and cmp_id and self.name.startswith(cmp_id):
            self.name = self.name.replace(cmp_id, "")

    class Meta:
        verbose_name_plural = 'CustomGroups'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        cmp_id = str(self.company_id)
        if not self.name.startswith(cmp_id):
            self.name = cmp_id+self.name
        super(Group, self).save(*args, **kwargs)

    # def natural_key(self):
    #    return (self.name, )


# class PermissionGroup(models.Model):
#
#     name = models.CharField(max_length=64)
#     group = models.OneToOneField(Group, on_delete=models.CASCADE)
#     company = models.ForeignKey(Company, on_delete=models.CASCADE)
#
#     class Meta:
#         unique_together = ('name', 'company')
#         db_table = 'account_permission_group'


# *********************************** Multifactor Authentication ******************************************


class UserOTP(models.Model):

    OTP_TYPES = (('HOTP', 'hotp'), ('TOTP', 'totp'))

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    otp_type = models.CharField(max_length=20, choices=OTP_TYPES)
    secret_key = models.CharField(max_length=100, blank=True)


def is_mfa_enabled(user):
    """
    Determine if a user has MFA enabled
    """
    return hasattr(user, 'userotp')


class UserRecoveryCodes(models.Model):
    user = models.ForeignKey(UserOTP, on_delete=models.CASCADE)
    secret_code = models.CharField(max_length=10)


class U2FKey(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='u2f_keys', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True)

    # public_key = models.TextField(unique=True)
    public_key = models.TextField()
    key_handle = models.TextField()
    app_id = models.TextField()

    def to_json(self):
        return {'publicKey': self.public_key, 'keyHandle': self.key_handle, 'appId': self.app_id, 'version': 'U2F_V2'}


def is_u2f_enabled(user):
    """
    Determine if a user has U2F enabled
    """
    return user.u2f_keys.all().exists()


# *****************************************************************************

