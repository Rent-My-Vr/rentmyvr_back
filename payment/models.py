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


class PaymentProfile(StampedModel):
    """ 
        This will store all form of subscriptions including PDL/MDLs
        All Subscriptions must be associated to a Transaction and the 
        transaction status MUST be Successful  
    """
    STRIPE = 'stripe'
    CHANNELS = ((STRIPE, 'Stripe'), )
    
    external_ref = models.CharField(max_length=254, verbose_name="External Reference Id")
    external_obj = models.CharField(max_length=128, verbose_name="External Reference Object")
    channel = models.CharField(max_length=16, verbose_name="Channel", choices=CHANNELS, default=STRIPE)
    profile = models.OneToOneField(Profile, on_delete=models.CASCADE, related_name="payment")
    
    class Meta:
        ordering = ('channel',)
        verbose_name = _('Payment Profile')
        verbose_name_plural = _('Payment Profiles')

    def __str__(self):
        return self.channel


class Transaction(TrackedModel):
    """ 
        We need to keep record of all attempted transactions both failed and successful here
    """
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    DISPUTED = "disputed"
    EXPIRED = "expired"
    FAILED = "failed"
    OPEN = "open"
    REFUND = "refund"
    REVERSE = "reverse"

    STATUS_CHOICES = (
        (CANCELLED, "Cancelled"),
        (COMPLETED, "Completed"),
        (DISPUTED, "Disputed"),
        (EXPIRED, 'Expired'),
        (FAILED, "Failed"),
        (OPEN, "Open"),
        (REFUND, "Refund"),
        (REVERSE, "Reverse")
    )
    
    PDL = 'pdl'
    MDL = 'mdl'
    SETUP = 'setup'
    OTHER = 'other'
    TYPES = ((MDL, 'MDL'), (PDL, 'PDL'),(SETUP, 'Setup'), (OTHER, 'Other'))
    
    CHECKOUT = 'checkout'
    CHARGE = 'charge'
    PAYMENT = 'payment'
    SUBSCRIPTION = 'subscription'
    EXT_OBJECTS = ((CHECKOUT, 'Checkout'), (CHARGE, 'Charge'), (PAYMENT, 'Payment'), (SUBSCRIPTION, 'Subscription'))
    
    # draft, open, paid, uncollectible, or void
    DRAFT = 'draft'
    OPEN = 'open'
    PAID = 'paid'
    UNCOLLECTIBLE = 'uncollectible'
    VOID = 'void'
    INVOICE_STATUSES = ((DRAFT, 'Draft'), (OPEN, 'Open'), (PAID, 'Paid'), (UNCOLLECTIBLE, 'Uncollectible'), (VOID, 'Void'))
    
    ref = models.CharField(max_length=16, verbose_name="Ref", unique=True, blank=False, null=False)
    ext_subscription_ref = models.CharField(max_length=254, verbose_name="Ext. Subscription Reference", default=None, null=True, blank=True)
    external_ref = models.CharField(max_length=254, verbose_name="External Reference", null=False, blank=False)
    external_obj = models.CharField(max_length=32, choices=EXT_OBJECTS, verbose_name="External Object", null=False, blank=False)
    channel = models.CharField(max_length=128, verbose_name="Channel", choices=PaymentProfile.CHANNELS, default=PaymentProfile.STRIPE, null=False, blank=False)
    status = models.CharField(verbose_name="status", max_length=32,choices=STATUS_CHOICES, default=OPEN, null=True, blank=True)
    currency = models.CharField(verbose_name="curreny", max_length=32)
    type = models.CharField(verbose_name="type", max_length=32, choices=TYPES)
    items = models.JSONField(verbose_name="items", max_length=128, default=list)
    # pdl = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="transactions", default=None, null=True, blank=True)
    # mdl = models.ForeignKey(ManagerDirectory, on_delete=models.CASCADE, related_name="transactions", default=None, null=True, blank=True)
    # other = models.CharField(max_length=128, verbose_name="other", default=None, null=True, blank=True)
    discount_id = models.CharField(max_length=128, verbose_name="discount_id", default=None, null=True, blank=True)
    discount = models.DecimalField(verbose_name="discount", max_digits=12, decimal_places=2, default=0.0)
    quantity = models.IntegerField(verbose_name="unit")
    unit_price = models.DecimalField(verbose_name="unit price", max_digits=12, decimal_places=2, default=0.0)
    total = models.DecimalField(verbose_name="total", max_digits=12, decimal_places=2, default=0.0)
    invoice_id = models.CharField(max_length=254, verbose_name="invoice_id", default=None, null=True, blank=True)
    invoice_status = models.CharField(max_length=32, verbose_name="invoice_status", choices=INVOICE_STATUSES, default=None, null=True, blank=True)
    invoice_url = models.URLField(verbose_name="invoice_url", default=None, null=True, blank=True)
    invoice_pdf = models.URLField(verbose_name="invoice_pdf", default=None, null=True, blank=True)
    payee = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="transactions")
    
    class Meta:
        ordering = ('created',)
        verbose_name = _('Transaction')
        verbose_name_plural = _('Transactions')

    def save(self, *args, **kwargs):
        if not self.created:
            try:
                x = int(Transaction.objects.latest('created').ref[2:]) + 1
            except (AttributeError, TypeError, Transaction.DoesNotExist):
                x = 1
            self.ref = f'TX{x:06}'
        return super(Transaction, self).save(*args, **kwargs)

    def __str__(self):
        return self.ref


class Subscription(StampedModel):
    """ 
        This will store all form of subscriptions including PDL/MDLs
        All Subscriptions must be associated to a Transaction and the 
        transaction status MUST be Successful  
    """

    ACTIVE = 'active'
    CANCELLED = 'canceled'
    INCOMPLETE = 'incomplete'
    INCOMPLETE_EXPIRED = 'incomplete_expired'
    PAST_DUE = 'past_due'
    PAUSED = 'paused'
    TRIALING = 'trialing'
    UNPAID = 'unpaid'

    STATUS_CHOICES = (
        (ACTIVE, 'Active'),
        (CANCELLED, 'Cancelled'),
        (INCOMPLETE, 'Incomplete'),
        (INCOMPLETE_EXPIRED, 'Incomplete Expired'),
        (PAST_DUE, 'Past Due'),
        (PAUSED, 'Paused'),
        (TRIALING, 'Trialing'),
        (UNPAID, 'Unpaid')
        )
    
    ref = models.CharField(max_length=16, verbose_name="Ref", unique=True, blank=False, null=False)
    external_ref = models.CharField(max_length=254, verbose_name="External Reference")
    external_obj = models.CharField(max_length=32, choices=Transaction.EXT_OBJECTS, verbose_name="External Object")
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE, related_name="subscriptions")
    subscriber = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="subscriptions")
    start_date = models.DateField(verbose_name="Start Date")
    end_date = models.DateField(verbose_name="End Date", null=True, blank=True, default=None)
    status = models.CharField(verbose_name="status", max_length=32,choices=STATUS_CHOICES, default=UNPAID)
    type = models.CharField(verbose_name="type", max_length=32, choices=Transaction.TYPES)
    item = models.CharField(verbose_name="item", max_length=128, default=None, null=True, blank=True)
    # pdl = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="subscriptions", default=None, null=True, blank=True)
    # mdl = models.ForeignKey(ManagerDirectory, on_delete=models.CASCADE, related_name="subscriptions", default=None, null=True, blank=True)
    # other = models.CharField(max_length=128, verbose_name="other", default=None, null=True, blank=True)
    
    class Meta:
        unique_together = ('external_ref', 'subscriber', 'transaction')
        ordering = ('start_date',)
        verbose_name = _('Subscription')
        verbose_name_plural = _('Subscription')

    def save(self, *args, **kwargs):
        if not self.created:
            try:
                x = int(Subscription.objects.latest('created').ref[1:]) + 1
            except Subscription.DoesNotExist:
                x = 1
            self.ref = f'B{x:05}'
        return super(Subscription, self).save(*args, **kwargs)

    def __str__(self):
        return f'{self.status.title()} {self.type.upper()}'
