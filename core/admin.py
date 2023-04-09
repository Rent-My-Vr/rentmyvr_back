# from django.contrib import admin
from django.contrib import admin
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


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_filter = ('enabled', 'region', 'subregion', 'currency_name')
    list_display = ('name', 'capital', 'enabled', 'iso2', 'iso3', 'numeric_code', 'phone_code', 'currency', 'currency_name', 'currency_symbol', 'tld', 'native', 'region', 'subregion', 'latitude', 'longitude', 'emoji', 'emojiU')


@admin.register(State)
class StateAdmin(admin.ModelAdmin):
    list_filter = ('enabled', 'country_name')
    list_display = ('name', 'code', 'enabled', 'country_name', 'latitude', 'longitude')


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'email', 'phone', 'is_active', 'is_staff', 'is_superuser')
    # list_display = ("ref", "employment_type", "position", "status", "first_name", "last_name", "email", "phone", "is_active", "is_staff", "is_superuser", 'enabled', "address")

    @admin.display(ordering='first_name', description='First Name')
    def first_name(self, instance):
        return instance.user.first_name 

    @admin.display(ordering='last_name', description='Last Name')
    def last_name(self, instance):
        return instance.user.last_name 

    @admin.display(description='Email')
    def email(self, instance):
        return instance.user.email 

    @admin.display(description='Phone')
    def phone(self, instance):
        return instance.user.phone 

    @admin.display(description='is_active')
    def is_active(self, instance):
        return instance.user.is_active 

    @admin.display(description='Staff')
    def is_staff(self, instance):
        return instance.user.is_staff 

    @admin.display(description='Super Admin')
    def is_superuser(self, instance):
        return instance.user.is_superuser 

