# from django.contrib import admin
from django.contrib import admin
from directory.models import ManagerDirectory
from .models import *
from .forms import *
from import_export import resources
from import_export.fields import Field
from import_export.admin import ImportExportModelAdmin
from import_export.widgets import ForeignKeyWidget



class CityResource(resources.ModelResource):
    name = Field(attribute='name', column_name='City')
    state_name = Field(attribute='state_name', column_name='State')
    country_name = Field(attribute='country_name', column_name='Country')
    
    name = Field(attribute='name', column_name='City')
    
    def __init__(self):
        self.id = None

    def before_save_instance(self, instance, using_transactions, dry_run):
        instance.id = self.id

    def skip_row(self, instance, original, row, data):
        # print("\n\n")
        # print(self)
        # print(instance)
        # print(original)
        # print(row)
        # print(data)
        # print("=======")
        d = dict(row)
        # print(type(instance), "   ", type(original), " ", type(row), " ", type(data))
        count = City.objects.filter(name=d['City'], state_name=d['State'], country_name=d['Country']).count()
        # print(count > 0, "  ", d['id'])
        return count > 0;
    
    class Meta:
        model = City
        fields = ('id', 'state_name', 'name', 'imported', 'import_id', 'country_name',)
        export_order = ('id', 'name', 'state_name', 'country_name', 'imported', 'import_id')


@admin.register(City)
class CityAdmin(ImportExportModelAdmin):
    resource_classes = [CityResource]
    list_filter = ('enabled', 'imported', 'state_name', 'country_name', 'approved')
    list_display = ('name', 'state_name', 'country_name', 'approved', 'enabled', 'imported', 'import_id')


class AddressResource(resources.ModelResource):
    country = Field(column_name='Country', attribute='country')
    street = Field(column_name='Street', attribute='street')
    city = Field(column_name='city_id', attribute='city', widget=ForeignKeyWidget(City, field='id'))
    number = Field(column_name='House Number', attribute='number')
    zipcode = Field(column_name='Zipcode', attribute='zipcode')
    more_info = Field(column_name='Property Address', attribute='more_info')
    
    # def before_import_row(self, row, **kwargs):
    #     name = row["city"]
    #     state_name = row["state_name"]
    #     City.objects.get_or_create(name=name, defaults={"name": name, "state_name": state_name, "country_name": "United States"})

    class Meta:
        model = Address
        fields = ('country', 'street', 'city', 'number', 'zipcode', 'more_info', 'import_id')


@admin.register(Address)
class AddressAdmin(ImportExportModelAdmin):
    resource_classes = [AddressResource]
    list_filter = ('imported', 'enabled', 'city__state_name')
    list_display = ('street', 'number', 'city', 'zip_code', 'hidden', 'formatted', 'location', 'more_info', 'enabled', 'imported', 'import_id')


class CompanyResource(resources.ModelResource):
    name = Field(attribute='name', column_name='Company Name')
    website = Field(attribute='website', column_name='URL')
    contact_name = Field(attribute='contact_name', column_name='Contact Name')
    email = Field(attribute='email', column_name='Email')
    phone = Field(attribute='phone', column_name='Phone')
    ext = Field(attribute='ext', column_name='Ext.#')
    street = Field(attribute='street', column_name='Street Name and Unit')
    number = Field(attribute='number', column_name='House Number')
    city_id = Field(attribute='city_id', column_name='City ID')
    zip_code = Field(attribute='zip_code', column_name='Zip')
    administrator_id = Field(attribute='administrator_id', column_name='Local')
    
    def __init__(self):
        print("\n 111 ****  __init__(self) ")
        self.mdl = None
        self.id = None
        self.skip = False
        self.updated_by = None

    def before_save_instance(self, instance, using_transactions, dry_run):
        print("\n 333 ***** before_save_instance()", self.id, "   ", instance.id)
        # instance.id = self.id
        print(instance.name)
        instance.updated_by = self.updated_by
        self.mdl.company = instance
        self.mdl.updated_by = self.updated_by

    def after_save_instance(self, instance, using_transactions, dry_run):
        print(f"\n 4444 **** {instance.id} after_save_instance()(self): {self.id}")
        self.mdl.save()
        # print("1. ", self.address)
        # print(instance.id, "  ===== ", instance)
        # print("+++++++++\n")

    def before_import_row(self, row, **kwargs):
        # print("\n   555  **** before_import_row(self)", kwargs)
        profile = Profile.objects.get(id=row['Local'])
        try:
            print(f"This profile {profile.id} already have and Administrative Company {profile.administrative_company} ({profile.administrative_company.id})")
            self.skip = True
        except Profile.administrative_company.RelatedObjectDoesNotExist:
            pass
        mdl = ManagerDirectory()
        mdl.phone_2 = row['Phone 2']
        mdl.instagram = row['IG']
        mdl.facebook = row['FB']
        mdl.tiktok = row['TT']
        self.mdl = mdl
        self.updated_by = kwargs.get('user')
        
    def skip_row(self, instance, original, row, data):
        print(" 666 ***** skip_row()")
        return self.skip
    #     # print(self)
    #     # print(instance)
    #     # print(original)
    #     # print(row)
    #     # print(data)
    #     # print("=======")
    #     d = dict(row)
    #     # print(type(instance), "   ", type(original), " ", type(row), " ", type(data))
    #     # print(count > 0, "  ", d['id'])
    #     return False;
    
    class Meta:
        model = Company
        fields = ('id', 'ref', 'name', 'administrator_id', 'website', 'contact_name', 'email', 'phone', 'ext', 'country','street', 'number', 'city_id', 'zip_code', 'updated_by')
        export_order = ('id', 'ref', 'name', 'administrator_id', 'website', 'contact_name', 'email', 'phone', 'ext', 'country','street', 'number', 'city_id', 'zip_code', 'updated_by')


@admin.register(Company)
class CompanyAdmin(ImportExportModelAdmin):
    resource_classes = [CompanyResource]
    search_fields = ('ref', 'name', 'email', 'website', 'contact_name', 'phone', 'mdl__name', 'mdl__ref')
    list_filter = ('city', 'state')
    list_display = ('ref', 'name', 'mdl', 'administrator', 'website', 'contact_name', 'email', 'phone', 'ext', 'city', 'state')

    @admin.display(description='Phone')
    def phone(self, instance):
        return f"{instance.company.phone}-{instance.company.ext}" if instance.company.ext else instance.company.phone


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_filter = ('enabled', 'region', 'subregion', 'currency_name')
    list_display = ('name', 'capital', 'enabled', 'iso2', 'iso3', 'numeric_code', 'phone_code', 'currency', 'currency_name', 'currency_symbol', 'tld', 'native', 'region', 'subregion', 'latitude', 'longitude', 'emoji', 'emojiU')


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_filter = ('enabled', 'company')
    list_display = ('email', 'sent', 'token', 'status', 'company', 'sender')


@admin.register(State)
class StateAdmin(admin.ModelAdmin):
    list_filter = ('enabled', 'country_name')
    list_display = ('name', 'code', 'enabled', 'country_name', 'latitude', 'longitude')


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display_links = ('first_name', 'last_name', 'email',)
    list_filter = ('company', )
    search_fields = ('user__first_name', 'user__last_name', 'user__email', 'user__phone', 'company__name')
    list_display = ('first_name', 'last_name', 'email', 'phone', 'company', 'is_active', 'is_staff', 'is_superuser', 'image')
    # list_display = ("ref", "employment_type", "position", "status", "first_name", "last_name", "email", "phone", "is_active", "is_staff", "is_superuser", 'enabled', "address")

    @admin.display(ordering='user__first_name', description='First Name')
    def first_name(self, instance):
        return instance.user.first_name 

    @admin.display(ordering='user__last_name', description='Last Name')
    def last_name(self, instance):
        return instance.user.last_name 

    @admin.display(ordering='user__email', description='Email')
    def email(self, instance):
        return instance.user.email 

    @admin.display(ordering='user__phone', description='Phone')
    def phone(self, instance):
        return instance.user.phone 

    @admin.display(ordering='user__is_active', description='is_active')
    def is_active(self, instance):
        return instance.user.is_active 

    @admin.display(ordering='user__is_staff', description='Staff')
    def is_staff(self, instance):
        return instance.user.is_staff 

    @admin.display(ordering='user__is_superuser', description='Super Admin')
    def is_superuser(self, instance):
        return instance.user.is_superuser 

