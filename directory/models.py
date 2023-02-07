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
from django.core.validators import FileExtensionValidator
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.utils.deconstruct import deconstructible
from django.template.defaultfilters import filesizeformat
# from django_mysql.models import ListCharField

from core.models import *


# Create your models here.

log = logging.getLogger(f"{__package__}.*")
log.setLevel(settings.LOGGING_LEVEL)

UserModel = get_user_model()
AUTO_MANAGE = True
SELECT_EMPTY = ('', '------')


class Accessibility(StampedModel):

    name = models.CharField(max_length=128, verbose_name="name")
    
    class Meta:
        ordering = ('name',)
        verbose_name = _('Accessibility')
        verbose_name_plural = _('Accessibility')


    def __str__(self):
        return self.name


class Activity(StampedModel):

    name = models.CharField(max_length=128, verbose_name="name")
    
    class Meta:
        ordering = ('name',)
        verbose_name = _('Activity')
        verbose_name_plural = _('Activities')


    def __str__(self):
        return self.name


class Bathroom(StampedModel):

    name = models.CharField(max_length=128, verbose_name="name")
    
    class Meta:
        ordering = ('name',)
        verbose_name = _('Bathroom')
        verbose_name_plural = _('Bathrooms')


    def __str__(self):
        return self.name


class BookingSite(StampedModel):

    name = models.CharField(max_length=24, verbose_name="name")
    site = models.URLField(max_length=254, verbose_name="site")
    
    class Meta:
        ordering = ('name',)
        verbose_name = _('Booking Site')
        verbose_name_plural = _('Booking Sites')


    def __str__(self):
        return self.email


class Entertainment(StampedModel):

    name = models.CharField(max_length=128, verbose_name="name")
    
    class Meta:
        ordering = ('name',)
        verbose_name = _('Kitchen')
        verbose_name_plural = _('Kitchens')


    def __str__(self):
        return self.name


class Essential(StampedModel):

    name = models.CharField(max_length=64, verbose_name="name", unique=True)
    
    class Meta:
        ordering = ('name',)
        verbose_name = _('Essential')
        verbose_name_plural = _('Essentials')


    def __str__(self):
        return self.name


class Family(StampedModel):

    name = models.CharField(max_length=64, verbose_name="name", unique=True)
    
    class Meta:
        ordering = ('name',)
        verbose_name = _('Family')
        verbose_name_plural = _('Families')


    def __str__(self):
        return self.name


class Feature(StampedModel):

    name = models.CharField(max_length=64, verbose_name="name", unique=True)
    
    class Meta:
        ordering = ('name',)
        verbose_name = _('Feature')
        verbose_name_plural = _('Features')


    def __str__(self):
        return self.name


class Kitchen(StampedModel):

    name = models.CharField(max_length=128, verbose_name="name")
    
    class Meta:
        ordering = ('name',)
        verbose_name = _('Kitchen')
        verbose_name_plural = _('Kitchens')


    def __str__(self):
        return self.name


class Laundry(StampedModel):

    name = models.CharField(max_length=128, verbose_name="name")
    
    class Meta:
        ordering = ('name',)
        verbose_name = _('Laundry')
        verbose_name_plural = _('Laundries')


    def __str__(self):
        return self.name


class Outside(StampedModel):

    name = models.CharField(max_length=128, verbose_name="name")
    
    class Meta:
        ordering = ('name',)
        verbose_name = _('Outside')
        verbose_name_plural = _('Outside')


    def __str__(self):
        return self.name


class Parking(StampedModel):

    name = models.CharField(max_length=128, verbose_name="name")
    
    class Meta:
        ordering = ('name',)
        verbose_name = _('Parking')
        verbose_name_plural = _('Parking')


    def __str__(self):
        return self.name


class PoolSpa(StampedModel):

    name = models.CharField(max_length=128, verbose_name="name")
    
    class Meta:
        ordering = ('name',)
        verbose_name = _('Pool & Spa')
        verbose_name_plural = _('Pool & Spa')


    def __str__(self):
        return self.name
 
 
class Safety(StampedModel):

    name = models.CharField(max_length=64, verbose_name="name", unique=True)
    
    class Meta:
        ordering = ('name',)
        verbose_name = _('Safety')
        verbose_name_plural = _('Safeties')


    def __str__(self):
        return self.name
    
  
class Space(StampedModel):

    name = models.CharField(max_length=64, verbose_name="name", unique=True)
    
    class Meta:
        ordering = ('name',)
        verbose_name = _('Space')
        verbose_name_plural = _('Spaces')


    def __str__(self):
        return self.name
    

class Service(StampedModel):

    name = models.CharField(max_length=64, verbose_name="name", unique=True)
    
    class Meta:
        ordering = ('name',)
        verbose_name = _('Service')
        verbose_name_plural = _('Services')


    def __str__(self):
        return self.email
         

class Property(StampedUpdaterModel):
    """
    Property model:
    """

    BARN = 'barn'
    BED_AND_BREAKFAST = 'bed-and-breakfast'
    BOAT = 'boat'
    BUNGALOW = 'bungalow'
    BUS = 'bus'
    CABIN = 'cabin'
    CAMPER = 'camper'
    CARAVAN = 'caravan'
    CASA_PARTICULARS = 'casa-particulars'
    CASTLE = 'castle'
    CAVE = 'cave'
    CHALET = 'chalet'
    CONDO = 'condo'
    COTTAGE = 'cottage'
    COUNTRY_HOUSE = 'country-house'
    CYCLADIC = 'cycladic'
    DAMUSI = 'damusi'
    EARTH_HOME = 'earth-home'
    ESTATE = 'estate'
    FARM_HOUSE = 'farm-house'
    GUEST_HOUSE = 'guest-house'
    HANOK = 'hanok'
    HISTORIC_HOME = 'historic-home'
    HOTEL = 'hotel'
    HOUSE = 'house'
    HOUSEBOAT = 'houseboat'
    LODGE = 'lodge'
    MINSUS = 'minsus'
    RESORT = 'resort'
    RIAD = 'riad'
    RYOKAN = 'ryokan'
    SHEPHERDS_HUT = 'shepherds-hut'
    SPECIALTY = 'specialty'
    STUDIO = 'studio'
    TENT = 'tent'
    TINY_HOME = 'tiny-home'
    TOWER = 'tower'
    TOWNHOUSE = 'townhouse'
    TRAIN_CAR = 'train-car'
    TREEHOUSE = 'treehouse'
    TRULLI = 'trulli'
    VILLA = 'villa'
    WINDMILL = 'windmill'
    YACHT = 'yacht'
    YURT = 'yurt'

    TYPES = (
                (BARN, 'Barn'),
                (BED_AND_BREAKFAST, 'Bed and Breakfast'),
                (BOAT, 'Boat'),
                (BUNGALOW, 'Bungalow'),
                (BUS, 'Bus'),
                (CABIN, 'Cabin'),
                (CAMPER, 'Camper'),
                (CARAVAN, 'Caravan'),
                (CASA_PARTICULARS, 'Casa Particulars'),
                (CASTLE, 'Castle'),
                (CAVE, 'Cave'),
                (CHALET, 'Chalet'),
                (CONDO, 'Condo'),
                (COTTAGE, 'Cottage'),
                (COUNTRY_HOUSE, 'Country House'),
                (CYCLADIC, 'Cycladic'),
                (DAMUSI, 'Damusi'),
                (EARTH_HOME, 'Earth Home'),
                (ESTATE, 'Estate'),
                (FARM_HOUSE, 'Farm House'),
                (GUEST_HOUSE, 'Guest House'),
                (HANOK, 'Hanok'),
                (HISTORIC_HOME, 'Historic Home'),
                (HOTEL, 'Hotel'),
                (HOUSE, 'House'),
                (HOUSEBOAT, 'Houseboat'),
                (LODGE, 'Lodge'),
                (MINSUS, 'Minsus'),
                (RESORT, 'Resort'),
                (RIAD, 'Riad'),
                (RYOKAN, 'Ryokan'),
                (SHEPHERDS_HUT, "Shepherd's Hut"),
                (SPECIALTY, 'Specialty'),
                (STUDIO, 'Studio'),
                (TENT, 'Tent'),
                (TINY_HOME, 'Tiny Home'),
                (TOWER, 'Tower'),
                (TOWNHOUSE, 'Townhouse'),
                (TRAIN_CAR, 'Train Car'),
                (TREEHOUSE, 'Treehouse'),
                (TRULLI, 'Trulli'),
                (VILLA, 'Villa'),
                (WINDMILL, 'Windmill'),
                (YACHT, 'Yacht'),
                (YURT, 'Yurt')
            )
    
    ENTIRE_HOUSE = 'entire-house'
    PRIVATE_ROOM = 'private-room'
    CASITA_SEP_GUEST_QUARTERS = 'casita-sep-guest-quarters'
    
    BOOKED_SPACE = ((ENTIRE_HOUSE, 'Entire House'),
                    (PRIVATE_ROOM, 'Private Room'),
                    (CASITA_SEP_GUEST_QUARTERS, 'Casita/Sep Guest Quarters'))
    
    ref = models.CharField(max_length=16, verbose_name="Ref", unique=True)
    name = models.CharField(max_length=254, verbose_name="Name", unique=True)
    video = models.FileField(blank=True, null=True, default=None)
    virtual_tour = models.FileField(blank=True, null=True, default=None)
    type = models.CharField(max_length=254, verbose_name="Type", choices=TYPES, default='', blank=True, null=True)
    space = models.CharField(max_length=254, verbose_name="Booked Space", choices=BOOKED_SPACE, default='', blank=True, null=True)
    hosted_by = models.CharField(max_length=254, verbose_name="Hosted By", default='', blank=True, null=True)
    no_of_guest = models.IntegerField(verbose_name="No of Guest")
    no_of_bedrooms = models.IntegerField(verbose_name="No of Bedrooms")
    no_of_bathrooms = models.IntegerField(verbose_name="No of Bathrooms")
    is_pet_allowed = models.BooleanField(default=True, )
    suitability = models.BooleanField(default=True, )
    description = models.TextField(verbose_name="Description", default='', blank=True, null=True)
    host_note = models.TextField(verbose_name="Host Notes", default='', blank=True, null=True)
    
    price_night = models.DecimalField(verbose_name="Ave $ Per Night", max_digits=9, decimal_places=2)
    address = models.ForeignKey(Address, related_name='property_address', on_delete=models.CASCADE, null=True, blank=True)
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

    accessibility = models.ManyToManyField(Accessibility, blank=True)
    activities = models.ManyToManyField(Activity, blank=True)
    bathrooms = models.ManyToManyField(Bathroom, blank=True)
    booking_sites = models.ManyToManyField(BookingSite, blank=True)
    entertainments = models.ManyToManyField(Entertainment, blank=True)
    essentials = models.ManyToManyField(Essential, blank=True)
    families = models.ManyToManyField(Family, blank=True)
    features = models.ManyToManyField(Feature, blank=True)
    kitchens = models.ManyToManyField(Kitchen, blank=True)
    laundries = models.ManyToManyField(Laundry, blank=True)
    outsides = models.ManyToManyField(Outside, blank=True)
    parking = models.ManyToManyField(Parking, blank=True)
    pool_spas = models.ManyToManyField(PoolSpa, blank=True)
    safeties = models.ManyToManyField(Safety, blank=True)
    spaces = models.ManyToManyField(Space, blank=True)
    services = models.ManyToManyField(Service, blank=True)
    
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

  
       

