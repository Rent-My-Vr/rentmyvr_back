# from django.contrib import admin
from django.contrib import admin
from .models import *
from .forms import *


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ('street', 'number', 'city', 'zip_code', 'more_info', 'enabled')


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

