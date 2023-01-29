import json
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
from rest_framework import viewsets, status, mixins
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser, FileUploadParser

from django.db.models import Q, Prefetch
from datetime import datetime, timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model
from auths.utils import get_domain
from auths_api.serializers import UserSerializer, UserUpdateSerializer
from notifications.signals import notify

from core.models import *
from core.utils import send_gmail

from core.custom_permission import IsAuthenticatedOrCreate
from core_api.serializers import *
from core_api.models import *


log = logging.getLogger(f"{__package__}.*")
log.setLevel(settings.LOGGING_LEVEL)



class UUIDEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, UUID):
            return obj.hex
        return json.JSONEncoder.default(self, obj)


class InterestedEMailViewSet(viewsets.ModelViewSet, AchieveModelMixin):
    permission_classes = (AllowAny, )
    authentication_classes = (TokenAuthentication,)
    parser_classes = (JSONParser, )
        
    def get_serializer_class(self):
        if self.action in ['create', 'update']:
            return InterestedEMailSerializer
        return InterestedEMailSerializer

    def get_queryset(self):
        """
        This view should return a list of all the Interested EMail
        """
         
        return InterestedEMail.objects.filter(enabled=True)
 
    def perform_create(self, serializer):
        return serializer.save()
        
    def perform_update(self, serializer):
        return serializer.save()
      
    @action(methods=['get'], detail=False, url_path='names', url_name='names')
    def names(self, request, *args, **kwargs):
        return Response(self.get_queryset().values_list('email', flat=True), status=status.HTTP_200_OK)

