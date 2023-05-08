import logging
from uuid import UUID

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model, password_validation
from django.contrib.auth.forms import AuthenticationForm as AF, PasswordResetForm as PRF, PasswordChangeForm as PCF, \
    SetPasswordForm as SPF, UserCreationForm, UserChangeForm
from django.core.exceptions import ValidationError
from django.template import loader
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from .models import CustomGroup

UserModel = get_user_model()

log = logging.getLogger(f"{__package__}.*")
log.setLevel(settings.LOGGING_LEVEL)

DEFAULT_COMPANY_ID = UUID(settings.DEFAULT_COY_PK)

class AuthenticationForm(AF):

    def confirm_login_allowed_(self, user):
        if not user.is_active or not user.is_validated:
            raise forms.ValidationError('There was a problem with your login.', code='invalid_login')


class LoginForm(AuthenticationForm):
    def __init__(self, request=None, *args, **kwargs):

        super(LoginForm, self).__init__(request=request, *args, **kwargs)
        if getattr(settings, "AUTH_TRACK_CLIENT", False):
            # del self.fields['client']
            self.fields['client_id'] = forms.CharField(max_length=160, widget=forms.HiddenInput())
            self.fields['timezone'] = forms.CharField(max_length=160, widget=forms.HiddenInput())
            self.fields['remember_me'] = forms.BooleanField(required=False, label="Remember Me", widget=forms.CheckboxInput())

    # captcha = CaptchaField(label='Are you an human? ', )
    # captcha = CaptchaField(label='Are you an human? ', widget=forms.TextInput(attrs={'class': 'form-control'}))
    # log.info(getattr(settings, "AUTH_SIGN_IN_BY", "username"))
    if getattr(settings, "AUTH_SIGN_IN_BY", "username") == "email":
        username = forms.EmailField(label="Email", max_length=254, widget=forms.EmailInput(attrs={'class': 'form-control  m-input', 'placeholder': 'Email Address', 'autocomplete': "off"}))
    else:
        username = forms.CharField(label="Username", max_length=254, widget=forms.TextInput(attrs={'class': 'form-control  m-input', 'placeholder': 'Username', 'autocomplete': "off"}))
    password = forms.CharField(required=True, label="Password", max_length=20, widget=forms.PasswordInput(attrs={'class': 'form-control m-input m-login__form-input--last', 'name': 'password', 'placeholder': 'Password'}))

    # client = forms.CharField(max_length=100)
    # def __init__(self, *args, **kwargs):
    #     super(LoginForm, self).__init__(*args, **kwargs)
    #     for field in self.fields.values():
    #         field.widget.attrs = {'class': 'form-control'}


class PasswordResetForm(PRF):
    email = forms.EmailField(label=_("Enter your email to reset your password"), max_length=254,  widget=forms.TextInput(attrs={'class': 'form-control m-input', 'name': 'email', 'placeholder': 'Email',  'autocomplete': "off"}))

    def send_mail(self, subject_template_name, email_template_name, context, from_email, to_email, html_email_template_name=None):
        """
        Send a django.core.mail.EmailMultiAlternatives to `to_email`.
        """
        subject = loader.render_to_string(subject_template_name, context)
        # Email subject *must not* contain newlines
        subject = ''.join(subject.splitlines())
        body = loader.render_to_string(email_template_name, context)

        # email_message = EmailMultiAlternatives(subject, layout, from_email, [to_email])

        if html_email_template_name is not None:
            from core.tasks import sendMail
            html_message = loader.render_to_string(html_email_template_name, context)
            # sendMail(subject, message, recipients, fail_silently=settings.DEBUG, html_message=None, channel="SMTP", connection_label=None):
            sendMail.apply_async(
                kwargs={'subject': subject, 'message': "", 'recipients': [f"{context['user'].full_name if context['user'] else ''} <{to_email}>"],
                        'fail_silently': False, 'html_message': html_message, 'connection': None})

    def clean_email(self):
        email = self.cleaned_data["email"]
        para = {f'{UserModel.get_email_field_name()}__iexact': email, 'is_active': False}
        user = UserModel._default_manager.filter(**para).first()
        if next(self.get_users(email), "***") == "***" or (hasattr(user, "email_verified") and not user.email_verified):
            if user:
                msg = "This account is deactivated, please contact your administrator"
                if user.last_login is None:
                    u = reverse('auths:send-mail-activation', args=(user.pk,))
                    msg = f"New Account requires activation: <a href='{u}' title='Click to request activation link' data-toggle='tooltip'>Request Activation Link</a>"
                raise ValidationError(mark_safe(msg))
        return email


class SetPasswordForm(SPF):
    """
    A form that lets a user change set their password without entering the old password
    """
    error_messages = {
        'password_mismatch': _("The two password fields didn't match."),
    }
    new_password1 = forms.CharField(
        label=_("New password"),
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': ''}),
        strip=False,
        help_text=password_validation.password_validators_help_text_html(),
    )
    new_password2 = forms.CharField(
        label=_("New password confirmation"),
        strip=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': ''}),
    )

    def save(self, commit=True):
        print('+++++++++ Saving in form()')
        self.user.is_active = True
        self.user.force_password_change = False
        if hasattr(self.user, "email_verified"):
            self.user.email_verified = True
        password = self.cleaned_data["new_password1"]
        self.user.set_password(password)
        if commit:
            self.user.save()
        return self.user


class PasswordChangeForm(PCF):
    """
    A form that lets a user change their password by entering their old
    password.
    """
    error_messages = dict(SetPasswordForm.error_messages, **{
        'password_incorrect': _("Your old password was entered incorrectly. Please enter it again."),
    })
    old_password = forms.CharField(
        label=_("Old password"),
        strip=False,
        widget=forms.PasswordInput(attrs={'autofocus': True, 'class': 'form-control m-input', 'placeholder': 'Enter current password'}),
    )
    new_password1 = forms.CharField(
        label=_("New password"),
        strip=False,
        widget=forms.PasswordInput(attrs={'autofocus': True, 'class': 'form-control m-input', 'placeholder': 'Enter new password'}),
    )
    new_password2 = forms.CharField(
        label=_("Re-enter New password"),
        strip=False,
        widget=forms.PasswordInput(attrs={'autofocus': True, 'class': 'form-control m-input', 'placeholder': 'Re-enter new password'}),
    )

    field_order = ['old_password', 'new_password1', 'new_password2']


class SignupForm(UserCreationForm):
    # email = forms.EmailField(max_length=200, help_text='Required', )

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super(SignupForm, self).__init__(*args, **kwargs)  # populates the post
        # self.fields['timezone'] = EmptyChoiceField(required=False, empty_label="--- select timezone ---", choices=Timezone.objects.filter(enabled=True).values_list("utc", "utc"),)
        # self.fields['timezone'] = EmptyChoiceField(required=False, empty_label="--- select timezone ---", choices=AbstractUser.TZONES)
        # self.fields['timezone'].widget.attrs = {'class': 'form-control select2'}

        #if not (self.request and (self.request.user.is_manager or self.request.user.is_superuser)):
        #    if self.fields.has_key('is_manager'):            
        #        del self.fields["is_manager"]

        if self.request:
            self.fields['groups'].queryset = CustomGroup.objects.filter(
                company = self.request.user.company
            )
            self.fields['groups'].widget.attrs = {'class': 'form-control select2'}

            if self.request.user.company.id == DEFAULT_COMPANY_ID:
                self.fields['is_manager'].label = "Savvybiz Admin"
                del self.fields['user_permissions']
                del self.fields['blacklist_permissions']

        if self.instance.date_joined or getattr(settings, 'AUTH_AUTO_GENERATE_PASSWORD_ON_CREATE', False):
            del self.fields["password1"]
            del self.fields["password2"]
        # else:
        # self.fields['timezone'].queryset = Tzone.objects.filter(enabled=True)
        # choices = list(Tzone.objects.filter(enabled=True).values_list("utc", "alias")),
        # try:
    #     timezone = forms.CharField(
    #         label=_("Timezone"),
    #         strip=True,
    #         widget=forms.Select(attrs={'class': 'form-control form-control-sm select2'}, choices=Tzone.objects.filter(enabled=True).values_list("utc", "alias"))
    #     )
    # except ProgrammingError:
    #     timezone = forms.CharField(
    #         label=_("Timezone"),
    #         strip=True,
    #         widget=forms.Select(attrs={'class': 'form-control form-control-sm select2'}, choices=[])
    #     )

    password1 = forms.CharField(
        empty_value="33",
        label=_(""),
        strip=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'Password'}),
        help_text=password_validation.password_validators_help_text_html(),
    )
    password2 = forms.CharField(
        required=False,
        label=_(""),
        widget=forms.PasswordInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'Confirm Password'}),
        strip=False,
        help_text=_("Enter the same password as before, for verification."),
    )

    class Meta:
        model = UserModel
        # fields = ('first_name', 'last_name', 'email', 'timezone')
        fields = ('email', 'first_name', 'last_name', 'phone', 'password1', 'password2', 'is_active', 'is_manager', "groups", "user_permissions", "blacklist_permissions")
        # exclude = ('password1', 'password2')
        widgets = {
            # 'timezone': forms.Select(attrs={'class': 'form-control select2', }),
            'first_name': forms.TextInput(attrs={'class': 'form-control m-input', 'placeholder': 'First name', }),
            'last_name': forms.TextInput(attrs={'class': 'form-control m-input', 'placeholder': 'Last name', }),
            'email': forms.EmailInput(attrs={'class': 'form-control m-input', 'placeholder': 'Email'}),

            'is_active': forms.Select(attrs={'class': 'form-control select2', }),
            #'groups': forms.Select(attrs={'class': 'form-control select2', }),
            #"is_manager": models.BooleanField()
            # 'password1': forms.PasswordInput(attrs={'class': 'form-control', 'style': 'width: 100%', 'data-options': "label:'Password:', required:true"}),
            # 'password2': forms.PasswordInput(attrs={'class': 'form-control', 'style': 'width: 100%', 'data-options': "label:'Confirm Password:', required:true"}),
        }

    # Add some custom validation to our file field
    def clean_first_name(self):
        first_name = self.cleaned_data.get('first_name', None)
        if first_name:
            return first_name
        else:
            raise ValidationError("This field is required")

    def clean_last_name(self):
        last_name = self.cleaned_data.get('last_name', None)
        if last_name:
            return last_name
        else:
            raise ValidationError("This field is required")

    # def clean_password2(self):
    #     password1 = self.cleaned_data.get("password1")
    #     password2 = self.cleaned_data.get("password2")
    #     if password1 and password2 and password1 != password2:
    #         raise forms.ValidationError(
    #             self.error_messages['password_mismatch'],
    #             code='password_mismatch',
    #         )
    #     return password2

    # def _post_clean(self):
    #     super()._post_clean()
    #     # Validate the password after self.instance is updated with form data by super().
    #     # password = self.cleaned_data.get('password2')
    #     if self.instance.created is None:
    #         password = self.instance.password_generator(size=10)
    #     else:
    #         password = self.cleaned_data.get('password2')
    #     if password:
    #         try:
    #             password_validation.validate_password(password, self.instance)
    #         except forms.ValidationError as error:
    #             self.add_error('password2', error)

    def save(self, commit=True):
        if self.instance._state.adding and getattr(settings, 'AUTH_AUTO_GENERATE_PASSWORD_ON_CREATE', False) and \
                (not (self.cleaned_data.get("password1") and self.cleaned_data.get("password2"))):
            self.cleaned_data["password1"] = self.instance.password_generator(size=10)
            self.cleaned_data["password2"] = self.cleaned_data["password1"]
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class UserUpdateForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super(UserUpdateForm, self).__init__(*args, **kwargs)  # populates the post
        if self.instance.date_joined:
            self.fields['email'].widget.attrs['readonly'] = True
            if not (self.request and (self.request.user.is_manager or self.request.user.is_superuser)):
                del self.fields["is_manager"]
        else:
            del self.fields["is_manager"]
        if self.request:
            if self.request.user.user_profile.company.name == settings.COY_NAME and \
                    (self.request.user.has_perm('auth.change_group') or self.request.user.has_perm('auth.view_group')):
                self.fields['groups'].queryset = CustomGroup.objects.filter(
                    company = self.request.user.company
                )
                self.fields['groups'].widget.attrs = {'class': 'form-control select2'}
            elif self.request.user.is_manager or (self.request.user.has_perm('auth.change_group') or self.request.user.has_perm('auth.view_group')):
                self.fields['groups'].queryset = CustomGroup.objects.filter(
                    company = self.request.user.company
                )
                self.fields['groups'].widget.attrs = {'class': 'form-control select2'}
            else:
                del self.fields["groups"]

            if self.request.user.company.id == DEFAULT_COMPANY_ID:
                self.fields['is_manager'].label = "Savvybiz Admin"
                del self.fields['user_permissions']
                del self.fields['blacklist_permissions']

            if not self.request.user.is_manager:
                self.fields['is_manager'].widget.attrs['disabled'] = True

            # if self.request.user.is_superuser:
            #     self.fields['user_permissions'].queryset = Permission.objects.all()
            # elif request.user.user_profile.company.name == settings.COY_NAME and (self.request.user.has_perm('auth.change_permission') or self.request.user.has_perm('auth.view_permission')):
            #     self.fields['user_permissions'].queryset = Permission.objects.filter(user_set__in=[self.request.user])
            # else:
            #     del self.fields['user_permissions']
        else:
            del self.fields["groups"]

    def clean_first_name(self):
        first_name = self.cleaned_data.get('first_name', None)
        if first_name:
            return first_name
        else:
            raise ValidationError("This field is required")

    def clean_last_name(self):
        last_name = self.cleaned_data.get('last_name', None)
        if last_name:
            return last_name
        else:
            raise ValidationError("This field is required")

    class Meta:
        model = UserModel
        fields = ('email', 'first_name', 'last_name', 'phone', 'is_active', "is_manager", 'groups',
                  'user_permissions', 'blacklist_permissions')
        #exclude = ('user_permissions', )
        try:
            # from core.models import Timezone
            widgets = {
                # 'first_name': forms.TextInput(attrs={'class': 'form-control m-input', 'placeholder': 'First name', }),
                # 'last_name': forms.TextInput(attrs={'class': 'form-control m-input', 'placeholder': 'Last name', }),
                # 'timezone': forms.Select(choices=list(Timezone.objects.filter(enabled=True).values_list("utc", "alias")), attrs={'class': 'form-control select2', }),
            }
        except Exception:
            pass


class UserAdminUpdateForm(UserChangeForm):

    class Meta:
        try:
            from core.models import Timezone
            widgets = {
                'timezone': forms.Select(choices=list(Timezone.objects.filter(enabled=True).values_list("utc", "alias")), attrs={'class': 'form-control select2', }),
            }
        except Exception:
            pass


class SavvybizGroupForm(forms.ModelForm):
    class Meta:
        model = CustomGroup
        fields = ('name', 'permissions', )