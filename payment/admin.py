# from django.contrib import admin
from django.contrib import admin
from .models import *
from import_export import resources
from import_export.fields import Field
from import_export.admin import ImportExportModelAdmin
from import_export.widgets import ForeignKeyWidget




@admin.register(PriceChart)
class PriceChartAdmin(admin.ModelAdmin):
    list_filter = ('enabled', 'category', 'type')
    list_display = ('start', 'end', 'category', 'type', 'monthly_price', 'yearly_price', 'emails')
