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
    code = models.CharField(max_length=8, verbose_name="code")
    latitude = models.CharField(max_length=16, verbose_name="Latitude", null=True, blank=True, default='')
    longitude = models.CharField(max_length=16, verbose_name="Longitude", null=True, blank=True, default='')
    
    def __str__(self):
        return self.name

    def get_admin_url(self):
        return reverse('admin:{}_{}_change'.format(self._meta.app_label, self._meta.model_name), args=(self.pk, ))

    class Meta:
        unique_together = ('name', 'country_name')
        ordering = ('country_name', 'name')
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
    # 1km = 1/111.325 degrees. 5km is therefore approximately 0.0449 or about 0.05 degrees
    # location = gis_model.PointField(null=True, blank=True, spatial_index=True, geography=True, srid=4326, dim=3)
    location = gis_model.PointField(null=True, blank=True, spatial_index=True, geography=True, srid=4326)
    hidden = models.BooleanField(default=False, )
    imported = models.BooleanField(default=False, )
    import_id = models.CharField(max_length=16, verbose_name="Imported Id", default='', blank=True, null=True)
    
    def __str__(self):
        return self.more_info if self.more_info else self.formatted if self.formatted else 'No. {}, {}, {}, {}'.format(self.number, self.street, self.city, self.zip_code)

    def get_admin_url(self):
        return reverse('admin:{}_{}_change'.format(self._meta.app_label, self._meta.model_name), args=(self.pk, ))

    class Meta:
        ordering = ('city', )
        managed = AUTO_MANAGE
        verbose_name = _('Address')
        verbose_name_plural = _('Addresses')


class Company(UntrackedModel):
    ref = models.CharField(max_length=16, verbose_name="Ref", unique=True)
    name = models.CharField(max_length=254, verbose_name="Company Name", unique=True)
    website = models.CharField(max_length=254, verbose_name="Website", default='', blank=True, null=True)
    note = models.CharField(max_length=254, verbose_name="Note", default='', blank=True, null=True)
    address = models.ForeignKey(Address, related_name='company_address', on_delete=models.CASCADE, null=True, blank=True)
    email = models.CharField(max_length=128, verbose_name="email", default='', blank=True, null=True)
    phone = models.CharField(max_length=16, verbose_name="phone", default='', blank=True, null=True)
    logo = models.ImageField(blank=True, null=True, default=None)
    # url = models.URLField(max_length=254, verbose_name="Facebook", default='', blank=True, null=True)
    facebook = models.URLField(max_length=254, verbose_name="Facebook", default='', blank=True, null=True)
    instagram = models.URLField(max_length=254, verbose_name="Instagram", default='', blank=True, null=True)
    tiktok = models.URLField(max_length=254, verbose_name="TikTok", default='', blank=True, null=True)
    twitter = models.URLField(max_length=254, verbose_name="Twitter", default='', blank=True, null=True)
    google_business = models.URLField(max_length=254, verbose_name="GoogleBusiness", default='', blank=True, null=True)
    yelp = models.URLField(max_length=254, verbose_name="Yelp", default='', blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.created:
            try:
                coy = Company.objects.latest('created')
                x = int(coy.ref[1:])
            except Company.DoesNotExist:
                x = 0
            x += 1
            self.ref = f'K0{x}' if x < 10 else f'K{x}'
        return super(Company, self).save(*args, **kwargs)

    def __str__(self):
        return self.name

    def get_admin_url(self):
        return reverse('admin:{}_{}_change'.format(self._meta.app_label, self._meta.model_name), args=(self.pk, ))

    class Meta:
        ordering = ('name', )
        managed = AUTO_MANAGE
        verbose_name = _('Company')
        verbose_name_plural = _('Companies')


class Profile(TrackedModel):
    """
    Profile model:
    """
    
    ref = models.CharField(max_length=16, verbose_name="Ref", unique=True, blank=False, null=False)
    user = models.OneToOneField(UserModel, on_delete=models.CASCADE, related_name='user_profile')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, blank=True, null=True, default=None, related_name='company_profiles')
    address = models.ForeignKey(Address, on_delete=models.CASCADE, blank=True, null=True, default=None, related_name='address_profiles')
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
                profile = Profile.objects.latest('created')
                x = int(profile.ref[1:]) + 1 if profile else 1
            except Profile.DoesNotExist:
                x = 1
            self.ref = f'U{x:04}'
        return super(Profile, self).save(*args, **kwargs)

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

