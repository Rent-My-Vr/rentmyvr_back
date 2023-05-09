import json
import logging
from uuid import UUID
from inspect import Attribute
from xml import dom
from pprint import pprint
from django.conf import settings
from django.db import transaction
from django.shortcuts import render
from django.urls import reverse
from django.utils.encoding import force_str, force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import viewsets, status, mixins
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser, FileUploadParser

from django.db.models import Q, Prefetch
from datetime import datetime, timedelta
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.translation import gettext_lazy as _
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode
from django.contrib.auth import get_user_model
from auths.utils import get_domain, random_with_N_digits
from auths_api.serializers import UserUpdateSerializer
from notifications.signals import notify

from directory.models import *

from core.models import *
from core.utils import send_gmail

from core.custom_permission import IsAuthenticatedOrCreate
from core_api.serializers import *
from core_api.models import *


log = logging.getLogger(f"{__package__}.*")
log.setLevel(settings.LOGGING_LEVEL)
UserModel = get_user_model()


class UUIDEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, UUID):
            return obj.hex
        return json.JSONEncoder.default(self, obj)


class AddressViewSet(viewsets.ModelViewSet, AchieveModelMixin):
    permission_classes = (IsAuthenticated, )
    authentication_classes = (TokenAuthentication,)
    parser_classes = (JSONParser, MultiPartParser)
        
    # def perform_create(self, serializer):
    #     return serializer.save(updated_by_id=self.request.user.id) 
    #     # return serializer.save(updated_by_id=settings.EMAIL_PROCESSOR_ID) 
        
    def get_queryset(self):
        """
        This view should return a list of all the Company for
        the user as determined by currently logged in user.
        """
        return Address.objects.filter(enabled=True)
 
    def get_serializer_class(self):
        if self.action in ['retrieve',]:
            return AddressDetailSerializer
        return AddressSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        address = self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)

    def update(self, request, *args, **kwargs):
        with transaction.atomic():
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)

            serializer.is_valid(raise_exception=True)
            address = serializer.save()
            
            self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        return Response(serializer.data, status=status.HTTP_201_CREATED)


class CountryViewSet(viewsets.ModelViewSet, AchieveModelMixin):
    permission_classes = (AllowAny, )
    # permission_classes = (IsAuthenticated, )
    authentication_classes = (TokenAuthentication,)
    parser_classes = (JSONParser, MultiPartParser)
        
    def get_queryset(self):
        """
        This view should return a list of all the Company for
        the user as determined by currently logged in user.
        """
        return Country.objects.filter(enabled=True)
 
    def get_serializer_class(self):
        if self.action in ['retrieve',]:
            return CountrySerializer
        return CountrySerializer

    @action(methods=['post'], detail=False, url_path='bulk/add', url_name='bulk-add')
    def select_list(self, request, *args, **kwargs):
        with transaction.atomic():
            data = request.data.copy()
            
            print('-------')
            print(data)
            x = 0
            for d in data:
                serializer = self.get_serializer(data=d)
                serializer.is_valid(raise_exception=True)
                self.perform_create(serializer)
                x += 1

            headers = self.get_success_headers(serializer.data)

            return Response({'message': f'{x} Countries created successfully'}, status=status.HTTP_201_CREATED, headers=headers)
            # return Response({}, status=status.HTTP_201_CREATED)


class StateViewSet(viewsets.ModelViewSet, AchieveModelMixin):
    permission_classes = (AllowAny, )
    # permission_classes = (IsAuthenticated, )
    authentication_classes = (TokenAuthentication,)
    parser_classes = (JSONParser, MultiPartParser)
        
    def get_queryset(self):
        """
        This view should return a list of all the Company for
        the user as determined by currently logged in user.
        """
        return State.objects.filter(enabled=True)
 
    def get_serializer_class(self):
        if self.action in ['retrieve',]:
            return StateSerializer
        return StateSerializer

    @action(methods=['post'], detail=False, url_path='bulk/add', url_name='bulk-add')
    def bulk_add(self, request, *args, **kwargs):
        with transaction.atomic():
            data = request.data.copy()
            x = 0
            for d in data:
                serializer = self.get_serializer(data=d)
                serializer.is_valid(raise_exception=True)
                self.perform_create(serializer)
                x += 1

            headers = self.get_success_headers(serializer.data)

            return Response({'message': f'{x} City created successfully'}, status=status.HTTP_201_CREATED, headers=headers)


class CityViewSet(viewsets.ModelViewSet, AchieveModelMixin):
    permission_classes = (AllowAny, )
    # permission_classes = (IsAuthenticated, )
    authentication_classes = (TokenAuthentication,)
    parser_classes = (JSONParser, MultiPartParser)
        
    def get_queryset(self):
        """
        This view should return a list of all the Company for
        the user as determined by currently logged in user.
        """
        return City.objects.filter(enabled=True)
 
    def get_serializer_class(self):
        if self.action in ['retrieve',]:
            return CitySerializer
        return CitySerializer

    @action(methods=['post'], detail=False, url_path='bulk/add', url_name='bulk-add')
    def select_list(self, request, *args, **kwargs):
        with transaction.atomic():
            data = request.data.copy()
            
            print('-------')
            # print(data)
            x = 0
            for d in data:
                try:
                    serializer = self.get_serializer(data=d)
                    serializer.is_valid(raise_exception=False)
                    self.perform_create(serializer)
                    x += 1
                except AssertionError:
                    print(f'Not adding {d}')

            headers = self.get_success_headers(serializer.data)

            return Response({'message': f'{x} State created successfully'}, status=status.HTTP_201_CREATED, headers=headers)
            # return Response({}, status=status.HTTP_201_CREATED)


class ContactViewSet(viewsets.ModelViewSet):
    permission_classes = (AllowAny, )
    authentication_classes = ()
    parser_classes = (JSONParser, MultiPartParser)
        
    def get_queryset(self):
        """
        This view should return a list of all the Company for
        the user as determined by currently logged in user.
        """
        return Contact.objects.filter(enabled=True)
 
    def get_serializer_class(self):
        # if self.action in ['retrieve',]:
        #     return ContactSerializer
        return ContactSerializer


class CompanyViewSet(viewsets.ModelViewSet, AchieveModelMixin):
    permission_classes = (IsAuthenticated, )
    authentication_classes = (TokenAuthentication,)
    # parser_classes = (JSONParser, MultiPartParser)

    def get_queryset(self):
        """
        This view should return a list of all the Company for
        the user as determined by currently logged in user.
        """
        return Company.objects.filter(enabled=True)
 
    def get_serializer_class(self):
        if self.action in ['retrieve',]:
            return CompanySerializer
        return CompanySerializer

    def perform_update(self, serializer):
        return serializer.save(updated_by_id=self.request.user.id)

    def perform_create(self, serializer):
        return serializer.save(updated_by_id=self.request.user.id)

    def create(self, request, *args, **kwargs):
        with transaction.atomic():
            data = request.data
            print(data)
            if data.get('city').get('id', None):
                print('====Have City****')
                data['country'] = data.get('city').get('country_name')
                data['state'] = data.get('city').get('state_name')
                data['city'] = data.get('city').get('id')
            else:
                print('====Create City****')
                ser = CitySerializer(data=data.get('city'))
                ser.is_valid(raise_exception=True)
                inst = ser.save()
                data['country'] = inst.country_name
                data['state'] = inst.state_name
                data['city'] = inst.id
            profile = request.user.user_profile
            data['administrator'] = profile.id
            if profile.company:
                return Response({'message': f'User {profile} is already and existing memeber of a different Company'}, status=status.HTTP_403_FORBIDDEN)
            serializer = self.get_serializer(data=data)
            serializer.is_valid(raise_exception=True)
            company = self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            profile.company = company
            profile.save()

        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    def update(self, request, *args, **kwargs):
        with transaction.atomic():
            data = request.data
            print(data)
            if data.get('city').get('id', None):
                print('====Have City****')
                data['country'] = data.get('city').get('country_name')
                data['state'] = data.get('city').get('state_name')
                data['city'] = data.get('city').get('id')
            else:
                print('====Create City****')
                ser = CitySerializer(data=data.get('city'))
                ser.is_valid(raise_exception=True)
                inst = ser.save()
                data['country'] = inst.country_name
                data['state'] = inst.state_name
                data['city'] = inst.id
                    
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            
            serializer.is_valid(raise_exception=True)
            instance = serializer.save()
            
            self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    # def retrieve(self, request, *args, **kwargs):
    #     if kwargs['pk'] != request.user.id and request.user.position == UserModel.BASIC:
    #         return Response({'message': 'You are not authorised to access this record'}, status=status.HTTP_403_FORBIDDEN)
    #     r = Profile.objects.filter(id=kwargs['pk']).first()
    #     # r = Profile.objects.filter(id=kwargs['pk']).prefetch_related(Prefetch('worker_statuses', queryset=WorkStatus.objects.filter(enabled=True, project__enabled=True))).first()
    #     print(r)
    #     return Response(self.get_serializer(instance=r).data)

    @action(methods=['get'], detail=False, url_path='me', url_name='me')
    def me(self, request, *args, **kwargs):
        p = request.user.user_profile
        company = Company.objects.filter(Q(administrator=p) | Q(members=p), enabled=True).prefetch_related(
            Prefetch('company_offices', queryset=Office.objects.filter(enabled=True).prefetch_related(
                Prefetch('office_properties', queryset=Property.objects.filter(enabled=True)))), 
            Prefetch('company_portfolios', queryset=Portfolio.objects.filter(enabled=True).prefetch_related(
                Prefetch('portfolio_properties', queryset=Property.objects.filter(enabled=True)))),
            Prefetch('members', queryset=Profile.objects.filter(enabled=True).prefetch_related(
                Prefetch('portfolios', queryset=Portfolio.objects.filter(enabled=True)),
                Prefetch('offices', queryset=Office.objects.filter(enabled=True))))
        ).first()
        if company:
            return Response(CompanyMDLDetailSerializer(company).data, status=status.HTTP_200_OK)
        else:
            return Response(None, status=status.HTTP_200_OK)


class InvitationViewSet(viewsets.ModelViewSet):
    permission_classes = (AllowAny, )
    authentication_classes = (TokenAuthentication, )
    parser_classes = (JSONParser, MultiPartParser)
        
    def get_queryset(self):
        """
        This view should return a list of all the Company for
        the user as determined by currently logged in user.
        """
        return Invitation.objects.filter(enabled=True)
 
    def get_serializer_class(self):
        # if self.action in ['retrieve',]:
        #     return ContactSerializer
        return InvitationSerializer

    def perform_create(self, serializer):
        # serializer.save(updated_by_id=self.request.user.id) 
        return serializer.save(company=self.company, sender=self.sender) 
    
    def create(self, request, *args, **kwargs):
        print('****** 1');
        data = request.data
        print(data)
        emails = data['emails']
        client_callback_link = data['client_callback_link']
        profile = request.user.user_profile
        print('****** 2');
        self.sender = profile
        self.company = profile.company
        
        print(emails)
        print(data)
        
        if not profile.company:
            return Response({'message': f'User {profile} must be a mamber of a Company/MDL b4 you can axecute this action'}, status=status.HTTP_403_FORBIDDEN)
        
        existing_same_company = list(Profile.objects.filter(company=profile.company, user__email__in=emails).values_list('user__email', flat=True))
        existing_other_company = list(Profile.objects.filter(~Q(company=profile.company), ~Q(company__isnull=False), user__email__in=emails).values_list('user__email', flat=True))
        sent_same_company = list(Invitation.objects.filter(company=profile.company, email__in=emails).values_list('email', flat=True))
        sent_other_company = list(Invitation.objects.filter(~Q(status__in=[Invitation.REJECTED, Invitation.CANCELLED]), ~Q(company=profile.company), ~Q(company__isnull=False), email__in=emails).values_list('email', flat=True))
        existing = list(set(existing_same_company) | set(existing_other_company) | set(sent_same_company) | set(sent_other_company))
        remaining = list(filter(lambda x: x not in existing, emails))
        
        message = []
        if len(existing_same_company) > 0:
            message.append({"existing_same": existing_same_company})
        if len(existing_other_company) > 0:
            message.append({"existing_other": existing_other_company})
        if len(sent_same_company) > 0:
            message.append({"sent_same": sent_same_company})
        if len(sent_other_company) > 0:
            message.append({"sent_other": sent_other_company})
        
        print(f"Existing Same: {existing_same_company}\nExisting Other: {existing_other_company}\Sent Same: {sent_same_company}\Sent Other: {sent_other_company}\nExisting: {existing}\nRemaining: {remaining}")
        
        if len(remaining) == 0:
            return Response({"message": "No invite sent!", 'result': message}, status=status.HTTP_403_FORBIDDEN)

        data.pop('emails', False)
        with transaction.atomic():
            for email in remaining:
                data['email'] = email
                print(data)
                serializer = self.get_serializer(data=data)
                serializer.is_valid(raise_exception=True)
                invitation = self.perform_create(serializer)
                
                token = random_with_N_digits(12)
                uidb64 = urlsafe_base64_encode(force_bytes(email))
                action_link = f"{reverse('core_api:invitation-verify', kwargs={'uidb64': uidb64, 'token': token})}"
        
                domain = get_domain(request)
                print({
                    'coy_name': settings.COMPANY_NAME,
                    'user': self,
                    'action_link': f"{client_callback_link if client_callback_link else domain}?link={action_link}",
                    'domain': domain,
                    'project_title': profile.company.name
                })
                html_message = render_to_string('auths/mail_templates/invite.html', {
                    'coy_name': settings.COMPANY_NAME,
                    'user': self,
                    'action_link': f"{client_callback_link if client_callback_link else domain}?link={action_link}",
                    'domain': domain,
                    'project_title': profile.company.name
                })
                
                print(action_link)
                from core.tasks import sendMail
                sendMail.apply_async(kwargs={'subject': 'Rent MyVR User Invite', "message": html_message,
                                            "recipients": [email],
                                            "fail_silently": settings.DEBUG, "connection": None})
        
        headers = self.get_success_headers(serializer.data)

        return Response({"message": "Ok", "result": message}, status=status.HTTP_201_CREATED, headers=headers)
    
    @action(methods=['patch', 'post'], detail=False, permission_classes=[], url_path='verify/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>\d+)', url_name='verify')
    def verify(self, request, *args, **kwargs):
        print(kwargs)
        email = urlsafe_base64_decode(kwargs['uidb64']).decode()
        print(email)
        invite = Invitation.objects.filter(email=email, token=kwargs['token'])
        print(invite)
        
        profile = Profile.objects.filter(pk=pk, company=request.user.company).first()
        if profile is None:
            profile = Profile.objects.filter(pk=kwargs['pk'], company=request.user.user_profile.company).first()

        if profile and len(request.data.get('timezone', "")) > 2:
            user = profile.user
            user.timezone_id = request.data['timezone']
            user.save()
            return Response({'msg': 'Timezone Updated', 'data': {'timezone': user.timezone.alias}},
                            status=status.HTTP_201_CREATED)
        else:
            return Response({'msg': 'wrong parameters'}, status=status.HTTP_400_BAD_REQUEST)


class ProfileViewSet(viewsets.ModelViewSet, AchieveModelMixin):
    permission_classes = (IsAuthenticatedOrCreate, )
    authentication_classes = (TokenAuthentication,)
    parser_classes = (JSONParser, MultiPartParser)
    # parser_classes = (MultiPartParser, FormParser, JSONParser)
    # parser_classes = (MultiPartParser, FormParser,JSONParser, FileUploadParser)
    # serializer_class = ProfileSerializer

    def get_queryset(self):
        """
        This view should return a list of all the Profiles for
        the user as determined by currently logged in user.
        """
        searchTerm = self.request.GET.get('term')
        queryset = Profile.objects.filter(enabled=True)
        # queryset = Profile.objects.filter(company=self.request.user.company)
        if (searchTerm is not None):
            print('---4---')
            queryset = queryset[:50]
            print('---5---')
            if (searchTerm != ''):
                print('---6---')
                queryset = queryset.filter(Q(user__first_name__icontains=searchTerm) |
                                           Q(user__last_name__icontains=searchTerm))
        
        return queryset

    def get_serializer_class(self):
        print('********', self.request.method, "   ", self.action)
        if self.action in ['update']:
            # Since the ReadSerializer does nested lookups
            # in multiple tables, only use it when necessary
            return ProfileUpdateSerializer
        elif self.request.method == 'PATCH' and self.action == 'update_picture':
            return ProfileSerializer
        elif self.action == 'retrieve':
            print('======12======')
            return ProfileDetailSerializer
        return ProfileSerializer

    def perform_create(self, serializer):
        # serializer.save(updated_by_id=self.request.user.id) 
        return serializer.save(updated_by_id=settings.EMAIL_PROCESSOR_ID) 
    
    def retrieve(self, request, *args, **kwargs):
        if kwargs['pk'] != request.user.id and request.user.position == UserModel.BASIC:
            return Response({'message': 'You are not authorised to access this record'}, status=status.HTTP_403_FORBIDDEN)
        r = Profile.objects.filter(id=kwargs['pk']).first()
        # r = Profile.objects.filter(id=kwargs['pk']).prefetch_related(Prefetch('worker_statuses', queryset=WorkStatus.objects.filter(enabled=True, project__enabled=True))).first()
        print(r)
        return Response(self.get_serializer(instance=r).data)

    def create(self, request, *args, **kwargs):
        with transaction.atomic():
            data = request.data
            channel = data.get('channel')
            processing_channel = data.get('processing_channel', UserModel.TOKEN)
            client_callback_link = data.get('client_callback_link', None)
            if not channel:
                raise serializers.ValidationError('channel', _('Account verification Channel not provided'))
            if not client_callback_link:
                raise serializers.ValidationError('client_callback_link', _('Account verification Callback Link not provided'))
            extra = {"processing_channel": processing_channel, "client_callback_link": client_callback_link}
            is_password_generated = not data['user'].get('password', None)
            data['user']['password'] = UserModel.objects.make_random_password() if is_password_generated else data['user']['password']
            print(data)
            print('==============')
            
            # data['address'] = data['address'] if data.get('address', None) else None
            serializer = self.get_serializer(data=data)
            print(type(serializer))
            print('----- b4')
            serializer.is_valid(raise_exception=True)
            print('----- after')
            profile = self.perform_create(serializer)

            uidb64 = urlsafe_base64_encode(force_bytes(profile.user.pk))
            headers = self.get_success_headers(serializer.data)

            # print(user)
            user = profile.user
            client_domain = settings.FRONT_SERVER
            server_domain = get_domain(request)
            
            if is_password_generated:
                user.force_password_change = True
                user.save()
                action = UserModel.NEW_REG_PASS_SET
                session_key = user.send_access_token(client_domain, action, channel, template='auths/mail_templates/welcome.html', extra=extra)
                messages = f"Account Registration successful, activation link has been sent to: '{user.email}'"
                data = {"message": messages, "user": serializer.data}
            else:
                action = UserModel.NEW_REG_ACTIVATION
                session_key = user.send_access_token(client_domain, action, channel, template='auths/mail_templates/welcome.html', extra=extra)
                request_url = f"{server_domain}{reverse('auths_api:activation-send', args=(uidb64,))}?action={action}&channel={channel}&processing_channel={processing_channel}&client_callback_link={client_callback_link}"
                activation_url = f"{server_domain}{reverse('auths_api:activation-confirm-token', kwargs={'uidb64': uidb64, 'session_key': session_key})}?action={action}&channel={channel}&processing_channel={processing_channel}&client_callback_link={client_callback_link}"
                
                messages = f"Account activation Token successfully sent to '{user.email}'"
                data = {"message": messages, "type": UserModel.ACCOUNT_ACTIVATION, "user": serializer.data, "resend_url": request_url, "activation_url": activation_url}
                
            if session_key:
                return Response(data, status=status.HTTP_201_CREATED, headers=headers)
            else:
                return Response({"message": "Something went wrong", }, status=status.HTTP_404_NOT_FOUND, headers=headers)

    def update(self, request, *args, **kwargs): 
        with transaction.atomic():
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            data = request.data
            print(data)
            print(instance)
            user_instance = UserModel.objects.get(id=data['user']['id'])
            serializer = self.get_serializer(instance, data=request.data, partial=partial)

            print(data.get('address'))
            city_id = None
            if data.get('address').get('city').get('id', None):
                print('====Have City****')
                city_id = data.get('address').get('city').get('id')
                data['address']['city_id'] = city_id
                data['address'].pop('city', None)
            else:
                print('====Create City****')
                ser = CitySerializer(data=data.get('address').get('city'))
                ser.is_valid(raise_exception=True)
                inst = ser.save()
                data['address']['city_id'] = inst.id
                city_id = inst.id
            print(data.get('address'))
            inst = Address.objects.filter(id=data.get('address').get('id', None)).first()
            print(inst)
            if inst:
                ser = AddressSerializer(inst, data=data.get('address'), partial=partial) 
            else:
                ser = AddressSerializer(data=data.get('address'))
            print(1)
            ser.is_valid(raise_exception=True)
            print(2)
            address = ser.save(city_id=city_id)
            # address.city_id = city_id
            # address.save()
            print(address)
            print(address.id)
                 
            user_serializer = UserUpdateSerializer(user_instance, data=data['user'], partial=partial)
            print(3)
            user_serializer.is_valid(raise_exception=True)

            print(4)
            user = user_serializer.save()

            print(5)
            serializer.is_valid(raise_exception=True)
            
            print(6)
            new_profile = self.perform_update(serializer)
            new_profile = self.get_object()
            print(7)
            new_profile.address_id = address.id
            new_profile.save()
            print(8)

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(methods=['patch'], detail=False, permission_classes=[], url_path='timezone/(?P<pk>[^/.]+)',
            url_name='timezone-update')
    def update_timezone(self, request, *args, **kwargs):
        # serializer = ProfileSerializer(profile, data=request.data, partial=True)  # set partial=True to update a data partially
        # serializer = ProfileSerializer(profile, data=request.data, partial=True)  # set partial=True to update a data partially
        # if serializer.is_valid():
        #     serializer.save()
        #     return Response(serializer.data, status=status.HTTP_201_CREATED)

        profile = Profile.objects.filter(pk=kwargs['pk'], company=request.user.company).first()
        if profile is None:
            profile = Profile.objects.filter(pk=kwargs['pk'], company=request.user.user_profile.company).first()

        if profile and len(request.data.get('timezone', "")) > 2:
            user = profile.user
            user.timezone_id = request.data['timezone']
            user.save()
            return Response({'msg': 'Timezone Updated', 'data': {'timezone': user.timezone.alias}},
                            status=status.HTTP_201_CREATED)
        else:
            return Response({'msg': 'wrong parameters'}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['get'], detail=False, url_path='me', url_name='me')
    def me(self, request, *args, **kwargs):
        p = request.user.user_profile
        profile = self.get_queryset().filter(id=p.id).prefetch_related(
            Prefetch('offices', queryset=Office.objects.filter(enabled=True).prefetch_related(
                Prefetch('office_properties', queryset=Property.objects.filter(enabled=True)))), 
            Prefetch('administrative_offices', queryset=Office.objects.filter(enabled=True).prefetch_related(
                Prefetch('office_properties', queryset=Property.objects.filter(enabled=True)))), 
            Prefetch('portfolios', queryset=Portfolio.objects.filter(enabled=True).prefetch_related(
                Prefetch('portfolio_properties', queryset=Property.objects.filter(enabled=True)))),
            Prefetch('administrative_portfolios', queryset=Portfolio.objects.filter(enabled=True).prefetch_related(
                Prefetch('portfolio_properties', queryset=Property.objects.filter(enabled=True)))),
            # Prefetch('properties', queryset=Property.objects.filter(enabled=True).prefetch_related),
            Prefetch('administrative_properties', queryset=Property.objects.filter(enabled=True))
        ).first()
        return Response(ProfileDetailSerializer(profile).data, status=status.HTTP_200_OK)

    @action(methods=['get'], detail=False, url_path='members', url_name='members')
    def members(self, request, *args, **kwargs):
        data = None
        profile = request.user.user_profile
        company = profile.company
        if not company:
            try:
                company = Company.objects.filter(Q(Q(administrator=profile) | Q(members=profile)), enabled=True).first()
                if company:
                    profiles = Profile.objects.filter(Q(Q(company=company) | Q(administrative_company=company), enabled=True)).distinct()
                    data = ProfileSerializer(profiles).data
            except Profile.administrative_company.RelatedObjectDoesNotExist:
                pass
        else:
            profiles = Profile.objects.filter(Q(Q(company=company) | Q(administrative_company=company), enabled=True)).distinct()
            data = ProfileSerializer(profiles, many=True).data
              
        return Response(data, status=status.HTTP_200_OK)

    @action(methods=['get'], detail=False, url_path='names', url_name='names')
    def names(self, request, *args, **kwargs):
        profiles = Profile.objects.all().values('id', 'user__first_name', 'user__last_name', 'position')
        prof = map(lambda x: {"id": str(x['id']), "name": f"{x['user__first_name']} {x['user__last_name']}", "position": x['position']}, profiles)
        return Response(prof, status=status.HTTP_200_OK)

    @action(methods=['patch', 'post'], detail=True, url_path='picture/update', url_name='picture-update')
    def update_picture(self, request, *args, **kwargs):
        data=request.data
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        return Response(ProfileSerializer(instance).data)

    def list(self, request, *args, **kwargs):
        queryset = Profile.objects.filter(enabled=True).prefetch_related(Prefetch('worker_statuses', queryset=WorkStatus.objects.filter(enabled=True, project__enabled=True)))
        
        if request.query_params.get('project_id'):
            queryset = Profile.objects.filter(enabled=True, work_statuses__project_id=request.query_params.get('project_id')).prefetch_related(Prefetch('worker_statuses', queryset=WorkStatus.objects.filter(~Q(status=Project.FINISHED), enabled=True, project__enabled=True)))       
        else:
            queryset = Profile.objects.filter(enabled=True).prefetch_related(Prefetch('worker_statuses', queryset=WorkStatus.objects.filter(~Q(status=Project.FINISHED), enabled=True, project__enabled=True)))
        queryset = self.filter_queryset(queryset)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class SupportViewSet(viewsets.ModelViewSet):
    permission_classes = (AllowAny, )
    authentication_classes = ()
    parser_classes = (JSONParser, MultiPartParser)
        
    def get_queryset(self):
        """
        This view should return a list of all the Company for
        the user as determined by currently logged in user.
        """
        return Support.objects.filter(enabled=True)
 
    def get_serializer_class(self):
        # if self.action in ['retrieve',]:
        #     return CitySerializer
        return SupportSerializer
