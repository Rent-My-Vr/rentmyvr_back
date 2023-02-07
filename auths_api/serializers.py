from csv import field_size_limit
from dataclasses import fields
import logging
from abc import ABC

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.auth.forms import SetPasswordForm, PasswordResetForm as DjangoPasswordResetForm
from rest_framework import serializers
from rest_framework.authtoken.models import Token

from dj_rest_auth.serializers import PasswordResetSerializer as DJ_PasswordResetSerializer

from auths.models import CustomGroup
from .forms import PasswordResetForm


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


class PasswordResetSerializer(DJ_PasswordResetSerializer):
    """
    Serializer for requesting a password reset e-mail.
    """

    @property
    def password_reset_form_class(self):
        if 'allauth' in settings.INSTALLED_APPS:
            return PasswordResetForm
        else:
            return DjangoPasswordResetForm

    def get_email_options(self):
        """Override this method to change default e-mail options"""
        return {}

    def validate_email(self, value):
        # Create PasswordResetForm with the serializer
        self.reset_form = self.password_reset_form_class(data=self.initial_data)
        if not self.reset_form.is_valid():
            raise serializers.ValidationError(self.reset_form.errors)

        return value

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
        fields = ('id', 'first_name', 'last_name', 'phone', 'email', 'password', 'profile_id')
        # fields = ('id', 'first_name', 'last_name', 'phone', 'email', 'password', 'user_profile')
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

