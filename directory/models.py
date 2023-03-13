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
    
    class Meta:
        ordering = ('name',)
        verbose_name = _('Accessibility')
        verbose_name_plural = _('Accessibility')


    def __str__(self):
        return self.name


class Activity(StampedModel):

    name = models.CharField(max_length=128, verbose_name="name", unique=True)
    
    class Meta:
        ordering = ('name',)
        verbose_name = _('Activity')
        verbose_name_plural = _('Activities')


    def __str__(self):
        return self.name


class Bathroom(StampedModel):

    name = models.CharField(max_length=128, verbose_name="name", unique=True)
    
    class Meta:
        ordering = ('name',)
        verbose_name = _('Bathroom')
        verbose_name_plural = _('Bathrooms')


    def __str__(self):
        return self.name


class Entertainment(StampedModel):

    name = models.CharField(max_length=128, verbose_name="name", unique=True)
    
    class Meta:
        ordering = ('name',)
        verbose_name = _('Entertainment')
        verbose_name_plural = _('Entertainments')


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

    name = models.CharField(max_length=128, verbose_name="name", unique=True)
    
    class Meta:
        ordering = ('name',)
        verbose_name = _('Kitchen')
        verbose_name_plural = _('Kitchens')


    def __str__(self):
        return self.name


class Laundry(StampedModel):

    name = models.CharField(max_length=128, verbose_name="name", unique=True)
    
    class Meta:
        ordering = ('name',)
        verbose_name = _('Laundry')
        verbose_name_plural = _('Laundries')


    def __str__(self):
        return self.name


class Outside(StampedModel):

    name = models.CharField(max_length=128, verbose_name="name", unique=True)
    
    class Meta:
        ordering = ('name',)
        verbose_name = _('Outside')
        verbose_name_plural = _('Outside')


    def __str__(self):
        return self.name


class Parking(StampedModel):

    name = models.CharField(max_length=128, verbose_name="name", unique=True)
    
    class Meta:
        ordering = ('name',)
        verbose_name = _('Parking')
        verbose_name_plural = _('Parking')


    def __str__(self):
        return self.name


class PoolSpa(StampedModel):

    name = models.CharField(max_length=128, verbose_name="name", unique=True)
    
    class Meta:
        ordering = ('name',)
        verbose_name = _('Pool & Spa')
        verbose_name_plural = _('Pool & Spa')


    def __str__(self):
        return self.name
 

class Portfolio(TrackedModel):

    name = models.CharField(max_length=128, verbose_name="name")
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='company_portfolios')
    properties = models.ManyToManyField('Property', blank=False)
    
    class Meta:
        unique_together = ('company', 'name')
        ordering = ('company__name', 'name')
        verbose_name = _('Portfolio')
        verbose_name_plural = _('Portfolios')


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
    
 
class Sleeper(StampedModel):

    name = models.CharField(max_length=64, verbose_name="name", unique=True)
    
    class Meta:
        ordering = ('name',)
        verbose_name = _('Sleeper')
        verbose_name_plural = _('Sleepers')


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
    HUT = 'hut'
    LIGHTHOUSE = 'lighthouse'
    LODGE = 'lodge'
    MANSION = 'mansion'
    MINSUS = 'minsus'
    RESORT = 'resort'
    RIAD = 'riad'
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
                (HUT, 'Hut'),
                (LIGHTHOUSE, 'Lighthouse'),
                (LODGE, 'Lodge'),
                (MANSION, 'Mansion'),
                (MINSUS, 'Minsus'),
                (RESORT, 'Resort'),
                (RIAD, 'Riad'),
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
    
    ENTIRE_HOUSE = 'entire-house'
    PRIVATE_ROOM = 'private-room'
    CASITA_SEP_GUEST_QUARTERS = 'casita-sep-guest-quarters'
    
    BOOKED_SPACE = ((ENTIRE_HOUSE, 'Entire House'),
                    (PRIVATE_ROOM, 'Private Room'),
                    (CASITA_SEP_GUEST_QUARTERS, 'Casita/Sep Guest Quarters'))
    
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
    name = models.CharField(max_length=254, verbose_name="Name")
    video = models.FileField(upload_to="property_video_upload_path", blank=True, null=True, default=None)
    virtual_tour = models.FileField(upload_to="property_video_upload_path", blank=True, null=True, default=None)
    type = models.CharField(max_length=254, verbose_name="Type", choices=TYPES)
    space = models.CharField(max_length=254, verbose_name="Booked Space", choices=BOOKED_SPACE)
    hosted_by = models.CharField(max_length=254, verbose_name="Hosted By", blank=True, null=True, default=None)
    max_no_of_guest = models.IntegerField(verbose_name="Max No of Guest")
    no_of_bedrooms = models.IntegerField(verbose_name="No of Bedrooms")
    no_of_bathrooms = models.IntegerField(verbose_name="No of Bathrooms")
    is_pet_allowed = models.BooleanField(default=True, )
    suitability = models.BooleanField(default=True, )
    description = models.TextField(verbose_name="Description")
    host_note = models.TextField(verbose_name="Host Notes", default='', blank=True, null=True)
    # room_type = models.CharField(max_length=32, verbose_name="Room Type", choices=ROOM_TYPES)
    # sleeper_type = models.CharField(max_length=32, verbose_name="Sleeper Type", choices=SLEEPER_TYPES)
    
    price_night = models.DecimalField(verbose_name="Ave $ Per Night", max_digits=9, decimal_places=2, default=0.0)
    address = models.ForeignKey(Address, related_name='property_address', on_delete=models.CASCADE)
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
    
    def save(self, *args, **kwargs):
        if not self.created:
            try:
                prop = Property.objects.latest('created')
                x = int(prop.ref[1:])
            except Property.DoesNotExist:
                x = 0
            x += 1
            self.ref = f'P{str(x).zfill(7)}'
        return super(Property, self).save(*args, **kwargs)

    def __str__(self):
        return self.name

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
    
    def __str__(self):
        return f'{self.type} ({self.property})'
        

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
    AIR_BNB = 'air-bnb'
    VRBO = 'vrbo'
    GOOGLE_VACATION_RENTAL = 'google-vacation-rental'
    FLIPKEY = 'flipkey'
    WINDMU = 'windmu'
    BOOKING = 'booking'
    EXPEDIA = 'expedia'
    HOUSETRIP = 'housetrip'
    RENT_BY_OWNER = 'rent-by-owner'
    HOLIDAY_LETTINGS = 'holidaylettings'
    TRAVELOKA = 'traveloka'
    TRIP = 'trip'
    AGODA = 'agoda'
    GLAMPING = 'glamping'
    DESPEGAR_DECOLAR = 'despegar-decolar'
    EDREAMS = 'edreams'
    PEGIPEGI = 'pegipegi'
    RAKUTEN = 'rakuten'
    RIPARIDE = 'riparide'
    ANYPLACE = 'anyplace'
    FURNITURE_FINDERS = 'furniturefinders'
    NINE_FLATS = '9flats'
    COLIVING = 'coliving'
    INSTANT_WORLD_BOOKING = 'instant-world-booking'
    ONLY_APARTMENTS = 'only-apartments'

    NAMES = (
                (AIR_BNB, 'Air BNB'),
                (VRBO, 'VRBO'),
                (GOOGLE_VACATION_RENTAL, 'Google Vacation Rental'),
                (FLIPKEY, 'Flipkey'),
                (WINDMU, 'Windmu'),
                (BOOKING, 'Booking.com'),
                (EXPEDIA, 'Expedia'),
                (HOUSETRIP, 'Housetrip'),
                (RENT_BY_OWNER, 'Rent By Owner'),
                (HOLIDAY_LETTINGS, 'HolidayLettings'),
                (TRAVELOKA, 'Traveloka'),
                (TRIP, 'Trip.com'),
                (AGODA, 'Agoda'),
                (GLAMPING, 'Glamping.com'),
                (DESPEGAR_DECOLAR, 'Despegar/Decolar'),
                (EDREAMS, 'eDreams'),
                (PEGIPEGI, 'PegiPegi'),
                (RAKUTEN, 'Rakuten'),
                (RIPARIDE, 'Riparide'),
                (ANYPLACE, 'Anyplace'),
                (FURNITURE_FINDERS, 'FurnitureFinders'),
                (NINE_FLATS, '9flats'),
                (COLIVING, 'Coliving.com'),
                (INSTANT_WORLD_BOOKING, 'Instant World Booking'),
                (ONLY_APARTMENTS, 'Only-Apartments')
                )

    name = models.CharField(max_length=24, verbose_name="name", choices=NAMES)
    site = models.URLField(max_length=254, verbose_name="site")
    property = models.ForeignKey(Property, verbose_name="Property", related_name="booking_sites", on_delete=models.CASCADE)
    
    class Meta:
        ordering = ('name',)
        verbose_name = _('Booking Site')
        verbose_name_plural = _('Booking Sites')

    def __str__(self):
        return self.name


class SocialMediaLink(StampedModel):
    FACEBOOK = 'facebook'
    INSTAGRAM = 'instagram'
    TIKTOK = 'tiktok'
    YOUTUBE = 'youtube'
    TWITTER = 'twitter'
    GOOGLE_BUSINESS = 'google-business'
    YELP = 'yelp'

    MEDIAS = (
                (FACEBOOK, 'Facebook'),
                (INSTAGRAM, 'Instagram'),
                (TIKTOK, 'TikTok'),
                (YOUTUBE, 'YouTube'),
                (TWITTER, 'Twitter'),
                (GOOGLE_BUSINESS, 'GoogleBusiness'),
                (YELP, 'Yelp')
            )

    name = models.CharField(max_length=24, verbose_name="name", choices=MEDIAS)
    site = models.URLField(max_length=254, verbose_name="site")
    property = models.ForeignKey(Property, verbose_name="Property", related_name="social_media", on_delete=models.CASCADE)

    class Meta:
        ordering = ('name',)
        verbose_name = _('Social Media Link')
        verbose_name_plural = _('Social Media Links')

    def __str__(self):
        return self.name

  

