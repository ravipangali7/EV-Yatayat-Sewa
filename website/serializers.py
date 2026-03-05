from rest_framework import serializers
from .models import (
    Slider, CMSPage, Team, Testimonial, Service, FAQ,
    ContactMessage, Blog, SiteSetting,
)


class SliderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Slider
        fields = [
            'id', 'title', 'subtitle', 'image', 'is_active',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class CMSPageSerializer(serializers.ModelSerializer):
    class Meta:
        model = CMSPage
        fields = [
            'id', 'title', 'slug', 'image', 'content',
            'is_active', 'is_footer', 'is_header', 'is_about', 'section_in',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class CMSPageChildSerializer(serializers.ModelSerializer):
    """Used for nested child_sections only (no further nesting)."""
    class Meta:
        model = CMSPage
        fields = [
            'id', 'title', 'slug', 'image', 'content',
            'is_active', 'is_footer', 'is_header', 'is_about', 'section_in',
            'created_at', 'updated_at',
        ]


class CMSPagePublicSerializer(serializers.ModelSerializer):
    child_sections = serializers.SerializerMethodField()

    def get_child_sections(self, obj):
        children = obj.child_sections.filter(is_active=True).order_by('id')
        return CMSPageChildSerializer(children, many=True).data

    class Meta:
        model = CMSPage
        fields = [
            'id', 'title', 'slug', 'image', 'content',
            'is_active', 'is_footer', 'is_header', 'is_about', 'section_in',
            'child_sections', 'created_at', 'updated_at',
        ]


class CMSPageListSerializer(serializers.ModelSerializer):
    class Meta:
        model = CMSPage
        fields = ['id', 'title', 'slug', 'is_active', 'is_footer', 'is_header', 'is_about', 'section_in']


class TeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = [
            'id', 'order', 'name', 'image', 'designation', 'phone', 'email', 'address',
            'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class TestimonialSerializer(serializers.ModelSerializer):
    class Meta:
        model = Testimonial
        fields = [
            'id', 'name', 'message', 'star', 'image', 'is_active',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = [
            'id', 'name', 'slug', 'svg', 'description', 'icon', 'order', 'is_active',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class FAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQ
        fields = [
            'id', 'question', 'answer', 'is_active', 'order',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ContactMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = [
            'id', 'name', 'phone', 'message', 'is_read',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'is_read']


class ContactMessageCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = ['name', 'phone', 'message']


class BlogSerializer(serializers.ModelSerializer):
    class Meta:
        model = Blog
        fields = [
            'id', 'name', 'slug', 'image', 'content', 'excerpt', 'category', 'is_active',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class SiteSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteSetting
        fields = [
            'id', 'logo', 'name', 'tagline', 'phones', 'emails', 'address', 'map',
            'cover_image', 'footer_text', 'stats',
            'about_image', 'about_title', 'about_content', 'mission', 'vision', 'values',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ReorderSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    order = serializers.IntegerField()
