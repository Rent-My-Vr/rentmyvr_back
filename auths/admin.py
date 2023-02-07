from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission, Group
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.sites.shortcuts import get_current_site
from django.utils.translation import gettext, gettext_lazy as _
from django.contrib.auth.forms import UserCreationForm, UserChangeForm

from .forms import SignupForm, UserAdminUpdateForm
from .models import Audit, CustomGroup
UserModel = get_user_model()

@admin.register(UserModel)
class UserAdmin(DjangoUserAdmin):
    add_form = SignupForm
    form = UserAdminUpdateForm
    model = UserModel
    list_display = ['first_name', 'last_name', 'email', 'phone', 'position', 'email_verified', 'is_manager',
                    'is_staff', 'is_superuser', 'is_active', 'last_login_signature', 'failed_attempts', 'last_password_change']
    # list_display = ['email', 'username', 'phone', 'first_name', 'last_name', 'email_verified', 'last_login_signature',
    #                 'failed_attempts', 'last_password_change', 'force_password_change', 'avatar_url']
    list_max_show_all = settings.ADMIN_MAX_SHOW_ALL
    list_per_page = settings.ADMIN_PER_PAGE
    list_display_links = ('first_name', 'last_name', 'email',)

    list_filter = ('is_manager', 'is_staff', 'is_superuser', 'is_active', 'groups', 'force_password_change')
    search_fields = ('first_name', 'last_name', 'email', 'email_verified', 'last_login_signature')
    ordering = ('first_name', 'last_name', )
    readonly_fields = ('last_login', 'date_joined', 'last_password_change',)

    fieldsets = (
        (None, {'fields': ('email', 'password', 'position')}),
        # (_('Personal info'), {'fields': ('first_name', 'last_name', 'phone', 'avatar_image', 'avatar_thumbnail', 'avatar_url', 'timezone')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'phone', )}),
        (_('Permissions'), {'fields': ('is_active', 'email_verified', 'is_manager', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        (_('Important dates'), {'fields': ('last_login', 'last_password_change', 'date_joined')}),
    )
    prepopulated_fields = {'email': ('first_name', 'last_name',)}

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            # 'fields': ('first_name', 'last_name', 'email', 'password1', 'password2',),
            'fields': ('first_name', 'last_name', 'email'),
        }),
    )
    ordering = ('first_name',)

    def save_model(self, request, obj, form, change):
        is_new = False if obj.pk else True
        super().save_model(request, obj, form, change)
        if is_new:
            pwd = obj.password_generator(10)
            # obj.send_activation_link("{}://{}".format(request.scheme, get_current_site(request).domain), password=pwd)
            # obj.send_activation_link("{}://{}".format(request.scheme, request.META.get('HTTP_HOST', 'savvybiz.com')), password=pwd)
            obj.send_password_reset_link(f"{request.scheme}://{request.META.get('HTTP_HOST', 'savvybiz.com')}")
            obj.set_password(pwd)
            obj.save()


# @admin.register(UserModel)
# class UserAdmin(UserAdmin):
#     add_form = UserCreateForm
#     prepopulated_fields = {'username': ('first_name' , 'last_name', )}
#
#     add_fieldsets = (
#         (None, {
#             'classes': ('wide',),
#             'fields': ('first_name', 'last_name', 'username', 'password1', 'password2', ),
#         }),
#     )


@admin.register(Audit)
class AuditAdmin(admin.ModelAdmin):
    # add_form = CustomUserCreationForm
    # form = CustomUserChangeForm
    model = UserModel
    list_display = ['ip', 'session_key', 'created', 'last_seen', 'user', 'username', 'fingerprint', 'auth_backend',
                    'auth_status', 'session_status', 'browser', 'os', 'device', 'language', 'timezone']
    search_fields = ['ip', 'session_key', 'user', 'username', 'fingerprint', 'browser', 'os', 'language', 'timezone']

    date_hierarchy = 'created'
    list_filter = ('auth_backend', 'auth_status', 'session_status', 'browser', 'os')
    list_max_show_all = settings.ADMIN_MAX_SHOW_ALL
    list_per_page = settings.ADMIN_PER_PAGE


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    model = Permission
    list_display = ['name', 'content_type', 'codename']
    search_fields = ['name']
    list_max_show_all = settings.ADMIN_MAX_SHOW_ALL
    list_per_page = settings.ADMIN_PER_PAGE


@admin.register(CustomGroup)
class CustomGroupAdmin(admin.ModelAdmin):
    model = CustomGroup
    if settings.IS_MULTITENANT:
        list_display = ['name', 'company']
    else:
        list_display = ['name']
    search_fields = ['name']
    list_max_show_all = settings.ADMIN_MAX_SHOW_ALL
    list_per_page = settings.ADMIN_PER_PAGE

admin.site.unregister(Group)
