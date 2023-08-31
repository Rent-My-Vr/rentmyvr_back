import json
import copy
import logging
import requests
from requests.utils import requote_uri
from uuid import UUID
from inspect import Attribute
from xml import dom
from pprint import pprint
from decouple import config
from django.conf import settings
from django.db import transaction
from django.shortcuts import render
from django.urls import reverse
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import viewsets, status, mixins, pagination
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser, FileUploadParser

from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Q, Prefetch
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import fromstr, Point, Polygon, GEOSGeometry
from django.contrib.gis.measure import Distance
from django.views import generic
from django.contrib.gis.db.models.functions import Distance as KMDistance
from django.template.loader import render_to_string

from auths.utils import get_domain
from auths_api.serializers import UserSerializer, UserUpdateSerializer
from notifications.signals import notify
from core.models import *
from core.utils import send_gmail
from core_api.pagination import MyPagination
from core_api.serializers import *
from core_api.models import *
from core.tasks import processPropertyEvents
from directory.models import *
from directory_api.serializers import *


log = logging.getLogger(f"{__package__}.*")
log.setLevel(settings.LOGGING_LEVEL)


class ManagerDirectoryViewSet(viewsets.ModelViewSet, AchieveModelMixin):
    permission_classes = (IsAuthenticated, )
    authentication_classes = (TokenAuthentication,)
    parser_classes = (JSONParser, MultiPartParser, FormParser)
    # parser_classes = (MultiPartParser, FormParser, JSONParser, FileUploadParser)
        
    def get_permissions(self):
        print('********', self.request.method, "   ", self.action)
        if self.action in ['search', 'retrieve']:
            return []  # This method should return iterable of permissions
        return super().get_permissions()

    def get_serializer_class(self):
        if self.action in ['search']:
            return ManagerDirectoryListSerializer
        return ManagerDirectorySerializer

    def get_queryset(self):
        """
        This view should return a list of all the Interested EMail
        """
         
        return ManagerDirectory.objects.filter(enabled=True)
 
    def perform_create(self, serializer):
        return serializer.save(updated_by_id=self.request.user.id)
        
    def perform_update(self, serializer):
        return serializer.save(updated_by_id=self.request.user.id)
    
    def create(self, request, *args, **kwargs):
        print('---- data----')
        print(request.data)
        
        # verifyServer = f"https://www.google.com/recaptcha/api/siteverify?secret={settings.RECAPTCHA_SECRET_KEY}&response={request.data.get('token')}"
        # r = requests.get(verifyServer)
        # print(r.json())
        # d = r.json()
        # print()
        
        profile = request.user.user_profile
        if request.user.position == UserModel.ADMIN and (profile.company is not None or profile.administrative_company is not None):
            data = request.data.dict()
            data['company'] = profile.company.id if profile.company else None
            
            data['city'] = dict()
            data['city']['id'] = data.get('city[id]', None)
            data['city']['name'] = data.get('city[name]')
            data['city']['state_name'] = data.get('city[state_name]')
            data['city']['country_name'] = data.get('city[country_name]')
            data['city']['approved'] = True if data['city']['id'] else False
            data['city_data'] = data['city']

            data.pop("city[id]", None)
            data.pop("city[imported]", None)
            data.pop("city[import_id]", None)
            data.pop("city[name]", None)
            data.pop("city[state_name]", None)
            data.pop("city[updated]", None)
            data.pop("city[created]", None)
            data.pop("city[country_name]", None)
            data.pop("city[approved]", None)
            data.pop("city[updated]", None)
            data.pop("city[created]", None)
            data.pop("city[approved]", None)
            
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
            data['social_links'] = request.data.getlist('social_links[]', [])
            
            serializer = self.get_serializer(data=data)
            serializer.is_valid(raise_exception=True)
            instance = self.perform_create(serializer)

            serializer = ManagerDirectoryListSerializer(instance)
            headers = self.get_success_headers(serializer.data)

            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        else:
            return Response({"message": "This is not authorised!!!"}, status=status.HTTP_403_FORBIDDEN)
        # if r.status_code == 200 and d.get("success") and float(d.get("score")) > 0.5:
        #     serializer = self.get_serializer(data=request.data)
        #     serializer.is_valid(raise_exception=True)
        #     instance = self.perform_create(serializer)

        #     headers = self.get_success_headers(serializer.data)

        #     return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        # else:
        #     return Response({"message": "Recaptcha validation failed"}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        print('---- data----')
        print(request.data)
        instance = self.get_object()
        
        profile = request.user.user_profile
        if (not request.user.is_manager and request.user.position == UserModel.ADMIN and (profile.company is not None or profile.administrative_company is not None) and (profile.company == instance.company or profile.administrative_company == instance.company)) or (request.user.is_manager and profile.company is not None and profile.company == instance.company):
            data = request.data.dict()
            
            data['city'] = dict()
            data['city']['id'] = data.get('city[id]', None)
            data['city']['name'] = data.get('city[name]')
            data['city']['state_name'] = data.get('city[state_name]')
            data['city']['country_name'] = data.get('city[country_name]')
            data['city']['approved'] = True if data['city']['id'] else False
            data['city_data'] = data['city']

            data.pop("city[id]", None)
            data.pop("city[imported]", None)
            data.pop("city[import_id]", None)
            data.pop("city[name]", None)
            data.pop("city[state_name]", None)
            data.pop("city[updated]", None)
            data.pop("city[created]", None)
            data.pop("city[country_name]", None)
            data.pop("city[approved]", None)
            
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
            data['social_links'] = request.data.getlist('social_links[]', [])
              
            if type(data['logo']) == str:
                data.pop('logo', None)
            
            print('==========')
            print(data)
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            
            print('==========', partial)
            serializer = self.get_serializer(instance, data=data, partial=partial)
            serializer.is_valid(raise_exception=True)
            instance = self.perform_update(serializer)

            serializer = ManagerDirectoryListSerializer(instance)
            headers = self.get_success_headers(serializer.data)

            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        else:
            return Response({"message": "This is not authorised!!!"}, status=status.HTTP_403_FORBIDDEN)
        # if r.status_code == 200 and d.get("success") and float(d.get("score")) > 0.5:
        #     serializer = self.get_serializer(data=request.data)
        #     serializer.is_valid(raise_exception=True)
        #     instance = self.perform_create(serializer)

        #     headers = self.get_success_headers(serializer.data)

        #     return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        # else:
        #     return Response({"message": "Recaptcha validation failed"}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['get'], detail=False, url_path='me', url_name='me')
    def me(self, request, *args, **kwargs):
        p = request.user.user_profile
        md = ManagerDirectory.objects.filter(Q(company__administrator=p, administrator__user__is_manager=False) | Q(company__members=p), enabled=True).first()
        # company = ManagerDirectory.objects.filter(Q(company__administrator=p) | Q(company__members=p), enabled=True).prefetch_related(
        #     Prefetch('offices', queryset=Office.objects.filter(enabled=True).prefetch_related(
        #         Prefetch('properties', queryset=Property.objects.filter(enabled=True)))), 
        #     Prefetch('portfolios', queryset=Portfolio.objects.filter(enabled=True).prefetch_related(
        #         Prefetch('portfolio_properties', queryset=Property.objects.filter(enabled=True)))),
        #     Prefetch('members', queryset=Profile.objects.filter(enabled=True).prefetch_related(
        #         Prefetch('portfolios', queryset=Portfolio.objects.filter(enabled=True)),
        #         Prefetch('offices', queryset=Office.objects.filter(enabled=True))))
        # ).first()
        if md:
            return Response(ManagerDirectorySerializer(md).data, status=status.HTTP_200_OK)
        else:
            return Response(None, status=status.HTTP_200_OK)
        
    @action(methods=['get'], detail=False, url_path='names', url_name='names')
    def names(self, request, *args, **kwargs):
        return Response(self.get_queryset().values_list('email', flat=True), status=status.HTTP_200_OK)

    @action(methods=['post'], detail=False, url_path='search', url_name='search')
    def search(self, request, *args, **kwargs):
        print('----00000---')
        print(request.data)
        data = request.data
        
        qs = Company.objects.filter(enabled=True, mdl__is_active=True, mdl__is_published=True)
        if len(data.get('state', '')) > 0:
            print('1. ', data.get('state'))
            qs = qs.filter(mdl__state__icontains=data.get('state'))
        if len(data.get('city', '')) > 0:
            print('2. ', data.get('state'))
            qs = qs.filter(mdl__city__name__icontains=data.get('city'))
        if len(data.get('zip_code', '')) > 0:
            qs = qs.filter(mdl__zip_code=data.get('zip_code'))
            
        qs = qs.prefetch_related(
            Prefetch('offices', queryset=Office.objects.filter(enabled=True).prefetch_related(
                Prefetch('properties', queryset=Property.objects.filter(enabled=True)))), 
            Prefetch('portfolios', queryset=Portfolio.objects.filter(enabled=True).prefetch_related(
                Prefetch('properties', queryset=Property.objects.filter(enabled=True)))),
            Prefetch('members', queryset=Profile.objects.filter(enabled=True).prefetch_related(
                Prefetch('member_portfolios', queryset=Portfolio.objects.filter(enabled=True)),
                Prefetch('member_offices', queryset=Office.objects.filter(enabled=True)))),
            Prefetch('invitations', queryset=Invitation.objects.filter(enabled=True))
        )
        print(qs.query)
        if request.query_params.get("limit", None):
            qs = qs[:int(request.query_params.get("limit"))]
        return Response(CompanyMDLDetailSerializer(qs, many=True).data)

    @action(methods=['patch', 'post'], detail=True, url_path='publisher', url_name='publish')
    def publisher(self, request, *args, **kwargs):
        instance = self.get_object()
        profile = request.user.user_profile
        if instance.company != profile.company or (instance.company.administrator != profile and not profile.user.is_manager):
            return Response({"message": "You are not authorised to perform this action", "required": []}, status=status.HTTP_403_FORBIDDEN)
        
        instance.is_published = not instance.is_published
        instance.save()
        
        return Response(ManagerDirectoryListSerializer(instance=instance).data)
    

class OfficeViewSet(viewsets.ModelViewSet, AchieveModelMixin):
    permission_classes = (IsAuthenticated, )
    authentication_classes = (TokenAuthentication,)
    parser_classes = (MultiPartParser, FormParser, JSONParser, FileUploadParser)
    
    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return OfficeDetailSerializer
        return OfficeSerializer

    def get_queryset(self):
        """
        This view should return a list of all the Interested EMail
        """
         
        return Office.objects.filter(enabled=True)
 
    def get_permissions(self):
        if self.action in ['check_name']:
            return []  # This method should return iterable of permissions
        return super().get_permissions()

    def perform_create(self, serializer):
        return serializer.save(updated_by_id=self.request.user.id)
        
    def perform_update(self, serializer):
        return serializer.save(updated_by_id=self.request.user.id)
    
    def create(self, request, *args, **kwargs):
        with transaction.atomic():
            data = request.data
            print(data)
            if data and data.get('city', {}).get('id', None):
                s = State.objects.filter(country__id=data.get('country').get('id'), name=data.get('state')).first()
                data['state'] = s.id if s else s
                data['city'] = data.get('city').get('id')
            else:
                print('====Create City****')
                ser = CitySerializer(data=data.get('city'))
                ser.is_valid(raise_exception=True)
                inst = ser.save()
                s = State.objects.filter(country__id=data.get('country').get('id'), name=data.get('state')).first()
                data['state'] = s.id if s else s
                data['city'] = inst.id
            
            profile = request.user.user_profile
            data['administrator'] = profile.id
            data['company'] = profile.company.id
            pids = data.get('properties', [])
            
            print('======================================')
            print(data)
            print(pids)
            serializer = self.get_serializer(data=data)
            serializer.is_valid(raise_exception=True)
            instance = self.perform_create(serializer)
            
            for property in Property.objects.filter(Q(Q(company__isnull=False, company=instance.company) | Q(administrator=profile, administrator__user__is_manager=False)), enabled=True, id__in=pids):
                property.office = instance
                property.save()

            serializer = OfficeDetailSerializer(instance)
            headers = self.get_success_headers(serializer.data)

            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        
        # print(request.data)
        # verifyServer = f"https://www.google.com/recaptcha/api/siteverify?secret={settings.RECAPTCHA_SECRET_KEY}&response={request.data.get('token')}"
        # r = requests.get(verifyServer)
        # print(r.json())
        # d = r.json()
        # # print()
        
        # if r.status_code == 200 and d.get("success") and float(d.get("score")) > 0.5:
        #     serializer = self.get_serializer(data=request.data)
        #     serializer.is_valid(raise_exception=True)
        #     instance = self.perform_create(serializer)

        #     headers = self.get_success_headers(serializer.data)

        #     return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        # else:
        #     return Response({"message": "Recaptcha validation failed"}, status=status.HTTP_400_BAD_REQUEST)
      
    def update(self, request, *args, **kwargs):
        with transaction.atomic():
            data = request.data
            print(data)
            if data.get('city').get('id', None):
                print('====Have City****')
                s = State.objects.filter(country__id=data.get('country', {}).get('id'), name=data.get('state')).first()
                data['state'] = s.id if s else State.objects.filter(country__name=data.get('city', {}).get('country_name'), name=data.get('state')).first().id
                data['city'] = data.get('city').get('id')
            else:
                print('====Create City****')
                ser = CitySerializer(data=data.get('city'))
                ser.is_valid(raise_exception=True)
                inst = ser.save()
                s = State.objects.filter(country__id=data.get('country').get('id'), name=data.get('state')).first()
                data['state'] = s.id if s else s
                data['city'] = inst.id
                    
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            
            profile = request.user.user_profile
            data['administrator'] = instance.administrator.id if not instance.administrator.user.is_manager else profile.id
            data['company'] = instance.company.id if instance.company else profile.company.id
            pids = data.get('properties', [])
            
            serializer = self.get_serializer(instance, data=data, partial=partial)
            
            serializer.is_valid(raise_exception=True)
            instance = self.perform_update(serializer)

            Property.objects.filter(office=instance).update(office=None)
            for property in Property.objects.filter(Q(Q(company__isnull=False, company=instance.company) | Q(administrator=profile, administrator__user__is_manager=False)), enabled=True, id__in=pids):
                property.office = instance
                property.save()
            serializer = OfficeDetailSerializer(instance)

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        return Response(serializer.data, status=status.HTTP_201_CREATED)
  
    @action(methods=['get'], detail=False, url_path='names', url_name='names')
    def names(self, request, *args, **kwargs):
        return Response(self.get_queryset().values_list('email', flat=True), status=status.HTTP_200_OK)
    
    @action(methods=['get'], detail=False, url_path='check/name', url_name='check-name')
    def check_name(self, request, *args, **kwargs):
        key = request.query_params.get('key', None)
        result = None
        kind = None
        if key:
            if key.startswith('F'):
                kind = 'Portfolio'
                result = Portfolio.objects.values('name', 'ref', 'company__name', 'company__ref').filter(ref=key).first()
            elif key.startswith('O'):
                kind = 'Office'
                result = Office.objects.values('name', 'ref', 'company__name', 'company__ref').filter(ref=key).first()
            elif key.startswith('C'):
                kind = 'Company'
                result = Company.objects.values('name', 'ref').filter(ref=key).first()
        if result:
            result['type'] = kind
            if kind in ['Office', 'Portfolio']:
                result['company'] = {'name': result['company__name'], 'ref': result['company__ref']}
                result.pop('company__name', None)
                result.pop('company__ref', None)
            print('....', result)
            
        return Response(result, status=status.HTTP_200_OK)
        
    @action(methods=['post'], detail=True, url_path='delete/member/(?P<mid>[0-9A-Fa-f-]+)', url_name='delete-member')
    def delete_member(self, request, *args, **kwargs):
        instance = self.get_object()
        p = request.user.user_profile
        
        if p.company is not None:
            if  instance.company == p.company:
                profile = Profile.objects.filter(id=kwargs['mid']).first()
                if profile is not None and (profile.company == p.company or profile.company is None) and (instance in profile.offices.all() or (instance.administrator == profile and not profile.user.is_manager)):
                    if instance.administrator == profile:
                        return Response({'message': 'You cannot evict the Administrator'}, status=status.HTTP_403_FORBIDDEN)
                        
                    removed = profile.offices.remove(instance)
                    print('Removed..... ', removed)
                    # profile.save()
                    
                    return Response({'message': 'Member is successfully Removed'}, status=status.HTTP_200_OK)
                else:    
                    return Response({'message': 'You are not authorised to perform this operation'}, status=status.HTTP_400_BAD_REQUEST)
            else:    
                return Response({'message': f'Only authorised members of the {instance.company} can perform this operation'}, status=status.HTTP_403_FORBIDDEN)
        else:    
            return Response({'message': 'You are not authorised to perform this operation.'}, status=status.HTTP_403_FORBIDDEN)
   

class PortfolioViewSet(viewsets.ModelViewSet, AchieveModelMixin):
    permission_classes = (IsAuthenticated, )
    authentication_classes = (TokenAuthentication,)
    parser_classes = (MultiPartParser, FormParser, JSONParser, FileUploadParser)
        
    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return PortfolioDetailSerializer
        return PortfolioSerializer

    def get_queryset(self):
        """
        This view should return a list of all the Interested EMail
        """
         
        return Portfolio.objects.filter(enabled=True)
 
    def perform_create(self, serializer):
        return serializer.save(updated_by_id=self.request.user.id)
        
    def perform_update(self, serializer):
        return serializer.save(updated_by_id=self.request.user.id)
    
    def create(self, request, *args, **kwargs):
        # print(request.data)
        # verifyServer = f"https://www.google.com/recaptcha/api/siteverify?secret={settings.RECAPTCHA_SECRET_KEY}&response={request.data.get('token')}"
        # r = requests.get(verifyServer)
        # print(r.json())
        # d = r.json()
        # # print()
        
        # if r.status_code == 200 and d.get("success") and float(d.get("score")) > 0.5:
        data = request.data
        
        with transaction.atomic():
            profile = request.user.user_profile
            data['administrator'] = profile.id
            data['company'] = profile.company.id
            pids = data.get('properties', [])
            
            print(data)
            serializer = self.get_serializer(data=data)
            serializer.is_valid(raise_exception=True)
            instance = self.perform_create(serializer)
            
            for property in Property.objects.filter(Q(Q(company__isnull=False, company=instance.company) | Q(administrator=profile, administrator__user__is_manager=False)), enabled=True, id__in=pids):
                property.portfolio = instance
                property.save()
            
            serializer = PortfolioDetailSerializer(instance)
            headers = self.get_success_headers(serializer.data)

        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        # else:
        #     return Response({"message": "Recaptcha validation failed"}, status=status.HTTP_400_BAD_REQUEST)
        
    def update(self, request, *args, **kwargs):
        with transaction.atomic():
            data = request.data
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            
            profile = request.user.user_profile
            data['administrator'] = instance.administrator.id if request.user.is_manager else profile.id
            data['company'] = instance.company.id if request.user.is_manager else profile.company.id
            pids = data.get('properties', [])
            
            serializer = self.get_serializer(instance, data=data, partial=partial)
            serializer.is_valid(raise_exception=True)
            instance = serializer.save()
            
            Property.objects.filter(portfolio=instance).update(portfolio=None)
            for property in Property.objects.filter(Q(Q(company__isnull=False, company=instance.company) | Q(administrator=profile, administrator__user__is_manager=False)), enabled=True, id__in=pids):
                property.portfolio = instance
                property.save()

            serializer = PortfolioDetailSerializer(instance)

            if getattr(instance, '_prefetched_objects_cache', None):
                # If 'prefetch_related' has been applied to a queryset, we need to
                # forcibly invalidate the prefetch cache on the instance.
                instance._prefetched_objects_cache = {}

            return Response(serializer.data, status=status.HTTP_201_CREATED)
  
    @action(methods=['get'], detail=False, url_path='names', url_name='names')
    def names(self, request, *args, **kwargs):
        return Response(self.get_queryset().values_list('email', flat=True), status=status.HTTP_200_OK)

    @action(methods=['post'], detail=True, url_path='delete/member/(?P<mid>[0-9A-Fa-f-]+)', url_name='delete-member')
    def delete_member(self, request, *args, **kwargs):
        instance = self.get_object()
        p = request.user.user_profile
        
        if p.company is not None:
            if  instance.company == p.company:
                profile = Profile.objects.filter(id=kwargs['mid']).first()
                if profile is not None and (profile.company == p.company or profile.company is None) and (instance in profile.portfolios.all() or (instance.administrator == profile and not profile.user.is_manager)):
                    if instance.administrator == profile:
                        return Response({'message': 'You cannot evict the Administrator'}, status=status.HTTP_403_FORBIDDEN)
                        
                    removed = profile.portfolios.remove(instance)
                    print('Removed..... ', removed)
                    # profile.save()
                    
                    return Response({'message': 'Member is successfully Removed'}, status=status.HTTP_200_OK)
                else:    
                    return Response({'message': 'You are not authorised to perform this operation'}, status=status.HTTP_400_BAD_REQUEST)
            else:    
                return Response({'message': f'Only authorised members of the {instance.company} can perform this operation'}, status=status.HTTP_403_FORBIDDEN)
        else:    
            return Response({'message': 'You are not authorised to perform this operation.'}, status=status.HTTP_403_FORBIDDEN)
   

class InquiryMessageViewSet(viewsets.ModelViewSet, AchieveModelMixin):
    permission_classes = (AllowAny, )
    authentication_classes = (TokenAuthentication,)
    parser_classes = (JSONParser, )
        
    def get_serializer_class(self):
        # if self.action in ['create', 'update']:
        #     return ContactSerializer
        return InquiryMessageSerializer

    def get_queryset(self):
        """
        This view should return a list of all the Interested EMail
        """
         
        return InquiryMessage.objects.filter(enabled=True)
 
    def perform_create(self, serializer):
        return serializer.save()
        
    def perform_update(self, serializer):
        return serializer.save()
    
    def create(self, request, *args, **kwargs):
        print(request.data)
        verifyServer = f"https://www.google.com/recaptcha/api/siteverify?secret={settings.RECAPTCHA_SECRET_KEY}&response={request.data.get('token')}"
        r = requests.get(verifyServer)
        print(r.json())
        d = r.json()
        # print()
        
        if r.status_code == 200 and d.get("success") and float(d.get("score")) > 0.5:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            instance = self.perform_create(serializer)

            headers = self.get_success_headers(serializer.data)

            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        else:
            return Response({"message": "Recaptcha validation failed"}, status=status.HTTP_400_BAD_REQUEST)
        
    @action(methods=['get'], detail=False, url_path='names', url_name='names')
    def names(self, request, *args, **kwargs):
        return Response(self.get_queryset().values_list('email', flat=True), status=status.HTTP_200_OK)


# https://github.com/andrewramsay/ical_to_gcal_sync/blob/master/config.py.example
class PropertyViewSet(viewsets.ModelViewSet, AchieveModelMixin):
    pagination_class = MyPagination
    # pagination_class = api_settings.DEFAULT_PAGINATION_CLASS
    permission_classes = (IsAuthenticated, )
    authentication_classes = (TokenAuthentication,)
    parser_classes = (MultiPartParser, FormParser, JSONParser, FileUploadParser)
        
    def get_queryset(self):
        """
        This view should return a list of all the Company for
        the user as determined by currently logged in user.
        """
        queryset = Property.objects.filter(enabled=True)
        return queryset
 
    def get_permissions(self):
        if self.action in ['form_items', 'search', 'retrieve']:
            return []  # This method should return iterable of permissions
        return super().get_permissions()

    def get_serializer_class(self):
        if self.action in ['retrieve']:
            return PropertyDetailSerializer
        elif self.action in ['list', 'publisher', 'our_list']:
            return PropertyListSerializer
        elif self.action in ['search']:
            return PropertySearchResultSerializer
        return PropertySerializer

    # def get_page_size(self, request):
    #     if _has_valid_filters(request.query_params.items()):
    #         return 200
    #     else:
    #         return 100
    def perform_create(self, serializer):
        return serializer.save(updated_by_id=self.request.user.id)
        
    def perform_update(self, serializer):
        return serializer.save(updated_by_id=self.request.user.id)
      
    #   TODO: Fix Country_name
    def create(self, request, *args, **kwargs):
        with transaction.atomic():
            print('============ 0 =============')
            print(request.data)
            print('============ 1 =============')
            
            data = dict()
            for d in list(request.data.keys()):
                data[d] = request.data.getlist(d) if '[]' in d else request.data[d]
            # pictures = request.data.getlist('pictures[]')
            # print(pictures)
            print('============ 2 =============')
            # data = copy.deepcopy(request.data)
            print(data)
            # data = request.data.copy()
            print('============ 3333 =============')
            
            # data['address'] = {}
            # data['address']['id'] = request.data.get('address[id]', None)
            # data['address']['type'] = request.data.get('address[type]', None)
            data['location'] = dict()
            data['location']['type'] = request.data.get('location[type]', None)
            data['location']['coordinates'] = [float(request.data.get('location[coordinates][0]', 0)), float(request.data.get('location[coordinates][1]', 0))]
            # data['address']['properties'] = dict()
            # data['address']['properties']['formatted'] = request.data.get('address[properties][formatted]')
            # data['address']['properties']['country_name'] = request.data.get('address[properties][country]')
            # data['address']['properties']['street'] = request.data.get('address[properties][street]')
            # data['address']['properties']['number'] = request.data.get('address[properties][number]')
            # data['address']['properties']['zip_code'] = request.data.get('address[properties][zip_code]')
            # data['address']['properties']['state'] = request.data.get('address[properties][state]')
            # data['address']['properties']['hidden'] = request.data.get('address[properties][hidden]')
            # data['address']['properties']['more_info'] = request.data.get('address[properties][more_info]')
            # data['address']['properties']['city'] = dict()
            # data['address']['properties']['city']['id'] = request.data.get('address[properties][city][id]', None)
            # data['address']['properties']['city']['imported'] = request.data.get('address[properties][city][imported]', False)
            # data['address']['properties']['city']['import_id'] = request.data.get('address[properties][city][import_id]', None)
            data['city'] = dict()
            data['city']['id'] = data.get('city[id]')
            data['city']['name'] = data.get('city[name]')
            data['city']['state_name'] = data.get('city[state_name]')
            data['city']['country_name'] = data.get('country[name]')
            data['city']['approved'] = True if data['city']['id'] else False
            data['country'] = dict()
            data['country']['id'] = data.get('country[id]')
            data['country']['name'] = data.get('country[name]')
            s = State.objects.filter(country__id=data.get('country', {}).get('id'), name=data.get('state')).first()
            data['state'] = s.id if s else State.objects.filter(country__name=data.get('city', {}).get('country_name'), name=data.get('state')).first().id
            data['city_data'] = data['city']
            
            # data.pop("address[id]", None)
            # data.pop("address[type]", None)
            data.pop("location[type]", None)
            data.pop("location[coordinates][0]", None)
            data.pop("location[coordinates][1]", None)
            # data.pop("address[properties][formatted]", None)
            # data.pop("address[properties][more_info]", None)
            # data.pop("address[properties][street]", None)
            # data.pop("address[properties][number]", None)
            # data.pop("address[properties][zip_code]", None)
            # data.pop("address[properties][state]", None)
            # data.pop("address[properties][hidden]", None)
            data.pop("city[id]", None)
            data.pop("city[imported]", None)
            data.pop("city[import_id]", None)
            data.pop("city[name]", None)
            data.pop("city[state_name]", None)
            data.pop("city[updated]", None)
            data.pop("city[created]", None)
            data.pop("city[country_name]", None)
            data.pop("city[approved]", None)
            data.pop("country[id]", None)
            data.pop("country[name]", None)
            print(data)
            print(data.get('booking_sites[]'))
            
            booking_sites_set = set()
            social_media_set = set()
            # pictures_set = set()
            suitabilities_set = set()
            room_types_set = set()
            room_types_dict = dict()
            max_sleeper = 0
            
            for k in data.keys():
                print(k)
                if f'booking_sites[' in k:
                    booking_sites_set.add(re.findall(r"^booking_sites\[(\d+)\]\[\w+\]", k)[0])
                elif f'social_media[' in k:
                    social_media_set.add(re.findall(r"^social_media\[(\d+)\]\[\w+\]$", k)[0])
                elif f'suitabilities[' in k:
                    suitabilities_set.add(re.findall(r"^suitabilities\[(\d+)\]\[\w+\]$", k)[0])
                elif f'room_types[' in k:
                    r = re.findall(r"^room_types\[(\d+)\]\[(\w+)\]\[(\d+)\]\[(\w+)\]$", k)
                    if len(r) > 0:
                        r = r[0]
                        # max_sleeper = int(r[2]) if int(r[2]) > max_sleeper else max_sleeper
                        if room_types_dict.get(r[0], -10) == -10:
                            room_types_dict[r[0]] = int(r[2])
                        else:
                            room_types_dict[r[0]] = room_types_dict[r[0]] if room_types_dict[r[0]] > int(r[2]) else int(r[2])
                    else:
                        # room_types_set.add(re.findall(r"^room_types\[(\d+)\]\[\w+\]$", k)[0])
                        d = re.findall(r"^room_types\[(\d+)\]\[\w+\]$", k)[0]
                        if room_types_dict.get(d, -10) == -10:
                            room_types_dict[d] = 0

            print('booking_sites_set: ', booking_sites_set)
            print('booking_sites_set_length: ', len(booking_sites_set))
            print('social_media_set_length: ', len(social_media_set))
            print('room_types_set_length: ', len(room_types_set))
            print('room_types_dict: ', room_types_dict)
            print('max_sleeper: ', max_sleeper)
            
            room_types = []
            for i in range(len(room_types_dict.keys())):
                d = dict()
                d['name'] = data[f'room_types[{i}][name]']
                d['label'] = data[f'room_types[{i}][label]']
                d['property'] = None
                data.pop(f'room_types[{i}][name]', None)
                data.pop(f'room_types[{i}][label]', None)
                
                d['sleepers'] = []
                for j in range(room_types_dict[str(i)]+1):
                    try:
                        d['sleepers'].append(data[f'room_types[{i}][sleepers][{j}][id]'])
                        # d['sleepers'].append({
                        #     "id": data[f'room_types[{i}][sleepers][{j}][id]'],
                        #     "name": data[f'room_types[{i}][sleepers][{j}][name]']
                        # })
                        data.pop(f'room_types[{i}][sleepers][{j}][id]', None)
                        data.pop(f'room_types[{i}][sleepers][{j}][name]', None)
                    except KeyError as ke:
                        pass
                room_types.append(d)
            
            booking_sites = []
            for i in range(len(booking_sites_set)):
                d = dict()
                d['site'] = data[f'booking_sites[{i}][site]']
                d['booker'] = data[f'booking_sites[{i}][booker]']
                # d['booker']['id'] = data[f'booking_sites[{i}][booker][id]']
                # d['booker']['base'] = data[f'booking_sites[{i}][booker][base]']
                # d['booker']['name'] = data[f'booking_sites[{i}][booker][name]']
                d['property'] = None
                
                data.pop(f'booking_sites[{i}][site]', None)
                data.pop(f'booking_sites[{i}][booker]', None)
                # data.pop(f'booking_sites[{i}][booker][id]', None)
                # data.pop(f'booking_sites[{i}][booker][base]', None)
                # data.pop(f'booking_sites[{i}][booker][name]', None)
                
                booking_sites.append(d)
                # ser = BookingSiteSerializer(data=d)
                # ser.is_valid(raise_exception=True)
                # ser.save(updated_by_id=self.request.user.id) 
            
            social_media = []
            for i in range(len(social_media_set)):
                d = dict()
                d['name'] = data[f'social_media[{i}][name]']
                data.pop(f'social_media[{i}][name]', None)
                d['site'] = data[f'social_media[{i}][site]']
                data.pop(f'social_media[{i}][site]', None)
                d['label'] = data[f'social_media[{i}][label]']
                data.pop(f'social_media[{i}][label]', None)
                d['property'] = None
                social_media.append(d)
                # ser = SocialMediaLinkSerializer(data=d)
                # ser.is_valid(raise_exception=True)
                # ser.save(updated_by_id=self.request.user.id) 
              
            suitabilities = []
            for i in range(len(suitabilities_set)):
                d = dict()
                d['id'] = data.get(f'suitabilities[{i}][id]', None)
                d['label'] = data.get(f'suitabilities[{i}][label]', None)
                d['days'] = data.get(f'suitabilities[{i}][days]', None)
                
                data.pop(f'suitabilities[{i}][id]', None)
                data.pop(f'suitabilities[{i}][label]', None)
                data.pop(f'suitabilities[{i}][days]', None)
                
                suitabilities.append(d)

            data['accessibility'] = data.get('accessibility[]', [])
            data.pop(f'accessibility[]', None)
            data['activities'] = data.get('activities[]', [])
            data.pop(f'activities[]', None)
            data['bathrooms'] = data.get('bathrooms[]', [])
            data.pop(f'bathrooms[]', None)
            data['entertainments'] = data.get('entertainments[]', [])
            data.pop(f'entertainments[]', None)
            data['essentials'] = data.get('essentials[]', [])
            data.pop(f'essentials[]', None)
            data['families'] = data.get('families[]', [])
            data.pop(f'families[]', None)
            data['features'] = data.get('features[]', [])
            data.pop(f'features[]', None)
            data['kitchens'] = data.get('kitchens[]', [])
            data.pop(f'kitchens[]', None)
            data['laundries'] = data.get('laundries[]', [])
            data.pop(f'laundries[]', None)
            data['outsides'] = data.get('outsides[]', [])
            data.pop(f'outsides[]', None)
            data['parking'] = data.get('parking[]', [])
            data.pop(f'parking[]', None)
            data['pool_spas'] = data.get('pool_spas[]', [])
            data.pop(f'pool_spas[]', None)
            data['safeties'] = data.get('safeties[]', [])
            data.pop(f'safeties[]', None)
            data['spaces'] = data.get('spaces[]', [])
            data.pop(f'spaces[]', None)
            data['services'] = data.get('services[]', [])
            data.pop(f'services[]', None)
            
            data['booking_sites'] = booking_sites
            data['social_media'] = social_media
            data['room_types'] = room_types
            data['suitabilities'] = suitabilities
            print('============ *3* =============')
            print(data)
            if not data.get('video'):
                data['logo'] = None
                data['video'] = None
                data['virtual_tour'] = None
            # print('----------------')
            # print(data.get('address'))
            # print('============ 4 =============')

            profile = request.user.user_profile
            data['administrator'] = profile.id
            if profile.company:
                data['company'] = profile.company.id
                print(profile.id, ' P:::C ', profile.company.id,'  ============ *****= + =***** =============') 
            print(data)
            
            serializer = PropertySerializer(data=data, context={'city_data': data['city_data']})
            print('============ 5 =============')
            serializer.is_valid(raise_exception=True)
            print('============ 6 =============')
            instance = self.perform_create(serializer)
            print('============ 7 =============')
            print(instance)
            print(type(instance))
            for rtd in room_types:
                rtd['property'] = instance.id
                ser = RoomTypeSerializer(data=rtd)
                ser.is_valid(raise_exception=True)
                rt = ser.save()
                print(rt)
                print(RoomTypeSerializer(instance=rt).data)
            isFirst = True
            for p in request.data.getlist('pictures[]'):
                ser = PropertyPhotoSerializer(data={'image': p, "property": instance.id, 'is_default': isFirst })
                ser.is_valid(raise_exception=True)
                pic = self.perform_create(ser)
                isFirst = False
            print('============ 8 =============')
            
            cal = Calendar(name=instance.name, slug=instance.ref)
            cal.save()
            instance.calendar = cal
            instance.save()

            if instance.ical_url:
                print('========>>>> Send processPropertyEvents()')
                processPropertyEvents.apply_async(kwargs={'calendar_id': cal.id, 'calendar_url': instance.ical_url})
            data = PropertySerializer(instance).data
            if request.data.get('paying', None):
                data['paying'] = instance.id
            return Response(data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        with transaction.atomic():
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            ical_old = instance.ical_url
            print('============ 0 update =============')
            print(request.data)
            print('============ 1 update =============')
            
            data = dict()
            for d in list(request.data.keys()):
                print(d)
                data[d] = request.data.getlist(d) if '[]' in d else request.data[d]

            # data['address'] = {}
            # data['address']['id'] = request.data.get('address[id]', None)
            # data['address']['type'] = request.data.get('address[type]', None)
            data['location'] = dict()
            data['location']['type'] = request.data.get('location[type]', None)
            data['location']['coordinates'] = [float(request.data.get('location[coordinates][0]', 0)), float(request.data.get('location[coordinates][1]', 0))]
            # data['address']['properties'] = dict()
            country = request.data.get('country_name')
            # data['address']['properties']['formatted'] = request.data.get('address[properties][formatted]')
            # data['address']['properties']['country_name'] = country if country else 'United States'
            # data['address']['properties']['street'] = request.data.get('address[properties][street]')
            # data['address']['properties']['number'] = request.data.get('address[properties][number]')
            # data['address']['properties']['zip_code'] = request.data.get('address[properties][zip_code]')
            # data['address']['properties']['state'] = request.data.get('address[properties][state]')
            # data['address']['properties']['hidden'] = request.data.get('address[properties][hidden]')
            # data['address']['properties']['more_info'] = request.data.get('address[properties][more_info]')
            data['city'] = dict()
            data['city']['id'] = request.data.get('city[id]', None)
            data['city']['imported'] = request.data.get('city[imported]', False)
            data['city']['import_id'] = request.data.get('city[import_id]', None)
            data['city']['name'] = request.data.get('city[name]')
            data['city']['state_name'] = request.data.get('city[state_name]')
            country = request.data.get('city[country_name]')
            data['city']['country_name'] = country if country else 'United States'
            data['city']['approved'] = True if data['city']['id'] else False
            data['city_data'] = data['city']
            # data['address']['properties']['city'] = data['address']['properties']['city'].get('id', None) if data['address']['properties']['city'].get('id', None) else None

            # data.pop("address[id]", None)
            # data.pop("address[type]", None)
            data.pop("location[type]", None)
            data.pop("location[coordinates][0]", None)
            data.pop("location[coordinates][1]", None)
            # data.pop("address[properties][formatted]", None)
            # data.pop("address[properties][more_info]", None)
            # data.pop("address[properties][country_name]", None)
            # data.pop("address[properties][street]", None)
            # data.pop("address[properties][number]", None)
            # data.pop("address[properties][zip_code]", None)
            # data.pop("address[properties][state]", None)
            # data.pop("address[properties][hidden]", None)
            data.pop("city[id]", None)
            data.pop("city[imported]", None)
            data.pop("city[import_id]", None)
            data.pop("city[name]", None)
            data.pop("city[state_name]", None)
            data.pop("city[updated]", None)
            data.pop("city[created]", None)
            data.pop("city[country_name]", None)
            data.pop("city[approved]", None)
            
            # print(data)
            # print(data.get('booking_sites[]'))
            
            booking_sites_set = set()
            social_media_set = set()
            # pictures_set = set()
            suitabilities_set = set()
            room_types_set = set()
            room_types_dict = dict()
            max_sleeper = 0
            for k in data.keys():
                if f'booking_sites[' in k:
                    booking_sites_set.add(re.findall(r"^booking_sites\[(\d+)\]\[\w+\]", k)[0])
                elif f'social_media[' in k:
                    social_media_set.add(re.findall(r"^social_media\[(\d+)\]\[\w+\]$", k)[0])
                # elif f'pictures[' in k:
                #     if k != 'pictures[]':
                #         pictures_set.add(re.findall(r"^pictures\[(\d+)\]", k)[0])
                #         # pictures_set.add(re.findall(r"^pictures\[(\d+)\]\[\w+\]$", k)[0])
                elif f'suitabilities[' in k:
                    suitabilities_set.add(re.findall(r"^suitabilities\[(\d+)\]\[\w+\]$", k)[0])
                elif f'room_types[' in k:
                    r = re.findall(r"^room_types\[(\d+)\]\[(\w+)\]\[(\d+)\]\[(\w+)\]$", k)
                    if len(r) > 0:
                        r = r[0]
                        # max_sleeper = int(r[2]) if int(r[2]) > max_sleeper else max_sleeper
                        if room_types_dict.get(r[0], -10) == -10:
                            room_types_dict[r[0]] = int(r[2])
                        else:
                            room_types_dict[r[0]] = room_types_dict[r[0]] if room_types_dict[r[0]] > int(r[2]) else int(r[2])
                    else:
                        # room_types_set.add(re.findall(r"^room_types\[(\d+)\]\[\w+\]$", k)[0])
                        d = re.findall(r"^room_types\[(\d+)\]\[\w+\]$", k)[0]
                        if room_types_dict.get(d, -10) == -10:
                            room_types_dict[d] = 0

            print('booking_sites_set: ', booking_sites_set)
            print('booking_sites_set_length: ', len(booking_sites_set))
            print('social_media_set_length: ', len(social_media_set))
            # print('pictures_set_length: ', len(pictures_set))
            print('social_media_set_length: ', len(social_media_set))
            print('room_types_set_length: ', len(room_types_set))
            print('room_types_dict: ', room_types_dict)
            print('max_sleeper: ', max_sleeper)
            
            id = request.data.get('id')
            
            rt_ids = []
            for i in range(len(room_types_dict.keys())):
                d = dict()
                d['id'] = data.get(f'room_types[{i}][id]', None)
                d['name'] = data[f'room_types[{i}][name]']
                d['label'] = data.get(f'room_types[{i}][label]', None)
                d['property'] = data.get(f'room_types[{i}][property]', id)
                
                data.pop(f'room_types[{i}][id]', None)
                data.pop(f'room_types[{i}][name]', None)
                data.pop(f'room_types[{i}][label]', None)
                data.pop(f'room_types[{i}][property]', None)
                
                d['sleepers'] = []
                for j in range(room_types_dict[str(i)]+1):
                    try:
                        d['sleepers'].append(data[f'room_types[{i}][sleepers][{j}][id]'])
                        data.pop(f'room_types[{i}][sleepers][{j}][id]', None)
                        data.pop(f'room_types[{i}][sleepers][{j}][name]', None)
                    except KeyError as ke:
                        pass
                
                inst = RoomType.objects.filter(id=d.get('id', None))
                if len(inst) == 0:
                    ser = RoomTypeSerializer(data=d)
                else:
                    inst = inst.first()
                    ser = RoomTypeSerializer(inst, data=d, partial=partial)
                ser.is_valid(raise_exception=True)
                inst = ser.save()
                rt_ids.append(inst.id)
            RoomType.objects.filter(~Q(id__in=rt_ids), property=instance).delete()
            
            b_ids = []
            for i in range(len(booking_sites_set)):
                d = dict()
                d['id'] = data.get(f'booking_sites[{i}][id]', None)
                d['site'] = data[f'booking_sites[{i}][site]']
                d['booker'] = data[f'booking_sites[{i}][booker]']
                d['property'] = data.get(f'booking_sites[{i}][property]', id)
                
                data.pop(f'booking_sites[{i}][id]', None)
                data.pop(f'booking_sites[{i}][site]', None)
                data.pop(f'booking_sites[{i}][booker]', None)
                data.pop(f'booking_sites[{i}][property]', None)
                
                inst = BookingSite.objects.filter(id=d.get('id', None))
                if len(inst) == 0:
                    ser = BookingSiteSerializer(data=d)
                else:
                    inst = inst.first()
                    ser = BookingSiteSerializer(inst, data=d, partial=partial)
                ser.is_valid(raise_exception=True)
                inst = ser.save()
                b_ids.append(inst.id)
            BookingSite.objects.filter(~Q(id__in=b_ids), property=instance).delete()
            
            s_ids = []
            for i in range(len(social_media_set)):
                d = dict()
                d['id'] = data.get(f'social_media[{i}][id]', None)
                d['name'] = data[f'social_media[{i}][name]']
                d['site'] = data[f'social_media[{i}][site]']
                d['label'] = data.get(f'social_media[{i}][label]', None)
                d['property'] = data.get(f'social_media[{i}][property]', id)
                
                data.pop(f'social_media[{i}][id]', None)
                data.pop(f'social_media[{i}][name]', None)
                data.pop(f'social_media[{i}][site]', None)
                data.pop(f'social_media[{i}][label]', None)
                data.pop(f'social_media[{i}][property]', None)
                
                inst = SocialMediaLink.objects.filter(id=d.get('id', None))
                if len(inst) == 0:
                    ser = SocialMediaLinkSerializer(data=d)
                else:
                    inst = inst.first()
                    ser = SocialMediaLinkSerializer(inst, data=d, partial=partial)
                ser.is_valid(raise_exception=True)
                inst = ser.save()
                s_ids.append(inst.id)
            SocialMediaLink.objects.filter(~Q(id__in=s_ids), property=instance).delete()
                
            # pi_ids = []
            # for i in range(len(pictures_set)):
            #     d = dict()
            #     d['id'] = data.get(f'pictures[{i}][id]', None)
            #     d['property'] = data.get(f'pictures[{i}][property]', id)
            #     # d['image'] = data[f'pictures[{i}][image]']
            #     d['image'] = data.get(f'pictures[{i}]', None) if data.get(f'pictures[{i}]', None) else data.get(f'pictures[{i}][image]', None)
                
            #     print(d, '----------\n')
                
            #     data.pop(f'pictures[{i}]', None)
            #     data.pop(f'pictures[{i}][id]', None)
            #     data.pop(f'pictures[{i}][property]', None)
            #     data.pop(f'pictures[{i}][image]', None)
                
            #     inst = PropertyPhoto.objects.filter(id=d.get('id', None))
            #     if len(inst) == 0:
            #         ser = PropertyPhotoSerializer(data=d)
            #         ser.is_valid(raise_exception=True)
            #         inst = ser.save(updated_by_id=self.request.user.id)
            #     else:
            #         inst = inst.first()
            #         # ser = PropertyPhotoSerializer(inst, data=d, partial=partial) 
            #     pi_ids.append(inst.id)
            # for p in request.data.getlist('pictures[]'):
            #     ser = PropertyPhotoSerializer(data={'image': p, "property": instance.id})
            #     ser.is_valid(raise_exception=True)
            #     inst = self.perform_create(ser)
            #     pi_ids.append(inst.id)
            # PropertyPhoto.objects.filter(~Q(id__in=pi_ids), property=instance).delete()
                
            suitabilities = []
            for i in range(len(suitabilities_set)):
                d = dict()
                d['id'] = data.get(f'suitabilities[{i}][id]', None)
                d['label'] = data.get(f'suitabilities[{i}][label]', None)
                d['days'] = data.get(f'suitabilities[{i}][days]', None)
                
                data.pop(f'suitabilities[{i}][id]', None)
                data.pop(f'suitabilities[{i}][label]', None)
                data.pop(f'suitabilities[{i}][days]', None)
                
                suitabilities.append(d)

            data['accessibility'] = data.get('accessibility[]', [])
            data.pop(f'accessibility[]', None)
            data['activities'] = data.get('activities[]', [])
            data.pop(f'activities[]', None)
            data['bathrooms'] = data.get('bathrooms[]', [])
            data.pop(f'bathrooms[]', None)
            data['entertainments'] = data.get('entertainments[]', [])
            data.pop(f'entertainments[]', None)
            data['essentials'] = data.get('essentials[]', [])
            data.pop(f'essentials[]', None)
            data['families'] = data.get('families[]', [])
            data.pop(f'families[]', None)
            data['features'] = data.get('features[]', [])
            data.pop(f'features[]', None)
            data['kitchens'] = data.get('kitchens[]', [])
            data.pop(f'kitchens[]', None)
            data['laundries'] = data.get('laundries[]', [])
            data.pop(f'laundries[]', None)
            data['outsides'] = data.get('outsides[]', [])
            data.pop(f'outsides[]', None)
            data['parking'] = data.get('parking[]', [])
            data.pop(f'parking[]', None)
            data['pool_spas'] = data.get('pool_spas[]', [])
            data.pop(f'pool_spas[]', None)
            data['safeties'] = data.get('safeties[]', [])
            data.pop(f'safeties[]', None)
            data['spaces'] = data.get('spaces[]', [])
            data.pop(f'spaces[]', None)
            data['services'] = data.get('services[]', [])
            data.pop(f'services[]', None)
            
            data['booking_sites'] = []
            data['social_media'] = []
            data['room_types'] = []
            # data['pictures'] = pictures
            data['suitabilities'] = suitabilities
            print('\n============ ******3***** =============')
            print(data)
            print(1)
            # print(pictures)
            print(1)
            print(suitabilities)
            print('============ ******3***** =============\n')
            
            data.pop('logo', None)
            data.pop('video', None)
            data.pop('virtual_tour', None)
            # if not data.get('video'):
                # data['logo'] = None
                # data['video'] = None
                # data['virtual_tour'] = None
            # print('----------------')
            # print(data.get('address'))
            # print('============ 4 =============')
            city_id = None
            if not data.get('city_data').get('id', None):
                print('====Create City****')
                ser = CitySerializer(data=data.get('city_data'))
                ser.is_valid(raise_exception=True)
                inst = ser.save()
                data['city_id'] = inst.id
                city_id = inst.id
            else:
                print('====Have City****')
                city_id = data.get('city_data').get('id')
                data['city_id'] = city_id
                data.pop('city_data', None)
            # print(data.get('address'))
            # inst = Address.objects.filter(id=data.get('address').get('id', None)).first()
            # print(inst)
            # addData = data.get('address')
            # addData['city'] = city_id
            # addData['properties']['updated_by_id'] = self.request.user.id
            # if inst:
            #     ser = AddressGeoSerializer(inst, data=addData, partial=partial) 
            # else:
            #     ser = AddressGeoSerializer(data=addData)
            # print(1)
            # ser.is_valid(raise_exception=True)
            # address = ser.save()
            # address.city_id = city_id
            # address.save()
            # print(city_id, ' ==================+++++++++++++++++++++++++++++++++++++>>>>>>>>>>>>> \n\n\n', addData)
            # print(address)
            # print(address.id)
            # print(data.get('address')['properties']['hidden'], ' <<<<<<<<<++++++++>>>>>>>>>>> ', address.hidden)
                
            serializer = PropertySerializer(instance, data=data, partial=partial, context={'updated_by_id': self.request.user.id})
            # serializer = self.get_serializer(instance, data=request.data, partial=partial)
            print(3)
            serializer.is_valid(raise_exception=True)
            print('============ 5 =============')
            print('============ 6 =============')
            instance = self.perform_update(serializer)
            if instance.office_id is not None and data.get('office') is None:
                instance.office_id = None
                instance.save()

            if instance.portfolio_id is not None and data.get('portfolio') is None:
                instance.portfolio_id = None
                instance.save()

            print('============ 7 =============')
            # print(instance__)
            if instance.calendar is None:
                cal = Calendar(name=instance.name, slug=instance.ref)
                cal.save()
                instance.calendar = cal
                instance.save()

            # print('***************pictures***************')
            # p_ids = []
            # for p in request.data.getlist('pictures'):
            #     inst = PropertyPhoto.objects.filter(id=p.get('id', None))
            #     if len(inst) == 0:
            #         ser = PropertyPhotoSerializer(data=p)
            #     else:
            #         inst = inst.first()
            #         ser = PropertyPhotoSerializer(inst, data=p, partial=partial)
            #     ser.is_valid(raise_exception=True)
            #     inst = ser.save()
            #     p_ids.append(inst.id)
            # PropertyPhoto.objects.filter(~Q(id__in=p_ids), property=instance).delete()
            print('============ 8 =============')

            # Reza: to save min_nights_stay
            instance.refresh_from_db()
            instance.save()

            if instance.ical_url != ical_old:    
                processPropertyEvents.apply_async(kwargs={'calendar_id': instance.calendar.id, 'calendar_url': instance.ical_url})
            return Response(PropertySerializer(instance).data, status=status.HTTP_201_CREATED)
    
    def list(self, request, *args, **kwargs):
        profile = request.user.user_profile
        page_number = request.query_params.get('page', None)
        size = request.query_params.get('size', 0)
        search = request.query_params.get('search', None)
        direction = '' if request.query_params.get('direction', 'asc') == 'asc' else '-'
        sortby = f"{direction}{request.query_params.get('sortby', 'created')}"
        print('size: ', size)
        print('sortby:...: ', sortby)
        print('page_number...: ', page_number)
        print('query_params...: ', request.query_params)
        print('...: ', type(request.query_params))
        print('Company: ', profile.company)
        print('Profile: ', profile)

        # queryset = Property.objects.filter(Q(Q(company__isnull=False, company=profile.company) | Q(administrator=profile)), enabled=True).prefetch_related(
        #     Prefetch('offices', queryset=Office.objects.filter(enabled=True).prefetch_related(
        #         Prefetch('properties', queryset=Property.objects.filter(enabled=True)))), 
        #     Prefetch('portfolios', queryset=Portfolio.objects.filter(enabled=True).prefetch_related(
        #         Prefetch('properties', queryset=Property.objects.filter(enabled=True)))),
        #     Prefetch('pictures', queryset=PropertyPhoto.objects.filter(enabled=True)
        # ).order_by(sortby)
            
        queryset = Property.objects.filter(Q(Q(company__isnull=False, company=profile.company) | Q(administrator=profile, administrator__user__is_manager=False)), enabled=True).prefetch_related(
            Prefetch('pictures', queryset=PropertyPhoto.objects.filter(enabled=True).order_by('index'))
        ).order_by(sortby)

        if size == 0 and page_number:
            # Remote Loader
            print(111)
            pagy = self.paginate_queryset(queryset)
            total = Property.objects.filter(Q(Q(company__isnull=False, company=profile.company) | Q(administrator=profile, administrator__user__is_manager=False)), enabled=True).count()
            # print('Pagination: ', page)
            if pagy is not None:
                size = request.query_params.get('size', None)
                print(size) 
                # page.page_size_query_param = 
                serializer = self.get_serializer(pagy, many=True)
                return self.get_paginated_response(serializer.data)
        else:
            page_number = int(page_number)-1 if page_number else 0
            page_number = 0 if page_number < 0 else page_number
            size = int(size) if size and int(size) > 0 else 100
            print("A222")
            print(page_number, '   ', page_number*size, ' ---- ', size)
            print(request.user.is_manager)
            
            if profile.company:
                total = Property.objects.filter(Q(Q(company=profile.company) | Q(administrator=profile, administrator__user__is_manager=False)), enabled=True).count()
                if search:
                    print("A333a")
                    queryset = Property.objects.filter(Q(Q(company=profile.company) | Q(administrator=profile, administrator__user__is_manager=False)), Q(Q(ref__icontains=search) | Q(name__icontains=search) | Q(type__icontains=search) | Q(space__icontains=search)), enabled=True).order_by(sortby)[page_number*size:(page_number*size)+size]
                    total = len(queryset)
                else:
                    print("A333b")
                    queryset = Property.objects.filter(Q(Q(company=profile.company) | Q(administrator=profile, administrator__user__is_manager=False)), enabled=True).order_by(sortby)
                    total = len(queryset)
                    # queryset = Property.objects.filter(Q(Q(company__isnull=False, company=profile.company) | Q(administrator=profile, administrator__user__is_manager=False)), enabled=True).order_by(sortby)[page_number*size:(page_number*size)+size]
            elif request.user.is_manager:
                if search:
                    print("A444a")
                    queryset = Property.objects.filter(Q(Q(ref__icontains=search) | Q(name__icontains=search) | Q(type__icontains=search) | Q(space__icontains=search)), company__isnull=True, enabled=True).order_by(sortby)[page_number*size:(page_number*size)+size]
                    total = len(queryset)
                else:
                    print("A444b")
                    queryset = Property.objects.filter(company__isnull=True, enabled=True).order_by(sortby)[page_number*size:(page_number*size)+size]
                    total = len(queryset)
            else:
                if search:
                    print("A555a")
                    queryset = Property.objects.filter(Q(Q(ref__icontains=search) | Q(name__icontains=search) | Q(type__icontains=search) | Q(space__icontains=search)), company__isnull=True, enabled=True).order_by(sortby)[page_number*size:(page_number*size)+size]
                    total = len(queryset)
                else:
                    print(size, ' --  ', page_number, " A555b ", [page_number*size, (page_number*size)+size])
                    queryset = Property.objects.filter(company__isnull=True, administrator=profile, enabled=True).order_by(sortby)[page_number*size:(page_number*size)+size]
                    total = len(queryset)
                
                # queryset = queryset[page_number*size:(page_number*size)+size]
            serializer = self.get_serializer(queryset, many=True)
            return Response({"data": serializer.data, "total_count": total})
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(methods=['post', 'get'], detail=False, url_path='search', url_name='search')
    def search(self, request, *args, **kwargs):
        # page_number = int(query_params.get("page", 1))
        size = int(request.query_params.get("size", 25))
        self.pagination_class.page_size = size

        queryset = Property.objects.filter(enabled=True, is_published=True).prefetch_related(
            Prefetch('pictures', queryset=PropertyPhoto.objects.filter(enabled=True, is_default=True))
        )
        
        is_direct = True
        query_params = request.query_params
        if query_params.get('com_ref', None):
            is_direct = False
            queryset = queryset.filter(company__ref=query_params.get('com_ref'))
        if query_params.get('off_ref', None):
            is_direct = False
            queryset = queryset.filter(office__ref=query_params.get('off_ref'))
        if query_params.get('port_ref', None):
            is_direct = False
            queryset = queryset.filter(portfolio__ref=query_params.get('port_ref'))
        
        data = request.data
        
        print('\n\n')
        print('1 ++++ ', len(queryset))
        print('1 ++++ ', queryset.query)
        print('1 ++++ ', data)
        print(size, '......query_params.....: ', query_params)
        
        
        if data:
            print('...........: ', data)
            location = data.get('location', None)
            boundary = data.get('boundary', None)
            # address = data.get('address', None)
            
            # if not location and not address:
            #     return Response({"message": "Address component is missing"}, status=status.HTTP_404_NOT_FOUND)
            
            print("boundary: ", boundary)
            print("location: ", location)
            # print(11111111111111111111111)
            # print(data.get('guest'))
            # print('-------Type: ', type(data.get('guest')))
            # print(queryset.count())
            # print(queryset)
            print(data.get('state', None))

            if boundary or location:
                
                if type(boundary) == dict:
                    print(111)
                    # ne = data.get('geometry').get('ne')
                    # sw = data.get('geometry').get('sw')

                    # https://stackoverflow.com/questions/9466043/geodjango-within-a-ne-sw-box
                    # sw = (latitude, longitude)
                    # ne = (latitude, longitude)
                    # sw = (boundary['south'], boundary['west'])
                    # ne = (boundary['north'], boundary['east'])
                    # xmin=sw[1]
                    # ymin=sw[0]
                    # xmax=ne[1]
                    # ymax=ne[0]

                    xmin=boundary['west']
                    ymin=boundary['south']
                    xmax=boundary['east']
                    ymax=boundary['north']
                    
                    bbox = (xmin, ymin, xmax, ymax)

                    geometry = Polygon.from_bbox(bbox)
                    b = boundary
                    point = Point((b['west']+b['east'])/2, (b['south']+b['north'])/2, srid=4326)
                    # queryset = Property.objects.annotate(distance=KMDistance('location', point)).filter(location__contained=geometry).order_by('distance').filter(enabled=True, is_published=True).prefetch_related(
                    queryset = Property.objects.annotate(distance=KMDistance('location', point)).filter(location__coveredby=geometry).order_by('distance').filter(enabled=True, is_published=True).prefetch_related(
                        Prefetch('pictures', queryset=PropertyPhoto.objects.filter(enabled=True, is_default=True))
                    )
                    
                    print('\n+++++++++++++++++++++++++++++++++++++++++++++++++')
                    print(queryset.query)
                    # xmin=sw[1]=sw.lng
                    # ymin=sw[0]=sw.lat
                    # xmax=ne[1]=ne.lng
                    # ymax=ne[0]=ne.lat
                    # bbox = (sw[1], sw[0], ne[1], ne[0]) = (xmin, ymin, xmax, ymax) = (sw['lng'], sw['lat'], ne['lng'], ne['lat'])

                    # # bbox = (ne['lat'], sw['lng'], ne['lng'], sw['lat'])
                    # bbox = (sw['lng'], sw['lat'], ne['lng'], ne['lat'])
                    # print('****bbox  ', bbox)
                    # geometry = Polygon.from_bbox(bbox)
                    # queryset = queryset.filter(location__within=geometry)
                elif type(location) == dict:
                    print(222)
                    # geometry = json.dumps(data.get('geometry'))
                    # print(type(geometry))
                    point = Point(location['lng'], location['lat'], srid=4326)
                    queryset = Property.objects.annotate(distance=KMDistance('location', point)).order_by('distance').filter(enabled=True, is_published=True, distance__lte=180000).prefetch_related(
                        Prefetch('pictures', queryset=PropertyPhoto.objects.filter(enabled=True, is_default=True))
                    )
            else:
                queryset = queryset.annotate(distance=KMDistance('location', Point(-109.9429638, 34.125919, srid=4326))).order_by('distance')
                
            if data.get('propertyId', None):
                queryset = queryset.filter(Q(id__iexact=data.get('propertyId')) | Q(ref__iexact=data.get('propertyId')))
            if data.get('name', None):
                queryset = queryset.filter(Q(name__icontains=data.get('name')))
            if not location and data.get('zip_code', None):
                queryset = queryset.filter(zip_code=data.get('zip_code'))
            if not location and data.get('city', None):
                queryset = queryset.filter(city__name__iexact=data.get('city'))
            if not location and data.get('state', None):
                queryset = queryset.filter(city__state_name__iexact=data.get('state'))
            if data.get('types', None):
                queryset = queryset.filter(type__in=data.get('types'))
            if data.get('bookedSpaces', None):
                queryset = queryset.filter(space__in=data.get('bookedSpaces'))
            
            print('2 ++++ ', len(queryset))
            if data.get('guest', None):
                try:
                    queryset = queryset.filter(max_no_of_guest__gte=int(data.get('guest')))
                except Exception:
                    queryset = queryset.filter(max_no_of_guest__in=data.get_list('guest', []))
            if data.get('bedrooms', None):
                queryset = queryset.filter(no_of_bedrooms__gte=data.get('bedrooms'))
            if data.get('no_of_bathrooms', None):
                queryset = queryset.filter(no_of_bathrooms__gte=data.get('no_of_bathrooms'))
            if data.get('bookers', None):
                queryset = queryset.filter(booking_sites__booker__in=data.get('bookers', []))
            if data.get('priceRange', None):
                pri = data.get('priceRange', [])
                queryset = queryset.filter(Q(price_night__gte=pri[0], price_night__lte=pri[1]))
            
            print('3 ++++ ', len(queryset))
            if data.get('suitabilities', None):
                s = data.get('suitabilities')
                # if len(s) == 4:
                #     queryset = queryset.filter(Q(suitabilities__icontains=s[0]) | Q(suitabilities__icontains=s[1]) | Q(suitabilities__icontains=s[2]) | Q(suitabilities__icontains=s[3]))
                # elif  len(s) == 3:
                #     queryset = queryset.filter(Q(suitabilities__icontains=s[0]) | Q(suitabilities__icontains=s[1]) | Q(suitabilities__icontains=s[2]))
                if  len(s) == 2:
                    queryset = queryset.filter(Q(suitabilities__icontains=s[0]) | Q(suitabilities__icontains=s[1]))
                elif  len(s) == 1:
                    queryset = queryset.filter(suitabilities__icontains=s[0])
            
            if data.get('checkIn', None) and data.get('checkOut', None):
                try:
                    check_in = datetime.fromtimestamp(
                        int(data['checkIn'])
                    )
                    check_out = datetime.fromtimestamp(
                        int(data['checkOut'])
                    )
                    days = (check_out - check_in).days;
                    queryset = queryset.filter(
                        min_night_stay__lte=days
                    )
                except:
                    print('Error on filtering by checkIn/checkOut')
            if data.get('petAllow', None):
                queryset = queryset.filter(is_pet_allowed=bool(data.get('petAllow')))
            if data.get('accessibility', None):
                queryset = queryset.filter(accessibility__in=data.get('accessibility', []))
            if data.get('activities', None):
                queryset = queryset.filter(activities__in=data.get('activities', []))
            if data.get('bathrooms', None):
                queryset = queryset.filter(bathrooms__in=data.get('bathrooms'))
            if data.get('entertainments', None):
                queryset = queryset.filter(entertainments__in=data.get('entertainments', []))
            if data.get('essentials', None):
                queryset = queryset.filter(essentials__in=data.get('essentials', []))
            if data.get('families', None):
                queryset = queryset.filter(families__in=data.get('families', []))
            if data.get('features', None):
                queryset = queryset.filter(features__in=data.get('features', []))
            if data.get('kitchens', None):
                queryset = queryset.filter(kitchens__in=data.get('kitchens', []))
            if data.get('laundries', None):
                queryset = queryset.filter(laundries__in=data.get('laundries', []))
            if data.get('outsides', None):
                queryset = queryset.filter(outsides__in=data.get('outsides', []))
            if data.get('parking', None):
                queryset = queryset.filter(parking__in=data.get('parking', []))
            if data.get('pool_spas', None):
                s = data.get('pool_spas')
                if  len(s) >= 2:
                    queryset = queryset.filter(Q(pool_spas__name__icontains=s[0]) | Q(pool_spas__name__icontains=s[1]))
                elif  len(s) == 1:
                    queryset = queryset.filter(pool_spas__name__icontains=s[0])
                # queryset = queryset.filter(pool_spas__name__in=data.get('pool_spas', []))
            if data.get('safeties', None):
                queryset = queryset.filter(safeties__in=data.get('safeties', []))
            if data.get('services', None):
                queryset = queryset.filter(services__in=data.get('services', []))
            if data.get('spaces', None):
                queryset = queryset.filter(spaces__in=data.get('spaces', []))
        else:
            # serializer = self.get_serializer(queryset[:size], many=True)
            # return Response({"data": serializer.data, "count": size, "total_pages": 1})?


            print('++++++++++++++\n')
            if is_direct:
                # {'south': 29.755532355140886, 'west': -117.26938590625, 'north': 47.98310225144885, 'east': -84.35434684375}
                point = Point(-109.9429638, 34.125919, srid=4326)
                queryset = Property.objects.annotate(distance=KMDistance('location', point)).filter(enabled=True, is_published=True).prefetch_related(
                    Prefetch('pictures', queryset=PropertyPhoto.objects.filter(enabled=True, is_default=True))
                ).order_by('distance')[0:25]
                
                print(queryset.query)
                page = self.paginate_queryset(queryset)
                if page is not None:
                    serializer = self.get_serializer(page, many=True)
                    print('\n\n')
                    for q in serializer.data:
                        print(q)
                        print('\n')
                    return self.get_paginated_response(serializer.data)
                serializer = self.get_serializer(queryset, many=True)
                return Response(serializer.data)
            else:
                return Response({"data": [], "count": size, "total_pages": 1})
        print(' +++ ', queryset.query)
        print('\n <<+++>> ', queryset)
        queryset = queryset[0:300] if (location or boundary) else queryset
        page = self.paginate_queryset(queryset)
        print(' >>>>>>> Pagination: ', page)
        if page is not None:
            # print(queryset.count())
            # page.count =  queryset.count()
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(methods=['get'], detail=False, url_path='our/list', url_name='our-list')
    def our_list(self, request, *args, **kwargs):
        profile = request.user.user_profile
        print(' ====>> ', request.query_params)
        if len(request.query_params.get("office", "")) > 3:
            print(1)
            para = request.query_params.get("office", "")
            queryset = Property.objects.filter(Q(Q(company__isnull=False, company=profile.company) | Q(administrator=profile, administrator__user__is_manager=False)), Q(Q(office__isnull=True) | Q(office__id=para) | Q(office__ref=para)), enabled=True)
        elif len(request.query_params.get("portfolio", "")) > 3:
            print(2)
            para = request.query_params.get("portfolio", "")
            queryset = Property.objects.filter(Q(Q(company__isnull=False, company=profile.company) | Q(administrator=profile, administrator__user__is_manager=False)), Q(Q(portfolio__isnull=True) | Q(portfolio__id=para) | Q(portfolio__ref=para)), enabled=True)
        else:
            print(3, ' ', )
            queryset = Property.objects.filter(Q(Q(company__isnull=False, company=profile.company) | Q(administrator=profile, administrator__user__is_manager=False)), enabled=True)
        print(queryset.query)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
           
    @action(methods=['get'], detail=False, url_path='form/items', url_name='form-items')
    def form_items(self, request, *args, **kwargs):
        selective = request.query_params.get('selective', '').split(',')
        if len(selective) == 1 and selective[0] == '':
            selective = []
        print(selective)

        bookers = []
        if 'bookers' in selective or len(selective) == 0:
            data = list(map(lambda d: dict(d), BookerSerializer(Booker.objects.filter(enabled=True), many=True).data))
            sort_order = {x['name']: i for i, x in enumerate(data) if 'Additional' not in x['name'] or 'Direct Booking' not in x['name']}
            data.sort(key=lambda x: sort_order.get(x["name"], 1000 if 'Additional' in x["name"] else -10))
            bookers = data
        
        offices = []
        portfolios = []
        if request.user.is_authenticated:
            profile = request.user.user_profile
            if profile.company:
                offices = OfficeSerializer(profile.company.offices.filter(enabled=True), many=True).data
                portfolios = PortfolioSerializer(profile.company.portfolios.filter(enabled=True), many=True).data
        
        services = ServiceSerializer(Service.objects.filter(enabled=True), many=True).data if 'services' in selective or len(selective) == 0 else []
        sleepers = SleeperSerializer(Sleeper.objects.filter(enabled=True), many=True).data if 'sleepers' in selective or len(selective) == 0 else []
        spaces = SpaceSerializer(Space.objects.filter(enabled=True), many=True).data if 'spaces' in selective or len(selective) == 0 else []
        bathrooms = BathroomSerializer(Bathroom.objects.filter(enabled=True), many=True).data if 'bathrooms' in selective or len(selective) == 0 else []
        kitchens = KitchenSerializer(Kitchen.objects.filter(enabled=True), many=True).data if 'kitchens' in selective or len(selective) == 0 else []
        pool_spas = PoolSpaSerializer(PoolSpa.objects.filter(enabled=True), many=True).data if 'pool_spas' in selective or len(selective) == 0 else []
        outsides = OutsideSerializer(Outside.objects.filter(enabled=True), many=True).data if 'outsides' in selective or len(selective) == 0 else []
        essentials = EssentialSerializer(Essential.objects.filter(enabled=True), many=True).data if 'essentials' in selective or len(selective) == 0 else []
        entertainments = EntertainmentSerializer(Entertainment.objects.filter(enabled=True), many=True).data if 'entertainments' in selective or len(selective) == 0 else []
        laundries = LaundrySerializer(Laundry.objects.filter(enabled=True), many=True).data if 'laundries' in selective or len(selective) == 0 else []
        families = FamilySerializer(Family.objects.filter(enabled=True), many=True).data if 'families' in selective or len(selective) == 0 else []
        parking = ParkingSerializer(Parking.objects.filter(enabled=True), many=True).data if 'parking' in selective or len(selective) == 0 else []
        accessibility = AccessibilitySerializer(Accessibility.objects.filter(enabled=True), many=True).data if 'accessibility' in selective or len(selective) == 0 else []
        
        safeties = SafetySerializer(Safety.objects.filter(enabled=True), many=True).data if 'safeties' in selective or len(selective) == 0 else []
        features = FeatureSerializer(Feature.objects.filter(enabled=True), many=True).data if 'features' in selective or len(selective) == 0 else []
        activities = ActivitySerializer(Activity.objects.filter(enabled=True), many=True).data if 'activities' in selective or len(selective) == 0 else []

        return Response({
            'bookers': bookers, 
            'sleepers': sleepers, 
            'services': services, 
            'spaces': spaces, 
            'bathrooms': bathrooms,
            'kitchens': kitchens,
            'pool_spas': pool_spas,
            'outsides': outsides,
            'essentials': essentials,
            'entertainments': entertainments,
            'laundries': laundries,
            'families': families,
            'parking': parking,
            'accessibility': accessibility,
            'safeties': safeties,
            'features': features,
            'activities': activities,
            'portfolios': portfolios,
            'offices': offices
        }, status=status.HTTP_201_CREATED)
     
    @action(methods=['get'], detail=False, url_path='fixed/items', url_name='fixed-items')
    def fixed_items(self, request, *args, **kwargs):
        
        return Response({
            'types': Property.TYPES, 
            'booked_spaces': Property.BOOKED_SPACE, 
            # 'room_types': Property.ROOM_TYPES,
            'sleeper_types': Property.SLEEPER_TYPES
            }, status=status.HTTP_201_CREATED)

    @action(methods=['patch', 'post'], detail=True, url_path='publisher', url_name='publish')
    def publisher(self, request, *args, **kwargs):
        instance = self.get_object()
        profile = request.user.user_profile
        if (instance.company is not None and instance.company != profile.company) or (instance.company is None and instance.administrator != profile and not profile.user.is_manager):
            return Response({"message": "You are not authorised to perform this action", "required": []}, status=status.HTTP_403_FORBIDDEN)
        
        if not instance.is_published and len(instance.pictures.all()) == 0:
            return Response({"message": "Atleast 1 picture is required for publication", "required": ["pictures"]}, status=status.HTTP_400_BAD_REQUEST)
        instance.is_published = not instance.is_published
        instance.save()
        
        return Response(PropertyDetailSerializer(instance=instance).data)
    
    @action(methods=['get'], detail=False, url_path='mine', url_name='mine')
    def mine(self, request, *args, **kwargs):
        p = request.user.user_profile
        properties = Property.objects.filter(Q(administrator=p, administrator__user__is_manager=False) | Q(members=p), enabled=True).prefetch_related(
            Prefetch('offices', queryset=Office.objects.filter(enabled=True).prefetch_related(
                Prefetch('office_properties', queryset=Property.objects.filter(enabled=True)))), 
            Prefetch('portfolios', queryset=Portfolio.objects.filter(enabled=True).prefetch_related(
                Prefetch('portfolio_properties', queryset=Property.objects.filter(enabled=True)))),
            Prefetch('members', queryset=Profile.objects.filter(enabled=True).prefetch_related(
                Prefetch('portfolios', queryset=Portfolio.objects.filter(enabled=True)),
                Prefetch('offices', queryset=Office.objects.filter(enabled=True)))),
            Prefetch('invitations', queryset=Invitation.objects.filter(enabled=True))
        ).first()

        if properties:
            return Response(PropertyListSerializer(properties, many=True).data, status=status.HTTP_200_OK)
        else:
            return Response(None, status=status.HTTP_200_OK)
       
    @action(methods=['post'], detail=True, url_path='pictures/upload', url_name='picture-upload')
    def pictures_upload(self, request, *args, **kwargs):
        with transaction.atomic():
            print('\n============ 0 =============\n')
            data = request.data
            print(data)
            instance = self.get_object()
            originalPIDs = list(map(lambda x: x.id, instance.pictures.all()))
            
            print('\n============ pictures =============\n')
            
            pictures_set = set()
            for k in data.keys():
                if f'pictures[' in k:
                    pictures_set.add(re.findall(r"^pictures\[(\d+)\]\[(\w+)\]", k)[0][0])
                    print(k, ' ==> ', data[k], '  =>> ', type(data[k]))
            
            pictures = []
            foundDefault = False
            defaultIndex = -1
            for i in range(len(pictures_set)):
                d = dict()
                d['index'] = i
                d['id'] = data.get(f'pictures[{i}][id]', None)
                d['caption'] = data.get(f'pictures[{i}][caption]', None)
                d['is_default'] = data.get(f'pictures[{i}][is_default]', False)
                d['image'] = data.get(f'pictures[{i}][image]', None)
                d['property'] = instance.id
                
                pictures.append(d)
                if d['is_default'] == 'true':
                    print(i, ': ......', foundDefault)
                    if foundDefault:
                        d['is_default'] = False
                    else:
                        foundDefault = True
                        defaultIndex = i
            
            print(defaultIndex, '::: =====>>> ', foundDefault)

            if len(pictures) > 0 and not foundDefault and defaultIndex == -1:
                pictures[0]['is_default'] = True
                print('.... ', 111)
            elif len(pictures) > 1 and defaultIndex > 0:
                print('.... ', 222)
                indexPic = pictures[defaultIndex]
                del pictures[defaultIndex]
                pictures.insert(0, indexPic)
                for i in range(len(pictures)):
                    pictures[i]['index'] = i
            
            print('\n')
            x = 0
            pids = []
            for p in pictures:
                print(p)
                print(f'======{x}\n')
                x += 1
                if p['id']:
                    inst = PropertyPhoto.objects.filter(id=p['id']).first()
                    if type(p['image']) == str:
                        print('String>>>>>>>>>>> 1')
                        p.pop("image", None)
                    else:
                        print(type(p['image']), ' String>>>>>>>>>>> 2')
                    ser = PropertyPhotoSerializer(inst, data=p, partial=True)
                    ser.is_valid(raise_exception=True)
                    inst = self.perform_update(ser)
                    pids.append(inst.id)
                else:
                    ser = PropertyPhotoSerializer(data=p)
                    ser.is_valid(raise_exception=True)
                    inst = self.perform_create(ser)
                    pids.append(inst.id)
                
            print('++++++++++++++++++++++++++++++++++++++++++++++++++++++\n', data)
            if data.get('videoLink', '') and len(data.get('videoLink', '')) > 5:
                print(' ===>> ', data['videoLink'])
                instance.video_link = data.get('videoLink')
                instance.video = None
            elif data.get('video[]', None):
                print(' ===>> ', data['video[]'])
                ser = PropertyVideoSerializer(instance, data={"id": instance, "video": data['video[]']}, partial=True)
                ser.is_valid(raise_exception=True)
                self.perform_update(ser)
                instance.video_link = None
            elif data.get('videoLink', None) is not None and len(data.get('videoLink').strip()) == 0:
                instance.video_link = None
            else:
                print(' ======>> Nothing')
            instance.save()
                
            deletedIds = list((set(originalPIDs).difference(pids)))
            if len(deletedIds) > 0:
                PropertyPhoto.objects.filter(id__in=deletedIds).delete()
                
        return Response(PropertyDetailSerializer(instance).data, status=status.HTTP_200_OK)
    
    
class SupportViewSet(viewsets.ModelViewSet):
    permission_classes = (AllowAny, )
    # authentication_classes = ()
    authentication_classes = (TokenAuthentication, )
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

    def perform_create(self, serializer):
        return serializer.save()
        
    def create(self, request, *args, **kwargs):
        print('****** 1');
        data = request.data
        print(data)
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        instance = self.perform_create(serializer)
        
        print(instance)
        if instance.company is not None:
            title = instance.company.name
            # email = instance.company.email if instance.company.email else instance.company.administrator.user.email
        else:
            # email = request.user.email
            title = settings.COMPANY_NAME
        email = 'info@rentmyvr.com'
        
        domain = get_domain(request)
        html_message = render_to_string('email/support_inquiry.html', {
            'coy_name': settings.COMPANY_NAME,
            'support': instance,
            'profile': request.user.user_profile,
            'domain': domain,
            'project_title': title
        })
        
        from core.tasks import sendMail
        sendMail.apply_async(kwargs={'subject': f"Support Needed ({instance.ref})", "message": html_message,
                                    "recipients": [email],
                                    "fail_silently": settings.DEBUG, "connection": None})

        headers = self.get_success_headers(serializer.data)

        return Response({"message": "Ok", "result": 'Message sent Successfully'}, status=status.HTTP_201_CREATED, headers=headers)
    
