from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.gis.admin import OSMGeoAdmin
from directory.models import ManagerDirectory
from .models import *
from .forms import *
from import_export import resources
from import_export.fields import Field
from import_export.admin import ImportExportModelAdmin
from import_export.widgets import ForeignKeyWidget


UserModel = get_user_model()

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
    search_fields = ['id', 'name', 'state_name', 'country_name']
    list_filter = ('enabled', 'imported', 'state_name', 'country_name', 'approved')
    list_display = ('name', 'state_name', 'country_name', 'approved', 'enabled', 'imported', 'import_id')


# class AddressResource(resources.ModelResource):
#     country = Field(column_name='Country', attribute='country')
#     street = Field(column_name='Street', attribute='street')
#     city = Field(column_name='city_id', attribute='city', widget=ForeignKeyWidget(City, field='id'))
#     number = Field(column_name='House Number', attribute='number')
#     zipcode = Field(column_name='Zipcode', attribute='zipcode')
#     more_info = Field(column_name='Property Address', attribute='more_info')
    
#     # def before_import_row(self, row, **kwargs):
#     #     name = row["city"]
#     #     state_name = row["state_name"]
#     #     City.objects.get_or_create(name=name, defaults={"name": name, "state_name": state_name, "country_name": "United States"})

#     class Meta:
#         model = Address
#         fields = ('country', 'street', 'city', 'number', 'zipcode', 'more_info', 'import_id')

# # https://realpython.com/location-based-app-with-geodjango-tutorial/#creating-a-django-model
@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
# # class AddressAdmin(ImportExportModelAdmin):
# class AddressAdmin(OSMGeoAdmin, ImportExportModelAdmin):
    # resource_classes = [AddressResource]
    search_fields = ['id', 'city__name', 'city__id', 'city__state_name', 'zip_code', 'country', 'formatted', 'import_id', 'more_info', 'street', 'number']
    list_filter = ('imported', 'enabled', 'hidden', 'city__state_name', 'import_id')
    list_display = ('number', 'street', 'city', 'state', 'zip_code', 'country', 'more_info', 'formatted', 'enabled', 'hidden', 'imported', 'import_id', 'location')

    @admin.display(ordering='city__state_name', description='State')
    def state(self, instance):
        return instance.city.state_name


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
        # print("\n 111 ****  __init__(self) ")
        self.skip_counter = 0
        self.mdl = None
        self.id = None
        self.skip = False
        self.updated_by = None

    def save_instance(self, instance, is_create, using_transactions=True, dry_run=False):
        """
        Takes care of saving the object to the database.
        Objects can be created in bulk if ``use_bulk`` is enabled.

        :param instance: The instance of the object to be persisted.
        :param is_create: A boolean flag to indicate whether this is a new object to be created, or an existing object to be updated.
        :param using_transactions: A flag to indicate whether db transactions are used.
        :param dry_run: A flag to indicate dry-run mode.
        """
        
        jump = False
        self.before_save_instance(instance, using_transactions, dry_run)
        if self._meta.use_bulk:
            if is_create:
                self.create_instances.append(instance)
            else:
                self.update_instances.append(instance)
        else:
            if not using_transactions and dry_run:
                # we don't have transactions and we want to do a dry_run
                pass
            else:
                try:
                    print(' ===>> ', instance.id)
                    instance.save()
                    jump = True
                except:
                    jump = False
        if jump:
            self.after_save_instance(instance, using_transactions, dry_run)
            

    def before_import_row(self, row, **kwargs):
        # print("\n   222  **** before_import_row(self)", kwargs)
        # print(row['Local'])
        # profile = Profile.objects.get(id=row['Local'])
        # print(' 22===> ', profile)
        user = kwargs['user']
        try:
            # print(f"\n\n22===> Attempt to this profile {profile.id} to Company already have and Administrative Company {profile.administrative_company} ({profile.administrative_company.id})")
            coy = Company.objects.get(name=row['Company Name'], state=City.objects.get(id=row['City ID']).state_name)
            self.skip = False
            self.skip_counter = self.skip_counter + 1
            print(f"\n\n Company => {coy} ({coy.id}) already exists")
        except Company.DoesNotExist:
            pass
            # except Profile.administrative_company.RelatedObjectDoesNotExist:
            # user.position = UserModel.ADMIN
            # user.save()
            # pass
        
        # print('+++++++++  ', row)
        self.mdl = ManagerDirectory()
        self.mdl.name = row['Company Name']
        self.mdl.status = ManagerDirectory.IMPORTED
        self.mdl.website = row['URL']
        self.mdl.contact_name = row['Contact Name']
        self.mdl.email = row['Email']
        self.mdl.phone = row['Phone']
        self.mdl.ext = row['Ext.#']
        self.mdl.street = row['Street Name and Unit']
        self.mdl.number = row['House Number']
        self.mdl.zip_code = row['Zip']
        self.mdl.phone_2 = row['Phone 2']
        self.mdl.social_links = []
 
        if row.get('FB') and len(row.get('FB')) > 8:
            self.mdl.social_links.append(row['FB'])
        if row.get('IG') and len(row.get('IG')) > 8:
            self.mdl.social_links.append(row['IG'])
        if row.get('TT') and len(row.get('TT')) > 8:
            self.mdl.social_links.append(row['TT'])
        self.mdl.updated_by = user
        # print(' 22===> Done!')
        
    def skip_row(self, instance, original, row, import_validation_errors=None):
        # def skip_row(self, instance, original, row, data):
        # print(" 333 ***** skip_row()", self.skip)
        if self.skip:
            print(self.skip_counter, ': Skipped  ***************  ===> ', instance.id, ' =>    ', row['Local'])
            return True

        return False
        # print(self)
        # print(instance)
        # print(original)
        # print(row)
        # print(data)
        # print("=======")
        # d = dict(row)
        # print(type(instance), "   ", type(original), " ", type(row), " ", type(data))
        # print(count > 0, "  ", d['id'])
        # return super().skip_row(instance, original, row, import_validation_errors=import_validation_errors)
    
    def before_save_instance(self, instance, using_transactions, dry_run):
        # print("\n 444 ***** before_save_instance()", self.id, "   ", instance.id)
        # instance.id = self.id
        # print(instance.name)
        instance.updated_by = self.mdl.updated_by
        instance.state = instance.city.state_name
        self.mdl.company = instance
        self.mdl.city = instance.city
        self.mdl.state = instance.city.state_name

    def after_save_instance(self, instance, using_transactions, dry_run):
        # print(f"\n 555 **** {instance.id} after_save_instance()(self): {self.id}")
        self.mdl.save()
        # print("1. ", self.address)
        # print(instance.id, "  ===== ", instance)
        # print("+++++++++\n")

    class Meta:
        model = Company
        skip_unchanged = False
        report_skipped = True
        fields = ('id', 'ref', 'name', 'administrator_id', 'website', 'contact_name', 'email', 'phone', 'ext', 'country','street', 'number', 'city_id', 'zip_code', 'updated_by')
        export_order = ('id', 'ref', 'name', 'administrator_id', 'website', 'contact_name', 'email', 'phone', 'ext', 'country','street', 'number', 'city_id', 'zip_code', 'updated_by')


@admin.register(Company)
class CompanyAdmin(ImportExportModelAdmin):
    resource_classes = [CompanyResource]
    search_fields = ('id', 'ref', 'name', 'email', 'website', 'contact_name', 'phone', 'mdl__name', 'mdl__ref', 'mdl__id', 'city__name', 'city__id', 
                     'state_obj__name', 'zip_code', 'state_obj__country__name', 'street', 'number')
    list_filter = ('enabled', 'state')
    list_display = ('ref', 'name', 'mdl', 'administrator', 'website', 'contact_name', 'email', 'phone', 'ext', 'city', 'address', 'created', 'updated', 'enabled')

    @admin.display(description='Phone')
    def phone(self, instance):
        return f"{instance.company.phone}-{instance.company.ext}" if instance.company.ext else instance.company.phone

    @admin.display(description='Address')
    def address(self, i):
        street = f'{i.number} {i.street}, ' if i.number and i.street else f'{i.street}, ' if i.street else ''
        zip = f' {i.zip_code}, ' if i.zip_code else ', '
        return '{}{}, {}{}{}'.format(street, i.city.name, i.state_obj.name, zip, i.state_obj.country.iso3)


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_filter = ('enabled', 'region', 'subregion', 'currency_name')
    list_display = ('name', 'capital', 'enabled', 'iso2', 'iso3', 'numeric_code', 'phone_code', 'currency', 'currency_name', 'currency_symbol', 'tld', 'native', 'region', 'subregion', 'latitude', 'longitude', 'emoji', 'emojiU')


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_filter = ('enabled', 'company')
    list_display = ('email', 'sent', 'token', 'status', 'company', 'sender', 'created', 'updated')


@admin.register(State)
class StateAdmin(admin.ModelAdmin):
    search_fields = ('id', 'name', 'code', 'enabled', 'latitude', 'longitude', )
    list_filter = ('enabled', 'country__name')
    list_display = ('name', 'code', 'enabled', 'country', 'latitude', 'longitude')


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display_links = ('first_name', 'last_name', 'email',)
    list_filter = ('user__is_manager', 'user__position', 'user__is_staff', 'user__is_superuser', 'user__is_active', 'user__email_verified', 'user__position', 'company', )
    search_fields = ('id', 'user__id', 'user__first_name', 'user__last_name', 'user__email', 'user__phone', 'company__name', 'city__name', 'city__id', 'state__name', 'zip_code', 'state__country__name', 'formatted', 'import_id', 'more_info', 'street', 'number')
    list_display = ('first_name', 'last_name', 'email', 'phone', 'company', 'address', 'is_manager', 'position', 'is_staff', 'is_superuser', 'is_active', 'image', 'created', 'updated')
    
    @admin.display(description='Address')
    def address(self, i):
        street = f'{i.number} {i.street}, ' if i.number and i.street else f'{i.street}, ' if i.street else ''
        zip = f' {i.zip_code}, ' if i.zip_code else ', '
        return '{}{}, {}{}{}'.format(street, i.city.name, i.state.name, zip, i.state.country.iso3)

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

    @admin.display(ordering='user__is_manager', description='is_manager')
    def is_manager(self, instance):
        return instance.user.is_manager 

    @admin.display(ordering='user__position', description='position')
    def position(self, instance):
        return instance.user.position 

    @admin.display(ordering='user__is_staff', description='Staff')
    def is_staff(self, instance):
        return instance.user.is_staff 

    @admin.display(ordering='user__is_superuser', description='Super Admin')
    def is_superuser(self, instance):
        return instance.user.is_superuser 

    @admin.display(ordering='user__is_active', description='is_active')
    def is_active(self, instance):
        return instance.user.is_active 

    @admin.display(ordering='user__email_verified', description='email_verified')
    def email_verified(self, instance):
        return instance.user.email_verified 

    @admin.display(ordering='user__position', description='position')
    def position(self, instance):
        return instance.user.position 

