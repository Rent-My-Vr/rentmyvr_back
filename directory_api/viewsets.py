import json
import copy
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
        if self.action in ['retrieve']:
            return PropertyDetailSerializer
        return PropertySerializer

    def perform_create(self, serializer):
        return serializer.save(updated_by_id=self.request.user.id)
        
    def perform_update(self, serializer):
        return serializer.save(updated_by_id=self.request.user.id)
      
    def create(self, request, *args, **kwargs):
        with transaction.atomic():
            print('============ 0 =============')
            # print(request.data)
            print('============ 1 =============')
            
            # pictures = request.data.getlist('pictures[]')
            # print(pictures)
            print('============ 2 =============')
            data = copy.deepcopy(request.data)
            print(data)
            # data = request.data.copy()
            print('============ 3 =============')
            data['address'] = {}
            data['address']['street'] = request.data.get('address[street]')
            data['address']['number'] = request.data.get('address[number]')
            data['address']['city'] = request.data.get('address[city]')
            data['address']['zip_code'] = request.data.get('address[zip_code]')
            data['address']['state'] = request.data.get('address[state]')
            data['address']['city_id'] = request.data.get('address[city_id]')
            
            print(data)
            print(data.getlist('booking_sites[]'))
            
            booking_sites_set = set()
            social_media_set = set()
            for k in data.keys():
                if f'booking_sites[' in k:
                    print('b ---: ', k)
                    booking_sites_set.add(re.findall(r"^booking_sites\[(\d+)\]\[\w+\]$", k)[0])
                elif f'social_media[' in k:
                    print('s ---: ', k)
                    social_media_set.add(re.findall(r"^social_media\[(\d+)\]\[\w+\]$", k)[0])
            
            print('booking_sites_set_length: ', len(booking_sites_set))
            print('social_media_set_length: ', len(social_media_set))
            booking_sites = []
            for i in range(len(booking_sites_set)):
                d = dict()
                d['name'] = data[f'booking_sites[{i}][name]']
                data.pop(f'booking_sites[{i}][name]', None)
                d['site'] = data[f'booking_sites[{i}][site]']
                data.pop(f'booking_sites[{i}][site]', None)
                d['label'] = data[f'booking_sites[{i}][label]']
                data.pop(f'booking_sites[{i}][label]', None)
                d['property'] = None
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

            data['accessibility'] = data.getlist('accessibility[]')
            data.pop(f'accessibility[]', None)
            data['activities'] = data.getlist('activities[]')
            data.pop(f'activities[]', None)
            data['bathrooms'] = data.getlist('bathrooms[]')
            data.pop(f'bathrooms[]', None)
            data['entertainments'] = data.getlist('entertainments[]')
            data.pop(f'entertainments[]', None)
            data['essentials'] = data.getlist('essentials[]')
            data.pop(f'essentials[]', None)
            data['families'] = data.getlist('families[]')
            data.pop(f'families[]', None)
            data['features'] = data.getlist('features[]')
            data.pop(f'features[]', None)
            data['kitchens'] = data.getlist('kitchens[]')
            data.pop(f'kitchens[]', None)
            data['laundries'] = data.getlist('laundries[]')
            data.pop(f'laundries[]', None)
            data['outsides'] = data.getlist('outsides[]')
            data.pop(f'outsides[]', None)
            data['parking'] = data.getlist('parking[]')
            data.pop(f'parking[]', None)
            data['pool_spas'] = data.getlist('pool_spas[]')
            data.pop(f'pool_spas[]', None)
            data['safeties'] = data.getlist('safeties[]')
            data.pop(f'safeties[]', None)
            data['spaces'] = data.getlist('spaces[]')
            data.pop(f'spaces[]', None)
            data['services'] = data.getlist('services[]')
            data.pop(f'services[]', None)
            
            data.pop("address[street]", None)
            data.pop("address[number]", None)
            data.pop("address[city]", None)
            data.pop("address[zip_code]", None)
            data.pop("address[state]", None)
            data.pop("address[city_id]", None)
            data = data.dict()
            data['booking_sites'] = booking_sites
            data['social_media'] = social_media
            print('============ 3 =============')
            print(data)
            if not data.get('video'):
                data['logo'] = None
                data['video'] = None
                data['virtual_tour'] = None
            print('----------------')
            print(data.get('address'))
            print('============ 4 =============')
            serializer = PropertySerializer(data=data)
            print('============ 5 =============')
            serializer.is_valid(raise_exception=True)
            print('============ 6 =============')
            instance = self.perform_create(serializer)
            print('============ 7 =============')
            print(instance)
            print(type(instance))
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

    @action(methods=['get'], detail=False, url_path='fixed/items', url_name='fixed-items')
    def fixed_items(self, request, *args, **kwargs):
        
        return Response({
            'types': Property.TYPES, 
            'booked_spaces': Property.BOOKED_SPACE, 
            'room_types': Property.ROOM_TYPES,
            'sleeper_types': Property.SLEEPER_TYPES
            }, status=status.HTTP_201_CREATED)
