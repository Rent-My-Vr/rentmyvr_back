from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils.safestring import mark_safe

from auths.overrides.auth_backend import SDBackend
from auths_api.serializers import UserSerializer

UserModel = get_user_model()


def user_can_authenticate(user):
    """
    Reject users with is_active=False. Custom user models that don't have
    that attribute are allowed.
    """
    is_active = getattr(user, 'is_active', None)
    return is_active or is_active is None


def authenticate(username=None, password=None, **kwargs):
    """
        API: Authenticates against settings.AUTH_USER_MODEL.
    """
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
            msg = f"""Hi {user.first_name}, to proceed please check your email for Account Activation.
                        <br>👉 <a href="{reverse('auths:send-mail-activation', args=(user.pk,))}" class="text-primary" title="Resend Activation Link">Resend Activation link</a> 👈"""
            if hasattr(user, "email_verified"):
                if getattr(settings, 'AUTH_ACTIVATION_REQUIRED', True) and not user.email_verified and not user.is_superuser:
                    return {"msg": msg, "title": 'Account Activation Required!'}
            elif getattr(settings, 'AUTH_ACTIVATION_REQUIRED', True) and not user.is_active and not user.last_login:
                return {"msg": mark_safe(msg), "title": 'Authentication Failed'}

            if user_can_authenticate(user):
                # TODO: Call this as Async Task
                # for queue in Queue.get_profile_queues(user.user_profile):
                #     is_valid = check_email_connection(queue)
                #     if not is_valid:
                #         msg = f"""Failed accessing <strong>{queue.channel}</strong> <br>
                #                     <div class='d-flex justify-content-around'>
                #                         <button class='btn btn-link clear' style='text-decoration: none;'>❌ Dismiss</button>
                #                         <button class='btn btn-link disable-email' style='text-decoration: none;' data-queue-id='{queue.pk}'>✔️ Do not show again</button>
                #                     </div>"""
                #     else:
                #         break

                return user

        else:
            if hasattr(user, 'failed_attempts'):
                user.failed_attempts = user.failed_attempts + 1
                user.save()
            if hasattr(user, 'last_login') and hasattr(user, 'email_verified'):
                if not user.is_active and user.last_login is None and not user.email_verified:
                    msg = f"""Hello {user}, please make sure you type the {UserModel.USERNAME_FIELD} and password 
                                correctly. Default password should be part of your activation email. 
                                <a href='{reverse('auths:send-mail-activation', args=(user.pk,))}' title='Click to Generate Activation Link'><u>Regenerate New Email</u></a>."""
                    return {"msg": mark_safe(msg), "title": 'Authentication Failed'}

    return {"msg": "Authentication failed, make sure `email` and `password` are correct",
            "title": "Authentication Failed"}


# class ObtainAuthToken(APIView):
#     throttle_classes = ()
#     permission_classes = ()
#     parser_classes = (parsers.FormParser, parsers.MultiPartParser, parsers.JSONParser,)
#     renderer_classes = (renderers.JSONRenderer,)
#     serializer_class = AuthTokenSerializer
#     if coreapi is not None and coreschema is not None:
#         schema = ManualSchema(
#             fields=[
#                 coreapi.Field(
#                     name="username",
#                     required=True,
#                     location='form',
#                     schema=coreschema.String(
#                         title="Username",
#                         description="Valid username for authentication",
#                     ),
#                 ),
#                 coreapi.Field(
#                     name="password",
#                     required=True,
#                     location='form',
#                     schema=coreschema.String(
#                         title="Password",
#                         description="Valid password for authentication",
#                     ),
#                 ),
#             ],
#             encoding="application/json",
#         )
#
#     def post(self, request, *args, **kwargs):
#         serializer = self.serializer_class(data=request.data,
#                                            context={'request': request})
#         serializer.is_valid(raise_exception=True)
#         user = serializer.validated_data['user']
#         token, created = Token.objects.get_or_create(user=user)
#         return Response({'token': token.key})



def get_first_matching_attr(obj, *attrs, default=None):
    for attr in attrs:
        if hasattr(obj, attr):
            return getattr(obj, attr)

    return default


def get_error_message(exc) -> str:
    if hasattr(exc, 'message_dict'):
        return exc.message_dict
    error_msg = get_first_matching_attr(exc, 'message', 'messages')

    if isinstance(error_msg, list):
        error_msg = ', '.join(error_msg)

    if error_msg is None:
        error_msg = str(exc)

    return error_msg
