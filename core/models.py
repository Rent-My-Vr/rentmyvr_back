from enum import unique
from itertools import product
import logging
import re
import uuid
from django.utils import timezone
from django.db import models
from django.db.models import Q, Prefetch
from django.conf import settings
from django.core.cache import cache
from django.contrib.auth import get_user_model
from django.contrib.gis.db import models as gis_model
from django.core.validators import FileExtensionValidator
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.contrib.gis.geos import Point
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.utils.deconstruct import deconstructible
from django.template.defaultfilters import filesizeformat

# from django_mysql.models import ListCharField


log = logging.getLogger(f"{__package__}.*")
log.setLevel(settings.LOGGING_LEVEL)

UserModel = get_user_model()
AUTO_MANAGE = True
SELECT_EMPTY = ('', '------')


def profile_upload_path(instance, filename):
    path = f'uploads/rental/profile/images/'
    filename = f"{instance.id}.{filename.split('.')[-1]}"
    import os
    return os.path.join(path, filename)

class BaseModel(models.Model):
    """
    BaseModel
    """

    def __eq__(self, other):
        return other and self.id == other.id

    def __hash__(self):
        return hash(self.id)

    # def __lt__(self, other):
    #     return self.created < other.created
    
    class Meta:
        abstract = True


class SingletonModel:
    
    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        company = kwargs.pop('company', None)
        super(SingletonModel, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    def set_cache(self, obj=None, name=None, timeout=360):
        try:
            if obj is None:
                cache.set(name if name else self.__class__.__name__.lower(), self, timeout=timeout)
            else:
                cache.set(name if name else self.__class__.__name__.lower(), obj, timeout=timeout)
        except Exception as err:
            log.error(err)

    @classmethod
    def reload(cls, company=None, id=None, name=None, timeout=360):
        cache.expire(name if name else cls.__name__, timeout=0)
        cls.load(company=company, id=id, name=name, timeout=timeout)

    @classmethod
    def load(cls, company, id=None, name=None, timeout=3600, reload=False, extra_query={}):
        instances = cache.get(name if name else cls.__name__)
        if reload or instances is None:
            if id is None:
                instances = cls.objects.filter(**{**{'company': company}, **extra_query})
                cls.set_cache(instances, name=name, timeout=timeout)
            else:
                instances = cls.objects.filter(**{**{'pk': id, 'company': company}, **extra_query}).first()
                if instances:
                    instances.set_cache(instances, name=name, timeout=timeout)
        return instances


class StampedModel(BaseModel):
    """
    Abstract Model for models that need to be timestamped
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    updated = models.DateTimeField(auto_now=True)
    created = models.DateTimeField(auto_now_add=True)
    enabled = models.BooleanField(default=True, )

    class Meta:
        abstract = True


class StampedUpdaterModel(StampedModel):
    """
    Abstract Model for models that need to tracked by Updater
    """
    updated_by = models.ForeignKey(UserModel, on_delete=models.CASCADE)

    # def update_tracked(self, user):
    #     if not self.pk and not isinstance(self, Company):
    #         self.company = user.company
    #     self.updated_by = user

    class Meta:
        abstract = True


class TrackedModel(StampedUpdaterModel):
    """
    Abstract Model for models that need to tracked by Company
    """
    if settings.IS_MULTITENANT:
        company = models.ForeignKey("Company", on_delete=models.CASCADE, null=True, default=None)

    def update_tracked(self, user):
        if settings.IS_MULTITENANT:
            if not self.created:
                self.company = user.company
        self.updated_by = user

    class Meta:
        abstract = True


class UntrackedModel(StampedModel):
    """
    Abstract Model for models that need do not need to be tracked
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    if settings.IS_MULTITENANT:
        company = models.ForeignKey("Company", on_delete=models.CASCADE, null=True, default=None)

    class Meta:
        abstract = True


class Country(UntrackedModel):
    name = models.CharField(max_length=254, verbose_name="Name", unique=True)
    iso3 = models.CharField(max_length=8, verbose_name="Iso3")
    iso2 = models.CharField(max_length=8, verbose_name="Iso2")
    numeric_code = models.CharField(max_length=32, verbose_name="Numeric Code")
    phone_code = models.CharField(max_length=32, verbose_name="Phone Code")
    capital = models.CharField(max_length=254, verbose_name="Capital", null=True, blank=True, default='')
    currency = models.CharField(max_length=8, verbose_name="Currency")
    currency_name = models.CharField(max_length=254, verbose_name="Currency Name")
    currency_symbol = models.CharField(max_length=32, verbose_name="Currency Symbol")
    tld = models.CharField(max_length=10, verbose_name="TLD")
    native = models.CharField(max_length=254, verbose_name="Native", null=True, blank=True, default='')
    region = models.CharField(max_length=128, verbose_name="Region", null=True, blank=True, default='')
    subregion = models.CharField(max_length=128, verbose_name="Subregion", null=True, blank=True, default='')
    latitude = models.CharField(max_length=16, verbose_name="Latitude")
    longitude = models.CharField(max_length=16, verbose_name="Longitude")
    emoji = models.CharField(max_length=16, verbose_name="Emoji")
    emojiU = models.CharField(max_length=64, verbose_name="EmojiU")
    timezones = models.JSONField()
    
    def __str__(self):
        return self.name

    def get_admin_url(self):
        return reverse('admin:{}_{}_change'.format(self._meta.app_label, self._meta.model_name), args=(self.pk, ))

    class Meta:
        ordering = ('name', )
        managed = AUTO_MANAGE
        verbose_name = _('Country')
        verbose_name_plural = _('Countries')


class State(UntrackedModel):
    name = models.CharField(max_length=254, verbose_name="Name")
    country_name = models.CharField(max_length=254, verbose_name="Country Name")
    
    country = models.ForeignKey(Country, on_delete=models.CASCADE, default="df5295cc-209d-4e62-b5a7-e718b1bc2368")
    
    code = models.CharField(max_length=8, verbose_name="code")
    latitude = models.CharField(max_length=16, verbose_name="Latitude", null=True, blank=True, default='')
    longitude = models.CharField(max_length=16, verbose_name="Longitude", null=True, blank=True, default='')
    
    def __str__(self):
        return self.name

    def get_admin_url(self):
        return reverse('admin:{}_{}_change'.format(self._meta.app_label, self._meta.model_name), args=(self.pk, ))

    class Meta:
        unique_together = ('name', 'country_name')
        ordering = ('country__name', 'name')
        managed = AUTO_MANAGE
        verbose_name = _('State')
        verbose_name_plural = _('States')


class City(UntrackedModel):
    name = models.CharField(max_length=254, verbose_name="Name")
    state_name = models.CharField(max_length=254, verbose_name="State Name")
    country_name = models.CharField(max_length=254, verbose_name="Country Name", default='United States')
    approved = models.BooleanField(default=True, )
    imported = models.BooleanField(default=False, )
    import_id = models.CharField(max_length=16, verbose_name="Imported Id", default='', blank=True, null=True)
    
    def __str__(self):
        return self.name

    def get_admin_url(self):
        return reverse('admin:{}_{}_change'.format(self._meta.app_label, self._meta.model_name), args=(self.pk, ))

    class Meta:
        unique_together = ('name', 'state_name', 'country_name')
        ordering = ('country_name', 'name')
        managed = AUTO_MANAGE
        verbose_name = _('City')
        verbose_name_plural = _('Cities')


class Address(UntrackedModel):
    # id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    country = models.CharField(max_length=254, verbose_name="Country", default="United States")
    street = models.CharField(max_length=254, verbose_name="Street", null=True, blank=True, default='')
    number = models.CharField(max_length=254, verbose_name="Number", null=True, blank=True, default='')
    city = models.ForeignKey(City, on_delete=models.CASCADE, verbose_name="City")
    zip_code = models.CharField(max_length=10, verbose_name="Zip Code", null=True, blank=True, default='')
    more_info = models.CharField(max_length=512, verbose_name="Additional Info", null=True, blank=True, default='')
    formatted = models.CharField(max_length=512, verbose_name="Formatted Address", null=True, blank=True, default='')
    # srid (default 4326 = WGS84 dd)
    # dim (default 2, 3 will support z)
    # spatial_index (default True, spatial index is built)
    # 1km = 1/111.325 degrees. 5km is therefore approximately 0.0449 or about 0.05 degrees
    # location = gis_model.PointField(null=True, blank=True, spatial_index=True, geography=True, srid=4326, dim=3)
    location = gis_model.PointField(null=True, blank=True, spatial_index=True, geography=True, srid=4326)
    hidden = models.BooleanField(default=False, )
    imported = models.BooleanField(default=False, )
    import_id = models.CharField(max_length=16, verbose_name="Imported Id", default='', blank=True, null=True)
    
    def __str__(self):
        # House number Street, City, state, zip
        # 23 Johnson St, Queen Creek, AZ, 123456, US
        return self.formatted if self.formatted else self.address()

    def address(self):
        street = f'{self.number} {self.street}, ' if self.number and self.street else f'{self.street}, ' if self.street else ''
        zip = f' {self.zip_code}, ' if self.zip_code else ', '
        return '{}{}, {}{}{}'.format(street, self.city.name, self.city.state_name, zip, self.city.country_name)
    
    def get_admin_url(self):
        return reverse('admin:{}_{}_change'.format(self._meta.app_label, self._meta.model_name), args=(self.pk, ))

    class Meta:
        ordering = ('city', )
        managed = AUTO_MANAGE
        verbose_name = _('Address')
        verbose_name_plural = _('Addresses')


class Company(TrackedModel):
    ref = models.CharField(max_length=16, verbose_name="Ref", unique=True)
    name = models.CharField(max_length=128, verbose_name="name")
    website = models.URLField(max_length=254, verbose_name="Company URL", default="", blank=True, null=True)
    contact_name = models.CharField(max_length=128, verbose_name="Contact name", null=True, blank=True, default='')
    email = models.CharField(max_length=254, verbose_name="Email", null=True, blank=True, default='')
    phone = models.CharField(max_length=16, verbose_name="Phone", null=True, blank=True, default='')
    ext = models.CharField(max_length=8, verbose_name="Ext #", null=True, blank=True, default='')
    description = models.TextField(verbose_name="Description", null=True, blank=True, default='')
    
    street = models.CharField(max_length=128, verbose_name="Street", null=True, blank=True, default='')
    number = models.CharField(max_length=16, verbose_name="Number", null=True, blank=True, default='')
    city = models.ForeignKey(City, on_delete=models.CASCADE, verbose_name="City")
    zip_code = models.CharField(max_length=16, verbose_name="Zip Code", null=True, blank=True, default='')
    state = models.CharField(max_length=128, verbose_name="State")
    state_obj = models.ForeignKey(State, on_delete=models.CASCADE, verbose_name="State")
    more_info = models.CharField(max_length=512, verbose_name="Additional Info", null=True, blank=True, default='')
    
    administrator = models.OneToOneField("Profile", on_delete=models.CASCADE, related_name='profile', verbose_name="Administrator", blank=True, null=True, default=None)
    
    def address(self):
        street = f'{self.number} {self.street}, ' if self.number and self.street else f'{self.street}, ' if self.street else ''
        zip = f' {self.zip_code}, ' if self.zip_code else ', '
        return '{}{}, {}{}{}'.format(street, self.city.name, self.state_obj.name, zip, self.state_obj.country.iso3)

    class Meta:
        ordering = ('name',)
        unique_together = ('name', 'state')
        verbose_name = _('Company')
        verbose_name_plural = _('Companies')

    def save(self, *args, **kwargs):
        if not self.created:
            try:
                x = int(Company.objects.latest('created').ref[1:]) + 1
            except (AttributeError, TypeError, Company.DoesNotExist):
                x = 1
            self.ref = f'C{x:05}'
        return super(Company, self).save(*args, **kwargs)

    def __str__(self):
        return self.name


class Contact(StampedModel):
    ref = models.CharField(max_length=16, verbose_name="Ref", unique=True, blank=False, null=False)
    email = models.CharField(max_length=128, verbose_name="email")
    name = models.CharField(max_length=128, verbose_name="name", null=True, blank=True, default=None)
    company_name = models.CharField(max_length=128, verbose_name="Company Name", null=True, blank=True, default=None)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="contacts", null=True, blank=True, default=None)
    phone = models.CharField(max_length=128, verbose_name="phone", null=True, blank=True, default=None)
    message = models.TextField()
     
    class Meta:
        ordering = ('email',)
        verbose_name = _('Contact')
        verbose_name_plural = _('Contact')

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        if not self.created:
            try:
                x = int(Contact.objects.latest('created').ref[1:]) + 1
            except (AttributeError, TypeError, Contact.DoesNotExist):
                x = 1
            self.ref = f'X{x:04}'
        return super(Contact, self).save(*args, **kwargs)


class Invitation(StampedModel):
    PENDING = 'pending'
    CANCELLED = 'cancelled'
    EJECTED = 'ejected'
    SENT = 'sent'
    RESENT = 'resent'
    REJECTED = 'rejected'
    REGISTERING = 'registering'
    ACCEPTED = 'accepted'
    STATUS = ((ACCEPTED, 'Accepted'),
              (CANCELLED, 'Cancelled'),
              (EJECTED, 'Ejected'),
              (PENDING, 'pending'),
              (REGISTERING, 'Registering'),
              (REJECTED, 'Rejected'),
              (RESENT, 'Resent'),
              (SENT, 'Sent')
              )
    
    email = models.CharField(max_length=128, verbose_name="email")
    sent = models.DateTimeField(null=True, blank=True, default=None)
    response = models.DateTimeField(null=True, blank=True, default=None)
    exists = models.BooleanField(default=False, )
    token = models.BigIntegerField(null=True, blank=True, default=None)
    status = models.CharField(max_length=128, choices=STATUS, default=PENDING)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='invitations')
    sender = models.ForeignKey("Profile", on_delete=models.CASCADE, related_name='invites')
    
    class Meta:
        ordering = ('email',)
        unique_together = ('email', 'company')
        verbose_name = _('Invitation')
        verbose_name_plural = _('Invitations')

    def __str__(self):
        return self.email


# class Support(StampedModel):
#     from directory.models import Property
#     MDL = 'mdl'
#     PDL = 'pdl'
#     OTHERS = 'others'
#     TYPES = ((MDL, 'A Management Company Listing'), 
#               (PDL, 'A Property Listing'),
#               (OTHERS, 'Others'))
#     TYPE = {MDL: TYPES[0][1], PDL: TYPES[1][1], OTHERS: TYPES[2][1]}
    
#     ref = models.CharField(max_length=16, verbose_name="Ref", unique=True, blank=False, null=False)
#     name = models.CharField(max_length=128, verbose_name="name", null=True, blank=True, default=None)
#     company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="supports", null=True, blank=True, default=None)
#     property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="supports", null=True, blank=True, default=None)
#     phone = models.CharField(max_length=128, verbose_name="phone", null=True, blank=True, default=None)
#     type = models.CharField(max_length=128, choices=TYPES)
#     message = models.TextField("message", null=True, blank=True, default=None)
    
#     class Meta:
#         ordering = ('type',)
#         verbose_name = _('Support')
#         verbose_name_plural = _('Support')

#     def __str__(self):
#         return self.message

#     def save(self, *args, **kwargs):
#         if not self.created:
#             try:
#                 x = int(Support.objects.latest('created').ref[1:]) + 1
#             except (AttributeError, TypeError, Support.DoesNotExist):
#                 x = 1
#             self.ref = f'S{x:04}'
#         return super(Support, self).save(*args, **kwargs)


class Profile(TrackedModel):
    """
    Profile model:
    """
    
    ref = models.CharField(max_length=16, verbose_name="Ref", unique=True, blank=False, null=False)
    user = models.OneToOneField(UserModel, on_delete=models.CASCADE, related_name='user_profile')
    company = models.ForeignKey(Company, on_delete=models.SET_NULL, related_name='members', blank=True, null=True, default=None)
    image = models.ImageField(upload_to=profile_upload_path, blank=True, null=True, default=None)
    
    address = models.ForeignKey(Address, on_delete=models.CASCADE, related_name='profiles', blank=True, null=True, default=None)
    
    street = models.CharField(max_length=128, verbose_name="Street", null=True, blank=True, default='')
    number = models.CharField(max_length=16, verbose_name="Number", null=True, blank=True, default='')
    city = models.ForeignKey(City, on_delete=models.CASCADE, verbose_name="City")
    zip_code = models.CharField(max_length=16, verbose_name="Zip Code", null=True, blank=True, default='')
    state = models.ForeignKey(State, on_delete=models.CASCADE, verbose_name="State")
    # location = gis_model.PointField(null=True, blank=True, spatial_index=True, geography=True, srid=4326)
    # formatted = models.CharField(max_length=512, verbose_name="Formatted Address", null=True, blank=True, default='')
    more_info = models.CharField(max_length=512, verbose_name="Additional Info", null=True, blank=True, default='')
    
    # position = models.CharField(max_length=32, verbose_name="Position", choices=POSITIONS, default="Worker")
    # status = models.CharField(max_length=32, verbose_name="Status", choices=STATUS, default=UNAVAILABLE)
    # projects = models.ManyToManyField('Project')
    # timezone = models.CharField(_('timezone'), max_length=128, blank=True, null=True, default="America/Denver")
    # avatar_image = models.ImageField(upload_to=profile_upload_path, blank=True, null=True, 
    #             default=None, validators=[FileValidator(max_size=1024 * 5000), 
    #                 FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])])
    # avatar_thumbnail = models.ImageField(blank=True, null=True, default=None)
    # avatar_url = models.URLField(null=True, blank=True, default=None)

    class Meta:
        ordering = ('user__first_name', 'user__last_name')
        verbose_name = _('Profile')
        verbose_name_plural = _('Profiles')
 
    def __str__(self):
        return self.fullname

    def save(self, *args, **kwargs):
        if not self.created:
            try:
                x = int(Profile.objects.latest('created').ref[1:]) + 1
            except (AttributeError, TypeError, Profile.DoesNotExist):
                x = 1
            self.ref = f'U{x:04}'
        return super(Profile, self).save(*args, **kwargs)
    
    @property
    def image_url(self):
        try:
            if self.image is not None and hasattr(self.image, 'url'):
                return self.image.url
        except:
            pass
        
    @property
    def fullname(self):
        return f"{self.user.full_name if self.pk else self.user.email}"

    @classmethod
    def get_add_url(cls):
        return reverse('core:profile-add')

    @classmethod
    def get_list_url(cls):
        return reverse('core:profile-list')

    def get_update_url(self):
        return reverse('core:profile-edit', kwargs={'pk': self.pk})

    def get_delete_url(self):
        return reverse('core:profile-delete', kwargs={'pk': self.pk})

    def get_disable_url(self):
        return reverse('core:profile-disable', kwargs={'pk': self.pk})

    def get_timers(self):
        return self.timers.all()

    def get_short_dict(self):
        return {"id": f"{self.id}", "value": self.fullname, "type": self.__class__.__name__}

