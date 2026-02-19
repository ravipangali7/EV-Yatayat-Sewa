from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, SuperSetting, Wallet, Transaction, Card, PaymentTransaction


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
        ('License & Ticket Dealer', {'fields': ('license_no', 'license_image', 'license_type', 'license_expiry_date', 'is_ticket_dealer', 'ticket_commission')}),
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
    list_display = ('id', 'per_km_charge', 'gps_threshold_second', 'point_cover_radius', 'minute_coverage_schedule', 'created_at', 'updated_at')
    list_editable = ('per_km_charge', 'gps_threshold_second', 'point_cover_radius', 'minute_coverage_schedule')
    readonly_fields = ('created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    """Wallet admin"""
    list_display = ('id', 'user', 'balance', 'to_pay', 'to_receive', 'created_at', 'updated_at')
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


@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    """Card admin"""
    list_display = ('id', 'card_number', 'user', 'balance', 'is_active', 'created_at', 'updated_at')
    list_filter = ('is_active', 'created_at', 'updated_at')
    search_fields = ('card_number', 'user__username', 'user__phone')
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('user',)


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    """NCHL payment transaction admin"""
    list_display = ('id', 'reference_id', 'user', 'amount', 'status', 'purpose', 'created_at', 'completed_at')
    list_filter = ('status', 'purpose', 'created_at')
    search_fields = ('reference_id', 'user__username', 'user__phone')
    readonly_fields = ('created_at', 'updated_at', 'completed_at')
    raw_id_fields = ('user', 'card', 'vehicle_ticket_booking')
    list_select_related = ('user',)