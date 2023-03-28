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
from rest_framework import viewsets, status, mixins, pagination
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser, FileUploadParser

from django.db.models import Q, Prefetch
from datetime import datetime, timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model
from auths.utils import get_domain
from auths_api.serializers import UserSerializer, UserUpdateSerializer
from notifications.signals import notify

from core.models import *
from core_api.pagination import MyPagination, MyPaginationMixin
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

# class PropertyViewSet(viewsets.ModelViewSet, AchieveModelMixin, MyPaginationMixin):
class PropertyViewSet(viewsets.ModelViewSet):
    # pagination_class = ExamplePagination
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
            data['address']['zip_code'] = request.data.get('address[zip_code]')
            data['address']['state'] = request.data.get('address[state]')
            data['address']['hidden'] = request.data.get('address[hidden]')
            data['address']['city'] = dict()
            data['address']['city']['id'] = request.data.get('address[city][id]', None)
            data['address']['city']['name'] = request.data.get('address[city][name]')
            data['address']['city']['state_name'] = request.data.get('address[city][state_name]')
            data['address']['city']['approved'] = True if data['address']['city']['id'] else False
            data['address']['city_data'] = data['address']['city']
            data['address']['city'] = data['address']['city'].get('id', None) if data['address']['city'].get('id', None) else None
            
            data.pop("address[street]", None)
            data.pop("address[number]", None)
            data.pop("address[zip_code]", None)
            data.pop("address[state]", None)
            data.pop("address[city_id]", None)
            data.pop("address[hidden]", None)
            data.pop("address[city]", None)
            data.pop("address[city][id]", None)
            data.pop("address[city][name]", None)
            data.pop("address[city][state_name]", None)
            data.pop("address[city][updated]", None)
            data.pop("address[city][created]", None)
            data.pop("address[city][country_name]", None)
            data.pop("address[city][approved]", None)
            
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
            print('============ *3* =============')
            print(data)
            if not data.get('video'):
                data['logo'] = None
                data['video'] = None
                data['virtual_tour'] = None
            print('----------------')
            print(data.get('address'))
            print('============ 4 =============')
            serializer = PropertySerializer(data=data, context={'city_data': data['address']['city_data']})
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
                data[d] = request.data.getlist(d) if '[]' in d else request.data[d]
            # pictures = request.data.getlist('pictures[]')
            # print(pictures)
            # print('============ 2 =============')
            # print(data)
            # print('============ 3333 =============')
            data['address'] = {}
            data['address']['id'] = request.data.get('address[id]', None)
            data['address']['street'] = request.data.get('address[street]')
            data['address']['number'] = request.data.get('address[number]')
            data['address']['zip_code'] = request.data.get('address[zip_code]')
            data['address']['state'] = request.data.get('address[state]')
            data['address']['hidden'] = request.data.get('address[hidden]')
            data['address']['more_info'] = request.data.get('address[more_info]')
            data['address']['city'] = dict()
            data['address']['city']['id'] = request.data.get('address[city][id]', None)
            data['address']['city']['imported'] = request.data.get('address[city][imported]', False)
            data['address']['city']['import_id'] = request.data.get('address[city][import_id]', None)
            data['address']['city']['name'] = request.data.get('address[city][name]')
            data['address']['city']['state_name'] = request.data.get('address[city][state_name]')
            data['address']['city']['approved'] = True if data['address']['city']['id'] else False
            data['address']['city_data'] = data['address']['city']
            data['address']['city'] = data['address']['city'].get('id', None) if data['address']['city'].get('id', None) else None
            
            data.pop("address[id]", None)
            data.pop("address[imported]", None)
            data.pop("address[more_info]", None)
            data.pop("address[street]", None)
            data.pop("address[number]", None)
            data.pop("address[zip_code]", None)
            data.pop("address[state]", None)
            data.pop("address[city_id]", None)
            data.pop("address[hidden]", None)
            data.pop("address[city]", None)
            data.pop("address[city][id]", None)
            data.pop("address[city][imported]", None)
            data.pop("address[city][import_id]", None)
            data.pop("address[city][name]", None)
            data.pop("address[city][state_name]", None)
            data.pop("address[city][updated]", None)
            data.pop("address[city][created]", None)
            data.pop("address[city][country_name]", None)
            data.pop("address[city][approved]", None)
            
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
                print(k)
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
            if not data.get('address').get('city_data').get('id', None):
                print('====Create City****')
                ser = CitySerializer(data=data.get('address').get('city_data'))
                ser.is_valid(raise_exception=True)
                inst = ser.save(updated_by_id=self.request.user.id)
                data['address']['city_id'] = inst.id
            else:
                print('====Have City****')
                data['address']['city_id'] = data.get('address').get('city_data').get('id')
            
            print(data.get('address'))
            inst = Address.objects.filter(id=data.get('address').get('id', None)).first()
            print(inst)
            if inst:
                ser = AddressSerializer(inst, data=data.get('address'), partial=partial) 
            else:
                ser = AddressSerializer(data=d)
            print(1)
            ser.is_valid(raise_exception=True)
            print(2)
            address = ser.save(updated_by_id=self.request.user.id)
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
            print(type(instance))
            
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
        p = request.query_params.get('page', None)
        # size = request.query_params.get('size', None)
        print('...: ',p)
        
        queryset = self.filter_queryset(self.get_queryset())
        queryset = Property.objects.all()

        page = self.paginate_queryset(queryset)
        print('Pagination: ', page)
        if page is not None:
            size = request.query_params.get('size', page.page_size_query_param)
            print(size)
            print(page.page_size_query_param)
            # page.page_size_query_param = 
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset[0:2], many=True)
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
