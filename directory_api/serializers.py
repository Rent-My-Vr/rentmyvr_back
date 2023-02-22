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
        fields = ('id', 'name', 'site')


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



class PropertySerializer(serializers.ModelSerializer):
    # tags = serializers.PrimaryKeyRelatedField(many=True, required=False, allow_null=True, pk_field=UUIDField(format='hex_verbose'), queryset=Tag.objects.filter(enabled=True, is_approved=True))
    # specifiers = serializers.PrimaryKeyRelatedField(many=True, required=False, allow_null=True, pk_field=UUIDField(format='hex_verbose'), queryset=Specifier.objects.filter(enabled=True, is_approved=True))
    
    
    class Meta:
        model = Property
        # depth = 1
        exclude = ()
        read_only_fields = ('id', 'ref', 'enabled', 'updated', 'updated_by')



class PropertyPhotoSerializer(serializers.ModelSerializer):
    pass

    class Meta:
        model = PropertyPhoto
        fields = ('id', 'type', 'property', 'image')


class SocialMediaLinkSerializer(serializers.ModelSerializer):
    pass

    class Meta:
        model = SocialMediaLink
        fields = ('id', 'name', 'site', 'property')
