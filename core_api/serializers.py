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

from auths_api.serializers import UserSerializer, UserSerializerClean, UserUpdateSerializer, UserNameSerializer
from core.models import *


log = logging.getLogger("{}.*".format(__package__))
log.setLevel(settings.LOGGING_LEVEL)
UserModel = get_user_model()


class AddressSerializer(serializers.ModelSerializer):
    # updated_by_id = serializers.SerializerMethodField()

    # def get_updated_by_id(self, obj):
    #     return obj.updated_by.id

    class Meta:
        model = Address
        depth = 1
        fields = ('id', 'street', 'number', 'city', 'zip_code', 'more_info')
        # read_only_fields = ('id', 'updated', 'updated_by')


class CompanySerializer(serializers.ModelSerializer):
    pass

    class Meta:
        model = Company
        # fields = ('email',)
        exclude = ('enabled', )


class InterestedEMailSerializer(serializers.ModelSerializer):
    pass

    class Meta:
        model = InterestedEMail
        fields = ('email',)


class ProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(many=False, read_only=False)
    address = AddressSerializer(many=False, read_only=True)
    # address = AddressSerializer(many=False, read_only=False, required=False)
    updated_by_id = serializers.SerializerMethodField()
    # worker_statuses = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    image_url = serializers.ImageField(required=False)

    def get_updated_by_id(self, obj):
        return obj.updated_by.id

    def create(self, validated_data):
        print('Ready to Create Profile***', validated_data)
        user_data = validated_data.pop('user')
        address_data = validated_data.pop('address') if validated_data.get('address', False) else None
        with transaction.atomic():
            user = UserModel.objects.create_user(**user_data)
            address = None
            if address_data:
                address = Address.objects.create(**address_data)
            profile = Profile.objects.create(user=user, address=address, **validated_data)
            return profile
        return None

    class Meta:
        model = Profile
        # depth = 0
        exclude = ('updated_by', )
        # extra_kwargs = {'updated_by': {'read_only': True}}
        read_only_fields = ('id', 'ref', 'enabled', 'updated', 'updated_by')


class ProfileDetailSerializer(serializers.ModelSerializer):
    user = UserSerializerClean(many=False, read_only=False)
    address = AddressSerializer(many=False, read_only=True)
    # address = AddressSerializer(many=False, read_only=False, required=False)
    updated_by_id = serializers.SerializerMethodField()
    # worker_statuses = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    image_url = serializers.ImageField(required=False)

    def get_updated_by_id(self, obj):
        return obj.updated_by.id

    class Meta:
        model = Profile
        # depth = 0
        exclude = ('updated_by', )
        # extra_kwargs = {'updated_by': {'read_only': True}}
        read_only_fields = ('id', 'ref', 'enabled', 'updated', 'updated_by')
