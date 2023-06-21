import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import serializers
from schedule.models.events import *


log = logging.getLogger("{}.*".format(__package__))
log.setLevel(settings.LOGGING_LEVEL)
UserModel = get_user_model()


class EventSerializer(serializers.ModelSerializer):

    class Meta:
        model = Event
        exclude = ('enabled', )


