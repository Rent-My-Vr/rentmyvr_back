import json
from lib2to3.pgen2 import token
import logging
import uuid

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login as auth_login, update_session_auth_hash, login, get_user, logout, authenticate
from django.contrib.auth.decorators import permission_required, login_required
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.views import LoginView as DjangoLoginView, LogoutView as DjangoLogoutView, PasswordChangeView as DjangoPasswordChangeView, \
PasswordChangeDoneView as DjangoPasswordChangeDoneView, PasswordResetView as DjangoPasswordResetView, PasswordResetDoneView as DjangoPasswordResetDoneView, \
PasswordResetConfirmView as DjangoPasswordResetConfirmView, PasswordResetCompleteView as DjangoPasswordResetCompleteView, PasswordContextMixin as DjangoPasswordContextMixin
from django.contrib.sites.shortcuts import get_current_site
from django.core.cache import cache
from django.http import JsonResponse, HttpResponseRedirect, HttpResponseForbidden
from django.http.response import Http404
from django.shortcuts import redirect, render, get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import FormView
from django.views.decorators.csrf import csrf_exempt
from rest_framework import parsers, renderers
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.serializers import AuthTokenSerializer
from rest_framework.response import Response
from rest_framework.views import APIView

from auths_api.serializers import UserSerializer
from auths.forms import SignupForm, UserUpdateForm, LoginForm, PasswordChangeForm, PasswordResetForm, SetPasswordForm
from auths.utils import account_activation_token
from django.utils.translation import gettext as _
from django.contrib.auth import SESSION_KEY, BACKEND_SESSION_KEY
from django.core.cache import cache
from django.contrib.auth.tokens import PasswordResetTokenGenerator

from .utils import get_domain, random_with_N_digits
UserModel = get_user_model()


log = logging.getLogger(f"{__package__}.*")
log.setLevel(settings.LOGGING_LEVEL)


COY_NAME = getattr(settings, "COY_NAME", "SavvyBiz")


@permission_required("auths.add_user")
def user_create(request, ):
    from core.forms import ProfileForm
    if request.method == 'POST':
        form = SignupForm(request.POST, request=request, prefix="user")
        profile_form = ProfileForm(
            request.POST, request=request, prefix='profile')
        print(form.is_valid(), profile_form.is_valid(), form.errors)
        if form.is_valid() and profile_form.is_valid():
            user = form.save(commit=False)
            validate_password(user.password, user)
            user.is_active = not getattr(
                settings, 'AUTH_ACTIVATION_REQUIRED', True)
            user.force_password_change = True
            user.save()

            profile = profile_form.save(commit=False)

            profile.update_tracked(request.user)
            profile.user = user
            profile.save()
            profile_form.save_m2m()
            # if profile.user.is_manager:
            #     profile.departments.add(
            #         *list(Department.objects.all().values_list('pk', flat=True)))
            #     profile.portfolios.add(
            #         *list(Portfolio.objects.all().values_list('pk', flat=True)))

            if getattr(settings, 'AUTH_ACTIVATION_REQUIRED', True):
                domain = f"{request.scheme}://{get_current_site(request).domain}"
                path = reverse('auths:activate', kwargs={'uuid': str(
                    user.pk), 'token': PasswordResetTokenGenerator().make_token(user)})

                html_message = render_to_string('auths/mail_templates/activation.html', {
                    'mail_header': "Account Activation",
                    'project_title': settings.PROJECT_NAME.title(),
                    'first_name': user.first_name,
                    'validation_url': f"{domain}{path}",
                    'domain': domain,
                })
                log.info(f"*******{user.email} Activation link is {domain}{path}")

                sendmail_outcome = user.email_user("Account Activation", html_message)
                log.info(f"Outcome of emailing: {sendmail_outcome}")
                msg = f"Registration Successful and Account activation link sent to {user.email}'"
                if not request.is_ajax():
                    messages.success(request, msg)
            else:
                msg = "Registration Successfully Completed"
                if not request.is_ajax():
                    messages.success(request, msg)
            # from letter.celery import app
            # app.send_task("core.sendMail", ["Account Activation", "", [user.email], False, html_message, "SMTP", 'default'])
            if request.is_ajax():
                return JsonResponse({"msg": msg, "type": "success", "data": {"pk": user.pk}}, safe=True)
            else:
                return sign_up_acknowledge(request, user.first_name)
        else:
            msg = "Please check you have filled the form correctly"
            if request.is_ajax():
                return JsonResponse({"msg": msg, "type": "info", "data": json.dumps(form.errors)}, safe=True)
            else:
                messages.warning(request, msg, "Error Response!!!")

    else:
        form = SignupForm(prefix="user", request=request)
        profile_form = ProfileForm(
            prefix='profile', request=request)

    template = "auths/user-form.html" if request.is_ajax() else "auths/user-add.html"
    return render(request, template, context={'form': form,
                                              'coy_name': COY_NAME,
                                              "profile_form": profile_form,
                                              "is_add": True})


@permission_required("auths.change_user")
def user_update(request, pk):
    from core.forms import ProfileForm
    user = UserModel.objects.get(pk=pk)

    # return profile_create(request, get_object_or_404(Profile, pk=pk, company=request.user.company))

    if request.method == 'POST':
        form = UserUpdateForm(request.POST, request.FILES, request=request, instance=user, prefix="user")
        profile_form = ProfileForm(request.POST, request=request, prefix='profile', instance=user.user_profile)

        print("user_profile", user.user_profile,
              user.user_profile.departments.all())

        if form.is_valid() and profile_form.is_valid():
            user = form.save(commit=False)
            user.save()
            form.save_m2m()

            profile = profile_form.save(commit=False)
            profile.update_tracked(request.user)
            profile.user = user
            profile.save()
            profile_form.save_m2m()
            # if profile.user.is_manager:
            #     profile.departments.add(*list(Department.objects.all().values_list('pk', flat=True)))
            #     profile.portfolios.add(*list(Portfolio.objects.all().values_list('pk', flat=True)))

            msg = "User Updated Successfully Completed"
            if request.is_ajax():
                return JsonResponse({"msg": msg, "type": "success", "data": {"pk": user.pk}})
            else:
                messages.success(request, msg)
                return redirect(reverse("auths:user-edit", kwargs={"pk": pk}))
        else:
            msg = "Please check you have filled the form correctly"
            if request.is_ajax():
                return JsonResponse({"msg": msg, "type": "info", "data": json.dumps(form.errors)}, safe=True)
            else:
                messages.warning(request, msg, "Error Response!!!")
    else:
        form = UserUpdateForm(instance=user, request=request, prefix="user")
        profile_form = ProfileForm(
            request=request, prefix='profile', instance=user.user_profile)

    template = "auths/user-form.html" if request.is_ajax() else "auths/user-add.html"
    return render(request, template, context={
        'form': form, 'coy_name': COY_NAME, "is_add": False,
        'profile_form': profile_form
    })


def test(request):

    return render(request, "auths/login-2.html", context={'coy_name': COY_NAME})


def accessdenied(request):
    return render(request, "auths/accessdenied.html")


@login_required
def current_user(request):
    current_user = request.user
    return JsonResponse({'type': 'success', 'user': UserSerializer(current_user).data})


@login_required
@permission_required("auths.delete_user")
def user_delete(request, pk):
    item = get_object_or_404(UserModel, pk=pk)
    item.delete()

    msg = f"{UserModel._meta.verbose_name} successfully deleted"
    if request.is_ajax():
        return JsonResponse({"msg": msg, "type": "success"}, safe=True)
    else:
        messages.warning(request, msg, "Success Response")
    return redirect(UserModel.get_list_url())


@login_required
@permission_required("auths.view_user")
def user_details(request, pk):
    from core.models import Profile
    item = get_object_or_404(UserModel, pk=pk)
    if item != request.user:
        if not request.user.user_profile.company.name == settings.COY_NAME:
            return HttpResponseForbidden()
    profile = Profile.objects.filter(user=item).first()
    if profile:
        from core.utils import PAGE_LENGTH
        from communication.models import Queue
        return render(request, "core/profile-detail.html", {"profile": profile, "coy_name": settings.COY_NAME,
                                                            "queues": Queue.get_profile_queues(profile),
                                                            "pageLength": PAGE_LENGTH})
    else:
        return redirect(item.get_admin_url())


def sign_up(request):
    if request.method == 'POST':
        form = SignupForm(request.POST, request=request)
        if form.is_valid():
            user = form.save(commit=False)
            validate_password(user.password, user)
            user.is_active = not getattr(settings, 'AUTH_ACTIVATION_REQUIRED', True)
            user.save()

            if getattr(settings, 'AUTH_ACTIVATION_REQUIRED', True):
                domain = f"{request.scheme}://{get_current_site(request).domain}"
                path = reverse('auths:activate', kwargs={'uuid': str(
                    user.pk), 'token': account_activation_token.make_token(user)})

                html_message = render_to_string('auths/mail_templates/activation.html', {
                    'mail_header': "Account Activation",
                    'project_title': settings.PROJECT_NAME.title(),
                    'first_name': user.first_name,
                    'validation_url': f"{domain}{path}",
                    'domain': domain,
                })
                log.info(f"*******{user.email} Activation link is {domain}{path}")

                sendmail_outcome = user.email_user(
                    "Account Activation", html_message)
                log.info(f"Outcome of emailing: {sendmail_outcome}")
                msg = f"Registration Successful and Account activation link sent to {user.email}'"
                if not request.POST.get("ajax", False):
                    messages.success(request, msg)
            else:
                msg = "Registration Successfully Completed"
                if not request.POST.get("ajax", False):
                    messages.success(request, msg)
            # from letter.celery import app
            # app.send_task("core.sendMail", ["Account Activation", "", [user.email], False, html_message, "SMTP", 'default'])
            if request.POST.get("ajax", False):
                return JsonResponse({"msg": msg, "type": "success"})
            else:
                return sign_up_acknowledge(request, user.first_name)
        log.info(json.dumps(form.errors))
        return render(request, "auths/sign-up.html", context={'form': form})
    else:
        form = SignupForm(request=request)
    return render(request, "auths/sign-up.html", context={'form': form, 'coy_name': COY_NAME})


def sign_up_acknowledge(request, first_name):

    return render(request, "auths/sign-up-acknowledge.html", context={'first_name': first_name, 'coy_name': COY_NAME})


def activation_send(request, uidb64):
    try:
        user = UserModel.objects.get(pk=uidb64)
        passw = user.password_generator()
        user.set_password(passw)

        # user.send_activation_link("{}://{}".format(request.scheme, request.META.get('HTTP_HOST', 'savvybiz.com')),
        #                           password=passw)
        
        user.send_password_reset_link(f"{get_domain(request)}")
        user.save()
        messages.success(request, f'Account activation link successfully sent to "{user.email}"',
                         extra_tags="Activation Link Sent")
        return redirect('auths:login')
    except(TypeError, ValueError, OverflowError, UserModel.DoesNotExist) as err:
        log.error(err)
        messages.error(request, 'Invalid User')
        return redirect('auths:login')


def activate(request, uuid, token):
    try:
        # uid = force_text(urlsafe_base64_decode(uidb64))
        # user = UserModel.objects.get(pk=force_text(urlsafe_base64_decode(uuid)))
        user = UserModel.objects.get(pk=uuid)
    except(TypeError, ValueError, OverflowError, UserModel.DoesNotExist) as err:
        log.error(err)
        user = None

    if user is not None:
        if getattr(settings, "AUTH_ACTIVATION_REQUIRE_PROFILE", False):
            from core.models import Profile
            member = Profile.objects.filter(user=user).first()
            if member and account_activation_token.check_token(user, token):
                user.is_active = True
                user.save()
                messages.success(
                    request, 'Account Activated Successfully, Please Login to Continue')
                # login(request, user)
                return redirect('auths:login')
            else:
                messages.warning(request, 'Activation link is invalid!')
                # TODO: Redirect to a page dedicated for this
                return redirect('core:index')
        else:
            if account_activation_token.check_token(user, token):
                user.is_active = True
                if hasattr(user, "email_verified"):
                    user.email_verified = True
                user.save()

                # Backend required by Social Auto. I disabled login auto login cos the code doesn't expire after use
                # from django.contrib.auth import login as auth_login
                # auth_login(request, user, backend=getattr(settings, 'DEFAULT_BACKEND', 'django.contrib.auth.backends.ModelBackend'))
                # messages.add_message(request, messages.SUCCESS, 'Account Activated Successfully')
                messages.success(request, 'Account Activated Successfully, Please Login to Continue',
                                 extra_tags='Account Activated Successfully')
                return redirect('auths:login')
                # return redirect('core:dashboard')
            else:
                messages.warning(request, 'Activation link is invalid!')
                # TODO: Redirect to a page dedicated for this
                return redirect('core:index')
    else:
        messages.warning(request, 'Activation link is invalid!')
        # TODO: Redirect to a page dedicated for this
        return redirect('core:index')


def activation_token_send(request, channel, email):
    """
        Accepts User ID as uidb64
        Channel in form of email, sms

        Generate and sends the Token via the specified channel, then returns a 'session key'
        that is only valid with this current session key
    """
    try:
        token_length = settings.AUTH_TOKEN_LENGTH
        user = UserModel.objects.get(email=email)
        session_key = user.send_access_token(token_length, channel)
        if isinstance(session_key, int):
            return JsonResponse({"msg": f'Authentication token has been sent to you via {channel}', "type": "success", "session_key": session_key}, safe=True)
        msg = "Something went wrong"
    except(TypeError, ValueError, OverflowError, UserModel.DoesNotExist) as err:
        log.error(err)
        msg = 'Invalid User'
    
    return JsonResponse({"msg": msg, "type": "error"}, safe=True)


@csrf_exempt
def verify_token(request, session_key):
    if request.method == 'POST':
        data = json.loads(request.body.decode("utf-8"))
        email = data.get('email', None)
        token = data.get('token', None)
        if email and token:
            try:
                user = UserModel.objects.get(email=email)
                print(f"Searching:   access_token_{user.id}_{session_key}")
                
                data = cache.get(f"access_token_{user.id}_{session_key}")

                u = UserModel.objects.get(id=data['id'])
                if data and isinstance(data, dict) and int(data['token']) == int(token) and u.email == email:
                    cache.delete_pattern(f"access_token_{user.id}_*")
                    if data["action"] == "Password Rest":
                        session_key = random_with_N_digits(12)
                        token = uuid.uuid4().hex
                        cache.set(f"access_token_authorised_{user.id}_{session_key}", 
                        {"action": data['action'], "id": user.id, "token": token}, timeout=60*10)
                        return JsonResponse({"msg": f'Password Rest Authorised', "type": "success", "session_key": session_key, "token": token}, safe=True)
                        
            except UserModel.DoesNotExist:
                msg = "Something went wrong"
        msg = "Invalid"
    else:
        msg = "Method not allowed"
    return JsonResponse({"msg": msg, "type": "error"}, safe=True)


@csrf_exempt
def password_reset_by_token(request, session_key):
    if request.method == 'POST':
        data = json.loads(request.body.decode("utf-8"))
        email = data.get('email', None)
        token = data.get('token', None)
        password = data.get('password', None)
        if email and token and password:
            try:
                user = UserModel.objects.get(email=email)
                data = cache.get(f"access_token_authorised_{user.id}_{session_key}")

                u = UserModel.objects.get(id=data['id'])
                if data and isinstance(data, dict) and data['token'] == token and u.email == email:
                    cache.delete_pattern(f"access_token_authorised_{user.id}_*")
                    if data["action"] == "Password Rest":
                        user.set_password(password)
                        user.save()
                        return JsonResponse({"msg": f'Password Rest Successful', "type": "success"}, safe=True)
            except Exception:
                msg = "Something went wrong"
        msg = "Invalid"
    else:
        msg = "Method not allowed"
    return JsonResponse({"msg": msg, "type": "error"}, safe=True)


def email_confirmation_sent(request):
    messages.success(request, 'Email sent to '.format(
        request.GET.get("email", "")))
    return render(request, "auths/email-confirmation-sent.html", context={'email': request.GET.get("email", "")})


class LoginView(DjangoLoginView):

    authentication_form = LoginForm
    template_name = 'auths/login.html'

    def form_valid(self, form):
        """Security check complete. Log the user in."""

        if not self.request.POST.get('remember_me', False):
            self.request.session.set_expiry(0)

        # TODO: Make sure the Timezone is pulling from the right list
        auth_login(self.request, form.get_user())

        if self.request.user.timezone is None and self.request.POST.get("timezone", None):
            try:
                from core.models import Timezone
                timezone = Timezone.objects.filter(utc=self.request.POST.get("timezone", None)).first()
                if timezone:
                    self.request.user.timezone = timezone
                    self.request.user.save()
            except ImportError:
                pass
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        if self.request.user.force_password_change:
            # this is just to clear off any previous messages in the request
            list(messages.get_messages(self.request))
            token = str(timezone.now().timestamp()).replace(".", "")
            cache.set(f"password_change_{self.request.user.email}", token, timeout=60*5)
            log.warning(reverse('auths:password_change_forced', kwargs={"token": token}))
            return reverse_lazy('auths:password_change_forced', kwargs={"token": token})
        return super(LoginView, self).get_success_url()

    def get_redirect_url(self):
        return super(LoginView, self).get_redirect_url()


class LogoutView(DjangoLogoutView):

    next_page = settings.LOGOUT_REDIRECT_URL


class PasswordChangeView(DjangoPasswordChangeView):

    form_class = PasswordChangeForm
    success_url = reverse_lazy('auths:password_change_done')
    template_name = 'auths/password_change_form.html'


class PasswordChangeDoneView(DjangoPasswordChangeDoneView):

    template_name = 'auths/password_change_done.html'


class PasswordResetView(DjangoPasswordResetView):

    success_url = reverse_lazy('auths:password_reset_done')
    form_class = PasswordResetForm
    html_email_template_name = 'auths/mail_templates/password_reset_email_html.html'
    email_template_name = 'auths/mail_templates/password_reset_email.html'
    template_name = 'auths/password_reset_form.html'
    token_generator = account_activation_token


class PasswordResetDoneView(DjangoPasswordResetDoneView):

    template_name = 'auths/password_reset_done.html'


class PasswordResetConfirmView(DjangoPasswordResetConfirmView):

    form_class = SetPasswordForm
    success_url = reverse_lazy('auths:password_reset_complete')
    template_name = 'auths/password_reset_confirm.html'
    token_generator = account_activation_token


class PasswordResetCompleteView(DjangoPasswordResetCompleteView):

    template_name = 'auths/password_reset_complete.html'


class PasswordChangeForcedView(DjangoPasswordContextMixin, FormView):
    form_class = SetPasswordForm
    success_url = reverse_lazy('auths:password_change_done')
    template_name = 'auths/password_change_form.html'
    title = _('Password change')

    # @method_decorator(sensitive_post_parameters())
    # @method_decorator(never_cache)
    # def dispatch(self, *args, **kwargs):
    #     assert 'token' in kwargs
    #
    #     token = str(kwargs.get('token', None))
    #     user = get_user(self.request)
    #     if token and type(user).__name__ == UserModel.__name__ and cache.get("password_change_{}".format(self.request.user.email)) == token:
    #         # logout(self.request)
    #         cache.set("password_change_{}".format(token), True, timeout=60 * 5)
    #         messages.warning(self.request, "Hello {}, you are required to change your password before you can proceed".format(user.first_name))
    #         cache.expire("password_change_{}".format(self.request.user.email), 0)
    #     else:
    #         messages.warning(self.request, "Please Login")
    #         return HttpResponseRedirect(reverse('auths:login'))
    #
    #     # Display the "Password reset unsuccessful" page.
    #     return self.render_to_response(self.get_context_data())

    def get(self, request, *args, **kwargs):
        token = str(kwargs.get('token', None))
        user = get_user(self.request)
        if token and type(user).__name__ == UserModel.__name__ and cache.get("password_change_{}".format(self.request.user.email)) == token:
            logout(self.request)
            messages.warning(
                self.request, "Hello {}, you are required to change your password before you can proceed".format(user.first_name))
            cache.set("password_change_{}".format(
                token), user.email, timeout=60 * 5)
            cache.expire("password_change_{}".format(user.email), 0)
            return render(request, self.template_name, self.get_context_data())
        else:
            messages.warning(self.request, "Please Login")
            return HttpResponseRedirect(reverse('auths:login'))

    def post(self, request, *args, **kwargs):
        token = str(kwargs.get('token', None))
        email = cache.get("password_change_{}".format(token))
        if email:
            user = UserModel.objects.filter(email=email).first()
            login(self.request, user,
                  backend='django.contrib.auth.backends.ModelBackend')
            form = self.form_class(request.POST)
            # self.kwargs['user'] = UserModel.objects.filter(email=email).first()

            if user and user.force_password_change and form.user.get('new_password1') and form.user.get('new_password2'):

                if token and cache.get("password_change_{}".format(token), None):
                    cache.expire("password_change_{}".format(token), 0)
                    messages.success(
                        self.request, "Password successfully changed, please login to continue")

                    password = form.user.get('new_password1')
                    user.set_password(password)
                    user.force_password_change = False
                    user.last_password_change = timezone.now()
                    user.save()

                    return HttpResponseRedirect(reverse("core:dashboard"))
                else:
                    logout(self.request)
                    messages.warning(self.request, "Please Login")
                    return HttpResponseRedirect(reverse('auths:login'))
            else:
                logout(self.request)
                for key in form.error_messages.keys():
                    messages.warning(request, form.error_messages[key], " ".join(
                        key.split("_")).title())
                return self.render_to_response(self.get_context_data(form=form))

    def get_context_data(self, **kwargs):
        context = super(PasswordChangeForcedView,
                        self).get_context_data(**kwargs)
        context['token'] = self.kwargs['token']
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.save()
        # Updating the password logs out all other sessions for the user
        # except the current one.
        update_session_auth_hash(self.request, form.user)
        return super().form_valid(form)


# @api_view(['POST'])
# def get_token(request):
#     username = request.POST.get('username')
#     password = request.POST.get('password')
#     user = authenticate(username=username, password=password)
#     if user is not None:
#         if user.is_active:
#             token, created = Token.objects.get_or_create(user=user)
#             request.session['auth-token'] = token.key
#             return redirect('core:home', request)
#     return redirect(settings.LOGIN_URL)

# TODO: Remove this from here and make this ONLY accessible unto the provision of Username & Password
class TokenView(APIView):
    throttle_classes = ()
    permission_classes = ()
    parser_classes = (parsers.FormParser,
                      parsers.MultiPartParser, parsers.JSONParser,)
    renderer_classes = (renderers.JSONRenderer, renderers.BrowsableAPIRenderer)
    serializer_class = AuthTokenSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        return Response({'token': token.key})


get_token = TokenView.as_view()


# TODO: Remove and redirect to the actual Login View
@login_required
def login_as_user(request, user_id):
    userobj = authenticate(request=request, su=True, user_id=user_id)
    if not userobj:
        raise Http404("User not found")

    exit_users_pk = request.session.get("exit_users_pk", default=[])
    exit_users_pk.append(
        (request.session[SESSION_KEY], request.session[BACKEND_SESSION_KEY]))

    auth_login(request, userobj)

    request.session["exit_users_pk"] = exit_users_pk

    return HttpResponseRedirect(reverse("core:dashboard"))


def su_logout(request):
    exit_users_pk = request.session.get("exit_users_pk", default=[])
    if not exit_users_pk:
        return HttpResponseRedirect(reverse("core:dashboard"))

    user_id, backend = exit_users_pk.pop()

    userobj = get_object_or_404(UserModel, pk=user_id)
    userobj.backend = backend

    # if not custom_login_action(request, userobj):
    auth_login(request, userobj)
    request.session["exit_users_pk"] = exit_users_pk

    return HttpResponseRedirect(reverse("core:dashboard"))
