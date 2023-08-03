from csv import field_size_limit
from dataclasses import fields
import logging

from django.conf import settings
from django.db import transaction
from django.contrib.auth import get_user_model
from pyparsing import empty
from rest_framework import serializers
from rest_framework.authtoken.models import Token
from rest_framework_gis.serializers import GeoFeatureModelSerializer

from django.contrib.auth.models import Permission

from auths_api.serializers import UserSerializer, UserSerializerClean, UserUpdateSerializer
from core.models import *
from directory.models import Office, Portfolio


log = logging.getLogger("{}.*".format(__package__))
log.setLevel(settings.LOGGING_LEVEL)
UserModel = get_user_model()


class CountrySerializer(serializers.ModelSerializer):
    pass

    class Meta:
        model = Country
        exclude = ('enabled', )


class CountryLiteSerializer(serializers.ModelSerializer):
    pass

    class Meta:
        model = Country
        fields = ('id', 'name', 'iso2', 'iso3')


class StateSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = State
        exclude = ('enabled', )


class StateLiteSerializer(serializers.ModelSerializer):
    country = CountryLiteSerializer(many=False, read_only=True)
    
    class Meta:
        model = State
        fields = ('id', 'name', 'code', 'country')


class CitySerializer(serializers.ModelSerializer):
    
    class Meta:
        model = City
        exclude = ('enabled', )
        read_only_fields = ('id', 'created', 'import_id', 'imported', 'updated', 'updated_by')


class CityLiteSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = City
        fields = ('id', 'name', 'state_name', 'country_name')
        read_only_fields = ('id', 'created', 'import_id', 'imported', 'updated', 'updated_by')


# class AddressSerializer(serializers.ModelSerializer):
#     city = serializers.PrimaryKeyRelatedField(many=False, read_only=True)

#     class Meta:
#         model = Address
#         fields = ('id', 'street', 'number', 'city', 'zip_code', 'formatted', 'hidden', 'location', 'more_info')
#         read_only_fields = ('id', 'created', 'import_id', 'imported', 'updated', 'updated_by')


# class AddressCreateSerializer(serializers.ModelSerializer):
#     city = CitySerializer(many=False, read_only=True)

#     class Meta:
#         model = Address
#         fields = ('id', 'street', 'number', 'city', 'zip_code', 'formatted', 'hidden', 'location',  'more_info')
#         read_only_fields = ('id', 'created', 'import_id', 'imported', 'updated', 'updated_by')


# class AddressDetailSerializer(serializers.ModelSerializer):
#     city = CitySerializer(many=False, read_only=False)

#     class Meta:
#         model = Address
#         fields = ('id', 'street', 'number', 'city', 'zip_code', 'formatted', 'hidden', 'location',  'more_info')
#         read_only_fields = ('id', 'created', 'import_id', 'imported', 'updated', 'updated_by')


# class AddressGeoSerializer(GeoFeatureModelSerializer):
#     # updated_by_id = serializers.SerializerMethodField()
#     # city = serializers.PrimaryKeyRelatedField(many=False, read_only=True)
#     city = serializers.PrimaryKeyRelatedField(many=False, read_only=True)

#     # def get_updated_by_id(self, obj):
#     #     return obj.updated_by.id

#     class Meta:
#         model = Address
#         geo_field = "location"
#         fields = ('id', 'street', 'number', 'city', 'zip_code', 'formatted', 'hidden', 'location', 'more_info')
#         read_only_fields = ('id', 'created', 'import_id', 'imported', 'updated', 'updated_by')


# class AddressGeoSmallSerializer(GeoFeatureModelSerializer):
#     class Meta:
#         model = Address
#         geo_field = "location"
#         fields = ('id', 'formatted', 'location')
#         read_only_fields = ('id', 'created', 'import_id', 'imported', 'updated', 'updated_by')


# class AddressCreateGeoSerializer(GeoFeatureModelSerializer):
#     # updated_by_id = serializers.SerializerMethodField()
#     # city = serializers.PrimaryKeyRelatedField(many=False, read_only=True)
#     # city_data = CitySerializer(many=False, read_only=True)
#     city = CitySerializer(many=False, read_only=True)

#     # def get_updated_by_id(self, obj):
#     #     return obj.updated_by.id

#     class Meta:
#         model = Address
#         geo_field = "location"
#         # fields = ('id', 'street', 'number', 'city', 'city_data', 'zip_code', 'formatted', 'hidden', 'location',  'more_info')
#         fields = ('id', 'street', 'number', 'city', 'zip_code', 'formatted', 'hidden', 'location',  'more_info')
#         read_only_fields = ('id', 'created', 'import_id', 'imported', 'updated', 'updated_by')


# class AddressDetailGeoSerializer(GeoFeatureModelSerializer):
#     city = CitySerializer(many=False, read_only=False)

#     class Meta:
#         model = Address
#         geo_field = "location"
#         fields = ('id', 'street', 'number', 'city', 'zip_code', 'formatted', 'hidden', 'location',  'more_info')
#         read_only_fields = ('id', 'created', 'import_id', 'imported', 'updated', 'updated_by')


class CompanySerializer(serializers.ModelSerializer):
    pass
    
    class Meta:
        model = Company
        # fields = ('email',)
        exclude = ('enabled', 'updated_by')
        read_only_fields = ('enabled', 'ref', 'updated_by')


class CompanyMinSerializer(serializers.ModelSerializer):
    city = CitySerializer(many=False, read_only=True)
    country = CountryLiteSerializer(many=False, read_only=True)
    
    class Meta:
        model = Company
        # fields = ('email',)
        exclude = ('enabled', 'updated_by')
        read_only_fields = ('enabled', 'ref', 'updated_by')


class ContactSerializer(serializers.ModelSerializer):

    class Meta:
        model = Contact
        exclude = ('enabled', )
        read_only_fields = ('id', 'enabled', 'ref')


class InvitationSerializer(serializers.ModelSerializer):
    # client_callback_link = serializers.SerializerMethodField()
    
    # def get_client_callback_link(self, obj):
    #     print('*************')
    #     print(self)
    #     print(obj)
    #     return obj.email

    class Meta:
        model = Invitation
        exclude = ('enabled', 'token')
        read_only_fields = ('id', 'enabled', 'updated_by', 'sender', 'company', 'status', 'sent')


class ProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(many=False, read_only=False)
    city = CitySerializer(many=False, read_only=True)
    offices = serializers.PrimaryKeyRelatedField(many=True, read_only=False, required=False, queryset=Office.objects.filter(enabled=True))
    portfolios = serializers.PrimaryKeyRelatedField(many=True, read_only=False, required=False, queryset=Portfolio.objects.filter(enabled=True))
    company_id = serializers.PrimaryKeyRelatedField(many=False, read_only=True, required=False)
    updated_by_id = serializers.SerializerMethodField()
    # worker_statuses = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    # image_url = serializers.ImageField(required=False)

    def get_updated_by_id(self, obj):
        return obj.updated_by.id

    def create(self, validated_data):
        print('Ready to Create Profile***', validated_data)
        user_data = validated_data.pop('user')
        with transaction.atomic():
            user = UserModel.objects.create_user(**user_data)
            # print(" +++++ *** 1 *** +++++ ")
            # print(user.id)
            # print(validated_data)
            # print(" +++++ *** 2 *** +++++ ")
            profile = Profile.objects.create(user=user, updated_by_id=user.id, company=validated_data.get('company', None)) #, **validated_data)
            # print(" +++++ *** 3 *** +++++ ")
            return profile
        return None

    class Meta:
        model = Profile
        # depth = 0
        exclude = ('updated_by', )
        # extra_kwargs = {'updated_by': {'read_only': True}}
        read_only_fields = ('id', 'ref', 'enabled', 'updated', 'updated_by')


class ProfileImageSerializer(serializers.ModelSerializer):
    # image = serializers.ImageField(required=True)

    class Meta:
        model = Profile
        fields = ['image']
        # extra_kwargs = {'image': {'write_only': True}}


class ProfileUpdateSerializer(ProfileSerializer):
    user = UserUpdateSerializer(many=False, read_only=True)
    # address = AddressSerializer(many=False, read_only=True)


class InvitationListSerializer(serializers.ModelSerializer):
    sender = ProfileSerializer(many=False, read_only=False)
    company = CompanySerializer(many=False, read_only=True)
    # client_callback_link = serializers.SerializerMethodField()
    # emails = serializers.ListField(child = serializers.EmailField(read_only=True))
    
    # def get_client_callback_link(self, obj):
    #     print('*************')
    #     print(self)
    #     print(obj)
    #     return obj.email

    class Meta:
        model = Invitation
        exclude = ('enabled', 'token')
        read_only_fields = ('id', 'enabled',  'updated_by', 'sender', 'company', 'status', 'sent', 'email')


class CompanyMineSerializer(serializers.ModelSerializer):
    from directory_api.serializers import ManagerDirectoryListSerializer, OfficeSerializer, PortfolioSerializer
    administrator = ProfileSerializer(many=False, read_only=True)
    members = ProfileSerializer(many=True, read_only=True)
    mdl = ManagerDirectoryListSerializer(many=False, read_only=True)
    offices = OfficeSerializer(many=True, read_only=True)
    portfolios = PortfolioSerializer(many=True, read_only=True)

    class Meta:
        model = Company
        # fields = ('email',)
        exclude = ('enabled', )


class ProfileMoreSerializer(serializers.ModelSerializer):
    from directory_api.serializers import OfficeSerializer, PortfolioSerializer
    user = UserSerializer(many=False, read_only=False)
    city = CitySerializer(many=False, read_only=True)
    # address = AddressSerializer(many=False, read_only=True)
    portfolios = PortfolioSerializer(many=True, read_only=True)
    offices = OfficeSerializer(many=True, read_only=True)

    class Meta:
        model = Profile
        # depth = 0
        exclude = ('updated_by', )
        # extra_kwargs = {'updated_by': {'read_only': True}}
        read_only_fields = ('id', 'ref', 'enabled', 'updated', 'updated_by')


class CompanyMDLDetailSerializer(serializers.ModelSerializer):
    from directory_api.serializers import ManagerDirectoryListSerializer, OfficeDetailSerializer, PortfolioDetailSerializer
    administrator = ProfileSerializer(many=False, read_only=True)
    members = ProfileMoreSerializer(many=True, read_only=True)
    city = CitySerializer(many=False, read_only=True)
    mdl = ManagerDirectoryListSerializer(many=False, read_only=True)
    invitations = InvitationListSerializer(many=True, read_only=True)
    offices = OfficeDetailSerializer(many=True, read_only=True)
    portfolios = PortfolioDetailSerializer(many=True, read_only=True)
    
    # administrator = ProfileSerializer(many=False, read_only=True)
    # members = ProfileSerializer(many=True, read_only=True)
    # mdl = ManagerDirectorySerializer(many=False, read_only=True)
    # offices = OfficeSerializer(many=True, read_only=True)
    # portfolios = PortfolioSerializer(many=True, read_only=True)

    class Meta:
        model = Company
        # fields = ('email',)
        exclude = ('enabled', )

class ContactSerializer(serializers.ModelSerializer):
    # company = CompanySerializer(many=False, read_only=True)

    class Meta:
        model = Contact
        exclude = ('enabled', )
        read_only_fields = ('id', 'ref', 'enabled',  'updated_by', )


class ProfileDetailSerializer(serializers.ModelSerializer):
    from directory_api.serializers import OfficeSerializer, PortfolioSerializer, PropertySerializer
    user = UserSerializerClean(many=False, read_only=False)
    city = CitySerializer(many=False, read_only=True)
    # address = AddressDetailSerializer(many=False, read_only=True)
    company = CompanySerializer(many=False, read_only=True)
    # company_admins = ProfileSerializer(many=True, read_only=True)
    offices = OfficeSerializer(many=True, read_only=True)
    administrative_offices = OfficeSerializer(many=True, read_only=True)
    portfolios = PortfolioSerializer(many=True, read_only=True)
    administrative_portfolios = PortfolioSerializer(many=True, read_only=True)
    administrative_properties = PropertySerializer(many=True, read_only=True)
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
