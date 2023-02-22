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
from directory.models import *

from core.custom_permission import IsAuthenticatedOrCreate
from core_api.serializers import *
from core_api.models import *
from directory_api.serializers import *
from directory.models import *


log = logging.getLogger(f"{__package__}.*")
log.setLevel(settings.LOGGING_LEVEL)



class UUIDEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, UUID):
            return obj.hex
        return json.JSONEncoder.default(self, obj)


class PropertyViewSet(viewsets.ModelViewSet, AchieveModelMixin):
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
 
    def get_serializer_class(self):
        if self.action in ['create', 'update']:
            return PropertySerializer
        return PropertySerializer

    def perform_create(self, serializer):
        return serializer.save(updated_by_id=self.request.user.id)
        
    def perform_update(self, serializer):
        return serializer.save(updated_by_id=self.request.user.id)
      
    def create(self, request, *args, **kwargs):
        with transaction.atomic():
            print('============1=============')
            print(request.data)
            print('============2=============')
            print(request.POST)
            print('============3=============')
            print(request)
            print('============4=============')
            serializer = PropertySerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            instance = self.perform_create(serializer)
            for p in request.data['pictures']:
                ser = PropertyPhotoSerializer(data={'image': p, "property": instance})
                ser.is_valid(raise_exception=True)
                pic = self.perform_create(ser)
            
            # data = request.data.copy()
            # print(data)
            # data['name'] = template.name
            # data['category'] = str(template.category.id)
            # x = 0
            # for t_id in map(lambda x: str(x.id), template.tags.filter(enabled=True, is_approved=True)):
            #     data[f'tags.{x}'] = t_id
            #     x += 1
            # data['time_per_unit'] = template.time_per_unit
            # data['worker_per_unit'] = template.worker_per_unit
            # data['measurement_unit'] = template.measurement_unit
            # data['container_type'] = json.dumps(template.container_type)
            # data['note'] = data['note'] if data['note'] else template.note
            # data['instructions'] = template.instructions
            # serializer = WorkActivitySerializer(data=data)
            # serializer.is_valid(raise_exception=True)
            # instance = self.perform_create(serializer)
            # if instance.report.status == WorkReport.MISSING:
            #     instance.report.status = WorkReport.INCOMPLETE
            #     instance.report.save()
            # delay_set = set()
            # activity_set = set()
            # for k in data.keys():
            #     if f'delay_images.' in k:
            #         delay_set.add(re.findall(r"^delay_images\.(\d+)\.\w", k)[0])
            #     elif f'activity_images.' in k:
            #         activity_set.add(re.findall(r"^activity_images\.(\d+)\.\w", k)[0])
            # print('delay_length: ', len(delay_set))
            # for i in range(len(delay_set)):
            #     d = dict()
            #     d['type'] = data[f'delay_images.{i}.type'] 
            #     d['image'] = data[f'delay_images.{i}.image'] 
            #     d['activity'] = instance.id
            #     ser = WorkActivityPhotoSerializer(data=d)
            #     ser.is_valid(raise_exception=True)
            #     ser.save(updated_by_id=self.request.user.id) 
            # print('activity_length: ', len(activity_set))
            # for i in range(len(activity_set)):
            #     d = dict()
            #     d['type'] = data[f'activity_images.{i}.type'] 
            #     d['image'] = data[f'activity_images.{i}.image'] 
            #     d['activity'] = instance.id
            #     ser = WorkActivityPhotoSerializer(data=d)
            #     ser.is_valid(raise_exception=True)
            #     ser.save(updated_by_id=self.request.user.id)   
            # headers = self.get_success_headers(serializer.data)
            return Response(PropertySerializer(instance).data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        with transaction.atomic():
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            serializer = WorkActivityByTemplateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            data = request.data.copy()
            print(data)
            print(type(data))
            print("=====================================================")
            data = data.dict()
            print(data)
            print(type(data))
            
            template = WorkActivityTemplate.objects.get(id=request.data['template'])
            data['name'] = template.name
            data['category'] = str(template.category.id)
            x = 0
            data['tags'] = list(map(lambda x: str(x.id), template.tags.filter(enabled=True)))
            # for t in map(lambda x: str(x.id), template.tags.filter(enabled=True)):
            #     data[f'tags.{x}'] = t
            #     x += 1
            data['time_per_unit'] = template.time_per_unit
            data['worker_per_unit'] = template.worker_per_unit
            data['measurement_unit'] = template.measurement_unit
            data['container_type'] = json.dumps(template.container_type)
            data['note'] = data['note'] if data['note'] else template.note
            data['instructions'] = template.instructions

            pictures_set = set()
            delay_set = set()
            activity_set = set()
            specifiers = []
            for k in data.keys():
                if f'delay_images.' in k:
                    delay_set.add(re.findall(r"^delay_images\.(\d+)\.\w", k)[0])
                elif f'activity_images.' in k:
                    activity_set.add(re.findall(r"^activity_images\.(\d+)\.\w", k)[0])
                elif f'pictures.' in k:
                    pictures_set.add(re.findall(r"^pictures\.(\d+)\.\w", k)[0])
                elif f'specifiers.' in k:
                    res = re.findall(r"^specifiers\.(\d+)", k)[0]
                    specifiers.append(data[f'specifiers.{res}'])
            
            data['specifiers'] = specifiers
            print(specifiers)
            serializer = WorkActivitySerializer(instance, data=data, partial=partial)
            serializer.is_valid(raise_exception=True)
            instance = self.perform_update(serializer)

            # images = data.getlist('pictures', [])
            # print('---------')
            # print(images)
            
            images = []
            print('pictures_length: ', len(pictures_set))
            for i in range(len(pictures_set)):
                images.append(data[f'pictures.{i}.id'] )
            
            print('--------')
            print(images)
            d=WorkActivityPhoto.objects.filter(~Q(id__in=images), activity=instance).delete()
            print(d)
            
            if instance.delay > 0:
                print('delay_length: ', len(delay_set))
                for i in range(len(delay_set)):
                    d = dict()
                    d['type'] = data[f'delay_images.{i}.type'] 
                    d['image'] = data[f'delay_images.{i}.image'] 
                    d['activity'] = instance.id
                
                    ser = WorkActivityPhotoSerializer(data=d)
                    ser.is_valid(raise_exception=True)
                    ser.save(updated_by_id=self.request.user.id) 
                
            print('activity_length: ', len(activity_set))
            for i in range(len(activity_set)):
                d = dict()
                d['type'] = data[f'activity_images.{i}.type'] 
                d['image'] = data[f'activity_images.{i}.image'] 
                d['activity'] = instance.id
            
                ser = WorkActivityPhotoSerializer(data=d)
                ser.is_valid(raise_exception=True)
                ser.save(updated_by_id=self.request.user.id) 
                
            if getattr(instance, '_prefetched_objects_cache', None):
                # If 'prefetch_related' has been applied to a queryset, we need to
                # forcibly invalidate the prefetch cache on the instance.
                instance._prefetched_objects_cache = {}

            return Response(WorkActivityListSerializer(instance).data, status=status.HTTP_201_CREATED)

    @action(methods=['get'], detail=False, url_path='form/items', url_name='form-items')
    def form_items(self, request, *args, **kwargs):
        services = ServiceSerializer(Service.objects.filter(enabled=True), many=True).data
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
