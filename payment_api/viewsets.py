import json
import logging
import stripe
import collections
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
from directory.models import * 


log = logging.getLogger(f"{__package__}.*")
log.setLevel(settings.LOGGING_LEVEL)
UserModel = get_user_model()


stripe.api_key = settings.STRIPE_SECRET_KEY
endpoint_secret = settings.STRIPE_ENDPOINT_SECRET


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
    parser_classes = (MultiPartParser, JSONParser)

    def get_permissions(self):
        if self.action in ['callback']:
            return []  # This method should return iterable of permissions
        return super().get_permissions()

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
        with transaction.atomic():
            print('Here.....1...')
            print(request.headers['Content-Type'])
            data = request.data
            
            print('Here.....2...')
            print(data)
            print(3)
            print(1)
            
            data = request.data
            meta = data.get("metadata", list)
            print(2)
            print(data)
            print("subscription" if data["price"]["type"] == "recurring" else "payment")
            
            profile = request.user.user_profile
            txn = Transaction()
            txn.type = meta.get('item_type', None)
            txn.currency = data["price"]["currency"]
            txn.items = meta.get('item_ids', [])
            # txn.pdl = Property.objects.filter(id=meta.get('item_ids', None)).first() if txn.type == Transaction.PDL else None
            # txn.mdl = ManagerDirectory.objects.filter(id=meta.get('item_ids', None)).first() if txn.type == Transaction.MDL else None
            # txn.other = meta.get('item_ids', None) if txn.type in [Transaction.SETUP, Transaction.OTHER] else None
            txn.quantity = int(data["quantity"])
            txn.unit_price = float(data["price"]["unit_amount"])
            txn.payee = profile
            txn.updated_by = request.user
            txn.save()
            
            print('==========')
            print(f"{data['success_url']}?txn_id={txn.id}&item_ids={meta.get('item_ids', [])}&type={txn.type}&next={meta.get('url', None)}")
            print(f"{data['cancel_url']}?txn_id={txn.id}&item_ids={meta.get('item_ids', [])}&type={txn.type}&next={meta.get('url', None)}")
            
            try:
                customer_id = profile.payment.external_ref
            except Profile.payment.RelatedObjectDoesNotExist:
                print('......,,,,')
                customer_id = None

            print({"enabled": txn.type != Transaction.MDL, "minimum": 1, "maximum": 100})
            print(data.get("metadata"))
            meta['item_ids'] = ','.join(meta.get('item_ids', None))
            checkout_session = stripe.checkout.Session.create(
                client_reference_id=txn.id,
                customer_creation="always" if data["price"]["type"] == "one_time" else None,
                subscription=None, # The ID of the subscription for Checkout Sessions in subscription mode.
                customer_email=request.user.email if customer_id is None else None,
                customer=customer_id if customer_id else None,
                allow_promotion_codes=True,
                discounts=[],
                mode="subscription" if data["price"]["type"] == "recurring" else "payment",
                metadata=meta,
                # payment_method_types=["card"],    # Manage from Dashboard
                # invoice_creation={"enabled": True, "invoice_data": {}},
                line_items=[{
                    "price": data["price"]["id"], 
                    "quantity": data.get("quantity", 1), 
                    "adjustable_quantity": None if txn.type == Transaction.MDL else {"enabled": True, "minimum": 1, "maximum": 100}
                }],
                success_url=f"{data['success_url']}?txn_id={txn.id}&item_ids={data.get('metadata', {}).get('item_ids', [])}&type={txn.type}&next={meta.get('url', None)}",
                cancel_url=f"{data['cancel_url']}?txn_id={txn.id}&item_ids={data.get('metadata', {}).get('item_ids', [])}&type={txn.type}&next={meta.get('url', None)}",
            )
            
            print('\n\n+++++++++++++++++++++++++++++++')
            print(checkout_session)
            txn.external_ref = checkout_session['id']
            txn.external_obj = Transaction.CHECKOUT
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
       
    @action(methods=['post', 'get'], detail=False, url_path='callback', url_name='callback')
    def callback(self, request, *args, **kwargs):
        print('\n\nHere........')
        # payload = request.data
        payload = request.body
        # print(payload)
        
        event = None
        sig_header = request.headers['STRIPE_SIGNATURE']

        try:
            event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
        except ValueError as e:
            print('Invalid payload... ', e)
            return Response(None, status=status.HTTP_400_BAD_REQUEST) 
        except stripe.error.SignatureVerificationError as e:
            print('Invalid signature... ', e)
            return Response(None, status=status.HTTP_400_BAD_REQUEST) 

        print('\n\n\n\nEvent ====>>>> \n\n', event['type'])
        
        if event:
            # if event.get('type', None) == 'charge.captured':
            #     # Occurs whenever a previously uncaptured charge is captured.
            #     charge = event['data']['object']
            #     print('\nDone with charge *******\n', charge)
            if event.get('type', None) == 'charge.dispute.closed':
                # Occurs when a dispute is closed and the dispute status changes to lost, warning_closed, or won.
                charge = event['data']['object']
                print('\nDone with charge *******\n', charge)
            elif event.get('type', None) == 'charge.dispute.created':
                # Occurs whenever a customer disputes a charge with their bank.
                charge = event['data']['object']
                print('\nDone with charge *******\n', charge)
            elif event.get('type', None) == 'charge.dispute.funds_reinstated':
                # Occurs when funds are reinstated to your account after a dispute is closed. This includes partially refunded payments.
                charge = event['data']['object']
                print('\nDone with charge *******\n', charge)
            elif event.get('type', None) == 'charge.dispute.funds_withdrawn':
                # Occurs when funds are removed from your account due to a dispute.
                charge = event['data']['object']
                print('\nDone with charge *******\n', charge)
            elif event.get('type', None) == 'charge.dispute.updated':
                # Occurs when the dispute is updated (usually with evidence).
                charge = event['data']['object']
                print('\nDone with charge *******\n', charge)
            elif event.get('type', None) == 'charge.expired':
                # Occurs whenever an uncaptured charge expires. 
                charge = event['data']['object']
                print('\nDone with charge *******\n', charge)
            elif event.get('type', None) == 'charge.failed':
                # Occurs whenever a failed charge attempt occurs.
                charge = event['data']['object']
                print('\nDone with charge *******\n', charge)
            elif event.get('type', None) == 'charge.pending':
                # Occurs whenever a pending charge is created.
                charge = event['data']['object']
                print('\nDone with charge *******\n', charge)
            elif event.get('type', None) == 'charge.refund.updated':
                # Occurs whenever a refund is updated, on selected payment methods.
                charge = event['data']['object']
                print('\nDone with charge *******\n', charge)
            elif event.get('type', None) == 'charge.refunded':
                # Occurs whenever a charge is refunded, including partial refunds.
                charge = event['data']['object']
                print('\nDone with charge *******\n', charge)
            # elif event.get('type', None) == 'charge.succeeded':
            #     # Occurs whenever a charge is successful.
            #     charge = event['data']['object']
            #     # TODO: not sure I need this
            #     print('\nDone with charge *******\n', charge)
            elif event.get('type', None) == 'charge.updated':
                # Occurs whenever a charge description or metadata is updated, or upon an asynchronous capture.
                charge = event['data']['object']
                print('\nDone with charge *******\n', charge)
            elif event.get('type', None) == 'checkout.session.async_payment_failed':
                # Occurs when a payment intent using a delayed payment method fails.
                checkoutSession = event['data']['object']
                print('\nDone with checkout *******\n', checkoutSession)
            elif event.get('type', None) == 'checkout.session.async_payment_succeeded':
                # Occurs when a payment intent using a delayed payment method finally succeeds.
                checkoutSession = event['data']['object']
                print('\nDone with checkout *******\n', checkoutSession)
            elif event.get('type', None) == 'checkout.session.completed':
                # Occurs when a Checkout Session has been successfully completed.
                checkoutSession = event['data']['object']
                if checkoutSession['mode'] == 'subscription':
                    txn = Transaction.objects.get(external_ref=checkoutSession['id'], channel=PaymentProfile.STRIPE)
                    txn.status = Transaction.COMPLETED
                    txn.invoice_id = checkoutSession['invoice']
                    if txn.ext_subscription_ref is None:
                        txn.ext_subscription_ref = checkoutSession['subscription']
                    txn.save()
                    
                    print('=======>>>> ', TransactionSerializer(txn).data)
                    
                    # This will show list of items that were finally paid for
                    # https://stripe.com/docs/payments/checkout/adjustable-quantity
                    # line_items = stripe.checkout.Session.list_line_items(session['id'], limit=100)
                    
                    subscription_id = checkoutSession['subscription']
                    if subscription_id:
                        subscrips = Subscription.objects.filter(external_ref=subscription_id, transaction__channel=PaymentProfile.STRIPE)
                        if len(subscrips) == 0:
                            # TODO: Schedule to create Subscription in 5mins if 
                            print('------ Create Subscription: ',  subscription_id)
                            subscription = stripe.Subscription.retrieve(subscription_id)
                            
                            items = Subscription.objects.filter(external_ref=subscription_id, transaction=txn, item__in=txn.items, type=txn.type, transaction__channel=PaymentProfile.STRIPE).values_list('item', flat=True)
                            print(items, ' ===1=== ', txn.items)
                            for it in txn.items:
                                if it not in items:
                                    subscrip = Subscription()
                                    subscrip.external_ref=subscription_id
                                    subscrip.external_obj = "subscription"
                                    subscrip.start_date = datetime.fromtimestamp(subscription['current_period_start'])
                                    subscrip.end_date = datetime.fromtimestamp(subscription['current_period_end'])
                                    subscrip.transaction = txn
                                    subscrip.status = subscription['status']
                                    subscrip.item = it
                                    subscrip.type = txn.type
                                    # subscrip.pdl = txn.pdl
                                    # subscrip.mdl = txn.mdl
                                    # subscrip.other = txn.other
                                    subscrip.subscriber = txn.payee
                                    subscrip.save()
                                    if txn.type == Transaction.MDL:
                                        ManagerDirectory.objects.filter(id=it).update(subscription=subscrip)
                                    elif txn.type == Transaction.PDL:
                                        Property.objects.filter(id=it).update(subscription=subscrip)
                                    else:
                                        print('..... ', txn.type)
                print('\nDone with checkout *******\n', checkoutSession)
            elif event.get('type', None) == 'checkout.session.expired':
                # Occurs when a Checkout Session is expired.
                checkoutSession = event['data']['object']
                if checkoutSession['mode'] == 'subscription':
                    txn = Transaction.objects.get(external_ref=checkoutSession['id'])
                    txn.status = Transaction.EXPIRED
                    txn.subscriptions.all().update(status=Subscription.INCOMPLETE_EXPIRED)
                    # for s in txn.subscriptions.all():
                    #     s.status=Subscription.INCOMPLETE_EXPIRED
                    #     s.save()
                    txn.save()
                print('\nDone with subscriptions*******\n', checkoutSession)
            elif event.get('type', None) == 'customer.created':
                # Occurs whenever a new customer is created.
                customer = event['data']['object']
                profile = Profile.objects.get(user__email=customer['email'])
                (paymentProfile, created) = PaymentProfile.objects.get_or_create(external_ref=customer['id'], profile=profile, defaults={"external_obj": 'customer', "profile": profile}) 
                print(created, '  ', paymentProfile)
                meta = {"profile_ref": profile.ref}
                desc = f"{profile.ref} - Private member"
                pref = profile.ref
                if profile.company:
                    meta["company_ref"] = profile.company.ref
                    desc = f"{profile.company.ref}-{profile.ref} {profile.company.name} member"
                    pref = profile.company.ref
                stripe.Customer.modify(customer['id'], invoice_prefix=pref, metadata=meta, description=desc)
                print('\nDone with customer: *******\n', customer)
            elif event.get('type', None) == 'customer.deleted':
                # Occurs whenever a customer is deleted.
                customer = event['data']['object']
                PaymentProfile.objects.filter(external_ref=customer['id'], channel=PaymentProfile.STRIPE).delete()
                print('\nDone with customer: *******\n', customer)
            elif event.get('type', None) == 'customer.discount.created':
                # Occurs whenever a coupon is attached to a customer.
                customer = event['data']['object']
                print('\nDone with customer: *******\n', customer)
            elif event.get('type', None) == 'customer.discount.deleted':
                # Occurs whenever a coupon is removed from a customer.
                customer = event['data']['object']
                print('\nDone with customer: *******\n', customer)
            elif event.get('type', None) == 'customer.discount.updated':
                # Occurs whenever a customer is switched from one coupon to another..
                customer = event['data']['object']
                print('\nDone with customer: *******\n', customer)
            elif event.get('type', None) == 'customer.source.expiring':
                # Occurs whenever a card or source will expire at the end of the month.
                customer = event['data']['object']
                print('\nDone with customer: *******\n', customer)
            elif event.get('type', None) == 'customer.subscription.created':
                # Occurs whenever a customer is signed up for a new plan
                # incomplete, incomplete_expired, trialing, active, past_due, canceled, or unpaid, paused
                subscription = event['data']['object']
                print('subscription_id: ', subscription['id'])
                txn = Transaction.objects.filter(ext_subscription_ref=subscription['id'], channel=PaymentProfile.STRIPE).first()
                
                if txn:
                    items = Subscription.objects.filter(external_ref=subscription['id'], transaction=txn, item__in=txn.items, type=txn.type, transaction__channel=PaymentProfile.STRIPE).values_list('item', flat=True)
                    print(items, ' ===1=== ', txn.items if txn else None)
                    for it in txn.items:
                        if it not in items:
                            subscrip = Subscription()
                            subscrip.external_ref=subscription['id']
                            subscrip.external_obj = subscription
                            subscrip.start_date = datetime.fromtimestamp(subscription['current_period_start'])
                            subscrip.end_date = datetime.fromtimestamp(subscription['current_period_end'])
                            subscrip.transaction = txn
                            subscrip.status = subscription['status']
                            subscrip.type = txn.type
                            subscrip.item = it
                            # subscrip.pdl = txn.pdl
                            # subscrip.mdl = txn.mdl
                            # subscrip.other = txn.other
                            subscrip.subscriber = txn.payee
                            subscrip.save()
                            if txn.type == Transaction.MDL:
                                ManagerDirectory.objects.filter(id=it).update(subscription=subscrip)
                            elif txn.type == Transaction.PDL:
                                Property.objects.filter(id=it).update(subscription=subscrip)
                            else:
                                print('..... ', txn.type)
                else:
                    print(subscription['id'], ' === ', PaymentProfile.STRIPE, ' ********** TXN NOT FOUND ****** ', txn)
                print('\nDone with subscription: *******\n', subscription)
            # elif event.get('type', None) == 'customer.subscription.deleted':
            #     # Occurs whenever a customer’s subscription ends.
            #     subscription = event['data']['object']
            #     Subscription.objects.filter(external_ref=subscription['id'], transaction__channel=PaymentProfile.STRIPE).update(status=subscription['status'])
            # elif event.get('type', None) == 'customer.subscription.paused':
            #     # Occurs whenever a customer’s subscription is paused. Only applies when 
            #     # subscriptions enter status=paused, not when payment collection is paused.
            #     subscription = event['data']['object']
            #     Subscription.objects.filter(external_ref=subscription['id'], transaction__channel=PaymentProfile.STRIPE).update(status=subscription['status'])
            # elif event.get('type', None) == 'customer.subscription.resumed':
            #     # Occurs whenever a customer’s subscription is no longer paused. Only applies when
            #     # a status=paused subscription is resumed, not when payment collection is resumed.
            #     subscription = event['data']['object']
            #     Subscription.objects.filter(external_ref=subscription['id'], transaction__channel=PaymentProfile.STRIPE).update(status=subscription['status'])
            elif event.get('type', None) == 'customer.subscription.trial_will_end':
                # Occurs three days before a subscription’s trial period is scheduled to end, 
                # or when a trial is ended immediately (using trial_end=now).
                customer = event['data']['object']
                print('\nDone with subscription: *******\n', subscription)
            elif event.get('type', None) == 'customer.subscription.updated':
                # Occurs whenever a subscription changes (e.g., switching from one 
                # plan to another, or changing the status from trial to active).
                # Occurs when a Checkout Session is expired.
                subscription = event['data']['object']
                subscrips = Subscription.objects.filter(external_ref=subscription['id'], transaction__channel=PaymentProfile.STRIPE)
                subscrips.update(status=subscription['status'])
                print('subscrips: ', subscrips)
                st = subscription['status']
                if len(subscrips) > 0:
                    ty = subscrips[0].type
                    s = subscrips[0]
                    if st == Subscription.ACTIVE and s.transaction.invoice_status == Transaction.PAID:
                        if ty == Transaction.MDL:
                            mdl = ManagerDirectory.objects.filter(subscription__in=subscrips).update(is_active=True)
                            print('MDL Updated: ', mdl)
                        elif ty == Transaction.PDL:
                            pdl = Property.objects.filter(subscription__in=subscrips).update(is_active=True)
                            print('PDL Updated: ', pdl)
                        else:
                            print(3)
                print('\nDone with subscription: *******\n', subscription)
            # elif event.get('type', None) == 'customer.updated':
            #     # Occurs whenever any property of a customer changes.
            #     customer = event['data']['object']
            #     pp = PaymentProfile.objects.filter(external_ref=customer['id'], channel=PaymentProfile.STRIPE)
            #     if len(pp) > 0:
            #         pp.update(external_obj=customer)
            elif event.get('type', None) == 'invoice.created':
                # https://stripe.com/docs/billing/subscriptions/webhooks
                invoice = event['data']['object']
                txn = Transaction.objects.filter(ext_subscription_ref=invoice['subscription'], channel=PaymentProfile.STRIPE).first()
                
                print('Updating... ', txn)
                if txn is not None and txn.invoice_url is None:
                    print('Updating... Transaction')
                    txn.invoice_url = invoice['hosted_invoice_url']
                    txn.invoice_status = invoice['status']
                    txn.save()
                if invoice['auto_advance'] == False and invoice['status'] == "draft":
                    print('Updating... Invoice')
                    res = stripe.Invoice.modify(invoice['id'], auto_advance=True)
                    print('Res: ', res)
                print('\nDone with invoice: *******\n', invoice)
            elif event.get('type', None) == 'invoice.deleted':
                # Occurs whenever any property of a customer changes.
                invoice = event['data']['object']
                Transaction.objects.filter(invoice_id=invoice['id'], channel=PaymentProfile.STRIPE).update(invoice_id=None, invoice_status=invoice['status'])
                print('\nDone with invoice: *******\n', invoice)
            elif event.get('type', None) == 'invoice.finalization_failed':
                # https://stripe.com/docs/billing/subscriptions/webhooks
                invoice = event['data']['object']
                Transaction.objects.filter(invoice_id=invoice['id'], channel=PaymentProfile.STRIPE).update(invoice_url=invoice['hosted_invoice_url'], invoice_pdf=invoice['invoice_pdf'], invoice_status=invoice['status'])
                print('\nDone with invoice: *******\n', invoice)
            elif event.get('type', None) == 'invoice.finalized':
                # Occurs whenever any property of a customer changes.
                invoice = event['data']['object']
                txn = Transaction.objects.filter(ext_subscription_ref=invoice['subscription'], channel=PaymentProfile.STRIPE).first()
                if txn is not None and txn.invoice_url is None:
                    txn.invoice_url = invoice['hosted_invoice_url']
                    txn.invoice_pdf = invoice['invoice_pdf']
                    txn.invoice_status = invoice['status']
                    txn.save()
                print('\nDone with invoice: *******\n', invoice)
            elif event.get('type', None) == 'invoice.updated':
                # Sent when a payment succeeds or fails. If payment is successful the paid attribute is set to true 
                # and the status is paid. If payment fails, paid is set to false and the status remains open. 
                # Payment failures also trigger a invoice.payment_failed event.
                invoice = event['data']['object']
                if invoice['status'] == 'paid' and invoice['paid'] == True: # Paid 
                    print('Invoice Paid....', invoice['id'])
                    subscription_id = invoice['subscription']
                    subscrips = Subscription.objects.filter(external_ref=subscription_id, transaction__channel=PaymentProfile.STRIPE)
                    print(subscription_id, ' ****subscrips: ', len(subscrips))
                    
                    txn = Transaction.objects.filter(Q(Q(invoice_id=invoice['id']) | Q(ext_subscription_ref=subscription_id)), channel=PaymentProfile.STRIPE).first()
                    print(' TXN: ', txn)
                    if txn:
                        txn.invoice_url = invoice['hosted_invoice_url']
                        txn.invoice_pdf = invoice['invoice_pdf']
                        txn.invoice_status = invoice['status']
                        txn.save()
                    else:
                        return Response({"message": "Something is inconsistent"}, status=status.HTTP_400_BAD_REQUEST) 
                    if txn is not None and len(subscrips) == 0:
                        print('.....')
                        for it in txn.items:
                            subscription = stripe.Subscription.retrieve(subscription_id)
                            subscrip = Subscription()
                            subscrip.external_ref = subscription_id
                            subscrip.external_obj = "subscription"
                            subscrip.start_date = datetime.fromtimestamp(subscription['current_period_start'])
                            subscrip.end_date = datetime.fromtimestamp(subscription['current_period_end'])
                            subscrip.transaction = txn
                            subscrip.status = subscription['status']
                            subscrip.type = txn.type
                            subscrip.item = it
                            # subscrip.pdl = txn.pdl
                            # subscrip.mdl = txn.mdl
                            # subscrip.other = txn.other
                            subscrip.subscriber = txn.payee
                            subscrip.save()
                            if txn.type == Transaction.MDL:
                                if subscription['status'] == Subscription.ACTIVE:
                                    ManagerDirectory.objects.filter(id=it).update(subscription=subscrip, is_active=True)
                                else:
                                    ManagerDirectory.objects.filter(id=it).update(subscription=subscrip)
                            elif txn.type == Transaction.PDL:
                                if subscription['status'] == Subscription.ACTIVE:
                                    Property.objects.filter(id=it).update(subscription=subscrip, is_active=True)
                                else:
                                    Property.objects.filter(id=it).update(subscription=subscrip)
                            else:
                                print('..... ', txn.type)
                    if len(subscrips) > 0:
                        print('++++ ', subscrips[0].status)
                        if subscrips[0].status == Subscription.ACTIVE:
                            if txn.type == Transaction.MDL:
                                ManagerDirectory.objects.filter(subscription__in=subscrips).update(is_active=True)
                            elif txn.type == Transaction.PDL:
                                Property.objects.filter(subscription__in=subscrips).update(is_active=True)
                            else:
                                # TODO: Not sure yet
                                print(3)
                    # Transaction.objects.filter(invoice_id=invoice['id'], channel=PaymentProfile.STRIPE).update(invoice_url=invoice['hosted_invoice_url'], invoice_pdf=invoice['invoice_pdf'])
                elif invoice['status'] == 'open' and invoice['paid'] == False: # Failed 
                    print('Invoice Paid....')
                    Transaction.objects.filter(invoice_id=invoice['id'], channel=PaymentProfile.STRIPE).update(invoice_url=invoice['hosted_invoice_url'], invoice_pdf=invoice['invoice_pdf'], invoice_status=invoice['status'])
                print('\nDone with invoice: *******\n', invoice)
            else:
                print('\n\nUnhandled event type {}'.format(event['type']))
                # print(event)
        return Response({'message': 'ok'}, status=status.HTTP_201_CREATED) 
        

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

class TransactionViewSet(viewsets.ModelViewSet, AchieveModelMixin):
    permission_classes = (IsAuthenticated, )
    authentication_classes = (TokenAuthentication,)
    parser_classes = (JSONParser, )
    
    def get_queryset(self):
        """
        This view should return a list of all the Company for
        the user as determined by currently logged in user.
        """
        queryset = Transaction.objects.filter(enabled=True)
        return queryset
 
    def get_permissions(self):
        if self.action in ['cancel']:
            return []  # This method should return iterable of permissions
        return super().get_permissions()

    def get_serializer_class(self):
        # if self.action in ['retrieve']:
        #     return TransactionSerializer
        return TransactionSerializer

    def perform_create(self, serializer):
        return serializer.save(updated_by_id=self.request.user.id)
        
    def perform_update(self, serializer):
        return serializer.save(updated_by_id=self.request.user.id)
      
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        address = self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)

    def update(self, request, *args, **kwargs):
        with transaction.atomic():
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            print('======== ', request.data)
            serializer.is_valid(raise_exception=True)
            instance = self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(methods=['post'], detail=True, url_path='cancel', url_name='cancel')
    def cancel(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.status == Transaction.OPEN:
            instance.status = Transaction.CANCELLED
        return Response({"message": "ok"}, status=status.HTTP_201_CREATED) 

    @action(methods=['post'], detail=True, url_path='crosscheck', url_name='crosscheck')
    def crosscheck(self, request, *args, **kwargs):
        txn = self.get_object()
        msg = None
        
        if txn.status != Transaction.COMPLETED:
            checkout = stripe.checkout.Session.retrieve(txn.external_ref)
            txn.status = checkout['status']
            if checkout['status'] != Transaction.COMPLETED:
                msg = f"Could not successfully complete checkout session \"{checkout['status']}\""
        if msg is None:
            if txn.invoice_status != Transaction.PAID:
                invoice = stripe.Invoice.retrieve(txn.invoice_id)
                txn.invoice_status = invoice['status']
                txn.invoice_url = invoice['hosted_invoice_url']
                txn.invoice_pdf = invoice['invoice_pdf']
                if invoice['status'] != Transaction.PAID:
                    msg = f"Payment not successful \"{invoice['status']}\""
        if msg is None:
            if txn.ext_subscription_ref:
                ids = Subscription.objects.filter(external_ref=txn.ext_subscription_ref, type=txn.type, transaction=txn).values_list('id', flat=True)
                subscription = stripe.Subscription.retrieve(txn.ext_subscription_ref)
                if subscription['active'] == Subscription.ACTIVE:
                    for it in txn.items:
                        subscrips = Subscription.objects.filter(external_ref=txn.ext_subscription_ref, item=it, type=txn.type, transaction=txn)
                        if len(subscrips) == 0:
                            subscrips = Subscription()
                            subscrips.external_ref = subscription['id']
                            subscrips.external_obj = "subscription"
                            subscrips.start_date = datetime.fromtimestamp(subscription['current_period_start'])
                            subscrips.end_date = datetime.fromtimestamp(subscription['current_period_end'])
                            subscrips.transaction = txn
                            subscrips.status = subscription['status']
                            subscrips.type = txn.type
                            subscrips.item = it
                            subscrips.subscriber = txn.payee
                            subscrips.save()
                            if txn.type == Transaction.MDL:
                                ManagerDirectory.objects.filter(id=it).update(subscription=subscrips, is_active=True)
                            elif txn.type == Transaction.PDL:
                                Property.objects.filter(id=it).update(subscription=subscrips, is_active=True)
                            else:
                                print('..... ', txn.type)
                        elif len(subscrips) == 1:
                            subscrips = subscrips[0]
                            if txn.type == Transaction.MDL:
                                ManagerDirectory.objects.filter(id=it).update(subscription=subscrips, is_active=True)
                            elif txn.type == Transaction.PDL:
                                Property.objects.filter(id=it).update(subscription=subscrips, is_active=True)
                            else:
                                print('..... ', txn.type)
                        else:
                            if txn.type == Transaction.MDL:
                                s = Subscription.objects.filter(external_ref=txn.ext_subscription_ref, item=it, type=txn.type, transaction=txn, mdl__isnull=False)
                                if len(s) == 0:
                                    id = subscrips[0].id
                                else:
                                    id = s[0].id
                                subscrips.filter(~Q(id=id)).delete()
                                ManagerDirectory.objects.filter(id=it).update(subscription_id=id)
                            elif txn.type == Transaction.PDL:
                                s = Subscription.objects.filter(external_ref=txn.ext_subscription_ref, item=it, type=txn.type, transaction=txn, pdl__isnull=False)
                                if len(s) == 0:
                                    id = subscrips[0].id
                                else:
                                    id = s[0].id
                                subscrips.filter(~Q(id=id)).delete()
                                Property.objects.filter(id=it).update(subscription_id=id)
                            else:
                                pass
                    