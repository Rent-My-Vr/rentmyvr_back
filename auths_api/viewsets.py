from email import message
from inspect import stack
import logging
from pickle import NONE
from unittest import result

from django.conf import settings
from django.contrib.auth import get_user_model, logout
from django.core.exceptions import ImproperlyConfigured
from django.core.paginator import Paginator
from django.db.models import Q
from django.core.cache import cache
from django.http import JsonResponse
from django.utils.encoding import force_str, force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.urls import reverse, reverse_lazy
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import Permission, AnonymousUser
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

from auths.utils import account_activation_token, get_domain

from rest_framework import viewsets, status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated, AllowAny

from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.facebook.views import FacebookOAuth2Adapter
from allauth.socialaccount.providers.apple.views import AppleOAuth2Adapter
from allauth.socialaccount.providers.apple.client import AppleOAuth2Client
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from allauth.account.adapter import get_adapter

from dj_rest_auth.registration.views import SocialLoginView, SocialLoginSerializer, SocialConnectView
from dj_rest_auth.views import LoginView as DJ_LoginView,  LogoutView as DJ_LogoutView, PasswordResetView as DJ_PasswordResetView, PasswordResetConfirmView as DJ_PasswordResetConfirmView
from dj_rest_auth.app_settings import (LoginSerializer, PasswordChangeSerializer)
from dj_rest_auth.models import get_token_model

from auths.models import CustomGroup
from auths.custom_exception import ActivationRequired

from auths_api import serializers
from auths_api.serializers import SavvybizGroupSerializer, PermissionSerializer, UserPasswordChangeSerializer, UserSerializer, PasswordResetSerializer as MyPasswordResetSerializer, PasswordResetConfirmSerializer as MyPasswordResetConfirmSerializer, PasswordTokenConfirmSerializer as MyPasswordTokenConfirmSerializer
from auths_api.utils import authenticate

from sesame.utils import get_token


if 'allauth' in settings.INSTALLED_APPS:
    from allauth.account import app_settings
    from allauth.account.adapter import get_adapter
    from allauth.account.forms import default_token_generator as token_generator
    from allauth.account.utils import (user_pk_to_url_str, user_username)
    from allauth.utils import build_absolute_uri

from .mixins import ApiErrorsMixin, PublicApiMixin, ApiAuthMixin
from core.custom_permission import IsAuthenticatedOrCreate


# https://stackoverflow.com/questions/53276279/how-to-add-tokenauthentication-authentication-classes-to-django-fbv

log = logging.getLogger(f"{__package__}.*")
log.setLevel(settings.LOGGING_LEVEL)

UserModel = get_user_model()


class SavvybizGroupViewSet(viewsets.ViewSet):
    permission_classes = (IsAuthenticated, )
    authentication_classes = (TokenAuthentication,)

    # @method_decorator(needed_permissions("auth.view_group", raise_exception=True))
    def list(self, request, *args, **kwargs):
        request.user.company.clone_groups()
        request_data = request.GET

        company = request_data.get("company", "").lower()
        name = request_data.get("name", "").lower()
        filter_query = request_data.get('_global', "").lower()
        page_number = int(request_data.get('page', '0')) + 1
        page_size = int(request_data.get('page_size', '20'))
        sort_id = request_data.get("sort_id", "name").lower()
        print(sort_id)
        sort_desc = bool(request_data.get('sort_desc', 'true') == 'true')

        items = CustomGroup.objects.filter(
            company=request.user.company
        )

        if len(filter_query) > 0:
            items = items.filter(
                Q(name__icontains=filter_query)
                | Q(company__name__icontains=filter_query)
            )

        if name:
            items = items.filter(name__icontains=name)

        if company:
            items = items.filter(company__name__icontains=company)

        items = items.order_by("%s%s" % ('-' if sort_desc else '', sort_id))

        paginator = Paginator(items, page_size)
        items = paginator.get_page(page_number)

        ser = SavvybizGroupSerializer(items, many=True)
        return Response({
            "items": ser.data,
            "page": page_number,
            "page_size": page_size,
            'total_items': paginator.count,
            'total_pages': paginator.num_pages
        })

    # @method_decorator(needed_permissions("auth.view_group", raise_exception=True))
    def retrieve(self, request, pk):
        group = CustomGroup.objects.filter(pk=pk).first()
        return Response({
            'success': True,
            'data': SavvybizGroupSerializer(group).data
        })

    # @method_decorator(needed_permissions("auth.change_group", raise_exception=True))
    def update(self, request, pk):
        data = request.data
        print("Data :******", data)
        group = CustomGroup.objects.filter(id=pk).first()
        if not group:
            return Response({
                'success': False,
                'err':  "Not Found"
            })
        group.name = data.get('name')
        group.permissions.set(data.get('permissions', []))

        group.save()
        return Response({
            'success': True,
            'data': {}
        })

    # @method_decorator(needed_permissions("auth.add_group", raise_exception=True))
    def create(self, request):
        data = request.data
        name = data.get("name", "").lower()
        duplicate = CustomGroup.objects.all().filter( name=str(request.user.company.id)+name).first()
        if duplicate:
            return Response({
                'success': False,
                'msg':  "A group with the same name exists, please choose another name."
            })
        data['company_id'] = request.user.company.id
        data['updated_by_id'] = request.user.id
        permissions = data.get('permissions', [])
        del data['permissions']
        ret = CustomGroup.objects.create(**data)
        ret.permissions.set(permissions)
        ret.save()

        return Response({
            'success': True,
            'data': SavvybizGroupSerializer(ret).data
        })


class PermissionViewSet(viewsets.ViewSet):
    permission_classes = (IsAuthenticated, )
    authentication_classes = (TokenAuthentication,)

    # @method_decorator(needed_permissions("auth.view_permission", raise_exception=True))
    def list(self, request, *args, **kwargs):
        request_data = request.GET

        type = request_data.get("type", None)
        name = request_data.get('name', "").lower()
        filter_query = request_data.get('_global', "").lower()
        page_number = int(request_data.get('page', '0')) + 1
        page_size = int(request_data.get('page_size', '20'))
        sort_id = request_data.get("sort_id", "name").lower()
        # print(sort_id)
        sort_desc = bool(request_data.get('sort_desc', 'true') == 'true')

        groups = request_data.getlist("groups[]")
        print(groups)

        if not groups:
            items = Permission.objects.all()
        else:
            items = Permission.objects.filter(group__in=groups)

        # items = items.order_by("%s%s" % ('-' if sort_desc else '', sort_id))

        paginator = Paginator(items, page_size)
        items = paginator.get_page(page_number)

        ser = PermissionSerializer(items, many=True)
        return Response({
            "items": ser.data,
            "page": page_number,
            "page_size": page_size,
            'total_items': paginator.count,
            'total_pages': paginator.num_pages
        })

    # @method_decorator(needed_permissions("auth.view_permission", raise_exception=True))
    # @action(detail=False, methods=['GET'])
    # def showPermission(self, request):
    #     per = default_perms()
    #     print(per)
    #     return Response({
    #         "items": per
    #     })


class WsAuthTokenView(APIView):
    permission_classes = (IsAuthenticated, )
    
    def get(self, request, *args, **kwargs):
        token = get_token(request.user)
        return Response(token, status=status.HTTP_200_OK)

    # @action(methods=['get'], detail=False, url_path='ws/auth/token', url_name='ws-token')
    # def ws_auth_token(self, request, *args, **kwargs):


class LoginView(DJ_LoginView):
    """
    Check the credentials and return the REST Token
    if the credentials are valid and authenticated.
    Calls Django Auth login method to register User ID
    in Django session framework

    Accept the following POST parameters: username, password
    Return the REST Framework Token Object's key.
    """
    permission_classes = (AllowAny,)
    authentication_classes = (TokenAuthentication,)
    serializer_class = LoginSerializer

    # def post(self, request, *args, **kwargs):
    #     print("In POST.......")
    #     request.msg_error = None
    #     response = super().post(request, *args, **kwargs)
    #     if request.msg_error:
    #         print(request.msg_error)
    #         response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    #         response.data = request.msg_error
    #     return response

    def get_response(self):
        serializer_class = self.get_response_serializer()

        if getattr(settings, 'REST_USE_JWT', False):
            from rest_framework_simplejwt.settings import (
                api_settings as jwt_settings,
            )
            access_token_expiration = (timezone.now() + jwt_settings.ACCESS_TOKEN_LIFETIME)
            refresh_token_expiration = (timezone.now() + jwt_settings.REFRESH_TOKEN_LIFETIME)
            return_expiration_times = getattr(settings, 'JWT_AUTH_RETURN_EXPIRATION', False)

            data = {
                'user': self.user,
                'access_token': self.access_token,
                'refresh_token': self.refresh_token,
            }

            if return_expiration_times:
                data['access_token_expiration'] = access_token_expiration
                data['refresh_token_expiration'] = refresh_token_expiration

            serializer = serializer_class(
                instance=data,
                context=self.get_serializer_context(),
            )
        elif self.token:
            serializer = serializer_class(
                instance=self.token,
                context=self.get_serializer_context(),
            )
        else:
            return Response(status=status.HTTP_204_NO_CONTENT)

        data = {"key": serializer.data.get('key'), "user": UserSerializer(self.user).data}
        response = Response(data, status=status.HTTP_200_OK)
        if getattr(settings, 'REST_USE_JWT', False):
            from .jwt_auth import set_jwt_cookies
            set_jwt_cookies(response, self.access_token, self.refresh_token)
        return response

    def login(self):
        print(".......")
        super().login()
        
        # # if self.request.msg_error:
            
        # try:
        #     dd=super().login()
        #     print("...........")
        # except Exception as ex:
        # # except ActivationRequired as ex:
        #     print(ex)


class LogoutView(DJ_LogoutView):
    """
    Calls Django logout method and delete the Token object
    assigned to the current User object.

    Accepts/Returns nothing.
    """
    permission_classes = (AllowAny,)
    authentication_classes = (TokenAuthentication,)

    # @action(methods=['post'], detail=False, permission_classes=[],
    #         url_path='logout/me', url_name='logout')
    def logout(self, request):
        if isinstance(request.user, AnonymousUser):
            response = Response(
            {'detail': _('Cannot logout Anonymous User')},
                status=status.HTTP_203_NON_AUTHORITATIVE_INFORMATION,
            )
            return response
        
        return super().logout(request=request)

  
# class ActivationRequestView(viewsets.ViewSet):
class ActivationRequestView(viewsets.ViewSet, DJ_PasswordResetView):
    """
    Calls Django Auth PasswordResetForm save method.

    Accepts the following POST parameters: email
    Returns the success/fail message.
    """
    permission_classes = []
    authentication_classes = ()


    def get_serializer_class(self):
        if self.action == 'confirm_token':
            return MyPasswordTokenConfirmSerializer
        return MyPasswordResetSerializer

    def post(self, request, *args, **kwargs):
        # Create a serializer with request.data
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        print('********12 ', request.data)
        print(args, '********123 ', kwargs)
        domain = get_domain(request)
        action = UserModel.PASSWORD_RESET
        channel = request.query_params.get("channel", UserModel.EMAIL_CHANNEL)
        processing_channel = request.data.get('processing_channel', UserModel.TOKEN)
        client_callback_link = request.data.get("client_callback_link")
        session_key = serializer.save()
        
        print(' 2 -- session_key: ', session_key)
        # Return the success message with OK HTTP status
        
        # id=urlsafe_base64_decode(serializer.initial_data.get('uid', None)).decode()
        id = serializer.initial_data.get('id', None)
        uidb64 = urlsafe_base64_encode(force_bytes(id))
        session_key = serializer.initial_data.get('session_key', 565666662222)
        request_url = f"{domain}{reverse('auths_api:activation-send', args=(uidb64,))}"
        activation_url = f"{domain}{reverse('auths_api:activation-confirm-token', args=(uidb64, session_key))}"
        
        print('.....', activation_url)
        return Response({
                "message": 'Password reset e-mail has been sent.', 
                "resend_url": f"{request_url}?action={action}&channel={channel}&processing_channel={processing_channel}&client_callback_link={client_callback_link}",
                "activation_url": f"{activation_url}?action={action}&channel={channel}&processing_channel={processing_channel}&client_callback_link={client_callback_link}"
                }, status=status.HTTP_200_OK)

    @action(methods=['get'], detail=False, permission_classes=[],
            url_path='send/(?P<uidb64>[0-9A-Za-z_\-]+)', url_name='send')
    def send(self, request, uidb64):
        """
        Sends activation token to user's email/phone number

        Returns an object with the following: 
        message: Text with details,
        user: User object,
        session_key: Unique key for this particular token request,
        resend_url: The URL to re-request for this action in case user doesn't receive the sent token
        activation_url: Unique url to POST the received token
        """
        try:
            print("=======>>>>>", request.GET)
            data = request.GET.dict()
            user = UserModel.objects.get(pk=urlsafe_base64_decode(uidb64).decode())
            domain = get_domain(request)
            action = data.get("action", UserModel.VERIFY_EMAIL)
            channel = data.get("channel", UserModel.EMAIL_CHANNEL)
            processing_channel = data.get('processing_channel', UserModel.TOKEN)
            client_callback_link = data.get("client_callback_link")
            extra = {"client_callback_link": client_callback_link, "processing_channel": processing_channel}
            session_key = user.send_access_token(domain, action, channel, template='auths/mail_templates/token.html', extra=extra)
            activation_url = f"{domain}{reverse('auths_api:activation-confirm-token', args=(uidb64, session_key))}"
            request_url = f"{domain}{reverse('auths_api:activation-send', args=(uidb64,))}"

            print('Domain: ', domain, '\nAction: ', action, '\nChannel: ', channel, '\nRequest_url: ', request_url, '\nCode Base: ', settings.CODE_BASED_ACTIVATION)
            print(111)

            return Response({
                "message": f"Account activation Token successfully sent to '{user.email}'", 
                "user": UserSerializer(user).data,
                "resend_url": f'{request_url}?action={action}&channel={channel}&processing_channel={processing_channel}&client_callback_link={client_callback_link}',
                "activation_url": f"{activation_url}?action={action}&channel={channel}&processing_channel={processing_channel}&client_callback_link={client_callback_link}"
                }, status=status.HTTP_200_OK)
        except(TypeError, ValueError, OverflowError, UserModel.DoesNotExist) as err:
            log.error(err)
            return Response({"details": 'Invalid User'}, status=status.HTTP_400_BAD_REQUEST)

    # @action(methods=['post'], detail=False, permission_classes=[], url_path='activate/(?P<uuid>[0-9A-Za-z_\-]+)/(?P<session_key>\d+)', url_name='activate')
    @action(methods=['post'], detail=False, permission_classes=[], url_path='activate/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<session_key>\d+)', url_name='activate')
    def activate(self, request, uidb64, session_key):
        """
        Activates user's Account/Verifies Email/Phone Number/Activate Password Rest   
        parameters:
        - name: token
            type: int
            required: true
            # location: form

        returns: an object with the following
        message Text with details,
        user: User object
        or 
        reset_url: URL to set User's password
        """ 
        try:
            print('******1*****')
            user = UserModel.objects.get(pk=urlsafe_base64_decode(uidb64).decode())
        except(TypeError, ValueError, OverflowError, UserModel.DoesNotExist) as err:
            log.error(err)
            user = None

        print('---------')
        print(user)
        if user is not None:
            from core.models import Profile
            member = Profile.objects.filter(user=user).first()
            if isinstance(request.data, dict):
                token = request.data.get('token', None) 
            
            if token is None:
                return Response({"message": "Token is required"}, status=status.HTTP_400_BAD_REQUEST)
            channel = request.data.get("channel", UserModel.EMAIL_CHANNEL)
            action = request.data.get("action")

            data = account_activation_token.check_token(user, action, token, channel, session_key)
            print('Data:  ', data)
            
            if getattr(settings, "PROFILE_IS_REQUIRED", False):
                if not member:
                    data = False
                    message = "Report to admin about this error `User with missing Profile details`"
                else:
                    messages = 'Invalid or expired token!' 
            else:
                messages = 'Invalid or expired token!'
            
            print('Session Key:  ', session_key)
            print('Token:  ', token)
            print('Channel:  ', channel)
            print('Data:  ', data)
            if isinstance(data, dict):
                action = data['action']

            if action in [UserModel.ACCOUNT_ACTIVATION, UserModel.NEW_REG_ACTIVATION, UserModel.NEW_REG_PASS_SET, UserModel.VERIFY_PHONE, UserModel.VERIFY_EMAIL]:
            # if getattr(settings, "AUTH_ACTIVATION_REQUIRE_PROFILE", False):
                if data:
                    if action in [UserModel.ACCOUNT_ACTIVATION, UserModel.NEW_REG_ACTIVATION, UserModel.NEW_REG_PASS_SET]:
                        user.is_active = True
                    if hasattr(user, "email_verified") and channel == UserModel.EMAIL_CHANNEL:
                        user.email_verified = True
                    if hasattr(user, "phone_verified") and channel == UserModel.PHONE_CHANNEL:
                        user.phone_verified = True
                    user.save()
                    return Response({"message": "ok", "user": UserSerializer(user).data}, status=status.HTTP_200_OK)
                else:
                    return Response({"message": messages}, status=status.HTTP_400_BAD_REQUEST)
            elif data and action == UserModel.PASSWORD_RESET:
                
                return Response({"message": "ok", "reset_url": data['extra']['reset_url']}, status=status.HTTP_200_OK)
                # return redirect('core:dashboard')
            else:
                return Response({"message": messages}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({"message": 'Activation link is invalid!'}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['post'], detail=False, permission_classes=[], url_path='token/confirm/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<session_key>\d+)', url_name='confirm-token')
    def confirm_token(self, request, uidb64, session_key):
        """
            Activates user's Account/Verifies Email/Phone Number/Activate Password Rest   
            parameters:
            - name: token
                type: int
                required: true
                # location: form

            returns: an object with the following
            message Text with details,
            user: User object
            or 
            reset_url: URL to set User's password
        """ 
        data = dict()
        data = request.query_params.dict()
        post = request.data if type(request.data) == dict else request.data.dict()
        data.update(post)
        data['uidb64'] = uidb64
        data['session_key'] = session_key
        print('++++++++>> ', data)

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        inst = serializer.save()
        print('*****1***** ', inst)
        print('*****2***** ', data)
        
        
        if getattr(settings, "PROFILE_IS_REQUIRED", False):
            from core.models import Profile
            member = Profile.objects.filter(user__id=urlsafe_base64_decode(data['uidb64']).decode()).first()
            if not member:
                data = False
                message = "Report to admin about this error `User with missing Profile details`"
                return Response({"message": message}, status=status.HTTP_400_BAD_REQUEST)
             
        print('------ Data:  ', data)
        # action = data.get("action")
        return Response({"message": "ok"}, status=status.HTTP_200_OK)
        # if action in [UserModel.ACCOUNT_ACTIVATION, UserModel.NEW_REG_ACTIVATION, UserModel.NEW_REG_PASS_SET, UserModel.VERIFY_PHONE, UserModel.VERIFY_EMAIL]:
        #     if action in [UserModel.ACCOUNT_ACTIVATION, UserModel.NEW_REG_ACTIVATION, UserModel.NEW_REG_PASS_SET]:
        #         self.user.is_active = True
        #         self.user.force_password_change = False
        #     if hasattr(self.user, "email_verified") and channel == UserModel.EMAIL_CHANNEL:
        #         self.user.email_verified = True
        #     if hasattr(self.user, "phone_verified") and channel == UserModel.PHONE_CHANNEL:
        #         self.user.phone_verified = True
        #     self.user.save()
            
        #     return Response({"message": "ok", "user": UserSerializer(self.user).data}, status=status.HTTP_200_OK)
        # elif data and action == UserModel.PASSWORD_RESET:
            
        #     return Response({"message": "ok"}, status=status.HTTP_200_OK)
        # else:
        #     return Response({"message": f"Invalid Action ({action})"}, status=status.HTTP_400_BAD_REQUEST)
        

class PasswordResetView(DJ_PasswordResetView):
    """
    Calls Django Auth PasswordResetForm save method.

    Accepts the following POST parameters: email
    Returns the success/fail message.
    """
    serializer_class = MyPasswordResetSerializer
    permission_classes = []
    authentication_classes = ()


    def post(self, request, *args, **kwargs):
        # Create a serializer with request.data
        data = dict()
        data = request.query_params.dict()
        post = request.data if type(request.data) == dict else request.data.dict()
        data.update(post)
        data.update(kwargs)
        data['action'] = UserModel.PASSWORD_RESET
        data['session_key'] = 565666662222
        domain = get_domain(request)
        data['domain'] = domain
        channel = data.get("channel", UserModel.EMAIL_CHANNEL)
        processing_channel = request.data.get('processing_channel', UserModel.TOKEN if channel == UserModel.PHONE_CHANNEL else UserModel.LINK)
        client_callback_link = request.data.get('client_callback_link')
        
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        session_key, user = serializer.save(data)
        print(session_key,' *****3***** ', data)
        
        print(' 2 -- session_key: ', user.id)
        # Return the success message with OK HTTP status
        
        # id=urlsafe_base64_decode(serializer.initial_data.get('uid', None)).decode()
        id = serializer.initial_data.get('id', None)
        uidb64 = urlsafe_base64_encode(force_bytes(user.id))
        request_url = f"{domain}{reverse('auths_api:activation-send', args=(uidb64,))}"
        activation_url = f"{domain}{reverse('auths_api:activation-confirm-token', args=(uidb64, session_key))}"
        
        print('.....', activation_url)
        return Response({
                "message": 'Password reset e-mail has been sent.', 
                "resend_url": f"{request_url}?action={action}&channel={channel}&processing_channel={processing_channel}&client_callback_link={client_callback_link}",
                "activation_url": f"{activation_url}?action={action}&channel={channel}&processing_channel={processing_channel}&client_callback_link={client_callback_link}"
                }, status=status.HTTP_200_OK)


class PasswordResetConfirmView(DJ_PasswordResetConfirmView):
    """
    Call this endpoint with New Password to reset the user's password.

    Accepts the following POST parameters: new_password1, new_password2
        
    Returns the success/fail message.
    """
    serializer_class = MyPasswordResetConfirmSerializer
    permission_classes = (AllowAny,)
    authentication_classes = (TokenAuthentication,)
    
    def is_valid_uuid(self, val):
        import uuid
        try:
            uuid.UUID(str(val))
            return True
        except ValueError:
            return False

    def post(self, request, *args, **kwargs):
        data = request.data
        print(data)
        print('+++++++', request.query_params)
        data['uid'] = urlsafe_base64_decode(kwargs['uidb64']).decode()
        data['session_key'] = kwargs['session_key']
        data['action'] = UserModel.PASSWORD_RESET
        serializer = self.get_serializer(data=data)
        
        print(data)
        print('.......')
        if serializer.is_valid(raise_exception=True):
            print(111)
            serializer.save()
        else:
            print(222)
            print(data['uid'])
            print(self.is_valid_uuid(data['uid']))
            if (not self.is_valid_uuid(data['uid'])):
                print(333)
                try:
                    data['uid'] = urlsafe_base64_decode(kwargs['uidb64']).decode()
                    serializer = self.get_serializer(data=data)
                    if not serializer.is_valid(raise_exception=False):
                        d = cache.get(f"access_token_password_{data['uid']}_email_{data['token']}")
                        print(d)

                        u = UserModel.objects.filter(id=data['uid']).first()
                        if d and isinstance(d, dict) and d['token'] == data['token'] and u.email == d['email']:
                            if d["action"] == UserModel.PASSWORD_RESET:
                                cache.delete_pattern(f"access_token_password_{u.id}_email_*")
                                u.set_password(data['new_password1'])
                                u.email_verified = True
                                u.force_password_change = True
                                u.save()
                                return JsonResponse({"msg": f'Password Reset Successful!!!', "type": "success"}, safe=True)
                        else:
                            return Response({'message': "Invalid or expired link, please reset password button to generate a new link"}, status=status.HTTP_400_BAD_REQUEST)
                except ValueError as e:
                    serializer.is_valid(raise_exception=True)
            
            print(444)
            serializer.is_valid(raise_exception=True)
            serializer.save()
        return Response(
            {'detail': _('Password has been reset with the new password.')},
        )


class PasswordChange(DJ_PasswordResetConfirmView):
    """
    Call this endpoint with Old & New Password to reset the user's password.

    Accepts the following POST parameters: old_password new_password1, new_password2
        
    Returns the success/fail message.
    """
    serializer_class = MyPasswordResetConfirmSerializer
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)
    
    def post(self, request, *args, **kwargs):
        user = request.user
        if user.check_password(request.data['old_password']):
            if request.data['new_password1'] == request.data['new_password2'] :
                user.set_password(request.data['new_password1']);
                user.save()

                return Response(
                    {'detail': _('Password has been changed successfully.')},
                    status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {'detail': _('New Password 1 & 2 must be uniquly the same')},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            return Response(
                {'detail': _('Old Password not correct')},
                status=status.HTTP_400_BAD_REQUEST
            )


class UserViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticatedOrCreate, )
    authentication_classes = (TokenAuthentication,)

    def get_queryset(self):
        """
        This view should return a list of all the Users for
        the user as determined by currently logged in user.
        """
        searchTerm = self.request.GET.get('term')
        # queryset = UserModel.objects.filter(company=self.request.user.company)
        queryset = UserModel.objects.filter()
        if (searchTerm is not None):
            queryset = queryset[:50]
            if (searchTerm != ''):
                queryset = queryset.filter(Q(user__first_name__icontains=searchTerm) |
                                           Q(user__last_name__icontains=searchTerm))

        return queryset

    def get_serializer_class(self):
        # print('********', self.request.method, "   ", self.action)
        if self.action == 'update_picture':
            return UserPasswordChangeSerializer
        return UserSerializer

    def perform_create(self, serializer): 
        return serializer.save() 
    
    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        # For Single Paged App/Mobile App they will provide client_callback_link which need to be 
        # passed around
        # 
        client_callback_link = data.get('client_callback_link', None)
        is_password_generated = not data.get('password', None)
        data['password'] = UserModel.objects.make_random_password() if is_password_generated else data['password']
        # print(data)
        # data['address'] = data['address'] if data.get('address', None) else None
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)

        user = self.perform_create(serializer)

        headers = self.get_success_headers(serializer.data)

        domain = get_domain(request)
        # send_access_token(self, token_length, domain, channel=UserModel.EMAIL_CHANNEL, action="Verify Email", extra={})

        print('------------')
        print(data)
        print(is_password_generated)
        if is_password_generated:
            user.force_password_change = True
            user.save()
            messages = f"Account Registration successful, activation link has been sent to: '{user.email}'"
            user.send_registration_password(domain, client_callback_link)
            return Response({"message": messages, "user": serializer.data}, status=status.HTTP_201_CREATED, headers=headers)
        else:
            uidb64 = urlsafe_base64_encode(force_bytes(user.id))
            action = UserModel.ACCOUNT_ACTIVATION
            session_key = user.send_access_token(domain, action, UserModel.EMAIL_CHANNEL, template='auths/mail_templates/token.html')
            request_url = f"{domain}{reverse('auths_api:activation-send', args=(uidb64,))}?action={action}&channel={UserModel.EMAIL_CHANNEL}"
            activation_url = f"{domain}{reverse('auths_api:activation-confirm-token', args=(uidb64, session_key))}"
            user.set_password(data['password'])
            user.save()
            
            messages = f"Account activation Token successfully sent to '{user.email}'"
            data = {
                    "message": messages,
                    "user": serializer.data,
                    "resend_url": request_url,
                    "activation_url": activation_url
                }
            return Response(data, status=status.HTTP_201_CREATED, headers=headers)

    @action(methods=['post', 'patch'], detail=True, url_path='password/change', url_name='password-change')
    def password_change(self, request, *args, **kwargs):
        print('*****====*****', kwargs['pk'])
        user = request.user
        print(' 1 -----', user.id)
        instance = self.get_object()
        print(' 2 -----', instance.id)
        if user.id != instance.id and user.position != UserModel.ADMIN:
            return Response({'detail': _('Sorry you are unauthorised to do this')}, status=status.HTTP_401_UNAUTHORIZED)
        
        if user.id != instance.id and user.position == UserModel.ADMIN:
            if request.data['new_password1'] == request.data['new_password2'] :
                user.set_password(request.data['new_password1']);
                user.save()
                return Response({'detail': _('Password has been changed successfully.')}, status=status.HTTP_200_OK)
            else:
                return Response({'detail': _('New Password 1 & 2 must be uniquely the same')}, status=status.HTTP_400_BAD_REQUEST)
        elif user.id == instance.id:
            if user.check_password(request.data['old_password']):
                if request.data['new_password1'] == request.data['new_password2'] :
                    user.set_password(request.data['new_password1']);
                    user.save()
                    return Response({'detail': _('Password has been changed successfully.')}, status=status.HTTP_200_OK)
                else:
                    return Response({'detail': _('New Password 1 & 2 must be uniquely the same')}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({'detail': _('Old Password not correct')}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['get'], detail=False, url_path='me', url_name='me')
    def me(self, request, *args, **kwargs):
        return Response(UserSerializer(request.user).data, status=status.HTTP_200_OK)








DOMAIN_URL = settings.DOMAIN_URL
AUTH_CALLBACK_URL = '/accounts/social/{}/login/callback/'
CONNECT_CALLBACK_URL = '/users/social/{}/connect/'


class GoogleConnect(SocialConnectView):
    adapter_class = GoogleOAuth2Adapter
    client_class = OAuth2Client
    serializer_class = SocialLoginSerializer
    callback_url = f"{DOMAIN_URL}{CONNECT_CALLBACK_URL.format('google')}"
    
    
class GoogleLogin(SocialLoginView):
    # renderer_classes = [renderers.JSONRenderer]
    adapter_class = GoogleOAuth2Adapter
    client_class = OAuth2Client
    serializer_class = SocialLoginSerializer
    callback_url = f"{DOMAIN_URL}{AUTH_CALLBACK_URL.format('google')}"

    def get_serializer(self, *args, **kwargs):
        serializer_class = self.get_serializer_class()
        kwargs['context'] = self.get_serializer_context()
        return serializer_class(*args, **kwargs)
    
class FacebookConnect(SocialConnectView):
    adapter_class = FacebookOAuth2Adapter
    client_class = OAuth2Client
    serializer_class = SocialLoginSerializer
    callback_url = f"{DOMAIN_URL}{CONNECT_CALLBACK_URL.format('facebook')}"
    

# class FacebookLogin(SocialLoginView):
#     adapter_class = FacebookOAuth2Adapter
    
class FacebookLogin(SocialLoginView):
    adapter_class = FacebookOAuth2Adapter
    


# https://stackoverflow.com/questions/64850805/apple-login-in-django-rest-framework-with-allauth-and-rest-auth
class CustomAppleSocialLoginSerializer(SocialLoginSerializer):
    def validate(self, attrs):
        view = self.context.get('view')
        request = self._get_request()

        if not view:
            raise serializers.ValidationError(
                _('View is not defined, pass it as a context variable')
            )

        adapter_class = getattr(view, 'adapter_class', None)
        if not adapter_class:
            raise serializers.ValidationError(_('Define adapter_class in view'))

        adapter = adapter_class(request)
        app = adapter.get_provider().get_app(request)

        # More info on code vs access_token
        # http://stackoverflow.com/questions/8666316/facebook-oauth-2-0-code-and-token

        # Case 1: We received the access_token
        if attrs.get('access_token'):
            access_token = attrs.get('access_token')
            token = {'access_token': access_token}

        # Case 2: We received the authorization code
        elif attrs.get('code'):
            self.callback_url = getattr(view, 'callback_url', None)
            self.client_class = getattr(view, 'client_class', None)

            if not self.callback_url:
                raise serializers.ValidationError(
                    _('Define callback_url in view')
                )
            if not self.client_class:
                raise serializers.ValidationError(
                    _('Define client_class in view')
                )

            code = attrs.get('code')

            provider = adapter.get_provider()
            scope = provider.get_scope(request)
            client = self.client_class(
                request,
                app.client_id,
                app.secret,
                adapter.access_token_method,
                adapter.access_token_url,
                self.callback_url,
                scope,
                key=app.key,
                cert=app.cert,
            )
            token = client.get_access_token(code)
            access_token = token['access_token']

        else:
            raise serializers.ValidationError(
                _('Incorrect input. access_token or code is required.'))

        social_token = adapter.parse_token(token)  # The important change is here.
        social_token.app = app

        try:
            login = self.get_social_login(adapter, app, social_token, access_token)
            complete_social_login(request, login)
        except HTTPError:
            raise serializers.ValidationError(_('Incorrect value'))

        if not login.is_existing:
            # We have an account already signed up in a different flow
            # with the same email address: raise an exception.
            # This needs to be handled in the frontend. We can not just
            # link up the accounts due to security constraints
            if allauth_settings.UNIQUE_EMAIL:
                # Do we have an account already with this email address?
                if get_user_model().objects.filter(email=login.user.email).exists():
                    raise serializers.ValidationError(_('E-mail already registered using different signup method.'))

            login.lookup()
            login.save(request, connect=True)

        attrs['user'] = login.account.user
        return attrs

class AppleConnect(SocialConnectView):
    adapter_class = GoogleOAuth2Adapter
    client_class = AppleOAuth2Client
    serializer_class = SocialLoginSerializer
    # serializer_class = CustomAppleSocialLoginSerializer
    callback_url = "{}{}".format(DOMAIN_URL, CONNECT_CALLBACK_URL.format('apple'))
    
    
class AppleLogin(SocialLoginView):
    adapter_class = AppleOAuth2Adapter
    client_class = AppleOAuth2Client
    serializer_class = SocialLoginSerializer
    # serializer_class = CustomAppleSocialLoginSerializer
    callback_url = "{}{}".format(DOMAIN_URL, AUTH_CALLBACK_URL.format('apple'))

    def get_serializer(self, *args, **kwargs):
        serializer_class = self.get_serializer_class()
        kwargs['context'] = self.get_serializer_context()
        return serializer_class(*args, **kwargs)
    



