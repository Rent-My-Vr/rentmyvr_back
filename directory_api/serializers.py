from csv import field_size_limit
from dataclasses import fields
import logging
from uuid import UUID
from django.conf import settings
from django.db import transaction
from django.contrib.auth import get_user_model
from pyparsing import empty
from rest_framework import serializers
from rest_framework.authtoken.models import Token
from rest_framework.fields import UUIDField

from django.contrib.auth.models import Permission

from auths_api.serializers import UserSerializer, UserUpdateSerializer, UserNameSerializer
from core.models import *
from core_api.serializers import *
from directory.models import *


log = logging.getLogger("{}.*".format(__package__))
log.setLevel(settings.LOGGING_LEVEL)
UserModel = get_user_model()



class AccessibilitySerializer(serializers.ModelSerializer):
    pass

    class Meta:
        model = Accessibility
        fields = ('id', 'name', 'icon')


class ActivitySerializer(serializers.ModelSerializer):
    pass

    class Meta:
        model = Activity
        fields = ('id', 'name', 'icon')


class BathroomSerializer(serializers.ModelSerializer):
    pass

    class Meta:
        model = Bathroom
        fields = ('id', 'name', 'icon')


class BookerSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Booker
        fields = ('id', 'name', 'base')


class BookingSiteSerializer(serializers.ModelSerializer):
    property = serializers.PrimaryKeyRelatedField(required=False, allow_null=True, pk_field=UUIDField(format='hex_verbose'), queryset=Property.objects.filter(enabled=True))
    
    class Meta:
        model = BookingSite
        fields = ('id', 'booker', 'site', 'property')


class BookingSiteFullSerializer(serializers.ModelSerializer):
    property = serializers.PrimaryKeyRelatedField(required=False, allow_null=True, pk_field=UUIDField(format='hex_verbose'), queryset=Property.objects.filter(enabled=True))
    booker = BookerSerializer(many=False, read_only=False)
    
    class Meta:
        model = BookingSite
        fields = ('id', 'booker', 'site', 'property')


class InquiryMessageSerializer(serializers.ModelSerializer):
    pass

    class Meta:
        model = InquiryMessage
        exclude = ('enabled', )


class EntertainmentSerializer(serializers.ModelSerializer):
    pass

    class Meta:
        model = Entertainment
        fields = ('id', 'name', 'icon')


class EssentialSerializer(serializers.ModelSerializer):
    pass

    class Meta:
        model = Essential
        fields = ('id', 'name', 'icon')


class FamilySerializer(serializers.ModelSerializer):
    pass

    class Meta:
        model = Family
        fields = ('id', 'name', 'icon')


class FeatureSerializer(serializers.ModelSerializer):
    pass

    class Meta:
        model = Feature
        fields = ('id', 'name', 'icon')


class KitchenSerializer(serializers.ModelSerializer):
    pass

    class Meta:
        model = Kitchen
        fields = ('id', 'name', 'icon')


class LaundrySerializer(serializers.ModelSerializer):
    pass

    class Meta:
        model = Laundry
        fields = ('id', 'name', 'icon')


class OutsideSerializer(serializers.ModelSerializer):
    pass

    class Meta:
        model = Outside
        fields = ('id', 'name', 'icon')


class ParkingSerializer(serializers.ModelSerializer):
    pass

    class Meta:
        model = Parking
        fields = ('id', 'name', 'icon')


class PoolSpaSerializer(serializers.ModelSerializer):
    pass

    class Meta:
        model = PoolSpa
        fields = ('id', 'name', 'icon')



class SleeperSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Sleeper
        fields = ('id', 'name', 'icon')


class RoomTypeSerializer(serializers.ModelSerializer):
    property = serializers.PrimaryKeyRelatedField(required=False, allow_null=True, pk_field=UUIDField(format='hex_verbose'), queryset=Property.objects.filter(enabled=True))
    
    class Meta:
        model = RoomType
        fields = ('id', 'name', 'sleepers', 'property')


class RoomTypeFullSerializer(serializers.ModelSerializer):
    property = serializers.PrimaryKeyRelatedField(required=False, allow_null=True, pk_field=UUIDField(format='hex_verbose'), queryset=Property.objects.filter(enabled=True))
    sleepers = SleeperSerializer(many=True, read_only=False)
    
    class Meta:
        model = RoomType
        fields = ('id', 'name', 'sleepers', 'property')


class SafetySerializer(serializers.ModelSerializer):
    pass

    class Meta:
        model = Safety
        fields = ('id', 'name', 'icon')


class SpaceSerializer(serializers.ModelSerializer):
    pass

    class Meta:
        model = Space
        fields = ('id', 'name', 'icon')


class ServiceSerializer(serializers.ModelSerializer):
    pass

    class Meta:
        model = Service
        fields = ('id', 'name', 'icon')


class SocialMediaLinkSerializer(serializers.ModelSerializer):
    property = serializers.PrimaryKeyRelatedField(required=False, allow_null=True, pk_field=UUIDField(format='hex_verbose'), queryset=Property.objects.filter(enabled=True))
    
    class Meta:
        model = SocialMediaLink
        fields = ('id', 'name', 'site', 'property')


class PropertyPhotoSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = PropertyPhoto
        fields = ('id', 'property', 'image')


class PropertySerializer(serializers.ModelSerializer):
    address = AddressCreateSerializer(many=False, read_only=False)
    # address = serializers.SerializerMethodField("get_address")
    booking_sites = BookingSiteSerializer(many=True, read_only=False)
    social_media = SocialMediaLinkSerializer(many=True, read_only=False)
    pictures = PropertyPhotoSerializer(many=True, read_only=True)
    room_types = RoomTypeSerializer(many=True, read_only=False)
    
    # def __init__(self, *args, **kwargs):
    #     # # Don't pass the 'fields' arg up to the superclass
    #     # request = kwargs.get('context', {}).get('request')
    #     # str_fields = request.GET.get('fields', '') if request else None
    #     # fields = str_fields.split(',') if str_fields else None
    #     # # Instantiate the superclass 
    #     print('=================11==================')
    #     print(kwargs['data'])
    #     print('=================111==================')
    #     print(kwargs['data']['address'])
    #     # print(kwargs['data']['address']['city'].get('id', None))
    #     print('==================1111=================', )
    #     super(PropertySerializer, self).__init__(*args, **kwargs)
    #     # self.address = AddressSerializer(many=False, read_only=False) if kwargs['data']['address']['city'].get('id', None) else AddressDetailSerializer(many=False, read_only=False)
    #     # print('=================2**2================== ', type(self.address))
    #     # if fields is not None:
    #     #     # Drop any fields that are not specified in the `fields`
    #     #     # argument.
    #     #     allowed = set(fields)
    #     #     existing = set(self.fields)
    #     #     for field_name in existing - allowed:
    #     #         self.fields.pop(field_name)
       
    # def get_address(self, obj):
    #     request = self.context.get('request')
    #     print('+++++++++++++++++++++++++++++++')
    #     print(request)
    #     print(request.data)
    #     # serializer_context = {'request': request }
    #     # authors = obj.authors.all()
    #     # serializer = AuthorModelSerializer(authors, many=True, context=serializer_context)
    #     serializer = AddressSerializer(many=False, read_only=False) if request.data['address']['city'].get('id', None) else AddressDetailSerializer(many=False, read_only=False)
        
    #     print(type(serializer))
    #     print(serializer.data)
    #     print('+++++++++++++++++++++++++++++++')
    #     return serializer.data
               
    def create(self, validated_data):
        print('===========: ******** : 11============')
        print(validated_data)
        print('===========: ******** : 22============')
        city_data = self.context.get('city_data', {})
        print(city_data)
        print('===========: ******** : 33============')
        address_data = validated_data.pop('address')
        accessibility = validated_data.pop('accessibility')
        activities = validated_data.pop('activities')
        bathrooms = validated_data.pop('bathrooms')
        entertainments = validated_data.pop('entertainments')
        essentials = validated_data.pop('essentials')
        families = validated_data.pop('families')
        features = validated_data.pop('features')
        kitchens = validated_data.pop('kitchens')
        laundries = validated_data.pop('laundries')
        outsides = validated_data.pop('outsides')
        parking = validated_data.pop('parking')
        pool_spas = validated_data.pop('pool_spas')
        safeties = validated_data.pop('safeties')
        spaces = validated_data.pop('spaces')
        services = validated_data.pop('services')
        social_media = validated_data.pop('social_media')
        booking_sites = validated_data.pop('booking_sites')
        validated_data.pop('room_types')
        # room_types = validated_data.pop('room_types')
        # pictures = validated_data.pop('pictures')

        with transaction.atomic():
            print('==== 1 ====')
            print(address_data)
            print('==== 2 ====')
            print(validated_data)
            print('==== 22 ====')
            print(social_media)
            print('==== 222 ====')
            print(booking_sites)
            print('==== 2222 ====')
            print(address_data)
            print('==== 22222 ====')
            print(address_data.get('city'))
            print('****************************')
            if address_data.get('city'):
                city = address_data.get('city')
            else:
                city = City.objects.get_or_create(**city_data)
                city = city[0].id
            address_data['city_id'] = city
            address = Address.objects.create(**address_data)
            print('==== 3 ====')
            property = Property.objects.create(address=address, **validated_data)
            # for r in room_types:
            #     r['property'] = property
            #     RoomType.objects.create(**r)
            for b in booking_sites:
                b['property'] = property
                BookingSite.objects.create(**b)
            for s in social_media:
                s['property'] = property
                SocialMediaLink.objects.create(**s)
            # for p in pictures:
            #     s['property'] = property
            #     SocialMediaLink.objects.create(**s)
            property.accessibility.add(*accessibility)
            property.activities.add(*activities)
            property.bathrooms.add(*bathrooms)
            property.entertainments.add(*entertainments)
            property.essentials.add(*essentials)
            property.families.add(*families)
            property.features.add(*features)
            property.kitchens.add(*kitchens)
            property.laundries.add(*laundries)
            property.outsides.add(*outsides)
            property.parking.add(*parking)
            property.pool_spas.add(*pool_spas)
            property.safeties.add(*safeties)
            property.spaces.add(*spaces)
            property.services.add(*services)
            print('==== 4 ====')
            print(accessibility)
            # for it in accessibility:
            #     Accessibility.objects.create(property=property, **it)
            # for it in activities:
            #     Activity.objects.create(property=property, **it)
            # for it in bathrooms:
            #     Bathroom.objects.create(property=property, **it)
            # for it in entertainments:
            #     Entertainment.objects.create(property=property, **it)
            # for it in essentials:
            #     Essential.objects.create(property=property, **it)
            # for it in families:
            #     Family.objects.create(property=property, **it)
            # for it in features:
            #     Feature.objects.create(property=property, **it)
            # for it in kitchens:
            #     Kitchen.objects.create(property=property, **it)
            # for it in laundries:
            #     Laundry.objects.create(property=property, **it)
            # for it in outsides:
            #     Outside.objects.create(property=property, **it)
            # for it in parking:
            #     Parking.objects.create(property=property, **it)
            # for it in pool_spas:
            #     PoolSpa.objects.create(property=property, **it)
            # for it in safeties:
            #     Safety.objects.create(property=property, **it)
            # for it in spaces:
            #     Space.objects.create(property=property, **it)
            # for it in services:
            #     Service.objects.create(property=property, **it)
            return property
        return None

    def update(self, instance, validated_data):
        print('===========: Update ******** : 11============')
        print(validated_data)
        print(instance)
        print('===========: ******** : 22============')
        # city_data = self.context.get('city_data', {})
        updated_by_id = self.context.get('updated_by_id', '')
        address_id = self.context.get('address_id', '')
        # print(city_data)
        print(updated_by_id, '  ===========: ******** : 33============')
        validated_data.pop('address')
        # address_data['city'] = city_data.get('id') if city_data.get('id', None) else None
        accessibility = validated_data.pop('accessibility')
        activities = validated_data.pop('activities')
        bathrooms = validated_data.pop('bathrooms')
        entertainments = validated_data.pop('entertainments')
        essentials = validated_data.pop('essentials')
        families = validated_data.pop('families')
        features = validated_data.pop('features')
        kitchens = validated_data.pop('kitchens')
        laundries = validated_data.pop('laundries')
        outsides = validated_data.pop('outsides')
        parking = validated_data.pop('parking')
        pool_spas = validated_data.pop('pool_spas')
        safeties = validated_data.pop('safeties')
        spaces = validated_data.pop('spaces')
        services = validated_data.pop('services')
        social_media = validated_data.pop('social_media')
        booking_sites = validated_data.pop('booking_sites')
        # pictures = validated_data.pop('pictures')
        # suitabilities = validated_data.pop('suitabilities')
        validated_data.pop('room_types')
        # room_types = validated_data.pop('room_types')
        # pictures = validated_data.pop('pictures')

        with transaction.atomic():
            print('==== 11 ====')
            # print(pictures)
            # print('==== 111 ====')
            # print(suitabilities)
            # print('==== 2 ====')
            print(validated_data)
            print('==== 22 ====')
            # print(social_media)
            # print('==== 222 ====')
            # print(booking_sites)
            # print('==== 2222 ====')
            print(address_id)
            # print('==== 22222 ====')
            # print(address_data.get('city'))
            print('****************************')
            # if address_data.get('city'):
            #     city = address_data.get('city')
            # else:
            #     city_data['updated_by_id'] = updated_by_id
            #     print(city_data)
            #     city = City.objects.get_or_create(id=city_data.get('id', None), defaults=city_data)
            #     city = city[0].id
            # address_data['city'] = None
            # address_data['city_id'] = city
            # address = Address.objects.update(id=address_data.get('id'), **address_data)
            print('==== 3 ====')
            print(validated_data)
            # property = Property.objects.update(id=validated_data.get('id'), **validated_data)
            property = Property.objects.filter(id=instance.id).update(address_id=address_id, **validated_data)
            # property = instance.update(address_id=address_id, **validated_data)
            # for r in room_types:
            #     r['property'] = property
            #     RoomType.objects.create(**r)
            # for b in booking_sites:
            #     b['property'] = instance
            #     bb, status = BookingSite.objects.get_or_create(**b)
            #     if not status:
            #         print(b)
            #         bb.updated(**b)
            # for s in social_media:
            #     s['property'] = instance
            #     ss, status = SocialMediaLink.objects.get_or_create(**s)
            #     if not status:
            #         ss.updated(**s)
            
            
            # for p in pictures:
            #     s['property'] = property
            #     SocialMediaLink.objects.create(**s)
            instance.accessibility.set(accessibility)
            instance.activities.set(activities)
            instance.bathrooms.set(bathrooms)
            instance.entertainments.set(entertainments)
            instance.essentials.set(essentials)
            instance.families.set(families)
            instance.features.set(features)
            instance.kitchens.set(kitchens)
            instance.laundries.set(laundries)
            instance.outsides.set(outsides)
            instance.parking.set(parking)
            instance.pool_spas.set(pool_spas)
            instance.safeties.set(safeties)
            instance.spaces.set(spaces)
            instance.services.set(services)
            print('==== 4 ====')
            print(accessibility)
            
            return instance
        return None

    class Meta:
        model = Property
        exclude = ()
        read_only_fields = ('id', 'ref', 'enabled', 'updated', 'updated_by')


class PropertyListSerializer(serializers.ModelSerializer):
    address = AddressSerializer(many=False, read_only=False)
    # address = serializers.SerializerMethodField("get_address")
    booking_sites = BookingSiteSerializer(many=True, read_only=False)
    social_media = SocialMediaLinkSerializer(many=True, read_only=False)
    pictures = PropertyPhotoSerializer(many=True, read_only=True)
    room_types = RoomTypeSerializer(many=True, read_only=False)
    
    class Meta:
        model = Property
        exclude = ()
        read_only_fields = ('id', 'ref', 'enabled', 'updated', 'updated_by')


class PropertyDetailSerializer(serializers.ModelSerializer):
    address = AddressDetailSerializer(many=False, read_only=True)
    booking_sites = BookingSiteFullSerializer(many=True, read_only=True)
    social_media = SocialMediaLinkSerializer(many=True, read_only=True)
    pictures = PropertyPhotoSerializer(many=True, read_only=True)
    room_types = RoomTypeFullSerializer(many=True, read_only=True)
    
    accessibility = AccessibilitySerializer(many=True, read_only=True)
    activities = ActivitySerializer(many=True, read_only=True)
    bathrooms = BathroomSerializer(many=True, read_only=True)
    entertainments = EntertainmentSerializer(many=True, read_only=True)
    essentials = EssentialSerializer(many=True, read_only=True)
    families = FamilySerializer(many=True, read_only=True)
    features = FeatureSerializer(many=True, read_only=True)
    kitchens = KitchenSerializer(many=True, read_only=True)
    laundries = LaundrySerializer(many=True, read_only=True)
    outsides = OutsideSerializer(many=True, read_only=True)
    parking = ParkingSerializer(many=True, read_only=True)
    pool_spas = PoolSpaSerializer(many=True, read_only=True)
    safeties = SafetySerializer(many=True, read_only=True)
    spaces = SpaceSerializer(many=True, read_only=True)
    services = ServiceSerializer(many=True, read_only=True)
    
    class Meta:
        model = Property
        exclude = ()
        read_only_fields = ('id', 'ref', 'enabled', 'updated', 'updated_by')
        
