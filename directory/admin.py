from django.contrib import admin
from .models import *
from import_export import resources
from import_export.fields import Field
from import_export.admin import ImportExportModelAdmin
from import_export.widgets import ForeignKeyWidget


@admin.register(Accessibility)
class AccessibilityAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'enabled', 'created', 'updated')


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'enabled', 'created', 'updated')


@admin.register(Bathroom)
class BathroomAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'enabled', 'created', 'updated')


@admin.register(Booker)
class BookerAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'base', 'enabled', 'created', 'updated')


@admin.register(Entertainment)
class EntertainmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'enabled', 'created', 'updated')


@admin.register(Essential)
class EssentialAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'enabled', 'created', 'updated')


@admin.register(Family)
class FamilyAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'enabled', 'created', 'updated')


@admin.register(Feature)
class FeatureAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'enabled', 'created', 'updated')


@admin.register(Kitchen)
class KitchenAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'enabled', 'created', 'updated')


@admin.register(Laundry)
class LaundryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'enabled', 'created', 'updated')


@admin.register(Outside)
class OutsideAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'enabled', 'created', 'updated')


@admin.register(Parking)
class ParkingAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'enabled', 'created', 'updated')


@admin.register(PoolSpa)
class PoolSpaAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'enabled', 'created', 'updated')


class PropertyResource(resources.ModelResource):
    BOOKING_SITES = ['Direct Booking Site', 'AirBNB', 'VRBO', 'Booking.com', 'Booked.net', 'Rent By Owner', 'Additional Site', 'Additional Site', 'Additional Site', 'Agoda', 'Houfy', 'Trip.com', 'Expedia', 'Priceline', 'Orbitz', 'Travelocity', 'Tripadvisor', 'Bring Fido']
    SOCIAL_MEDIA = ['Facebook', 'Insta', 'Twitter', 'TikTok', 'Youtube', 'Yelp', 'Pinterest']
    
    # author = Field(column_name='Property Name', attribute='author', widget=ForeignKeyWidget(Address, field='name'))
    name = Field(column_name='Property Name', attribute='name')
    type = Field(column_name='Property Type', attribute='type')
    space = Field(column_name='Space Booked', attribute='space')
    no_of_bedrooms = Field(column_name='# of Bedrooms', attribute='no_of_bedrooms')
    no_of_bathrooms = Field(column_name='# of Bathrooms', attribute='no_of_bathrooms')
    max_no_of_guest = Field(column_name='Max # of Guests', attribute='max_no_of_guest')
    description = Field(column_name='Property Description', attribute='description')
    email = Field(column_name='Email', attribute='email')
    phone = Field(column_name='Phone', attribute='phone')
    hosted_by = Field(column_name='Hosted By', attribute='hosted_by')
    phone = Field(column_name='Phone', attribute='phone')
    phone = Field(column_name='Phone', attribute='phone')
    
    def __init__(self):
        self.address = None

    def before_save_instance(self, instance, using_transactions, dry_run):
        instance.address = self.address

    def before_import_row(self, row, **kwargs):
        number = row["House Number"]
        street = row["Street"]
        city_id = row["city_id"]
        zip_code = row["Zipcode"]
        more_info = row["Property Address"]
        country = row["Country"]
        imported = row["imported"]
        import_id = row["import_id"]
        (address, created) = Address.objects.get_or_create(name=number, defaults={"number": number, "street": street, "city_id": city_id, "zip_code": zip_code, "country": country, "more_info": more_info, "imported": imported, "import_id": import_id})
        self.address = address

    class Meta:
        model = Property
        fields = ('is_draft', 'name', 'author', 'price', 'type', 'space', 'hosted_by', 'max_no_of_guest', 'no_of_bedrooms', 'no_of_bathrooms', 'is_pet_allowed', )


class BookAdmin(ImportExportModelAdmin):
    resource_classes = [PropertyResource]

        
@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ('ref', 'name', 'video', 'virtual_tour', 'subscription', 'is_draft', 'type', 'space', 'hosted_by', 'max_no_of_guest', 'no_of_bedrooms', 'no_of_bathrooms', 'is_pet_allowed', 'suitabilities', 'price_night', 'address', 'email', 'phone', 'logo', 'enabled', 'created', 'updated')


@admin.register(RoomType)
class RoomTypeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'property', 'enabled', 'created', 'updated')


@admin.register(Safety)
class SafetyAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'enabled', 'created', 'updated')


@admin.register(Sleeper)
class SleeperAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'enabled', 'created', 'updated')


@admin.register(Space)
class SpaceAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'enabled', 'created', 'updated')


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'enabled', 'created', 'updated')


