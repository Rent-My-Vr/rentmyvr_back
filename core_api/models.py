from django.db import models
from rest_framework.response import Response
from rest_framework.decorators import action


class AchieveModelMixin:
    """
    Achieve a queryset.
    """

    @action(methods=['patch', 'post'], detail=True, url_path='achieve', url_name='achieve')
    def achieve(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.enabled = False
        instance.save()
        
        return Response({'message': 'Achieved successfully'})