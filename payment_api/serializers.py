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
from payment.models import *


log = logging.getLogger("{}.*".format(__package__))
log.setLevel(settings.LOGGING_LEVEL)
UserModel = get_user_model()


class PriceChartSerializer(serializers.ModelSerializer):
    pass

    class Meta:
        model = PriceChart
        exclude = ('enabled', )


class SubscriptionSerializer(serializers.ModelSerializer):
    pass

    class Meta:
        model = Subscription
        exclude = ('enabled', )


class TransactionSerializer(serializers.ModelSerializer):
    pass

    class Meta:
        model = Transaction
        exclude = ('enabled', )

