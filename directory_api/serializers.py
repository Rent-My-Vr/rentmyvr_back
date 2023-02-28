from csv import field_size_limit
from dataclasses import fields
import logging

from django.conf import settings
from django.db import transaction
from django.contrib.auth import get_user_model
from pyparsing import empty
from rest_framework import serializers
from rest_framework.authtoken.models import Token

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


class BookingSiteSerializer(serializers.ModelSerializer):
    pass

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
    pass

    class Meta:
        model = SocialMediaLink
        fields = ('id', 'name', 'site', 'property')


class PropertySerializer(serializers.ModelSerializer):
    address = AddressSerializer(many=False, read_only=False)
    # booking_sites = BookingSiteSerializer(many=True, read_only=False)
    # social_media = SocialMediaLinkSerializer(many=True, read_only=False)
    
    def create(self, validated_data):
        print('===========: ******** :============')
        print(validated_data)
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
        # social_media = validated_data.pop('social_media')
        # booking_sites = validated_data.pop('booking_sites')

        with transaction.atomic():
            print('==== 1 ====')
            print(address_data)
            print('==== 2 ====')
            print(validated_data)
            address = Address.objects.create(**address_data)
            print('==== 3 ====')
            property = Property.objects.create(address=address, **validated_data)
            print('==== 4 ====')
            return property
        return None

    class Meta:
        model = Property
        exclude = ()
        read_only_fields = ('id', 'ref', 'enabled', 'updated', 'updated_by')



class PropertyPhotoSerializer(serializers.ModelSerializer):
    pass

    class Meta:
        model = PropertyPhoto
        fields = ('id', 'property', 'image')
