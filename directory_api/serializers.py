from csv import field_size_limit
from dataclasses import fields
import logging

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
        fields = ('id', 'name')



class ActivitySerializer(serializers.ModelSerializer):
    pass

    class Meta:
        model = Activity
        fields = ('id', 'name')


class BathroomSerializer(serializers.ModelSerializer):
    pass

    class Meta:
        model = Bathroom
        fields = ('id', 'name')


class BookerSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Booker
        fields = ('id', 'name', 'base')



class BookingSiteSerializer(serializers.ModelSerializer):
    property = serializers.PrimaryKeyRelatedField(required=False, allow_null=True, pk_field=UUIDField(format='hex_verbose'), queryset=Property.objects.filter(enabled=True))
    
    class Meta:
        model = BookingSite
        fields = ('id', 'name', 'site', 'property')


class EntertainmentSerializer(serializers.ModelSerializer):
    pass

    class Meta:
        model = Entertainment
        fields = ('id', 'name')


class EssentialSerializer(serializers.ModelSerializer):
    pass

    class Meta:
        model = Essential
        fields = ('id', 'name')


class FamilySerializer(serializers.ModelSerializer):
    pass

    class Meta:
        model = Family
        fields = ('id', 'name')


class FeatureSerializer(serializers.ModelSerializer):
    pass

    class Meta:
        model = Feature
        fields = ('id', 'name')


class KitchenSerializer(serializers.ModelSerializer):
    pass

    class Meta:
        model = Kitchen
        fields = ('id', 'name')


class LaundrySerializer(serializers.ModelSerializer):
    pass

    class Meta:
        model = Laundry
        fields = ('id', 'name')


class OutsideSerializer(serializers.ModelSerializer):
    pass

    class Meta:
        model = Outside
        fields = ('id', 'name')


class ParkingSerializer(serializers.ModelSerializer):
    pass

    class Meta:
        model = Parking
        fields = ('id', 'name')


class PoolSpaSerializer(serializers.ModelSerializer):
    pass

    class Meta:
        model = PoolSpa
        fields = ('id', 'name')



class SleeperSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Sleeper
        fields = ('id', 'name', )


class RoomTypeSerializer(serializers.ModelSerializer):
    property = serializers.PrimaryKeyRelatedField(required=False, allow_null=True, pk_field=UUIDField(format='hex_verbose'), queryset=Property.objects.filter(enabled=True))
    
    class Meta:
        model = RoomType
        fields = ('id', 'name', 'sleepers', 'property')


class SafetySerializer(serializers.ModelSerializer):
    pass

    class Meta:
        model = Safety
        fields = ('id', 'name')


class SpaceSerializer(serializers.ModelSerializer):
    pass

    class Meta:
        model = Space
        fields = ('id', 'name')


class ServiceSerializer(serializers.ModelSerializer):
    pass

    class Meta:
        model = Service
        fields = ('id', 'name')


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
    address = AddressSerializer(many=False, read_only=False)
    booking_sites = BookingSiteSerializer(many=True, read_only=False)
    social_media = SocialMediaLinkSerializer(many=True, read_only=False)
    pictures = PropertyPhotoSerializer(many=True, read_only=True)
    room_types = RoomTypeSerializer(many=True, read_only=False)
    
    def create(self, validated_data):
        print('===========: ******** :============')
        print(validated_data)
        print('===========: ******** :============')
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

    class Meta:
        model = Property
        exclude = ()
        read_only_fields = ('id', 'ref', 'enabled', 'updated', 'updated_by')


class PropertyDetailSerializer(serializers.ModelSerializer):
    address = AddressDetailSerializer(many=False, read_only=True)
    booking_sites = BookingSiteSerializer(many=True, read_only=True)
    social_media = SocialMediaLinkSerializer(many=True, read_only=True)
    pictures = PropertyPhotoSerializer(many=True, read_only=True)
    room_types = RoomTypeSerializer(many=True, read_only=True)
    
    class Meta:
        model = Property
        exclude = ()
        read_only_fields = ('id', 'ref', 'enabled', 'updated', 'updated_by')
        
