from rest_framework import serializers
from .models import WalkieTalkieGroup, WalkieTalkieGroupMember, WalkieTalkieRecording
from django.conf import settings


class WalkieTalkieGroupSerializer(serializers.ModelSerializer):
    """List groups (with optional member count)."""
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = WalkieTalkieGroup
        fields = ('id', 'name', 'created_at', 'member_count')

    def get_member_count(self, obj):
        return getattr(obj, '_member_count', obj.members.count())


class WalkieTalkieGroupMemberSerializer(serializers.ModelSerializer):
    """List members of a group (user id and name)."""
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    user_name = serializers.CharField(source='user.name', read_only=True)
    user_phone = serializers.CharField(source='user.phone', read_only=True)

    class Meta:
        model = WalkieTalkieGroupMember
        fields = ('id', 'user_id', 'user_name', 'user_phone', 'joined_at')


class WalkieTalkieRecordingSerializer(serializers.ModelSerializer):
    """Create/list recording metadata (with user_name and user_avatar for list)."""
    user_name = serializers.SerializerMethodField()
    user_avatar = serializers.SerializerMethodField()

    class Meta:
        model = WalkieTalkieRecording
        fields = (
            'id', 'group', 'user', 'user_name', 'user_avatar',
            'started_at', 'ended_at', 'file_path', 'storage_key',
            'duration_seconds', 'file_size_bytes', 'sample_rate', 'created_at'
        )
        read_only_fields = ('id', 'created_at')

    def get_user_name(self, obj):
        if not obj.user:
            return None
        return getattr(obj.user, 'name', None) or getattr(obj.user, 'username', None) or f'User #{obj.user.id}'

    def get_user_avatar(self, obj):
        if not obj.user:
            return None
        pic = getattr(obj.user, 'profile_picture', None)
        if not pic:
            return None
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(pic.url)
        return pic.url if pic else None


class WalkieTalkieRecordingCreateSerializer(serializers.Serializer):
    """Payload for Node to create a recording (group_id, user_id, etc.)."""
    group_id = serializers.IntegerField()
    user_id = serializers.IntegerField()
    started_at = serializers.DateTimeField()
    ended_at = serializers.DateTimeField()
    file_path = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    storage_key = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    duration_seconds = serializers.FloatField(required=False, allow_null=True)
    file_size_bytes = serializers.IntegerField(required=False, allow_null=True)
    sample_rate = serializers.IntegerField(required=False, allow_null=True)
