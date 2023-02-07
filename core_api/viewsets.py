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
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import viewsets, status, mixins
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser, FileUploadParser

from django.db.models import Q, Prefetch
from datetime import datetime, timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model
from auths.utils import get_domain
from auths_api.serializers import UserSerializer, UserUpdateSerializer
from notifications.signals import notify

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
        
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        address = self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)

    def update(self, request, *args, **kwargs):
        with transaction.atomic():
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            data = request.data
            serializer = self.get_serializer(instance, data=request.data, partial=partial)

            serializer.is_valid(raise_exception=True)
            address = serializer.save()
            
            self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        return Response(serializer.data, status=status.HTTP_201_CREATED)


class CompanyViewSet(viewsets.ModelViewSet, AchieveModelMixin):
    serializer_class = CompanySerializer
    permission_classes = (IsAuthenticated, )
    authentication_classes = (TokenAuthentication,)
    # parser_classes = (JSONParser, MultiPartParser)

    def get_queryset(self):
        """
        This view should return a list of all the Company for
        the user as determined by currently logged in user.
        """
        queryset = Company.objects.filter(enabled=True)
        return queryset
 
    def get_serializer_class(self):
        if self.action in ['retrieve',]:
            return CompanySerializer
        return CompanySerializer

    def perform_update(self, serializer):
        return serializer.save(updated_by_id=self.request.user.id)

    def perform_create(self, serializer):
        return serializer.save(updated_by_id=self.request.user.id)


class InterestedEMailViewSet(viewsets.ModelViewSet, AchieveModelMixin):
    permission_classes = (AllowAny, )
    authentication_classes = (TokenAuthentication,)
    parser_classes = (JSONParser, )
        
    def get_serializer_class(self):
        if self.action in ['create', 'update']:
            return InterestedEMailSerializer
        return InterestedEMailSerializer

    def get_queryset(self):
        """
        This view should return a list of all the Interested EMail
        """
         
        return InterestedEMail.objects.filter(enabled=True)
 
    def perform_create(self, serializer):
        return serializer.save()
        
    def perform_update(self, serializer):
        return serializer.save()
      
    @action(methods=['get'], detail=False, url_path='names', url_name='names')
    def names(self, request, *args, **kwargs):
        return Response(self.get_queryset().values_list('email', flat=True), status=status.HTTP_200_OK)


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
            queryset = queryset[:50]
            if (searchTerm != ''):
                queryset = queryset.filter(Q(user__first_name__icontains=searchTerm) |
                                           Q(user__last_name__icontains=searchTerm))

        return queryset

    def get_serializer_class(self):
        # print('********', self.request.method, "   ", self.action)
        if self.request.method in ['PUT']:
            # Since the ReadSerializer does nested lookups
            # in multiple tables, only use it when necessary
            return ProfileSerializer
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
        data = request.data.copy()
        
        print('-------')
        print(data)
        profile_reset_link = data.get('profile_reset_link', None)
        is_password_generated = not data['user'].get('password', None)
        data['user']['password'] = UserModel.objects.make_random_password() if is_password_generated else data['user']['password']
        # print(data)
        # data['address'] = data['address'] if data.get('address', None) else None
        serializer = self.get_serializer(data=data)
        print(type(serializer))
        print('----- b4')
        serializer.is_valid(raise_exception=True)
        print('----- after')
        profile = self.perform_create(serializer)

        headers = self.get_success_headers(serializer.data)

        # print(user)
        user = profile.user
        domain = get_domain(request)
        # send_access_token(self, token_length, domain, channel="email", action="Verify Email", extra={})

        if is_password_generated:
            user.force_password_change = True
            user.save()
            messages = f"Account Registration successful, activation link has been sent to: '{user.email}'"
            user.send_registration_password(domain, profile_reset_link)
            return Response({"message": messages, "user": serializer.data}, status=status.HTTP_201_CREATED, headers=headers)
        else:
            session_key = user.send_access_token(settings.AUTH_TOKEN_LENGTH, domain, "email", UserModel.ACCOUNT_ACTIVATION)
            request_url = f"{domain}{reverse('auths_api:activation-send', args=(user.pk,))}?action={UserModel.ACCOUNT_ACTIVATION}&channel={UserModel.EMAIL_CHANNEL}"
            activation_url = f"{domain}{reverse('auths_api:activation-activate', args=(user.pk, session_key))}"

            messages = f"Account activation Token successfully sent to '{user.email}'"
            data = {
                    "message": messages,
                    "user": serializer.data,
                    "resend_url": request_url,
                    "activation_url": activation_url
                }
            return Response(data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        with transaction.atomic():
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            data = request.data
            # print(data)
            user_instance = UserModel.objects.get(id=data['user']['id'])
            serializer = self.get_serializer(instance, data=request.data, partial=partial)

            address_data = data['address']
            address = Address.objects.filter(Q(id=address_data.get('id'))|Q(id=instance.address_id)).first()
            address_serializer = AddressSerializer(address, data=address_data, partial=partial)
            address_serializer.is_valid(raise_exception=True)
            address = address_serializer.save()

            user_serializer = UserUpdateSerializer(user_instance, data=data['user'], partial=partial)
            user_serializer.is_valid(raise_exception=True)

            user = user_serializer.save()

            serializer.is_valid(raise_exception=True)
            
            new_profile = self.perform_update(serializer)
            new_profile = self.get_object()
            new_profile.address_id = address.id
            new_profile.save()

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
        profile = request.user.user_profile
        return Response(ProfileSerializer(profile).data, status=status.HTTP_200_OK)

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
