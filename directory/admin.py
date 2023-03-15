# from django.contrib import admin
from django.contrib import admin
from .models import *


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


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ('ref', 'name', 'video', 'virtual_tour', 'subscription', 'is_draft', 'type', 'space', 'hosted_by', 'max_no_of_guest', 'no_of_bedrooms', 'no_of_bathrooms', 'is_pet_allowed', 'suitability', 'price_night', 'address', 'email', 'phone', 'logo', 'enabled', 'created', 'updated')


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


