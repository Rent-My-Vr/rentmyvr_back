from django.contrib import admin
from .models import *
from .forms import *


@admin.register(InterestedEMail)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('email', 'enabled', 'updated', 'created')
