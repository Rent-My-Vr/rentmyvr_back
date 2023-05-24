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
from django.contrib.gis.geos import Point, Polygon, GEOSGeometry
from django.contrib.gis.measure import Distance
from django.template.loader import render_to_string

from auths.utils import get_domain
from auths_api.serializers import UserSerializer, UserUpdateSerializer
from notifications.signals import notify
from core.models import *
from core.utils import send_gmail
from core_api.pagination import MyPagination
from core_api.serializers import *
from core_api.models import *
from directory.models import *
from directory_api.serializers import *


log = logging.getLogger(f"{__package__}.*")
log.setLevel(settings.LOGGING_LEVEL)


class ManagerDirectoryViewSet(viewsets.ModelViewSet, AchieveModelMixin):
    permission_classes = (IsAuthenticated, )
    authentication_classes = (TokenAuthentication,)
    parser_classes = (MultiPartParser, FormParser)
    # parser_classes = (MultiPartParser, FormParser, JSONParser, FileUploadParser)
        
    def get_permissions(self):
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
            data = request.data
            data['company'] = profile.company.id if profile.company else profile.administrative_company.id
            
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
            
            serializer = self.get_serializer(data=data)
            serializer.is_valid(raise_exception=True)
            instance = self.perform_create(serializer)

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
        md = ManagerDirectory.objects.filter(Q(company__administrator=p) | Q(company__members=p), enabled=True).first()
        # company = ManagerDirectory.objects.filter(Q(company__administrator=p) | Q(company__members=p), enabled=True).prefetch_related(
        #     Prefetch('company_offices', queryset=Office.objects.filter(enabled=True).prefetch_related(
        #         Prefetch('office_properties', queryset=Property.objects.filter(enabled=True)))), 
        #     Prefetch('company_portfolios', queryset=Portfolio.objects.filter(enabled=True).prefetch_related(
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
        print('-------')
        print(request.data)
        data = request.data
        
        qs = Company.objects.filter(enabled=True)
        if len(data.get('state', '')) > 0:
            print('1. ', data.get('state'))
            qs = qs.filter(mdl__state=data.get('state'))
        if len(data.get('city', '')) > 0:
            print('2. ', data.get('state'))
            qs = qs.filter(mdl__city_id=data.get('city').get('id', None))
        if len(data.get('zip_code', '')) > 0:
            print('3. ', data.get('state'))
            qs = qs.filter(mdl__zip_code=data.get('zip_code'))
            
        qs = qs.prefetch_related(
            Prefetch('company_offices', queryset=Office.objects.filter(enabled=True).prefetch_related(
                Prefetch('office_properties', queryset=Property.objects.filter(enabled=True)))), 
            Prefetch('company_portfolios', queryset=Portfolio.objects.filter(enabled=True).prefetch_related(
                Prefetch('portfolio_properties', queryset=Property.objects.filter(enabled=True)))),
            Prefetch('members', queryset=Profile.objects.filter(enabled=True).prefetch_related(
                Prefetch('portfolios', queryset=Portfolio.objects.filter(enabled=True)),
                Prefetch('offices', queryset=Office.objects.filter(enabled=True)))),
            Prefetch('invitations', queryset=Invitation.objects.filter(enabled=True))
    )
        print(qs.query)
        return Response(CompanyMDLDetailSerializer(qs, many=True).data)


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
 
    def perform_create(self, serializer):
        return serializer.save(updated_by_id=self.request.user.id)
        
    def perform_update(self, serializer):
        return serializer.save(updated_by_id=self.request.user.id)
    
    def create(self, request, *args, **kwargs):
        with transaction.atomic():
            data = request.data
            print(data)
            if data and data.get('city', {}).get('id', None):
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
            data['company'] = profile.company.id
            
            print(data)
            serializer = self.get_serializer(data=data)
            serializer.is_valid(raise_exception=True)
            instance = self.perform_create(serializer)
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
            
            profile = request.user.user_profile
            data['administrator'] = instance.administrator.id if instance.administrator else profile.id
            data['company'] = instance.company.id if instance.company else profile.company.id
            
            serializer = self.get_serializer(instance, data=data, partial=partial)
            
            serializer.is_valid(raise_exception=True)
            instance = serializer.save()
            self.perform_update(serializer)
            serializer = OfficeDetailSerializer(instance)

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
                if profile is not None and (profile.company == p.company or profile.company is None) and (instance in profile.offices.all() or instance.administrator == profile):
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
        
        profile = request.user.user_profile
        data['administrator'] = profile.id
        data['company'] = profile.company.id
        
        print(data)
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        instance = self.perform_create(serializer)

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
            data['administrator'] = instance.administrator.id if instance.administrator else profile.id
            data['company'] = instance.company.id if instance.company else profile.company.id
            
            serializer = self.get_serializer(instance, data=data, partial=partial)
            serializer.is_valid(raise_exception=True)
            instance = serializer.save()
            
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
                if profile is not None and (profile.company == p.company or profile.company is None) and (instance in profile.portfolios.all() or instance.administrator == profile):
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
        elif self.action in ['list', 'search']:
            return PropertyListSerializer
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
            
            data['address'] = {}
            data['address']['id'] = request.data.get('address[id]', None)
            data['address']['type'] = request.data.get('address[type]', None)
            data['address']['geometry'] = dict()
            data['address']['geometry']['type'] = request.data.get('address[geometry][type]', None)
            data['address']['geometry']['coordinates'] = [float(request.data.get('address[geometry][coordinates][0]', 0)), float(request.data.get('address[geometry][coordinates][1]', 0))]
            data['address']['properties'] = dict()
            data['address']['properties']['formatted'] = request.data.get('address[properties][formatted]')
            data['address']['properties']['country_name'] = request.data.get('address[properties][country]')
            data['address']['properties']['street'] = request.data.get('address[properties][street]')
            data['address']['properties']['number'] = request.data.get('address[properties][number]')
            data['address']['properties']['zip_code'] = request.data.get('address[properties][zip_code]')
            data['address']['properties']['state'] = request.data.get('address[properties][state]')
            data['address']['properties']['hidden'] = request.data.get('address[properties][hidden]')
            data['address']['properties']['more_info'] = request.data.get('address[properties][more_info]')
            data['address']['properties']['city'] = dict()
            data['address']['properties']['city']['id'] = request.data.get('address[properties][city][id]', None)
            # data['address']['properties']['city']['imported'] = request.data.get('address[properties][city][imported]', False)
            # data['address']['properties']['city']['import_id'] = request.data.get('address[properties][city][import_id]', None)
            data['address']['properties']['city']['name'] = request.data.get('address[properties][city][name]')
            data['address']['properties']['city']['state_name'] = request.data.get('address[properties][city][state_name]')
            data['address']['properties']['city']['country_name'] = request.data.get('address[properties][country]')
            data['address']['properties']['city']['approved'] = True if data['address']['properties']['city']['id'] else False
            data['address']['properties']['city_data'] = data['address']['properties']['city']
            # data['address']['properties']['city'] = data['address']['properties']['city'].get('id', None) if data['address']['properties']['city'].get('id', None) else None

            data.pop("address[id]", None)
            data.pop("address[type]", None)
            data.pop("address[geometry][type]", None)
            data.pop("address[geometry][coordinates][0]", None)
            data.pop("address[geometry][coordinates][1]", None)
            data.pop("address[properties][formatted]", None)
            data.pop("address[properties][more_info]", None)
            data.pop("address[properties][street]", None)
            data.pop("address[properties][number]", None)
            data.pop("address[properties][zip_code]", None)
            data.pop("address[properties][state]", None)
            data.pop("address[properties][hidden]", None)
            data.pop("address[properties][city][id]", None)
            data.pop("address[properties][city][imported]", None)
            data.pop("address[properties][city][import_id]", None)
            data.pop("address[properties][city][name]", None)
            data.pop("address[properties][city][state_name]", None)
            data.pop("address[properties][city][updated]", None)
            data.pop("address[properties][city][created]", None)
            data.pop("address[properties][city][country_name]", None)
            data.pop("address[properties][city][approved]", None)
            
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
            print('----------------')
            print(data.get('address'))
            print('============ 4 =============')
            serializer = PropertySerializer(data=data, context={'city_data': data['address']['properties']['city_data']})
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
            for p in request.data.getlist('pictures[]'):
                ser = PropertyPhotoSerializer(data={'image': p, "property": instance.id})
                ser.is_valid(raise_exception=True)
                pic = self.perform_create(ser)
            print('============ 8 =============')
            return Response(PropertySerializer(instance).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        with transaction.atomic():
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            print('============ 0 update =============')
            print(request.data)
            print('============ 1 update =============')
            
            data = dict()
            for d in list(request.data.keys()):
                print(d)
                data[d] = request.data.getlist(d) if '[]' in d else request.data[d]

            data['address'] = {}
            data['address']['id'] = request.data.get('address[id]', None)
            data['address']['type'] = request.data.get('address[type]', None)
            data['address']['geometry'] = dict()
            data['address']['geometry']['type'] = request.data.get('address[geometry][type]', None)
            data['address']['geometry']['coordinates'] = [float(request.data.get('address[geometry][coordinates][0]', 0)), float(request.data.get('address[geometry][coordinates][1]', 0))]
            data['address']['properties'] = dict()
            data['address']['properties']['formatted'] = request.data.get('address[properties][formatted]')
            data['address']['properties']['country_name'] = request.data.get('address[properties][country_name]')
            data['address']['properties']['street'] = request.data.get('address[properties][street]')
            data['address']['properties']['number'] = request.data.get('address[properties][number]')
            data['address']['properties']['zip_code'] = request.data.get('address[properties][zip_code]')
            data['address']['properties']['state'] = request.data.get('address[properties][state]')
            data['address']['properties']['hidden'] = request.data.get('address[properties][hidden]')
            data['address']['properties']['more_info'] = request.data.get('address[properties][more_info]')
            data['address']['properties']['city'] = dict()
            data['address']['properties']['city']['id'] = request.data.get('address[properties][city][id]', None)
            data['address']['properties']['city']['imported'] = request.data.get('address[properties][city][imported]', False)
            data['address']['properties']['city']['import_id'] = request.data.get('address[properties][city][import_id]', None)
            data['address']['properties']['city']['name'] = request.data.get('address[properties][city][name]')
            data['address']['properties']['city']['state_name'] = request.data.get('address[properties][city][state_name]')
            data['address']['properties']['city']['country_name'] = request.data.get('address[properties][city][country_name]')
            data['address']['properties']['city']['approved'] = True if data['address']['properties']['city']['id'] else False
            data['address']['properties']['city_data'] = data['address']['properties']['city']
            # data['address']['properties']['city'] = data['address']['properties']['city'].get('id', None) if data['address']['properties']['city'].get('id', None) else None

            data.pop("address[id]", None)
            data.pop("address[type]", None)
            data.pop("address[geometry][type]", None)
            data.pop("address[geometry][coordinates][0]", None)
            data.pop("address[geometry][coordinates][1]", None)
            data.pop("address[properties][formatted]", None)
            data.pop("address[properties][more_info]", None)
            data.pop("address[properties][country_name]", None)
            data.pop("address[properties][street]", None)
            data.pop("address[properties][number]", None)
            data.pop("address[properties][zip_code]", None)
            data.pop("address[properties][state]", None)
            data.pop("address[properties][hidden]", None)
            data.pop("address[properties][city][id]", None)
            data.pop("address[properties][city][imported]", None)
            data.pop("address[properties][city][import_id]", None)
            data.pop("address[properties][city][name]", None)
            data.pop("address[properties][city][state_name]", None)
            data.pop("address[properties][city][updated]", None)
            data.pop("address[properties][city][created]", None)
            data.pop("address[properties][city][country_name]", None)
            data.pop("address[properties][city][approved]", None)
            
            # print(data)
            # print(data.get('booking_sites[]'))
            
            booking_sites_set = set()
            social_media_set = set()
            pictures_set = set()
            suitabilities_set = set()
            room_types_set = set()
            room_types_dict = dict()
            max_sleeper = 0
            for k in data.keys():
                if f'booking_sites[' in k:
                    booking_sites_set.add(re.findall(r"^booking_sites\[(\d+)\]\[\w+\]", k)[0])
                elif f'social_media[' in k:
                    social_media_set.add(re.findall(r"^social_media\[(\d+)\]\[\w+\]$", k)[0])
                elif f'pictures[' in k:
                    if k != 'pictures[]':
                        pictures_set.add(re.findall(r"^pictures\[(\d+)\]", k)[0])
                        # pictures_set.add(re.findall(r"^pictures\[(\d+)\]\[\w+\]$", k)[0])
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
            print('pictures_set_length: ', len(pictures_set))
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
                
            pi_ids = []
            for i in range(len(pictures_set)):
                d = dict()
                d['id'] = data.get(f'pictures[{i}][id]', None)
                d['property'] = data.get(f'pictures[{i}][property]', id)
                # d['image'] = data[f'pictures[{i}][image]']
                d['image'] = data.get(f'pictures[{i}]', None) if data.get(f'pictures[{i}]', None) else data.get(f'pictures[{i}][image]', None)
                
                print(d, '----------\n')
                
                data.pop(f'pictures[{i}]', None)
                data.pop(f'pictures[{i}][id]', None)
                data.pop(f'pictures[{i}][property]', None)
                data.pop(f'pictures[{i}][image]', None)
                
                inst = PropertyPhoto.objects.filter(id=d.get('id', None))
                if len(inst) == 0:
                    ser = PropertyPhotoSerializer(data=d)
                    ser.is_valid(raise_exception=True)
                    inst = ser.save(updated_by_id=self.request.user.id)
                else:
                    inst = inst.first()
                    # ser = PropertyPhotoSerializer(inst, data=d, partial=partial) 
                pi_ids.append(inst.id)
            for p in request.data.getlist('pictures[]'):
                ser = PropertyPhotoSerializer(data={'image': p, "property": instance.id})
                ser.is_valid(raise_exception=True)
                inst = self.perform_create(ser)
                pi_ids.append(inst.id)
            PropertyPhoto.objects.filter(~Q(id__in=pi_ids), property=instance).delete()
                
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
            
            if not data.get('video'):
                data['logo'] = None
                data['video'] = None
                data['virtual_tour'] = None
            print('----------------')
            print(data.get('address'))
            print('============ 4 =============')
            city_id = None
            if not data.get('address').get('properties').get('city_data').get('id', None):
                print('====Create City****')
                ser = CitySerializer(data=data.get('address').get('properties').get('city_data'))
                ser.is_valid(raise_exception=True)
                inst = ser.save()
                data['address']['properties']['city_id'] = inst.id
                city_id = inst.id
            else:
                print('====Have City****')
                city_id = data.get('address').get('properties').get('city_data').get('id')
                data['address']['properties']['city_id'] = city_id
                data['address']['properties'].pop('city_data', None)
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
            address = ser.save(updated_by_id=self.request.user.id, city_id=city_id)
            # address.city_id = city_id
            # address.save()
            print(address)
            print(address.id)
                
            serializer = PropertySerializer(instance, data=data, partial=partial, context={'address_id': address.id, 'updated_by_id': self.request.user.id})
            # serializer = self.get_serializer(instance, data=request.data, partial=partial)
            print(3)
            serializer.is_valid(raise_exception=True)
            print('============ 5 =============')
            print('============ 6 =============')
            instance = self.perform_update(serializer)
            print('============ 7 =============')
            # print(instance__)
            
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
            return Response(PropertySerializer(instance).data, status=status.HTTP_201_CREATED)
    
    def list(self, request, *args, **kwargs):
        profile = request.user.user_profile
        page_number = request.query_params.get('page', None)
        size = request.query_params.get('size', 0)
        search = request.query_params.get('search', None)
        direction = '' if request.query_params.get('direction', 'asc') == 'asc' else '-'
        sortby = f"{direction}{request.query_params.get('sortby', 'created')}"
        print('...: ', page_number)
        print('...: ', request.query_params)
        print('...: ', type(request.query_params))
        
        # queryset = self.filter_queryset(self.get_queryset())
        queryset = Property.objects.filter(Q(Q(company__isnull=False, company=profile.company) | Q(administrator=profile)), enabled=True).order_by(sortby)

        if size == 0 and page_number:
            print(111)
            pagy = self.paginate_queryset(queryset)
            total = Property.objects.filter(Q(Q(company__isnull=False, company=profile.company) | Q(administrator=profile)), enabled=True).count()
            # print('Pagination: ', page)
            if pagy is not None:
                size = request.query_params.get('size', None)
                print(size) 
                # page.page_size_query_param = 
                serializer = self.get_serializer(pagy, many=True)
                return self.get_paginated_response(serializer.data)
        else:
            page_number = int(page_number) if page_number else 1
            size = int(size) if size and int(size) > 0 else 100
            print(222)
            print(page_number, '   ', page_number*size, ' ---- ', size)
            if request.user.is_manager:
                print(2222)
                total = Property.objects.filter(enabled=True).count()
                if search:
                    print("2222a")
                    total = Property.objects.filter(Q(ref__icontains=search) | Q(name__icontains=search) | Q(type__icontains=search) | Q(space__icontains=search)).count()
                    queryset = Property.objects.filter(Q(ref__icontains=search) | Q(name__icontains=search) | Q(type__icontains=search) | Q(space__icontains=search)).order_by(sortby)[page_number*size:(page_number*size)+size]
                else:
                    print("2222b")
                    queryset = Property.objects.filter(enabled=True).order_by(sortby)[page_number*size:(page_number*size)+size]
            else:
                print("3333")
                total = Property.objects.filter(Q(Q(company__isnull=False, company=profile.company) | Q(administrator=profile)), enabled=True).count()
                if search:
                    print("3333a")
                    total = Property.objects.filter(Q(Q(company__isnull=False, company=profile.company) | Q(administrator=profile)), Q(Q(ref__icontains=search) | Q(name__icontains=search) | Q(type__icontains=search) | Q(space__icontains=search)), enabled=True).count()
                    queryset = Property.objects.filter(Q(Q(company__isnull=False, company=profile.company) | Q(administrator=profile)), Q(Q(ref__icontains=search) | Q(name__icontains=search) | Q(type__icontains=search) | Q(space__icontains=search)), enabled=True).order_by(sortby)[page_number*size:(page_number*size)+size]
                else:
                    print("3333b")
                    queryset = Property.objects.filter(Q(Q(company__isnull=False, company=profile.company) | Q(administrator=profile)), enabled=True).order_by(sortby)[page_number*size:(page_number*size)+size]
                # queryset = queryset[page_number*size:(page_number*size)+size]
            serializer = self.get_serializer(queryset, many=True)
            return Response({"data": serializer.data, "total_count": total})
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(methods=['post', 'get'], detail=False, url_path='search', url_name='search')
    def search(self, request, *args, **kwargs):
        self.pagination_class.page_size = 20
        data = request.data
        print('...........: ', data)
        geometry = data.get('geometry', None)
        address = data.get('address', None)
        
        if not geometry and not address:
            return Response({"message": "Address component is missing"}, status=status.HTTP_404_NOT_FOUND)
        
        print(type(geometry))
        print(geometry)
        print(1)
        if geometry:
            print(2)
            if geometry.get('type') == 'Point':
                print(22)
                geometry = json.dumps(data.get('geometry'))
                print(type(geometry))
                point = GEOSGeometry(geometry)
                queryset = Property.objects.filter(address__location__distance_lt=(point, 300/40000*360))
            elif geometry.get('type') == 'Polygon':
                print(222)
                ne = data.get('geometry').get('ne')
                sw = data.get('geometry').get('sw')

                # https://stackoverflow.com/questions/9466043/geodjango-within-a-ne-sw-box
                # ne = (latitude, longitude) = high
                # sw = (latitude, longitude) = Low
                # xmin=sw[1]=sw.lng
                # ymin=sw[0]=sw.lat
                # xmax=ne[1]=ne.lng
                # ymax=ne[0]=ne.lat
                # bbox = (sw[1], sw[0], ne[1], ne[0]) = (xmin, ymin, xmax, ymax) = (sw['lng'], sw['lat'], ne['lng'], ne['lat'])

                # bbox = (ne['lat'], sw['lng'], ne['lng'], sw['lat'])
                bbox = (sw['lng'], sw['lat'], ne['lng'], ne['lat'])
                print('****bbox  ', bbox)
                geometry = Polygon.from_bbox(bbox)
                queryset = Property.objects.filter(address__location__within=geometry)
        else:
            print(3)
            print(address)
            print(config('GOOGLE_GEOCODING_KEY'))
            r = requests.get(requote_uri(config('GOOGLE_GEOCODING_LINK').format(config('GOOGLE_GEOCODING_KEY'), address)))
            if r.status_code == 200:
                js = r.json()
                print(js)
                if js['status'] == 'OK':
                    # loc = js['results'][0]['geometry']['location']
                    # geometry = json.dumps({"type": "Point", "coordinates": [loc['lat'], loc['lng']]})
                    
                    vp = js['results'][0]['geometry']['viewport']
                    ne = vp.get('northeast', {})
                    sw = vp.get('southwest', {})

                    # xmin=sw[1]
                    # ymin=sw[0]
                    # xmax=ne[1]
                    # ymax=ne[0]
                    # bbox = (sw.lng, sw.lat, ne.lng, ne.lat)
                    bbox = (sw.get('lng', 0), sw.get('lat', 0), ne.get('lng', 0), ne.get('lat', 0))
                    print('===== ', bbox)
                    geometry = Polygon.from_bbox(bbox)
                    queryset = Property.objects.filter(address__location__contains=geometry)
                else:
                    return Response({"message": "We are unable to Geolocate the address provided"}, status=status.HTTP_404_NOT_FOUND)
            else:
                return Response({"message": "We are unable to Geolocate the address provided"}, status=status.HTTP_404_NOT_FOUND)
                
        print(data.get('guest'))
        print(type(data.get('guest')))
        print(queryset.count())
        print(queryset)

        if data.get('types', None):
            queryset = queryset.filter(type__in=data.get('types', []))
        elif data.get('bookedSpaces', None):
            queryset = queryset.filter(spaces__in=data.get('bookedSpaces', []))
        elif data.get('guest', None):
            if type(data.get('guest')) == int:
                queryset = queryset.filter(max_no_of_guest__gte=data.get('guest'))
            else:
                queryset = queryset.filter(max_no_of_guest__in=data.get('guest', []))
        elif data.get('bedrooms', None):
            queryset = queryset.filter(no_of_bedrooms__in=data.get('bedrooms', []))
        elif data.get('bathrooms', None):
            queryset = queryset.filter(no_of_bathrooms__in=data.get('bathrooms', []))
        elif data.get('price', None):
            queryset = queryset.filter(price_night__in=data.get('price', []))
        elif data.get('accessibility', None):
            queryset = queryset.filter(accessibility__in=data.get('accessibility', []))
        elif data.get('activities', None):
            queryset = queryset.filter(activities__in=data.get('activities', []))
        elif data.get('bathrooms', None):
            queryset = queryset.filter(bathrooms__in=data.get('bathrooms', []))
        elif data.get('entertainments', None):
            queryset = queryset.filter(entertainments__in=data.get('entertainments', []))
        elif data.get('essentials', None):
            queryset = queryset.filter(essentials__in=data.get('essentials', []))
        elif data.get('families', None):
            queryset = queryset.filter(families__in=data.get('families', []))
        elif data.get('features', None):
            queryset = queryset.filter(features__in=data.get('features', []))
        elif data.get('kitchens', None):
            queryset = queryset.filter(kitchens__in=data.get('kitchens', []))
        elif data.get('laundries', None):
            queryset = queryset.filter(laundries__in=data.get('laundries', []))
        elif data.get('outsides', None):
            queryset = queryset.filter(outsides__in=data.get('outsides', []))
        elif data.get('parking', None):
            queryset = queryset.filter(parking__in=data.get('parking', []))
        elif data.get('pool_spas', None):
            queryset = queryset.filter(pool_spas__in=data.get('pool_spas', []))
        elif data.get('safeties', None):
            queryset = queryset.filter(safeties__in=data.get('safeties', []))
        elif data.get('spaces', None):
            queryset = queryset.filter(spaces__in=data.get('spaces', []))
        elif data.get('services', None):
            queryset = queryset.filter(services__in=data.get('services', []))
        
        page = self.paginate_queryset(queryset)
        # print('Pagination: ', page)
        if page is not None:
            print(queryset.count())
            # page.count =  queryset.count()
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(methods=['get'], detail=False, url_path='table/data', url_name='table-data')
    def table_data(self, request, *args, **kwargs):
        pass
        # {
        # data: tradesCollection,
        # paging: {
        #     total: tradesCollectionCount,
        #     page: currentPage,
        #     pages: totalPages,
        # },
        # }
            
    @action(methods=['get'], detail=False, url_path='form/items', url_name='form-items')
    def form_items(self, request, *args, **kwargs):
        orderedDict = BookerSerializer(Booker.objects.filter(enabled=True), many=True).data
        data = list(map(lambda d: dict(d), orderedDict))
        sort_order = {x['name']: i for i, x in enumerate(data) if 'Additional' not in x['name'] or 'Direct Booking' not in x['name']}
        data.sort(key=lambda x: sort_order.get(x["name"], 1000 if 'Additional' in x["name"] else -10))
        bookers = data
        services = ServiceSerializer(Service.objects.filter(enabled=True), many=True).data
        sleepers = SleeperSerializer(Sleeper.objects.filter(enabled=True), many=True).data
        spaces = SpaceSerializer(Space.objects.filter(enabled=True), many=True).data
        bathrooms = BathroomSerializer(Bathroom.objects.filter(enabled=True), many=True).data
        kitchens = KitchenSerializer(Kitchen.objects.filter(enabled=True), many=True).data
        pool_spas = PoolSpaSerializer(PoolSpa.objects.filter(enabled=True), many=True).data
        outsides = OutsideSerializer(Outside.objects.filter(enabled=True), many=True).data
        essentials = EssentialSerializer(Essential.objects.filter(enabled=True), many=True).data
        entertainments = EntertainmentSerializer(Entertainment.objects.filter(enabled=True), many=True).data
        laundries = LaundrySerializer(Laundry.objects.filter(enabled=True), many=True).data
        families = FamilySerializer(Family.objects.filter(enabled=True), many=True).data
        parking = ParkingSerializer(Parking.objects.filter(enabled=True), many=True).data
        accessibility = AccessibilitySerializer(Accessibility.objects.filter(enabled=True), many=True).data
        
        safeties = SafetySerializer(Safety.objects.filter(enabled=True), many=True).data
        features = FeatureSerializer(Feature.objects.filter(enabled=True), many=True).data
        activities = ActivitySerializer(Activity.objects.filter(enabled=True), many=True).data

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
            'activities': activities
            }, status=status.HTTP_201_CREATED)

    @action(methods=['get'], detail=False, url_path='fixed/items', url_name='fixed-items')
    def fixed_items(self, request, *args, **kwargs):
        
        return Response({
            'types': Property.TYPES, 
            'booked_spaces': Property.BOOKED_SPACE, 
            # 'room_types': Property.ROOM_TYPES,
            'sleeper_types': Property.SLEEPER_TYPES
            }, status=status.HTTP_201_CREATED)

    @action(methods=['patch', 'post'], detail=True, url_path='publish', url_name='publish')
    def publish(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_published = not instance.is_published
        instance.save()
        
        return Response(PropertyListSerializer(instance=instance).data)
    
    @action(methods=['get'], detail=False, url_path='mine', url_name='mine')
    def mine(self, request, *args, **kwargs):
        p = request.user.user_profile
        company = Property.objects.filter(Q(administrator=p) | Q(members=p), enabled=True).prefetch_related(
            Prefetch('company_offices', queryset=Office.objects.filter(enabled=True).prefetch_related(
                Prefetch('office_properties', queryset=Property.objects.filter(enabled=True)))), 
            Prefetch('company_portfolios', queryset=Portfolio.objects.filter(enabled=True).prefetch_related(
                Prefetch('portfolio_properties', queryset=Property.objects.filter(enabled=True)))),
            Prefetch('members', queryset=Profile.objects.filter(enabled=True).prefetch_related(
                Prefetch('portfolios', queryset=Portfolio.objects.filter(enabled=True)),
                Prefetch('offices', queryset=Office.objects.filter(enabled=True)))),
            Prefetch('invitations', queryset=Invitation.objects.filter(enabled=True))
        ).first()
        if company:
            return Response(CompanyMDLDetailSerializer(company).data, status=status.HTTP_200_OK)
        else:
            return Response(None, status=status.HTTP_200_OK)

    
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
    
