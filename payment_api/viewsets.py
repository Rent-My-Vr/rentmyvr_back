import json
import logging
import stripe
from uuid import UUID
from inspect import Attribute
from xml import dom
from pprint import pprint
from django.conf import settings
from django.db import transaction
from django.shortcuts import render, redirect
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

from payment.models import *
from core.utils import send_gmail

from core.custom_permission import IsAuthenticatedOrCreate
from payment_api.serializers import *
from core_api.models import *


log = logging.getLogger(f"{__package__}.*")
log.setLevel(settings.LOGGING_LEVEL)
UserModel = get_user_model()


stripe.api_key = settings.STRIPE_SECRET_KEY



    

# User = settings.AUTH_USER_MODEL

# def get_image_filename(instance, filename):
#     name = instance.name
#     slug = slugify(name)
#     return f"products/{slug}-{filename}"

# class ProductTag(models.Model):
#     name = models.CharField(
#         max_length=100, help_text=_("Designates the name of the tag.")
#     )
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     def __str__(self) -> str:
#         return self.name

# class Product(models.Model):
#     name = models.CharField(max_length=200)
#     tags = models.ManyToManyField(ProductTag, blank=True)
#     desc = models.TextField(_("Description"), blank=True)
#     thumbnail = models.ImageField(upload_to=get_image_filename, blank=True)
#     url = models.URLField()
#     quantity = models.IntegerField(default=1)

#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     class Meta:
#         ordering = ("-created_at",)

#     def __str__(self):
#         return self.name

# class Price(models.Model):
#     product = models.ForeignKey(Product, on_delete=models.CASCADE)
#     price = models.DecimalField(decimal_places=2, max_digits=10)

#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     def __str__(self) -> str:
#         return f"{self.product.name} {self.price}"
    
    
    

class ProcessingView(viewsets.ViewSet):
    """
    Create a checkout session and redirect the user to Stripe's checkout page
    """
    # permission_classes = []
    permission_classes = (IsAuthenticated,)  
    authentication_classes = (TokenAuthentication,)

    def get(self, request, *args, **kwargs):
        print(args)
        print(kwargs)
        print(request.data)
        print(request.body)
        products = list(stripe.Product.search(query=f"active:'true' AND metadata['product-type']:'{type}'"))
        print(products)
        return Response(products, status=status.HTTP_201_CREATED)
        
    @action(methods=['get'], detail=False, url_path='prices/(?P<type>[\w\-]+)', url_name='prices')
    def prices(self, request, *args, **kwargs):
        print('prices+++++++++', kwargs)
        products = list(stripe.Product.search(query=f"active:'true' AND metadata['product-type']:'{kwargs['type']}'"))
        print(products)
        prices = []
        if len(products) > 0:
            prices = stripe.Price.list(active=True, currency='usd', product=products[0].id)
        print(prices)
        return Response(prices, status=status.HTTP_201_CREATED)
          
    @action(methods=['get'], detail=False, url_path='products/(?P<type>[\w\-]+)', url_name='products')
    def products(self, request, *args, **kwargs):
        print('products+++++++++', kwargs)
        print(args)
        print(kwargs)
        print(request.data)
        print(request.body)
        products = list(stripe.Product.search(query=f"active:'true' AND metadata['product-type']:'{kwargs['type']}'"))
        print(products)
        return Response(products, status=status.HTTP_201_CREATED)
        
    @action(methods=['post'], detail=False, url_path='checkout', url_name='checkout')
    def checkout(self, request, *args, **kwargs):
        print('Here...')
        data = request.data
        meta = data.get("metadata", dict)
        print(data)
        print("subscription" if data["price"]["type"] == "recurring" else "payment")
        
        txn = Transaction()
        txn.type = meta.get('item_type', None)
        txn.currency = data["price"]["currency"]
        txn.pdl = Property.objects.filter(id=meta.get('item_id', None)).first() if txn.type == Transaction.PDL else None
        txn.mdl = ManagerDirectory.objects.filter(id=meta.get('item_id', None)).first() if txn.type == Transaction.MDL else None
        txn.other = meta.get('item_id', None) if txn.type in [Transaction.SETUP, Transaction.OTHER] else None
        txn.quantity = int(data["quantity"])
        txn.unit_price = float(data["price"]["unit_amount"])
        txn.payee = request.user
        txn.updated_by = request.user
        txn.save()
        
        print('==========')
        print(f"{data['success_url']}?txn_id={txn.id}&item_id={data.get('item_id', None)}&type={txn.type}&next={meta.get('url', None)}")
        print(f"{data['cancel_url']}?txn_id={txn.id}&item_id={data.get('item_id', None)}&type={txn.type}&next={meta.get('url', None)}")
        checkout_session = stripe.checkout.Session.create(
            # success_url=f"http://localhost:3002/payments/success/?txn_id={txn.id}&item_id={data.get('item_id', None)}&type={txn.type}",
            # cancel_url=f"http://localhost:3002/payments/cancel/?txn_id={txn.id}&item_id={data.get('item_id', None)}&type={txn.type}",
            success_url=f"{data['success_url']}?txn_id={txn.id}&item_id={data.get('item_id', None)}&type={txn.type}&next={meta.get('url', None)}",
            cancel_url=f"{data['cancel_url']}?txn_id={txn.id}&item_id={data.get('item_id', None)}&type={txn.type}&next={meta.get('url', None)}",
            payment_method_types=["card"],
            line_items=[{"price": data["price"]["id"], "quantity": data.get("quantity", 1)}],
            metadata=data.get("metadata"),
            mode="subscription" if data["price"]["type"] == "recurring" else "payment"
        )
        
        print(checkout_session)
        txn.external_ref = checkout_session['id']
        txn.save()
        # return redirect(checkout_session.url)
        return Response({"url": checkout_session.url}, status=status.HTTP_201_CREATED)
               
        
        # checkout_session = stripe.checkout.Session.create(
        #     payment_method_types=["card"],
        #     line_items=[
        #         {
        #             "price_data": {
        #                 "currency": "usd",
        #                 "unit_amount": int(price.price) * 100,
        #                 "product_data": {
        #                     "name": price.product.name,
        #                     "description": price.product.desc,
        #                     "images": [f"{settings.BACKEND_DOMAIN}/{price.product.thumbnail}"],
        #                 },
        #             },
        #             "quantity": price.product.quantity,
        #         }
        #     ],
        #     metadata={"product_id": price.product.id},
        #     mode="payment",
        #     success_url=settings.PAYMENT_SUCCESS_URL,
        #     cancel_url=settings.PAYMENT_CANCEL_URL,
        # )
        # return redirect(checkout_session.url)
    
    

class PriceChartViewSet(viewsets.ModelViewSet, AchieveModelMixin):
    permission_classes = (IsAuthenticated, )
    authentication_classes = (TokenAuthentication,)
    parser_classes = (JSONParser, MultiPartParser)
    
    def get_queryset(self):
        """
        This view should return a list of all the Company for
        the user as determined by currently logged in user.
        """
        queryset = PriceChart.objects.filter(enabled=True)
        return queryset
 
    def get_serializer_class(self):
        if self.action in ['retrieve']:
            return PriceChartSerializer
        return PriceChartSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        address = self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)

    def update(self, request, *args, **kwargs):
        with transaction.atomic():
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            data = request.data
            serializer = self.get_serializer(instance, data=request.data, partial=partial)

            serializer.is_valid(raise_exception=True)
            address = serializer.save()
            
            self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        return Response(serializer.data, status=status.HTTP_201_CREATED)

