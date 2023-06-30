from django.contrib import admin
from .models import *
from import_export import resources
from import_export.fields import Field
from import_export.admin import ImportExportModelAdmin
from import_export.widgets import ForeignKeyWidget


@admin.register(Accessibility)
class AccessibilityAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon', 'enabled', 'created', 'updated')


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon', 'enabled', 'created', 'updated')


@admin.register(Bathroom)
class BathroomAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon', 'enabled', 'created', 'updated')


@admin.register(Booker)
class BookerAdmin(admin.ModelAdmin):
    list_display = ('name', 'base', 'enabled', 'created', 'updated')


@admin.register(BookingSite)
class BookingSiteAdmin(admin.ModelAdmin):
    list_display = ('booker', 'site', 'property', 'enabled', 'created', 'updated')


@admin.register(Entertainment)
class EntertainmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon', 'enabled', 'created', 'updated')


@admin.register(Essential)
class EssentialAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon', 'enabled', 'created', 'updated')


@admin.register(Family)
class FamilyAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon', 'enabled', 'created', 'updated')


@admin.register(Feature)
class FeatureAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon', 'enabled', 'created', 'updated')


@admin.register(Kitchen)
class KitchenAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon', 'enabled', 'created', 'updated')


@admin.register(Laundry)
class LaundryAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon', 'enabled', 'created', 'updated')


@admin.register(ManagerDirectory)
class ManagerDirectoryAdmin(admin.ModelAdmin):
    search_fields = ('id', 'ref', 'name', 'email', 'website', 'contact_name', 'phone', 'company__name', 'company__ref', 'company__id', 'subscription__id', 'subscription__external_ref')
    list_filter = ('is_active', 'enabled', 'manage_for_others')
    list_display = ('ref', 'name', 'company', 'is_active', 'subscription', 'administrator', 'website', 'contact_name', 'email', 'phone', 'phone_2', 'ext_2', 'state', 'city', 'zip_code', 'manage_for_others', 'id', 'created', 'updated', 'description')

    @admin.display(ordering='name', description='Name')
    def name(self, instance):
        return instance.company.name 

    @admin.display(ordering='administrator', description='Administrator')
    def administrator(self, instance):
        return instance.company.administrator 

    @admin.display(description='Website')
    def website(self, instance):
        return instance.company.website 

    @admin.display(description='Contact Name')
    def contact_name(self, instance):
        return instance.company.contact_name 

    @admin.display(description='Email')
    def email(self, instance):
        return instance.company.email 

    @admin.display(description='Phone')
    def phone(self, instance):
        return f"{instance.company.phone}-{instance.company.ext}" if instance.company.ext else instance.company.phone

    @admin.display(description='Phone 2')
    def phone_2(self, instance):
        return f"{instance.company.phone_2}-{instance.company.ext_2}" if instance.company.ext_2 else instance.company.phone_2

    @admin.display(description='Description')
    def description(self, instance):
        return instance.company.description 

    # @admin.display(description='City')
    # def city(self, instance):
    #     return instance.company.city 

    @admin.display(description='State')
    def state(self, instance):
        return instance.company.state 


@admin.register(Office)
class OfficeAdmin(admin.ModelAdmin):
    list_display = ('ref', 'name', 'company', 'administrator', 'state', 'city', 'enabled', 'created', 'updated')
    
    @admin.display(description='State')
    def state(self, instance):
        return instance.city.state_name


@admin.register(Outside)
class OutsideAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon', 'enabled', 'created', 'updated')


@admin.register(Parking)
class ParkingAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon', 'enabled', 'created', 'updated')


@admin.register(PoolSpa)
class PoolSpaAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon', 'enabled', 'created', 'updated')


@admin.register(Portfolio)
class PortfolioAdmin(admin.ModelAdmin):
    list_filter = ('enabled', )
    list_display = ('ref', 'name', 'company', 'administrator', 'enabled', 'created', 'updated')
    

class PropertyResource(resources.ModelResource):
    BOOKING_SITES = ['Direct Booking', 'AirBNB', 'VRBO', 'Booking.com', 'Booked.net', 'Rent By Owner', 'Additional Site 1', 'Additional Site 2', 'Additional Site 3', 'Agoda', 'Houfy.com', 'Trip.com', 'Expedia', 'Priceline', 'Orbitz', 'Travelocity', 'Tripadvisor', 'Bring Fido']
    
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
    imported = Field(column_name='imported', attribute='imported')
    import_id = Field(column_name='property_id', attribute='import_id')
    
    def __init__(self):
        print("\n 111 ****  __init__(self) ")
        if not hasattr(self, 'address'):
            print(111)
            self.address = None
            self.bookings = []
            self.socials = []
        self.id = None

    def get_or_init_instance(self, instance_loader, row):
        # print("\n 222 **** get_or_init_instance(self)")
        instance = self.get_instance(instance_loader, row)
        # print("1 ", row)
        # print("2 ", instance_loader)
        # print("3 ", instance)
        # instance = (instance, False) if instance else (self.init_instance(row), True)
        # print("4 ", instance)
        # return instance
        if instance:
            return (instance, False)
        else:
            return (self.init_instance(row), True)
        
    def before_save_instance(self, instance, using_transactions, dry_run):
        # print(f"\n\n 444 **** {instance.id} before_save_instance(self): {self.id}")
        t = '--t--'
        s = '--s--'
        for k, v in Property.TYPES:
            if v == instance.type:
                instance.type = k
                t = k
        for k, v in Property.BOOKED_SPACE:
            if v == instance.space:
                instance.space = k
                s = k
        print( f"\n\n {self.id} **** {instance.type} ===> {t} :::: {instance.space} ===> {s}")
        # instance.id = self.id
        # print("1. ", self.address)
        # print("2. ", instance)
        # print("3. ", self.bookings)
        # print("4. ", self.socials)
        # for b in self.bookings:
        #     b.property = instance
        #     b.save()
        # for s in self.socials:
        #     s.property = instance
        #     s.save()
        # print("\n+++++++++")
        instance.address = self.address
        instance.updated_by_id = '6fc9383d-c476-4706-b6e2-a0752e0390b6'
   
    def after_save_instance(self, instance, using_transactions, dry_run):
        # print(f"\n\n 55555 **** {instance.id} after_save_instance()(self): {self.id}")
        # instance.id = self.id
        # print("1. ", self.address)
        # print(instance.id, "  ===== ", instance)
        # print("1. ", self.bookings)
        # print("2. ", self.socials)
        for b in self.bookings:
            b.property = instance
            b.save()
        for s in self.socials:
            s.property = instance
            s.save()
        # print("+++++++++\n")

    def before_import_row(self, row, **kwargs):
        # print("\n   555  **** before_import_row(self)")
        number = row["House Number"]
        street = row["Street"]
        city_id = row["city_id"]
        zip_code = row["Zipcode"]
        more_info = row["Property Address"]
        country = row["Country"]
        imported = row["imported"]
        import_id = row["import_id"]
        # print(".1\n\n\n", row)
        # defaults={"number": number, "street": street, "city_id": city_id, "zip_code": zip_code, "country": country, "more_info": more_info, "imported": imported, "import_id": import_id}
        (address, created) = Address.objects.get_or_create(number=number, street=street, city_id=city_id, zip_code=zip_code, country=country, more_info=more_info, imported=imported, import_id=import_id)
        self.address = address
        # print(".2", address)
        bookings = []
        socials = []
        for b in Booker.objects.filter(enabled=True):
            if row.get(b.name) and len(row[b.name].strip()) > 5:
                bookings.append(BookingSite(booker=b, site=row[b.name].strip()))
        for k,v in SocialMediaLink.MEDIAS:
            if row.get(v) and len(row[v].strip()) > 5:
                socials.append(SocialMediaLink(name=k, site=row[v].strip()))
        self.bookings = bookings
        self.socials = socials
         
    class Meta:
        model = Property
        fields = ('id', 'ref', 'is_draft', 'name', 'author', 'price', 'type', 'space', 'hosted_by', 'max_no_of_guest', 'no_of_bedrooms', 'no_of_bathrooms', 'is_pet_allowed', 'address', 'imported', 'import_id', 'created', 'updated')


@admin.register(InquiryMessage)
class InquiryMessageAdmin(admin.ModelAdmin):
    list_filter = ('enabled', )
    search_fields = ['name', 'email', 'phone', 'property__name', 'property__id', 'property__ref', 'subject', 'message']
    list_display = ('name', 'email', 'phone', 'property', 'enabled', 'subject', 'message', 'sent_time', 'created', 'updated')

        
@admin.register(Property)
class PropertyAdmin(ImportExportModelAdmin):
    resource_classes = [PropertyResource]
    search_fields = ['id','ref', 'name', 'type', 'space', 'hosted_by', 'suitabilities', 'price_night', 'email', 'phone', 'ical_url', 'subscription__external_ref', 'subscription__id', 'company__id', 'company__ref', 'company__name', 'administrator__id', 'administrator__ref', 'administrator__user__email', 'administrator__user__first_name', 'administrator__user__last_name', 'address__city__state_name', 'address__city__name', 'address__zip_code']
    list_filter = ('imported', 'enabled', 'is_active', 'is_published', 'is_draft', 'space', 'is_pet_allowed', 'type', )
    list_display = ('ref', 'name', 'company', 'administrator', 'subscription', 'video', 'virtual_tour', 'is_active', 'is_published', 'is_draft', 'calendar', 'ical_url', 'type', 'space', 'hosted_by', 'max_no_of_guest', 'no_of_bedrooms', 'no_of_bathrooms', 'is_pet_allowed', 'suitabilities', 'price_night', 'address', 'email', 'phone', 'id', 'logo', 'imported', 'enabled', 'created', 'updated', 'updated_by')
    

@admin.register(PropertyPhoto)
class PropertyPhotoAdmin(admin.ModelAdmin):
    list_filter = ('enabled', )
    search_fields = ['id','property__ref', 'property__name', 'image', ]
    list_display = ('property', 'enabled', 'index', 'image', 'created', 'updated')



@admin.register(RoomType)
class RoomTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'property', 'enabled', 'created', 'updated')


@admin.register(Safety)
class SafetyAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon', 'enabled', 'created', 'updated')


@admin.register(Sleeper)
class SleeperAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon', 'enabled', 'created', 'updated')


@admin.register(Space)
class SpaceAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon', 'enabled', 'created', 'updated')


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon', 'enabled', 'created', 'updated')


@admin.register(SocialMediaLink)
class SocialMediaLinkAdmin(admin.ModelAdmin):
    list_display = ('name', 'site', 'property', 'enabled', 'created', 'updated')


