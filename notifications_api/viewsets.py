from inspect import Attribute
from xml import dom
from django.conf import settings
from django.db import transaction
from django.shortcuts import render
from django.urls import reverse
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import viewsets, status, mixins
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser, FileUploadParser

from django.db.models import Q
from django.contrib.auth import get_user_model
from auths_api.serializers import UserSerializer, UserUpdateSerializer

from core.models import *
from core.utils import send_gmail
from core.custom_permission import IsAuthenticatedOrCreate
from .serializers import *
from .models import *
from notifications.models import Notification



class NotificationViewSet(viewsets.ViewSet):
    """
    A simple ViewSet for listing or retrieving users.
    """
    @action(detail=False, methods=['get'])
    def mine(self, request):
        queryset = request.user.notifications
        # data = queryset.active()
        return Response(NotificationSerializer(queryset.active(), many=True).data)

    @action(methods=['patch'], detail=True, url_path='mark/as/read', url_name='mark-as-read')
    def mark_as_read(self, request, *args, **kwargs):
        id = kwargs.get('pk', None)
        instance = get_object_or_404(Notification, pk=id)
        qs = Notification.objects.filter(pk=id)
        if request.user.user_profile.position == Profile.ADMIN:
            qs.mark_all_as_read()
            data = NotificationSerializer(request.user.notifications.active(), many=True).data
            return Response({'data': data, 'message': f'"{instance.verb}" notification for "{instance.recipient.first_name} {instance.recipient.last_name}" successful marked as Read'}, status=status.HTTP_200_OK)
        
        count = request.user.notifications.filter(pk=id).mark_all_as_read()
        
        data = NotificationSerializer(request.user.notifications.active(), many=True).data
        return Response({'data': data, 'message': f'"{instance.verb}" notification successful marked as Read'}, status=status.HTTP_200_OK)

    @action(methods=['patch'], detail=False, url_path='mark/all/as/read', url_name='mark-all-as-read')
    def mark_all_as_read(self, request):
        if request.user.user_profile.position == Profile.ADMIN:
            if request.query_params.get('all_users', None) == 'true':
                # if request.query.get('all_users', None) == 
                count = Notification.objects.mark_all_as_read()
                return Response({'message': f'All Notifications for All Users successful marked as Read (Count: {count})'}, status=status.HTTP_200_OK)
        
        count = request.user.notifications.mark_all_as_read()
        return Response({'message': f'All Notifications for "{request.user.first_name} {request.user.last_name}" successful marked as Read (Count: {count})'}, status=status.HTTP_200_OK)

    
    @action(methods=['patch'], detail=True, url_path='mark/as/unread', url_name='mark-as-unread')
    def mark_as_unread(self, request, *args, **kwargs):
        id = kwargs.get('pk', None)
        instance = get_object_or_404(Notification, pk=id)
        qs = Notification.objects.filter(pk=id)
        if request.user.user_profile.position == Profile.ADMIN:
            qs.mark_all_as_unread()
            data = NotificationSerializer(request.user.notifications.active(), many=True).data
            return Response({'data': data, 'message': f'"{instance.verb}" notification for "{instance.recipient.first_name} {instance.recipient.last_name}" successful marked as Unread'}, status=status.HTTP_200_OK)
        
        count = request.user.notifications.filter(pk=id).mark_all_as_unread()
        
        data = NotificationSerializer(request.user.notifications.active(), many=True).data
        return Response({'data': data, 'message': f'"{instance.verb}" notification successful marked as Unread'}, status=status.HTTP_200_OK)

    @action(methods=['patch'], detail=False, url_path='mark/all/as/unread', url_name='mark-all-as-unread')
    def mark_all_as_unread(self, request):
        if request.user.user_profile.position == Profile.ADMIN:
            if request.query_params.get('all_users', None) == 'true':
                # if request.query.get('all_users', None) == 
                count = Notification.objects.mark_all_as_unread()
                return Response({'message': f'All Notifications for All Users successful marked as Unread (Count: {count})'}, status=status.HTTP_200_OK)
        
        count = request.user.notifications.mark_all_as_unread()
        return Response({'message': f'All Notifications for "{request.user.first_name} {request.user.last_name}" successful marked as Unread (Count: {count})'}, status=status.HTTP_200_OK)

    