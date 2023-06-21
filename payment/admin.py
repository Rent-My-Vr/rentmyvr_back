# from django.contrib import admin
from django.contrib import admin
from .models import *
from import_export import resources
from import_export.fields import Field
from import_export.admin import ImportExportModelAdmin
from import_export.widgets import ForeignKeyWidget




@admin.register(PaymentProfile)
class PaymentProfile(admin.ModelAdmin):
    list_filter = ('enabled', 'channel')
    list_display = ('external_ref', 'external_obj', 'channel', 'profile', 'enabled', 'created', 'updated')


@admin.register(PriceChart)
class PriceChartAdmin(admin.ModelAdmin):
    list_filter = ('enabled', 'category', 'type', 'service_type')
    list_display = ('start', 'end', 'type', 'category', 'service_type', 'monthly_price', 'yearly_price', 'emails')


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_filter = ('enabled', 'status', 'type')
    list_display = ('ref', 'external_ref', 'start_date', 'end_date', 'transaction', 'status', 'type', 'item', 'enabled', 'created', 'updated')


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_filter = ('enabled', 'channel', 'status', 'type', 'currency')
    list_display = ('ref', 'external_ref', 'quantity', 'unit_price', 'total', 'channel', 'status', 'type', 'currency', 'items', 'created', 'updated')
