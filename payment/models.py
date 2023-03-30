from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _
from core.models import *


class PriceChart(TrackedModel):
    """ 
        Payable Product Price
        
    """
    PREMIUM = 'premium'
    SERVICE_TYPES = ((PREMIUM, 'Premium'),)
    
    STANDARD = 'standard'
    SUBSIDISED = 'subsidised'
    CATEGORIES = ((STANDARD, 'Standard'), (SUBSIDISED, 'Subsidised'))
    
    PDL = 'pdl'
    MDL = 'mdl'
    SETUP = 'setup'
    TYPES = ((MDL, 'MDL'), (PDL, 'PDL'),(SETUP, 'Setup'))
    
    start = models.DateField(verbose_name="Effective From")
    end = models.DateField(verbose_name="end Date", null=True, blank=True, default=None)
    service_type = models.CharField(max_length=128, verbose_name="Service Type", choices=SERVICE_TYPES, default=PREMIUM)
    category = models.CharField(max_length=128, verbose_name="Category", choices=CATEGORIES, default=STANDARD, null=False, blank=False)
    type = models.CharField(max_length=128, verbose_name="type", choices=TYPES, default=STANDARD, null=False, blank=False)
    monthly_price = models.DecimalField(verbose_name="Monthly Price", default=0.0, null=True, blank=True, max_digits=6, decimal_places=2, help_text="Eg Pay $25 monthly")
    yearly_price = models.DecimalField(verbose_name="Yearly Price", max_digits=6, decimal_places=2, help_text="Eg Save $60 pay annually pay $240 instead of $300")
    emails = models.JSONField(verbose_name="emails", default=list, null=True, blank=True, help_text="If subsidised for selected few, place the list of emails that can access this special price")
    
    
    class Meta:
        ordering = ('start',)
        verbose_name = _('PriceChart')
        verbose_name_plural = _('PriceChart')

    def __str__(self):
        return f"{self.yearly_price}|{self.monthly_price} ({self.category})"


class Transaction(TrackedModel):
    """ 
        We need to keep record of all attempted transactions both failed and successful here
        
    """
    STRIPE = 'stripe'
    CHANNELS = ((STRIPE, 'Stripe'), )
    
    OK = 200
    BAD_REQUEST = 400
    UNAUTHORIED = 401
    REQUEST_FAILED = 402
    FORBIDDEN = 403
    NOT_FOUND = 404
    CONFLICT = 409
    MANY_REQUEST = 429
    SERVER_ERROR = 500
    
    ref = models.CharField(max_length=16, verbose_name="Ref", unique=True, blank=False, null=False)
    date = models.DateTimeField(verbose_name="Start Date", null=True, blank=True, default=None)
    external_ref = models.CharField(max_length=254, verbose_name="External Reference")
    channel = models.CharField(max_length=128, verbose_name="Channel", default=STRIPE, null=False, blank=False)
    status = models.IntegerField(verbose_name="status") # 200 means successful
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")
    amount = models.DecimalField(verbose_name="Amonth", max_digits=6, decimal_places=2, help_text="Eg Pay $20 monthly if you intend to pay for one year upfront ($240 instead of $300)")
    price = models.ForeignKey(PriceChart, on_delete=models.CASCADE)
    payee = models.ForeignKey(UserModel, on_delete=models.CASCADE, related_name="transaction_payee")
    
    class Meta:
        ordering = ('created',)
        verbose_name = _('Subscription')
        verbose_name_plural = _('Subscription')

    def save(self, *args, **kwargs):
        if not self.created:
            try:
                trx = Transaction.objects.latest('created')
                x = int(trx.ref[1:]) + 1 if trx else 1
            except Transaction.DoesNotExist:
                x = 1
            self.ref = f'TX{x:04}'
        return super(Transaction, self).save(*args, **kwargs)

    def __str__(self):
        return self.date


class Subscription(TrackedModel):
    """ 
        This will store all form of subscriptions including PDL/MDLs
        All Subscriptions must be associated to a Transaction and the 
        transaction status MUST be Successful
    
    """
    ref = models.CharField(max_length=16, verbose_name="Ref", unique=True, blank=False, null=False)
    start_date = models.DateField(verbose_name="Start Date")
    end_date = models.DateField(verbose_name="End Date")
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")
    subscriber = models.ForeignKey(UserModel, on_delete=models.CASCADE, related_name="subscriber")
    
    
    class Meta:
        ordering = ('start_date',)
        verbose_name = _('Subscription')
        verbose_name_plural = _('Subscription')

    def save(self, *args, **kwargs):
        if not self.created:
            try:
                trx = Subscription.objects.latest('created')
                x = int(trx.ref[1:]) + 1 if trx else 1
            except Subscription.DoesNotExist:
                x = 1
            self.ref = f'B{x:04}'
        return super(Subscription, self).save(*args, **kwargs)


    def __str__(self):
        return self.start_date

