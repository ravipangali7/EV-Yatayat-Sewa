from django.contrib import admin
from .models import (
    Slider, CMSPage, Team, Testimonial, Service, FAQ,
    ContactMessage, Blog, SiteSetting,
)


@admin.register(Slider)
class SliderAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'subtitle', 'is_active', 'created_at', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('title', 'subtitle')


@admin.register(CMSPage)
class CMSPageAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'slug', 'is_active', 'is_footer', 'is_header', 'is_about', 'section_in', 'created_at')
    list_filter = ('is_active', 'is_footer', 'is_header', 'is_about')
    search_fields = ('title', 'slug')
    prepopulated_fields = {'slug': ('title',)}


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'name', 'designation', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'designation', 'email')
    list_editable = ('order',)


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'star', 'is_active', 'created_at')
    list_filter = ('is_active', 'star')
    search_fields = ('name', 'message')


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'slug', 'order', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'slug')
    list_editable = ('order',)
    prepopulated_fields = {'slug': ('name',)}


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ('id', 'question', 'order', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('question',)
    list_editable = ('order',)


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'phone', 'is_read', 'created_at')
    list_filter = ('is_read',)
    search_fields = ('name', 'phone', 'message')
    list_editable = ('is_read',)


@admin.register(Blog)
class BlogAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'slug', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(SiteSetting)
class SiteSettingAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'tagline', 'created_at')
    search_fields = ('name', 'tagline')
