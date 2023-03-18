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
            data['address']['street'] = request.data.get('address[street]')
            data['address']['number'] = request.data.get('address[number]')
            data['address']['city'] = dict()
            data['address']['city']['id'] = request.data.get('address[city][id]', None)
            data['address']['city']['name'] = request.data.get('address[city][name]')
            data['address']['city']['state_name'] = request.data.get('address[city][state_name]')
            data['address']['city']['approved'] = True if data['address']['city']['id'] else False
            data['address']['zip_code'] = request.data.get('address[zip_code]')
            data['address']['state'] = request.data.get('address[state]')
            data['address']['city_id'] = request.data.get('address[city_id]')
            data['address']['hidden'] = request.data.get('address[hidden]')
            
            
            data.pop("address[street]", None)
            data.pop("address[number]", None)
            data.pop("address[city]", None)
            data.pop("address[city][id]", None)
            data.pop("address[city][name]", None)
            data.pop("address[city][state_name]", None)
            data.pop("address[zip_code]", None)
            data.pop("address[state]", None)
            data.pop("address[city_id]", None)
            data.pop("address[hidden]", None)
            
            print(data)
            # print(data.get('booking_sites[]'))
            
            booking_sites_set = set()
            social_media_set = set()
            room_types_set = set()
            room_types_dict = dict()
            max_sleeper = 0
            for k in data.keys():
                print(k)
                if f'booking_sites[' in k:
                    booking_sites_set.add(re.findall(r"^booking_sites\[(\d+)\]\[\w+\]", k)[0])
                elif f'social_media[' in k:
                    social_media_set.add(re.findall(r"^social_media\[(\d+)\]\[\w+\]$", k)[0])
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

            if data.get('accessibility[]', False):
                data['accessibility'] = data.get('accessibility[]')
                data.pop(f'accessibility[]', None)
            if data.get('activities[]', False):
                data['activities'] = data.get('activities[]')
                data.pop(f'activities[]', None)
            if data.get('bathrooms[]', False):
                data['bathrooms'] = data.get('bathrooms[]')
                data.pop(f'bathrooms[]', None)
            if data.get('entertainments[]', False):
                data['entertainments'] = data.get('entertainments[]')
                data.pop(f'entertainments[]', None)
            if data.get('essentials[]', False):
                data['essentials'] = data.get('essentials[]')
                data.pop(f'essentials[]', None)
            if data.get('families[]', False):
                data['families'] = data.get('families[]')
                data.pop(f'families[]', None)
            if data.get('features[]', False):
                data['features'] = data.get('features[]')
                data.pop(f'features[]', None)
            if data.get('kitchens[]', False):
                data['kitchens'] = data.get('kitchens[]')
                data.pop(f'kitchens[]', None)
            if data.get('laundries[]', False):
                data['laundries'] = data.get('laundries[]')
                data.pop(f'laundries[]', None)
            if data.get('outsides[]', False):
                data['outsides'] = data.get('outsides[]')
                data.pop(f'outsides[]', None)
            if data.get('parking[]', False):
                data['parking'] = data.get('parking[]')
                data.pop(f'parking[]', None)
            if data.get('pool_spas[]', False):
                data['pool_spas'] = data.get('pool_spas[]')
                data.pop(f'pool_spas[]', None)
            if data.get('safeties[]', False):
                data['safeties'] = data.get('safeties[]')
                data.pop(f'safeties[]', None)
            if data.get('spaces[]', False):
                data['spaces'] = data.get('spaces[]')
                data.pop(f'spaces[]', None)
            if data.get('services[]', False):
                data['services'] = data.get('services[]')
                data.pop(f'services[]', None)
            
            data['booking_sites'] = booking_sites
            data['social_media'] = social_media
            data['room_types'] = room_types
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
        orderedDict = BookerSerializer(Booker.objects.filter(enabled=True), many=True).data
        data = list(map(lambda d: dict(d), orderedDict))
        sort_order = {x['name']: i for i, x in enumerate(data) if 'Additional' not in x['name'] or 'Direct Booking' not in x['name']}
        data.sort(key=lambda x: sort_order.get(x["name"], 1000 if 'Additional' in x["name"] else -10))
        bookers = data
        services = ServiceSerializer(Service.objects.filter(enabled=True), many=True).data
        sleepers = SleeperSerializer(Sleeper.objects.filter(enabled=True), many=True).data
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
