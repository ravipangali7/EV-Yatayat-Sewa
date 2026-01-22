from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, SuperSetting, Wallet, Transaction


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom User admin"""
    list_display = ('username', 'phone', 'name', 'email', 'is_driver', 'is_staff', 'is_superuser')
    list_filter = ('is_driver', 'is_staff', 'is_superuser', 'is_active')
    
    # Override fieldsets to exclude first_name and last_name
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('email', 'name')}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
        ('Additional Info', {'fields': ('phone', 'profile_picture', 'fcm_token', 'token', 'biometric_token', 'is_driver')}),
    )
    
    # Override add_fieldsets to exclude first_name and last_name
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'phone', 'password1', 'password2'),
        }),
        ('Additional Info', {'fields': ('name', 'email', 'is_driver')}),
    )


@admin.register(SuperSetting)
class SuperSettingAdmin(admin.ModelAdmin):
    """SuperSetting admin"""
    list_display = ('id', 'per_km_charge', 'created_at', 'updated_at')
    list_editable = ('per_km_charge',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    """Wallet admin"""
    list_display = ('id', 'user', 'balance', 'to_be_pay', 'to_be_received', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('user__username', 'user__phone', 'user__name')
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('user',)


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    """Transaction admin"""
    list_display = ('id', 'user', 'wallet', 'type', 'amount', 'status', 'balance_before', 'balance_after', 'created_at')
    list_filter = ('status', 'type', 'created_at')
    search_fields = ('user__username', 'user__phone', 'user__name', 'remarks')
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('user', 'wallet')
    date_hierarchy = 'created_at'