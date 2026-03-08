from django.contrib import admin
from .models import WalkieTalkieGroup, WalkieTalkieGroupMember, WalkieTalkieRecording, AdminDriverVoiceMessage


class WalkieTalkieGroupMemberInline(admin.TabularInline):
    model = WalkieTalkieGroupMember
    extra = 0
    raw_id_fields = ('user',)


@admin.register(WalkieTalkieGroup)
class WalkieTalkieGroupAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'created_at')
    search_fields = ('name',)
    inlines = (WalkieTalkieGroupMemberInline,)


@admin.register(WalkieTalkieGroupMember)
class WalkieTalkieGroupMemberAdmin(admin.ModelAdmin):
    list_display = ('id', 'group', 'user', 'joined_at')
    list_filter = ('group',)
    raw_id_fields = ('group', 'user')
    search_fields = ('user__phone', 'user__name', 'group__name')


@admin.register(WalkieTalkieRecording)
class WalkieTalkieRecordingAdmin(admin.ModelAdmin):
    list_display = ('id', 'group', 'user', 'started_at', 'ended_at', 'duration_seconds')
    list_filter = ('group',)
    raw_id_fields = ('group', 'user')
    readonly_fields = ('started_at', 'ended_at', 'created_at')


@admin.register(AdminDriverVoiceMessage)
class AdminDriverVoiceMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'sender', 'recipient', 'duration_seconds', 'read_at', 'created_at')
    list_filter = ('created_at',)
    raw_id_fields = ('sender', 'recipient')
    readonly_fields = ('created_at',)
