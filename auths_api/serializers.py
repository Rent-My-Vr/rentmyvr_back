from csv import field_size_limit
from dataclasses import fields
import logging
import json
from abc import ABC

from django.conf import settings
from django.db.models import Q
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.auth.forms import PasswordResetForm as DjangoPasswordResetForm
from django.utils.encoding import force_str, force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import serializers
from rest_framework.authtoken.models import Token

from rest_framework.exceptions import ValidationError
from dj_rest_auth.serializers import PasswordResetSerializer as DJ_PasswordResetSerializer

if 'allauth' in settings.INSTALLED_APPS:
    from allauth.account.adapter import get_adapter
from auths.models import CustomGroup
from .forms import PasswordResetForm, SetPasswordForm
from auths.utils import account_activation_token


log = logging.getLogger("{}.*".format(__package__))
log.setLevel(settings.LOGGING_LEVEL)
UserModel = get_user_model()


class SavvybizGroupSerializer(serializers.ModelSerializer):
    company_name = serializers.SerializerMethodField()
    user_set_list = serializers.SerializerMethodField()

    def get_user_set_list(self, obj):
        return [{"id": u.id, "first_name": u.first_name, "last_name": u.last_name} for u in obj.user_set.all()]

    def get_company_name(self, obj):
        return obj.company.name

    class Meta:
        model = CustomGroup
        fields = '__all__'


class PasswordResetConfirmSerializer(serializers.Serializer):
    """
    Serializer for requesting a password reset e-mail.
    """
    new_password1 = serializers.CharField(max_length=64)
    new_password2 = serializers.CharField(max_length=64)
    uid = serializers.CharField(max_length=64)
    token = serializers.CharField(max_length=12)
    action = serializers.CharField(max_length=32)
    channel = serializers.CharField(max_length=32)
    session_key = serializers.CharField(max_length=32)
    processing_channel = serializers.CharField(max_length=64, required=False, allow_blank=True)
    client_callback_link = serializers.CharField(max_length=64, required=False, allow_blank=True)

    set_password_form_class = SetPasswordForm

    def custom_validation(self, attrs):
        pass

    def validate(self, data):
        self._errors = {}

        # Decode the uidb64 to uid to get User object
        try:
            self.user = UserModel._default_manager.get(pk=data['uid'])
        except (TypeError, ValueError, OverflowError, UserModel.DoesNotExist):
            raise ValidationError({'url': ['Invalid link. Regenerate a new one and try again']})
        
        self.custom_validation(data)
        # Construct SetPasswordForm instance
        self.set_password_form = self.set_password_form_class(user=self.user, data=data)
        if not self.set_password_form.is_valid():
            raise serializers.ValidationError(self.set_password_form.errors)
        if not account_activation_token.check_token(self.user, action=data['action'], token=str(data['token']), channel=data['channel'], session_key=data['session_key']):
            raise ValidationError({'token': ['Invalid or expired token/link. Regenerate a new one and try again']})

        return data

    def save(self):
        d = self.set_password_form.save()
        print('...... ', d)
        return d


class PasswordTokenConfirmSerializer(serializers.Serializer):
    """
    Serializer for validating EMail token.
    """

    uidb64 = serializers.CharField(max_length=64)
    token = serializers.CharField(max_length=12)
    action = serializers.CharField(max_length=32)
    channel = serializers.CharField(max_length=32)
    session_key = serializers.CharField(max_length=32)
    processing_channel = serializers.CharField(max_length=64, required=False, allow_blank=True)
    client_callback_link = serializers.CharField(max_length=64)
    
    def validate(self, data):
        self._errors = {}

        # Decode the uidb64 to uid to get User object
        try:
            # pk = urlsafe_base64_encode(force_bytes(data['uid']))
            pk = urlsafe_base64_decode(data['uidb64']).decode()
            print(pk)
            self.user = UserModel._default_manager.get(pk=pk)
            print(self.user)
        except (TypeError, ValueError, OverflowError, UserModel.DoesNotExist):
            raise ValidationError({'url': ['Invalid link. Regenerate a new one and try again']})

        if not account_activation_token.check_token(self.user, action=data['action'], token=str(data['token']), channel=data['channel'], session_key=data['session_key']):
            raise ValidationError({'token': ['Invalid or expired token/link. Regenerate a new one and try again']})
        return data
    
    def save(self):
        print('=======>> Saving() ', self.data)
        if self.data.get('action') in [UserModel.NEW_REG_PASS_SET, UserModel.PASSWORD_RESET]:
            print(1)
            if self.data.get('action') == UserModel.NEW_REG_PASS_SET:
                print(2)
                self.user.is_active = True
                self.user.force_password_change = False
                if hasattr(self.user, "email_verified") and self.data.get('channel') == UserModel.EMAIL_CHANNEL:
                    self.user.email_verified = True
                if hasattr(self.user, "phone_verified") and self.data.get('channel') == UserModel.PHONE_CHANNEL:
                    self.user.phone_verified = True
            else:
                print(3)
                self.set_password_form.save()
        elif self.data.get('action') in [UserModel.ACCOUNT_ACTIVATION, UserModel.NEW_REG_ACTIVATION, UserModel.VERIFY_PHONE, UserModel.VERIFY_EMAIL]:
            print(4)
            if self.data.get('action') in [UserModel.ACCOUNT_ACTIVATION, UserModel.NEW_REG_ACTIVATION]:
                print(5)
                self.user.is_active = True
                self.user.force_password_change = False
            if hasattr(self.user, "email_verified") and self.data.get('channel') == UserModel.EMAIL_CHANNEL:
                print(6)
                self.user.email_verified = True
            if hasattr(self.user, "phone_verified") and self.data.get('channel') == UserModel.PHONE_CHANNEL:
                print(7)
                self.user.phone_verified = True
        self.user.save()
        return self.user
            
    class Meta:
        ref_name = "PasswordToken"


class PasswordResetSerializer(DJ_PasswordResetSerializer):
    """
    Serializer for requesting a password reset e-mail.
    """

    action = serializers.CharField(max_length=32)
    channel = serializers.CharField(max_length=32)
    session_key = serializers.CharField(max_length=32)
    processing_channel = serializers.CharField(max_length=64, required=False, allow_blank=True)
    client_callback_link = serializers.CharField(max_length=64, required=False, allow_blank=True)
    
    # set_password_form_class = PasswordResetForm  if 'allauth' in settings.INSTALLED_APPS else DjangoPasswordResetForm
    
    @property
    def password_reset_form_class(self):
        if 'allauth' in settings.INSTALLED_APPS:
            return PasswordResetForm
        else:
            return 

    # def get_email_options(self):
    #     """Override this method to change default e-mail options"""
    #     return {}

    def validate_email(self, value):
        # Create PasswordResetForm with the serializer
        print(value, ' -------- validate_email()', self.initial_data)
        self.reset_form = self.password_reset_form_class(data=self.initial_data)
        if not self.reset_form.is_valid():
            raise serializers.ValidationError(self.reset_form.errors)
        return value

    def save(self, data):
        self.users = UserModel.objects.filter(Q(email=data["email"], is_active=True) | Q(email=data["email"], is_active=False, last_login__isnull=True))
        extra = {"processing_channel": data.get('processing_channel'), "client_callback_link": data.get('client_callback_link')}
        
        print(self.users)
        session_key = None
        user = None
        x=0
        for u in self.users:
            if session_key:
                break
            user = u
            session_key = u.send_access_token(data["domain"], data.get('action'), data.get('channel'), extra=extra)
            x += 1
            print('..........', session_key, '\n\n')
            
        print('---session_key: ', session_key)
    
        print('++++++++ 1 ++++++++ ', data)
        return session_key, user
    
    class Meta:
        ref_name = "PasswordRest"


class PermissionSerializer(serializers.ModelSerializer):
    content_type_obj = serializers.SerializerMethodField()

    def get_content_type_obj(self, obj):
        return {'app_label': obj.content_type.app_label, 'model': obj.content_type.model}

    class Meta:
        model = Permission
        fields = '__all__'


class UserSerializer(serializers.ModelSerializer):
    profile_id = serializers.SerializerMethodField(source='user_profile')
    company = serializers.SerializerMethodField(source='user_profile__company')
    
    def get_company(self, obj):
        try:
            c =  obj.user_profile.company
            if c:
                try:
                    return {'id': c.id, 'name': c.name, 'mdl': c.mdl.id }
                except Exception:
                    return {'id': str(c.id), 'name': c.name, 'mdl': None}
            else:
                return None
        except Exception as e:
            print('==> ', e)
            return None

    
    def get_profile_id(self, obj):
        try:
            return obj.user_profile.id
        except UserModel.DoesNotExist:
            print('1111')
            return ''
        except Exception:
            print('2222')
            return ''

    class Meta:
        model = UserModel
        # exclude = ('username', )
        read_only_fields = ('id', 'last_login', 'is_superuser', 'is_staff',
        'is_active', 'email_verified', 'is_manager', 'failed_attempts', 
        'last_password_change', 'force_password_change', 'remember', 
        'last_login_signature', 'user_permissions', 'groups', 'blacklist_permissions')
        fields = ('id', 'first_name', 'last_name', 'phone', 'email', 'password', 'profile_id', 'company')
        # fields = ('id', 'first_name', 'last_name', 'phone', 'email', 'password', 'user_profile', 'company')
        extra_kwargs = {'password': {'write_only': True}}


class UserSpecialSerializer(serializers.ModelSerializer):
    # profile_id = serializers.SerializerMethodField(source='user_profile')
    company = serializers.SerializerMethodField(source='user_profile__company')

    def get_profile_id(self, obj):
        try:
            return obj.user_profile.id
        except UserModel.DoesNotExist:
            print('1111')
            return ''
        except Exception:
            print('2222')
            return ''
    
    def get_company(self, obj):
        try:
            c =  obj.user_profile.company
            if c:
                try:
                    return {'id': c.id, 'name': c.name, 'mdl': c.mdl.id }
                except Exception:
                    return {'id': str(c.id), 'name': c.name, 'mdl': None}
            else:
                return None
        except Exception as e:
            print('==> ', e)
            return None

    class Meta:
        model = UserModel
        # exclude = ('username', )
        read_only_fields = ('id', 'last_login', 'is_superuser', 'is_staff',
        'is_active', 'email_verified', 'is_manager', 'failed_attempts', 
        'last_password_change', 'force_password_change', 'remember', 
        'last_login_signature', 'user_permissions', 'groups', 'blacklist_permissions')
        fields = ('id', 'first_name', 'last_name', 'phone', 'email', 'password', 'company')
        # fields = ('id', 'first_name', 'last_name', 'phone', 'email', 'password', 'user_profile', 'company')
        extra_kwargs = {'password': {'write_only': True}}


class UserUpdateSerializer(UserSerializer):
    class Meta:
        model = UserModel
        fields = ('id', 'first_name', 'last_name', 'phone', 'email', )


class UserSerializerClean(serializers.ModelSerializer):
    # from core_api.serializers import TimezoneSerializerLite
    # timezone = TimezoneSerializerLite()
    name = serializers.SerializerMethodField()

    def get_name(self, obj):
        return f"{obj.full_name if obj.pk else obj.email}"

    class Meta:
        model = UserModel
        fields = ('id', 'first_name', 'last_name', 'name', 'email', 'phone', 'position', 'is_active', 'is_staff',
                  'is_superuser', 'is_manager', 'email_verified')
        read_only_fields = ('id',)
        extra_kwargs = {'password': {'write_only': True}}

class UserNameSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    
    def get_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"

    class Meta:
        model = UserModel
        fields = ('id', 'name')

class UserPasswordChangeSerializer(serializers.ModelSerializer):
    old_password = serializers.SerializerMethodField()
    password1 = serializers.SerializerMethodField()
    password2 = serializers.SerializerMethodField()
    
    def get_old_password(self, obj):
        return obj.password
   
    def get_password1(self, obj):
        return obj.password
   
    def get_password2(self, obj):
        return obj.password

    class Meta:
        model = UserModel
        fields = ('id', 'old_password', 'password1', 'password2')


class UserShortSerializer(serializers.ModelSerializer):
    type = serializers.SerializerMethodField()
    value = serializers.SerializerMethodField()

    def get_type(self, obj):
        return obj.__class__.__name__

    def get_value(self, obj):
        return obj.user_profile.fullname

    def get_auth_token(self, obj):
        return Token.objects.create(user=obj)

    class Meta:
        model = UserModel
        fields = ('id', 'value', 'type', 'auth_token')
        read_only_fields = ('id', 'auth_token')


class UserLoginSerializer(serializers.ModelSerializer):
    email = serializers.CharField(max_length=200, required=True)
    password = serializers.CharField(required=True, write_only=True)

    class Meta:
        model = UserModel
        fields = ('email', 'password')


class EmptySerializer(serializers.ModelSerializer):
    pass

    class Meta:
        model = UserModel
        fields = ('email',)





# class RegisterSerializer(serializers.Serializer):
#     username = serializers.CharField(
#         max_length=get_username_max_length(),
#         min_length=allauth_settings.USERNAME_MIN_LENGTH,
#         required=allauth_settings.USERNAME_REQUIRED,
#     )
#     email = serializers.EmailField(required=allauth_settings.EMAIL_REQUIRED)
#     password1 = serializers.CharField(write_only=True)
#     password2 = serializers.CharField(write_only=True)

#     def validate_username(self, username):
#         username = get_adapter().clean_username(username)
#         return username

#     def validate_email(self, email):
#         email = get_adapter().clean_email(email)
#         if allauth_settings.UNIQUE_EMAIL:
#             if email and email_address_exists(email):
#                 raise serializers.ValidationError(
#                     _('A user is already registered with this e-mail address.'),
#                 )
#         return email

#     def validate_password1(self, password):
#         return get_adapter().clean_password(password)

#     def validate(self, data):
#         if data['password1'] != data['password2']:
#             raise serializers.ValidationError(_("The two password fields didn't match."))
#         return data

#     def custom_signup(self, request, user):
#         pass

#     def get_cleaned_data(self):
#         return {
#             'username': self.validated_data.get('username', ''),
#             'password1': self.validated_data.get('password1', ''),
#             'email': self.validated_data.get('email', ''),
#         }

#     def save(self, request):
#         adapter = get_adapter()
#         user = adapter.new_user(request)
#         self.cleaned_data = self.get_cleaned_data()
#         user = adapter.save_user(request, user, self, commit=False)
#         if "password1" in self.cleaned_data:
#             try:
#                 adapter.clean_password(self.cleaned_data['password1'], user=user)
#             except DjangoValidationError as exc:
#                 raise serializers.ValidationError(
#                     detail=serializers.as_serializer_error(exc)
#             )
#         user.save()
#         self.custom_signup(request, user)
#         setup_user_email(request, user, [])
#         return user

