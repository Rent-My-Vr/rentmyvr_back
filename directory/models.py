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
from payment.models import Subscription
from schedule.models.calendars import Calendar

# Create your models here.

log = logging.getLogger(f"{__package__}.*")
log.setLevel(settings.LOGGING_LEVEL)

UserModel = get_user_model()
AUTO_MANAGE = True
SELECT_EMPTY = ('', '------')


def manager_image_upload_path(instance, filename):
    path = f'uploads/rental/company/images/'
    filename = f"{instance.id}.{filename.split('.')[-1]}"
    import os
    return os.path.join(path, filename)


def property_image_upload_path(instance, filename):
    path = f'uploads/rental/property/images/'
    filename = f"{instance.id}.{filename.split('.')[-1]}"
    import os
    return os.path.join(path, filename)


def property_video_upload_path(instance, filename):
    path = f'uploads/rental/property/videos/'
    filename = f"{instance.id}.{filename.split('.')[-1]}"
    import os
    return os.path.join(path, filename)


class Accessibility(StampedModel):

    name = models.CharField(max_length=128, verbose_name="name", unique=True)
    icon = models.URLField(max_length=254, verbose_name="icon", default="https://rentmyvr.com/assets/images/amenties-svg/barn.svg")
    
    class Meta:
        ordering = ('name',)
        verbose_name = _('Accessibility')
        verbose_name_plural = _('Accessibility')

    def __str__(self):
        return self.name


class Activity(StampedModel):

    name = models.CharField(max_length=128, verbose_name="name", unique=True)
    icon = models.URLField(max_length=254, verbose_name="icon", default="https://rentmyvr.com/assets/images/amenties-svg/barn.svg")
    
    class Meta:
        ordering = ('name',)
        verbose_name = _('Activity')
        verbose_name_plural = _('Activities')

    def __str__(self):
        return self.name


class Bathroom(StampedModel):

    name = models.CharField(max_length=128, verbose_name="name", unique=True)
    icon = models.URLField(max_length=254, verbose_name="icon", default="https://rentmyvr.com/assets/images/amenties-svg/barn.svg")
    
    class Meta:
        ordering = ('name',)
        verbose_name = _('Bathroom')
        verbose_name_plural = _('Bathrooms')

    def __str__(self):
        return self.name


class CompanySocialMediaLink(StampedModel):
    FACEBOOK = 'facebook'
    INSTAGRAM = 'instagram'
    TIKTOK = 'tiktok'
    YOUTUBE = 'youtube'
    TWITTER = 'twitter'
    GOOGLE_BUSINESS = 'google-business'
    YELP = 'yelp'
    PINTEREST = 'pinterest'

    MEDIAS = (
                (FACEBOOK, 'Facebook'),
                (INSTAGRAM, 'Instagram'),
                (TIKTOK, 'TikTok'),
                (YOUTUBE, 'YouTube'),
                (TWITTER, 'Twitter'),
                (GOOGLE_BUSINESS, 'GoogleBusiness'),
                (PINTEREST, 'Pinterest'),
                (YELP, 'Yelp')
            )

    name = models.CharField(max_length=24, verbose_name="name", choices=MEDIAS)
    site = models.TextField(max_length=1024, verbose_name="site")
    property = models.ForeignKey(Company, verbose_name="Company", related_name="social_media", on_delete=models.CASCADE)

    class Meta:
        ordering = ('name',)
        verbose_name = _('Social Media Link')
        verbose_name_plural = _('Social Media Links')

    def __str__(self):
        return self.name


class InquiryMessage(StampedModel):

    name = models.CharField(max_length=128, verbose_name="Name")
    email = models.CharField(max_length=254, verbose_name="Email Address")
    phone = models.CharField(max_length=16, verbose_name="Phone", null=True, blank=True, default="")
    subject = models.CharField(max_length=128, verbose_name="Subject")
    message = models.TextField(verbose_name="Message")
    property = models.ForeignKey('Property', verbose_name="Property", on_delete=models.CASCADE)
    sent_time = models.DateTimeField(null=True, blank=True, default=None)
    
    class Meta:
        ordering = ('subject',)
        verbose_name = _('InquiryMessage')
        verbose_name_plural = _('InquiryMessages')


    def __str__(self):
        return self.subject


class Entertainment(StampedModel):

    name = models.CharField(max_length=128, verbose_name="name", unique=True)
    icon = models.URLField(max_length=254, verbose_name="icon", default="https://rentmyvr.com/assets/images/amenties-svg/barn.svg")
    
    class Meta:
        ordering = ('name',)
        verbose_name = _('Entertainment')
        verbose_name_plural = _('Entertainments')


    def __str__(self):
        return self.name


class Essential(StampedModel):

    name = models.CharField(max_length=64, verbose_name="name", unique=True)
    icon = models.URLField(max_length=254, verbose_name="icon", default="https://rentmyvr.com/assets/images/amenties-svg/barn.svg")
    
    class Meta:
        ordering = ('name',)
        verbose_name = _('Essential')
        verbose_name_plural = _('Essentials')

    def __str__(self):
        return self.name


class Family(StampedModel):

    name = models.CharField(max_length=64, verbose_name="name", unique=True)
    icon = models.URLField(max_length=254, verbose_name="icon", default="https://rentmyvr.com/assets/images/amenties-svg/barn.svg")
    
    class Meta:
        ordering = ('name',)
        verbose_name = _('Family')
        verbose_name_plural = _('Families')

    def __str__(self):
        return self.name


class Feature(StampedModel):

    name = models.CharField(max_length=64, verbose_name="name", unique=True)
    icon = models.URLField(max_length=254, verbose_name="icon", default="https://rentmyvr.com/assets/images/amenties-svg/barn.svg")
    
    class Meta:
        ordering = ('name',)
        verbose_name = _('Feature')
        verbose_name_plural = _('Features')

    def __str__(self):
        return self.name


class Kitchen(StampedModel):

    name = models.CharField(max_length=128, verbose_name="name", unique=True)
    icon = models.URLField(max_length=254, verbose_name="icon", default="https://rentmyvr.com/assets/images/amenties-svg/barn.svg")
    
    class Meta:
        ordering = ('name',)
        verbose_name = _('Kitchen')
        verbose_name_plural = _('Kitchens')

    def __str__(self):
        return self.name


class Laundry(StampedModel):

    name = models.CharField(max_length=128, verbose_name="name", unique=True)
    icon = models.URLField(max_length=254, verbose_name="icon", default="https://rentmyvr.com/assets/images/amenties-svg/barn.svg")
    
    class Meta:
        ordering = ('name',)
        verbose_name = _('Laundry')
        verbose_name_plural = _('Laundries')

    def __str__(self):
        return self.name


class ManagerDirectory(TrackedModel):
    DRAFT = 'draft'
    DEACTIVATED = 'deactivated'
    EXPIRED = 'expired'
    IMPORTED = 'imported'
    PUBLISHED = 'published'
    
    STATUS_CHOICES = ((DRAFT, 'Draft'), (DEACTIVATED, 'Deactivated'), (EXPIRED, 'Expired'), (IMPORTED, 'Imported'), (PUBLISHED, 'Published'))
    # ref = models.CharField(max_length=16, verbose_name="Ref", default=None, blank=True, null=True)
    ref = models.CharField(max_length=16, verbose_name="Ref", unique=True)
    name = models.CharField(max_length=254, verbose_name="name")
    is_active = models.BooleanField(default=False)
    status = models.CharField(verbose_name="status", max_length=32, choices=STATUS_CHOICES, default=DRAFT)
    manage_for_others = models.BooleanField(default=False)
    
    website = models.URLField(max_length=254, verbose_name="Company URL", default="", blank=True, null=True)
    contact_name = models.CharField(max_length=128, verbose_name="Contact name", null=True, blank=True, default='')
    email = models.CharField(max_length=254, verbose_name="Email", null=True, blank=True, default='')
    phone = models.CharField(max_length=16, verbose_name="Phone", null=True, blank=True, default='')
    ext = models.CharField(max_length=8, verbose_name="Ext #", null=True, blank=True, default='')
    description = models.TextField(verbose_name="Description", null=True, blank=True, default='')
    country = models.CharField(max_length=128, verbose_name="Country", default="United States")
    state = models.CharField(max_length=128, verbose_name="State")
    street = models.CharField(max_length=254, verbose_name="Street", null=True, blank=True, default='')
    number = models.CharField(max_length=32, verbose_name="Number", null=True, blank=True, default='')
    city = models.ForeignKey(City, on_delete=models.CASCADE, verbose_name="City")
    zip_code = models.CharField(max_length=10, verbose_name="Zip Code", null=True, blank=True, default='')
    more_info = models.CharField(max_length=512, verbose_name="Additional Info", null=True, blank=True, default='')
    formatted = models.CharField(max_length=512, verbose_name="Formatted Address", null=True, blank=True, default='')
    
    location = gis_model.PointField(null=True, blank=True, spatial_index=True, geography=True, srid=4326, dim=3)
    phone_2 = models.CharField(max_length=16, verbose_name="Phone 2", null=True, blank=True, default='')
    ext_2 = models.CharField(max_length=8, verbose_name="Ext #", null=True, blank=True, default='')
    social_links = models.JSONField(null=False, blank=True, default=list)
    logo = models.ImageField(upload_to=manager_image_upload_path, blank=True, null=True, default=None)
    # facebook = models.URLField(max_length=254, verbose_name="Facebook", default='', blank=True, null=True)
    # instagram = models.URLField(max_length=254, verbose_name="Instagram", default='', blank=True, null=True)
    # tiktok = models.URLField(max_length=254, verbose_name="TikTok", default='', blank=True, null=True)
    # twitter = models.URLField(max_length=254, verbose_name="Twitter", default='', blank=True, null=True)
    # google_business = models.URLField(max_length=254, verbose_name="GoogleBusiness", default='', blank=True, null=True)
    # yelp = models.URLField(max_length=254, verbose_name="Yelp", default='', blank=True, null=True)

    company = models.OneToOneField(Company, on_delete=models.CASCADE, related_name='mdl')
    subscription = models.OneToOneField(Subscription, on_delete=models.CASCADE, related_name='mdl', default=None, blank=True, null=True)
    
    class Meta:
        ordering = ('company__name',)
        verbose_name = _('Manager Directory')
        verbose_name_plural = _('Manager Directories')

    def __str__(self):
        return self.company.name

    def save(self, *args, **kwargs):
        if not self.created or self.ref is None:
            try:
                if not self.created:
                    x = int(ManagerDirectory.objects.latest('created').ref[1:]) + 1
                else:
                    x = int(ManagerDirectory.objects.latest('updated').ref[1:]) + 1
            except (AttributeError, TypeError, ManagerDirectory.DoesNotExist):
                x = 1
            self.ref = f'M{x:05}'
            print(x,"  ", self.ref, "   ", self.id)
        return super(ManagerDirectory, self).save(*args, **kwargs)


class Office(TrackedModel):
    ref = models.CharField(max_length=16, verbose_name="Ref", unique=True)
    name = models.CharField(max_length=128, verbose_name="Name", db_index=True)
    country = models.CharField(max_length=128, verbose_name="Country", default="United States")
    street = models.CharField(max_length=254, verbose_name="Street", null=True, blank=True, default='')
    number = models.CharField(max_length=32, verbose_name="Number", null=True, blank=True, default='')
    city = models.ForeignKey(City, on_delete=models.CASCADE, verbose_name="City")
    zip_code = models.CharField(max_length=10, verbose_name="Zip Code", null=True, blank=True, default='')
    more_info = models.CharField(max_length=512, verbose_name="Additional Info", null=True, blank=True, default='')
    formatted = models.CharField(max_length=512, verbose_name="Formatted Address", null=True, blank=True, default='')
    # location = gis_model.PointField(null=True, blank=True, geography=True, spatial_index=True, srid=4326, dim=3)
    # location = gis_model.PointField(null=True, blank=True, geography=True, spatial_index=True, srid=4326)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='company_offices')
    administrator = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='administrative_offices', verbose_name="Admin")
    members = models.ManyToManyField(Profile, blank=True, related_name='offices')
    # pdls = models.ManyToManyField('Property', blank=False)
    
    class Meta:
        ordering = ('name',)
        verbose_name = _('Office')
        verbose_name_plural = _('Offices')

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.created:
            try:
                x = int(Office.objects.latest('created').ref[1:]) + 1
            except (AttributeError, TypeError, Office.DoesNotExist):
                x = 1
            self.ref = f'O{x:06}'
        return super(Office, self).save(*args, **kwargs)


class Outside(StampedModel):

    name = models.CharField(max_length=128, verbose_name="name", unique=True)
    icon = models.URLField(max_length=254, verbose_name="icon", default="https://rentmyvr.com/assets/images/amenties-svg/barn.svg")
    
    class Meta:
        ordering = ('name',)
        verbose_name = _('Outside')
        verbose_name_plural = _('Outside')

    def __str__(self):
        return self.name


class Parking(StampedModel):

    name = models.CharField(max_length=128, verbose_name="name", unique=True)
    icon = models.URLField(max_length=254, verbose_name="icon", default="https://rentmyvr.com/assets/images/amenties-svg/barn.svg")
    
    class Meta:
        ordering = ('name',)
        verbose_name = _('Parking')
        verbose_name_plural = _('Parking')

    def __str__(self):
        return self.name


class PoolSpa(StampedModel):

    name = models.CharField(max_length=128, verbose_name="name", unique=True)
    icon = models.URLField(max_length=254, verbose_name="icon", default="https://rentmyvr.com/assets/images/amenties-svg/barn.svg")
    
    class Meta:
        ordering = ('name',)
        verbose_name = _('Pool & Spa')
        verbose_name_plural = _('Pool & Spa')

    def __str__(self):
        return self.name
 

class Portfolio(TrackedModel):
    ref = models.CharField(max_length=16, verbose_name="Ref", unique=True)
    name = models.CharField(max_length=128, verbose_name="name")
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='company_portfolios')
    administrator = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='administrative_portfolios')
    members = models.ManyToManyField(Profile, blank=False, related_name='portfolios')
    # pdls = models.ManyToManyField('Property', blank=False)
    
    class Meta:
        unique_together = ('company', 'name')
        ordering = ('company__name', 'name')
        verbose_name = _('Portfolio')
        verbose_name_plural = _('Portfolios')

    def __str__(self):
        return self.name
  
    def save(self, *args, **kwargs):
        if not self.created:
            try:
                x = int(Portfolio.objects.latest('created').ref[1:]) + 1
            except (AttributeError, TypeError, Portfolio.DoesNotExist):
                x = 1
            self.ref = f'F{x:06}'
        return super(Portfolio, self).save(*args, **kwargs)

 
class Safety(StampedModel):

    name = models.CharField(max_length=64, verbose_name="name", unique=True)
    icon = models.URLField(max_length=254, verbose_name="icon", default="https://rentmyvr.com/assets/images/amenties-svg/barn.svg")
    
    class Meta:
        ordering = ('name',)
        verbose_name = _('Safety')
        verbose_name_plural = _('Safeties')

    def __str__(self):
        return self.name
    
 
class Sleeper(StampedModel):

    name = models.CharField(max_length=64, verbose_name="name", unique=True)
    icon = models.URLField(max_length=254, verbose_name="icon", default="https://rentmyvr.com/assets/images/amenties-svg/barn.svg")
    
    class Meta:
        ordering = ('name',)
        verbose_name = _('Sleeper')
        verbose_name_plural = _('Sleepers')

    def __str__(self):
        return self.name
    
  
class Space(StampedModel):

    name = models.CharField(max_length=64, verbose_name="name", unique=True)
    icon = models.URLField(max_length=254, verbose_name="icon", default="https://rentmyvr.com/assets/images/amenties-svg/barn.svg")
    
    class Meta:
        ordering = ('name',)
        verbose_name = _('Space')
        verbose_name_plural = _('Spaces')

    def __str__(self):
        return self.name
    

class Service(StampedModel):

    name = models.CharField(max_length=64, verbose_name="name", unique=True)
    icon = models.URLField(max_length=254, verbose_name="icon", default="https://rentmyvr.com/assets/images/amenties-svg/barn.svg")
    
    class Meta:
        ordering = ('name',)
        verbose_name = _('Service')
        verbose_name_plural = _('Services')

    def __str__(self):
        return self.name
 
  
class Property(StampedUpdaterModel):
    """
    Property model:
    """
    APARTMENT = 'apartment'
    BARN = 'barn'
    BED_AND_BREAKFAST = 'bed-and-breakfast'
    BOAT = 'boat'
    BUNGALOW = 'bungalow'
    BUS = 'bus'
    BUILDING = 'building-staff-24-7'
    CABIN = 'cabin'
    CAMPER = 'camper'
    CARAVAN = 'caravan'
    CASA_PARTICULARS = 'casa-particulars'
    CASITA = 'casita'
    CASTLE = 'castle'
    CAVE = 'cave'
    CHALET = 'chalet'
    CONDO = 'condo'
    # COTTA = 'cotta'
    COTTAGE = 'cottage'
    COUNTRY_HOUSE = 'country-house'
    # CSA = 'csa'
    CYCLADIC = 'cycladic'
    DUPLEX = 'duplex'
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
    HUT = 'hut'
    LIGHTHOUSE = 'lighthouse'
    LODGE = 'lodge'
    MANSION = 'mansion'
    MINSU = 'minsu'
    RESORT = 'resort'
    RIAD = 'riad'
    # ROOM = 'room'
    RV = 'rv'
    RYOKAN = 'ryokan'
    SHEPHERDS_HUT = 'shepherds-hut'
    SPECIALTY = 'specialty'
    STUDIO = 'studio'
    SUITE = 'suite'
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
                (APARTMENT, 'Apartment'),
                (BARN, 'Barn'),
                (BED_AND_BREAKFAST, 'Bed and Breakfast'),
                (BOAT, 'Boat'),
                (BUNGALOW, 'Bungalow'),
                (BUS, 'Bus'),
                (BUILDING, 'Building Staff 24/7'),
                (CABIN, 'Cabin'),
                (CAMPER, 'Camper'),
                (CARAVAN, 'Caravan'),
                (CASA_PARTICULARS, 'Casa Particulars'),
                (CASITA, 'Casita'),
                (CASTLE, 'Castle'),
                (CAVE, 'Cave'),
                (CHALET, 'Chalet'),
                (CONDO, 'Condo'),
                # (COTTA, 'Cotta'),
                (COTTAGE, 'Cottage'),
                (COUNTRY_HOUSE, 'Country House'),
                (CYCLADIC, 'Cycladic'),
                (DAMUSI, 'Damusi'),
                (DUPLEX, 'Duplex'),
                (EARTH_HOME, 'Earth Home'),
                (ESTATE, 'Estate'),
                (FARM_HOUSE, 'Farm House'),
                (GUEST_HOUSE, 'Guest House'),
                (HANOK, 'Hanok'),
                (HISTORIC_HOME, 'Historic Home'),
                (HOTEL, 'Hotel'),
                (HOUSE, 'House'),
                (HOUSEBOAT, 'Houseboat'),
                (HUT, 'Hut'),
                (LIGHTHOUSE, 'Lighthouse'),
                (LODGE, 'Lodge'),
                (MANSION, 'Mansion'),
                (MINSU, 'Minsu'),
                (RESORT, 'Resort'),
                (RIAD, 'Riad'),
                # (ROOM, 'Room'),
                (RV, 'RV'),
                (RYOKAN, 'Ryokan'),
                (SHEPHERDS_HUT, "Shepherd's Hut"),
                (SPECIALTY, 'Specialty'),
                (STUDIO, 'Studio'),
                (SUITE, 'Suite'),
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
        
        # ENTIRE_HOUSE = 'entire-house'
        # PARTIAL = 'partial'
        # PRIVATE_ROOM = 'private-room'
        # CASITA_SEP_GUEST_QUARTERS = 'casita-sep-guest-quarters'
        
        # BOOKED_SPACE = (
        #                 (CASITA_SEP_GUEST_QUARTERS, 'Casita/Sep Guest Quarters'),
        #                 (ENTIRE_HOUSE, 'Entire House'),
        #                 (PARTIAL, 'Partial'),
        #                 (PRIVATE_ROOM, 'Private Room'),
        #                 )
        
    ENTIRE_HOUSE = 'entire'
    LOWER = 'lower'
    PARTIAL = 'partial'
    UPPER = 'upper'
    PRIVATE_ROOM = 'room'
    # CASITA_SEP_GUEST_QUARTERS = 'casita-sep-guest-quarters'
    
    BOOKED_SPACE = ((ENTIRE_HOUSE, 'Entire'),
                    (LOWER, 'Lower'),
                    (PARTIAL, 'Partial'),
                    (PRIVATE_ROOM, 'Room'),
                    (UPPER, 'Upper'),
                    )
    
    KING_BED = 'king-bed'
    QUEEN_BED = 'queen-bed'
    DOUBLE_BED = 'double-bed'
    TWIN_SINGLE_BED = 'twin-single-bed'
    FUTON = 'futon'
    SOFA_SLEEPER = 'sofa-sleeper'
    COT = 'cot'
    TRUNDLE = 'trundle'
    BUNK_BED = 'bunk-bed'
    AIR_MATTRESS_FLOOR_MATTRESS = 'air-mattress-floor-mattress'
    
    SLEEPER_TYPES = (
        (KING_BED, 'King Bed'),
        (QUEEN_BED, 'Queen Bed'),
        (DOUBLE_BED, 'Double Bed'),
        (TWIN_SINGLE_BED, 'Twin/Single Bed'),
        (FUTON, 'Futon'),
        (SOFA_SLEEPER, 'Sofa Sleeper'),
        (COT, 'Cot'),
        (TRUNDLE, 'Trundle'),
        (BUNK_BED, 'Bunk Bed'),
        (AIR_MATTRESS_FLOOR_MATTRESS, 'Air Mattress/Floor Mattress')
    )
    
    STABILITY = (
        
    )
    
    ref = models.CharField(max_length=16, verbose_name="Ref", unique=True)
    name = models.CharField(max_length=254, verbose_name="Name") # db_index=False
    video = models.FileField(upload_to="property_video_upload_path", blank=True, null=True, default=None)
    virtual_tour = models.FileField(upload_to="property_video_upload_path", blank=True, null=True, default=None)
    is_active = models.BooleanField(verbose_name="Is Active", default=False)
    is_draft = models.BooleanField(verbose_name="is draft", default=False)
    is_published = models.BooleanField(verbose_name="is published", default=False)
    type = models.CharField(max_length=254, verbose_name="Type", choices=TYPES)
    space = models.CharField(max_length=254, verbose_name="Booked Space", choices=BOOKED_SPACE)
    hosted_by = models.CharField(max_length=254, verbose_name="Hosted By", blank=True, null=True, default=None)
    max_no_of_guest = models.IntegerField(verbose_name="Max No of Guest")
    no_of_bedrooms = models.IntegerField(verbose_name="No of Bedrooms")
    no_of_bathrooms = models.DecimalField(verbose_name="No of Bathrooms", max_digits=5, decimal_places=1, default=0.0)
    is_pet_allowed = models.BooleanField(default=True, )
    suitabilities = models.JSONField(default=list, blank=True, null=True)
    description = models.TextField(verbose_name="Description")
    host_note = models.TextField(verbose_name="Host Notes", default='', blank=True, null=True)
    cancellation_policy = models.TextField(verbose_name="Cancellation Policy", default='', blank=True, null=True)
    ical_url = models.URLField(verbose_name="iCal URL", default=None, blank=True, null=True)
    calendar = models.OneToOneField(Calendar, on_delete=models.SET_NULL, related_name="property", default=None, blank=True, null=True)
    # room_type = models.CharField(max_length=32, verbose_name="Room Type", choices=ROOM_TYPES)
    # sleeper_type = models.CharField(max_length=32, verbose_name="Sleeper Type", choices=SLEEPER_TYPES)
    
    price_night = models.DecimalField(verbose_name="Ave $ Per Night", max_digits=9, decimal_places=2, default=0.0)
    address = models.ForeignKey(Address, related_name='property_address', on_delete=models.CASCADE)
    hide_address = models.BooleanField(default=False, )
    hide_phone = models.BooleanField(default=False, )
    hide_email = models.BooleanField(default=False, )
    email = models.CharField(max_length=128, verbose_name="email", default='', blank=True, null=True)
    phone = models.CharField(max_length=16, verbose_name="phone", default='', blank=True, null=True)
    logo = models.ImageField(blank=True, null=True, default=None)
    
    accessibility = models.ManyToManyField(Accessibility, blank=True)
    activities = models.ManyToManyField(Activity, blank=True)
    bathrooms = models.ManyToManyField(Bathroom, blank=True)
    # booking_sites = models.ManyToManyField(BookingSite, blank=True)
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
    # social_media_links = models.ManyToManyField(SocialMediaLink, blank=True)
    spaces = models.ManyToManyField(Space, blank=True)
    services = models.ManyToManyField(Service, blank=True)
    
    calendar = models.ForeignKey(Calendar, on_delete=models.SET_NULL, related_name='properties', blank=True, null=True, default=None)
    company = models.ForeignKey(Company, on_delete=models.SET_NULL, related_name='properties', blank=True, null=True, default=None)
    administrator = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='administrative_properties', blank=True, null=True, default=None)
    office = models.ForeignKey(Office, on_delete=models.CASCADE, related_name='office_properties', blank=True, null=True, default=None)
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name='portfolio_properties', blank=True, null=True, default=None)
    subscription = models.OneToOneField(Subscription, on_delete=models.CASCADE, related_name='pdl', default=None, blank=True, null=True)
    
    imported = models.BooleanField(default=False, )
    import_id = models.CharField(max_length=128, verbose_name="import id", default='', blank=True, null=True)
    
    def save(self, *args, **kwargs):
        if not self.created:
            try:
                x = int(Property.objects.latest('created').ref[1:]) + 1
            except (AttributeError, TypeError, Property.DoesNotExist):
                x = 1
            self.ref = f'P{x:07}'
        return super(Property, self).save(*args, **kwargs)

    def __str__(self):
        return f"{self.name}"

    def get_admin_url(self):
        return reverse('admin:{}_{}_change'.format(self._meta.app_label, self._meta.model_name), args=(self.pk, ))

    class Meta:
        ordering = ('name', )
        managed = AUTO_MANAGE
        verbose_name = _('Property')
        verbose_name_plural = _('Properties')


class RoomType(StampedModel):
    
    BEDROOM = 'bedroom'
    CASITA = 'casita'
    DEN = 'den'
    OFFICE = 'office' 
    LIVING_ROOM = 'living-room'
    FAMILY_ROOM = 'family-room'
    LOFT = 'loft'
    STUDIO = 'studio'
    
    ROOM_TYPES = (
                    (BEDROOM, 'Bedroom'),
                    (CASITA, 'Casita'),
                    (DEN, 'Den'),
                    (OFFICE, 'Office'),
                    (LIVING_ROOM, 'Living Room'),
                    (FAMILY_ROOM, 'Family Room'),
                    (LOFT, 'Loft'),
                    (STUDIO, 'Studio')
                )
    
    name = models.CharField(max_length=32, verbose_name="Room Type", choices=ROOM_TYPES)
    sleepers = models.ManyToManyField(Sleeper, blank=True)
    property = models.ForeignKey(Property, verbose_name="Property", related_name="room_types", on_delete=models.CASCADE)
    
    class Meta:
        ordering = ('name',)
        verbose_name = _('Room Type')
        verbose_name_plural = _('Room Types')

    def __str__(self):
        return self.name
 
  
class PropertyPhoto(StampedUpdaterModel):
    # type = models.CharField(max_length=254, verbose_name="type", choices=Property.TYPES)
    property = models.ForeignKey(Property, verbose_name="Property", related_name="pictures", on_delete=models.CASCADE)
    image = models.ImageField(upload_to="property_image_upload_path")
    caption = models.CharField(max_length=256, verbose_name="caption", default='', blank=True, null=True) 
    is_default = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.image}"
        

class Booker(StampedModel):
    name = models.CharField(max_length=128, verbose_name="name", unique=True)
    base = models.CharField(max_length=256, verbose_name="base site", default='', blank=True, null=True)
    
    class Meta:
        ordering = ('name',)
        verbose_name = _('Booker')
        verbose_name_plural = _('Bookers')

    def __str__(self):
        return self.name


class BookingSite(StampedModel):
    booker = models.ForeignKey(Booker, verbose_name="Booker", related_name="bookers", on_delete=models.CASCADE)
    site = models.TextField(max_length=4096, verbose_name="site")
    property = models.ForeignKey(Property, verbose_name="Property", related_name="booking_sites", on_delete=models.CASCADE)
    
    class Meta:
        ordering = ('site',)
        verbose_name = _('Booking Site')
        verbose_name_plural = _('Booking Sites')

    def __str__(self):
        return self.booker.name


class SocialMediaLink(StampedModel):
    FACEBOOK = 'facebook'
    INSTAGRAM = 'instagram'
    TIKTOK = 'tiktok'
    YOUTUBE = 'youtube'
    TWITTER = 'twitter'
    GOOGLE_BUSINESS = 'google-business'
    YELP = 'yelp'
    PINTEREST = 'pinterest'

    MEDIAS = (
                (FACEBOOK, 'Facebook'),
                (INSTAGRAM, 'Instagram'),
                (TIKTOK, 'TikTok'),
                (YOUTUBE, 'YouTube'),
                (TWITTER, 'Twitter'),
                (GOOGLE_BUSINESS, 'GoogleBusiness'),
                (PINTEREST, 'Pinterest'),
                (YELP, 'Yelp')
            )

    name = models.CharField(max_length=24, verbose_name="name", choices=MEDIAS)
    site = models.TextField(max_length=1024, verbose_name="site")
    property = models.ForeignKey(Property, verbose_name="Property", related_name="social_media", on_delete=models.CASCADE)

    class Meta:
        ordering = ('name',)
        verbose_name = _('Social Media Link')
        verbose_name_plural = _('Social Media Links')

    def __str__(self):
        return self.name


class Support(StampedModel):
    MDL = 'mdl'
    PDL = 'pdl'
    OTHERS = 'others'
    TYPES = ((MDL, 'A Management Company Listing'), 
              (PDL, 'A Property Listing'),
              (OTHERS, 'Others'))
    TYPE = {MDL: TYPES[0][1], PDL: TYPES[1][1], OTHERS: TYPES[2][1]}
    
    ref = models.CharField(max_length=16, verbose_name="Ref", unique=True, blank=False, null=False)
    name = models.CharField(max_length=128, verbose_name="name", null=True, blank=True, default=None)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="supports", null=True, blank=True, default=None)
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="supports", null=True, blank=True, default=None)
    phone = models.CharField(max_length=128, verbose_name="phone", null=True, blank=True, default=None)
    type = models.CharField(max_length=128, choices=TYPES)
    message = models.TextField("message", null=True, blank=True, default=None)
    
    class Meta:
        ordering = ('type',)
        verbose_name = _('Support')
        verbose_name_plural = _('Support')

    def __str__(self):
        return self.message

    def save(self, *args, **kwargs):
        if not self.created:
            try:
                x = int(Support.objects.latest('created').ref[1:]) + 1
            except (AttributeError, TypeError, Support.DoesNotExist):
                x = 1
            self.ref = f'S{x:04}'
        return super(Support, self).save(*args, **kwargs)

  

