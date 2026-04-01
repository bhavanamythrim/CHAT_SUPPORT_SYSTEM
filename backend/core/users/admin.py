from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import NotificationPreference, User, UserProfile

class UserAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Extra Info', {'fields': ('role', 'phone')}),
    )

    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Extra Info', {'fields': ('role', 'phone')}),
    )

admin.site.register(User, UserAdmin)
admin.site.register(NotificationPreference)
admin.site.register(UserProfile)
