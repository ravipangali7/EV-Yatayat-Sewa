import os
from django.http import FileResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authtoken.models import Token

from .models import WalkieTalkieGroup, WalkieTalkieGroupMember, WalkieTalkieRecording
from .serializers import (
    WalkieTalkieGroupSerializer,
    WalkieTalkieGroupMemberSerializer,
    WalkieTalkieRecordingSerializer,
    WalkieTalkieRecordingCreateSerializer,
)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def group_list_view(request):
    """List groups the current user is a member of."""
    memberships = WalkieTalkieGroupMember.objects.filter(user=request.user).select_related('group')
    groups = [m.group for m in memberships]
    for g in groups:
        g._member_count = g.members.count()
    serializer = WalkieTalkieGroupSerializer(groups, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def group_members_view(request, pk):
    """List members of a group. User must be a member of the group."""
    try:
        group = WalkieTalkieGroup.objects.get(pk=pk)
    except WalkieTalkieGroup.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
    if not WalkieTalkieGroupMember.objects.filter(group=group, user=request.user).exists():
        return Response({'detail': 'Not a member of this group.'}, status=status.HTTP_403_FORBIDDEN)
    members = WalkieTalkieGroupMember.objects.filter(group=group).select_related('user')
    serializer = WalkieTalkieGroupMemberSerializer(members, many=True)
    return Response(serializer.data)


def _get_user_from_token(token_key):
    """Resolve user from DRF Token key. Returns (user, None) or (None, error_response)."""
    if not token_key:
        return None, Response({'detail': 'Token required.'}, status=status.HTTP_401_UNAUTHORIZED)
    try:
        token = Token.objects.get(key=token_key)
        return token.user, None
    except Token.DoesNotExist:
        return None, Response({'detail': 'Invalid token.'}, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['GET'])
@permission_classes([AllowAny])
def validate_token_view(request):
    """
    Validate token and return user_id, username, group_ids.
    Accepts Authorization: Token <key> or query param ?token=<key>.
    Used by Node (and optionally Flutter) to validate and get group membership.
    """
    token_key = None
    auth = request.META.get('HTTP_AUTHORIZATION')
    if auth and auth.startswith('Token '):
        token_key = auth[6:].strip()
    if not token_key:
        token_key = request.query_params.get('token', '').strip()
    user, err = _get_user_from_token(token_key)
    if err:
        return err
    group_ids = list(
        WalkieTalkieGroupMember.objects.filter(user=user)
        .values_list('group_id', flat=True)
    )
    return Response({
        'user_id': user.id,
        'username': user.username,
        'name': getattr(user, 'name', None) or user.username,
        'group_ids': [str(gid) for gid in group_ids],
    })


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def recording_list_create_view(request):
    """
    GET: List recordings (filter by group_id, user_id). User sees only their groups' recordings.
    POST: Create recording metadata. Called by Node after saving a recording file.
    """
    if request.method == 'GET':
        qs = WalkieTalkieRecording.objects.filter(
            group__members__user=request.user
        ).select_related('group', 'user').distinct()
        group_id = request.query_params.get('group_id')
        if group_id:
            qs = qs.filter(group_id=group_id)
        user_id = request.query_params.get('user_id')
        if user_id:
            qs = qs.filter(user_id=user_id)
        qs = qs.order_by('-started_at')[:100]
        serializer = WalkieTalkieRecordingSerializer(qs, many=True)
        return Response(serializer.data)

    # POST: create recording
    serializer = WalkieTalkieRecordingCreateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    data = serializer.validated_data
    if data['user_id'] != request.user.id and not request.user.is_staff:
        return Response({'detail': 'Can only create recordings for yourself.'}, status=status.HTTP_403_FORBIDDEN)
    try:
        group = WalkieTalkieGroup.objects.get(pk=data['group_id'])
    except WalkieTalkieGroup.DoesNotExist:
        return Response({'detail': 'Group not found.'}, status=status.HTTP_404_NOT_FOUND)
    rec = WalkieTalkieRecording.objects.create(
        group=group,
        user_id=data['user_id'],
        started_at=data['started_at'],
        ended_at=data['ended_at'],
        file_path=data.get('file_path') or None,
        storage_key=data.get('storage_key') or None,
        duration_seconds=data.get('duration_seconds'),
        file_size_bytes=data.get('file_size_bytes'),
    )
    return Response(
        WalkieTalkieRecordingSerializer(rec).data,
        status=status.HTTP_201_CREATED
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def recording_play_view(request, pk):
    """Stream a recording file. User must be a member of the recording's group."""
    try:
        rec = WalkieTalkieRecording.objects.select_related('group').get(pk=pk)
    except WalkieTalkieRecording.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
    if not WalkieTalkieGroupMember.objects.filter(group=rec.group, user=request.user).exists():
        return Response({'detail': 'Not a member of this group.'}, status=status.HTTP_403_FORBIDDEN)
    if rec.file_path and os.path.isfile(rec.file_path):
        return FileResponse(
            open(rec.file_path, 'rb'),
            as_attachment=False,
            content_type='application/octet-stream',
            filename=os.path.basename(rec.file_path),
        )
    if rec.storage_key:
        return Response({'detail': 'Storage key playback not implemented.'}, status=status.HTTP_501_NOT_IMPLEMENTED)
    return Response({'detail': 'Recording file not found.'}, status=status.HTTP_404_NOT_FOUND)
