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
from django.core.serializers.json import DjangoJSONEncoder

from auths_api.serializers import UserSerializer
from core_api.serializers import *
from core.models import *


log = logging.getLogger("{}.*".format(__package__))
log.setLevel(settings.LOGGING_LEVEL)
UserModel = get_user_model()


class GenericNotificationRelatedField(serializers.RelatedField):

    def to_representation(self, value):
        if isinstance(value, InterestedEMail):
            serializer = InterestedEMailSerializer(value)
        # elif isinstance(value, Profile):
        #     serializer = ProfileSerializer(value)
        
        return serializer.data


class NotificationSerializer(serializers.Serializer):
    # recipient = UserSerializer(read_only=True)
    # # recipient = UserSerializer(UserModel, read_only=True)
    # target = GenericNotificationRelatedField(read_only=True)

    id = serializers.IntegerField(read_only=True)
    public = serializers.BooleanField(read_only=True)
    unread = serializers.BooleanField(read_only=True)
    emailed = serializers.BooleanField(read_only=True)
    deleted = serializers.BooleanField(read_only=True)
    level = serializers.CharField(read_only=True)
    verb = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True)
    timestamp = serializers.CharField(read_only=True)
    data = serializers.JSONField(read_only=True)

    # class Meta:
    #     fields = ('id', 'public', 'unread', 'emailed', 'deleted', 'level', 'verb', 'description', 'timestamp', 'data')