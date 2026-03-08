import os
from django.db.models import Q
from django.http import FileResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authtoken.models import Token

from django.utils import timezone
from core.models import User
from .models import WalkieTalkieGroup, WalkieTalkieGroupMember, WalkieTalkieRecording, AdminDriverVoiceMessage
from .serializers import (
    WalkieTalkieGroupSerializer,
    WalkieTalkieGroupMemberSerializer,
    WalkieTalkieRecordingSerializer,
    WalkieTalkieRecordingCreateSerializer,
    AdminDriverVoiceMessageSerializer,
    AdminDriverVoiceMessageCreateSerializer,
)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def group_list_view(request):
    """List groups for the current user. Staff see all groups; others see only groups they are a member of."""
    if getattr(request.user, 'is_staff', False):
        groups = list(WalkieTalkieGroup.objects.all().order_by('name'))
    else:
        memberships = (
            WalkieTalkieGroupMember.objects.filter(user=request.user)
            .select_related('group')
            .order_by('group__name')
        )
        groups = [m.group for m in memberships]
    for g in groups:
        g._member_count = g.members.count()
    serializer = WalkieTalkieGroupSerializer(groups, many=True)
    data = list(serializer.data)
    return Response(data)


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
    if getattr(user, 'is_staff', False):
        group_ids = [str(g['id']) for g in WalkieTalkieGroup.objects.all().values('id')]
    else:
        group_ids = list(
            WalkieTalkieGroupMember.objects.filter(user=user)
            .values_list('group_id', flat=True)
        )
        group_ids = [str(gid) for gid in group_ids]
    if getattr(user, 'is_driver', False):
        group_ids.append(f'direct:{user.id}')
        admin_ids = User.objects.filter(Q(is_staff=True) | Q(is_superuser=True)).values_list('id', flat=True)
        group_ids.extend(f'direct:{aid}' for aid in admin_ids)
    if getattr(user, 'is_staff', False) or getattr(user, 'is_superuser', False):
        group_ids.append(f'direct:{user.id}')
    return Response({
        'user_id': user.id,
        'username': user.username,
        'name': getattr(user, 'name', None) or user.username,
        'group_ids': group_ids,
        'is_superuser': getattr(user, 'is_superuser', False),
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def drivers_list_view(request):
    """List drivers for superuser (for direct PTT)."""
    if not getattr(request.user, 'is_superuser', False):
        return Response({'detail': 'Superuser only.'}, status=status.HTTP_403_FORBIDDEN)
    drivers = User.objects.filter(is_driver=True).order_by('name', 'username')
    out = []
    for u in drivers:
        avatar = None
        if getattr(u, 'profile_picture', None) and u.profile_picture:
            avatar = request.build_absolute_uri(u.profile_picture.url)
        out.append({
            'id': u.id,
            'name': getattr(u, 'name', None) or u.username,
            'avatar': avatar,
        })
    return Response(out)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admins_list_view(request):
    """List admins (staff/superuser) for drivers (for direct PTT to admin)."""
    if not getattr(request.user, 'is_driver', False):
        return Response({'detail': 'Drivers only.'}, status=status.HTTP_403_FORBIDDEN)
    admins_qs = User.objects.filter(Q(is_staff=True) | Q(is_superuser=True)).order_by('name', 'username')
    out = []
    for u in admins_qs:
        avatar = None
        if getattr(u, 'profile_picture', None) and u.profile_picture:
            avatar = request.build_absolute_uri(u.profile_picture.url)
        out.append({
            'id': u.id,
            'name': getattr(u, 'name', None) or u.username,
            'avatar': avatar,
        })
    return Response(out)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def recording_list_create_view(request):
    """
    GET: List recordings (filter by group_id, user_id). User sees only their groups' recordings.
    POST: Create recording metadata. Called by Node after saving a recording file.
    """
    if request.method == 'GET':
        if getattr(request.user, 'is_staff', False):
            qs = WalkieTalkieRecording.objects.all().select_related('group', 'user')
        else:
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
        serializer = WalkieTalkieRecordingSerializer(qs, many=True, context={'request': request})
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
        sample_rate=data.get('sample_rate'),
    )
    return Response(
        WalkieTalkieRecordingSerializer(rec).data,
        status=status.HTTP_201_CREATED
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def recording_play_view(request, pk):
    """Stream a recording file. User must be a member of the recording's group."""
    from django.conf import settings
    try:
        rec = WalkieTalkieRecording.objects.select_related('group').get(pk=pk)
    except WalkieTalkieRecording.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
    if not WalkieTalkieGroupMember.objects.filter(group=rec.group, user=request.user).exists():
        return Response({'detail': 'Not a member of this group.'}, status=status.HTTP_403_FORBIDDEN)
    if rec.file_path:
        base_dir = os.path.abspath(settings.WALKIETALKIE_RECORDINGS_DIR)
        is_absolute = rec.file_path.startswith(('/', '\\'))
        if is_absolute:
            full_path = os.path.normpath(rec.file_path)
            if not full_path.startswith(base_dir):
                return Response({'detail': 'Recording file not found.'}, status=status.HTTP_404_NOT_FOUND)
        else:
            safe_path = os.path.normpath(rec.file_path.replace('\\', '/')).lstrip('/')
            if '..' in safe_path:
                return Response({'detail': 'Invalid file path.'}, status=status.HTTP_400_BAD_REQUEST)
            full_path = os.path.normpath(os.path.join(base_dir, safe_path))
            if not full_path.startswith(base_dir):
                return Response({'detail': 'Invalid file path.'}, status=status.HTTP_400_BAD_REQUEST)
        if os.path.isfile(full_path):
            return FileResponse(
                open(full_path, 'rb'),
                as_attachment=False,
                content_type='application/octet-stream',
                filename=os.path.basename(full_path),
            )
    if rec.storage_key:
        return Response({'detail': 'Storage key playback not implemented.'}, status=status.HTTP_501_NOT_IMPLEMENTED)
    return Response({'detail': 'Recording file not found.'}, status=status.HTTP_404_NOT_FOUND)


def _resolve_direct_message_file_path(msg, base_dir):
    """Resolve file path for AdminDriverVoiceMessage; return (full_path, error_response or None)."""
    if not msg.file_path:
        return None, Response({'detail': 'Recording file not found.'}, status=status.HTTP_404_NOT_FOUND)
    safe_path = os.path.normpath(msg.file_path.replace('\\', '/')).lstrip('/')
    if '..' in safe_path:
        return None, Response({'detail': 'Invalid file path.'}, status=status.HTTP_400_BAD_REQUEST)
    full_path = os.path.normpath(os.path.join(base_dir, safe_path))
    if not full_path.startswith(base_dir):
        return None, Response({'detail': 'Invalid file path.'}, status=status.HTTP_400_BAD_REQUEST)
    if not os.path.isfile(full_path):
        return None, Response({'detail': 'Recording file not found.'}, status=status.HTTP_404_NOT_FOUND)
    return full_path, None


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def direct_message_list_create_view(request):
    """
    GET: List direct voice messages. Query params: driver_id (admin sees messages with that driver),
         recipient=me (driver sees messages where they are recipient).
    POST: Create direct message (called by Node after saving PCM for direct PTT).
    """
    if request.method == 'GET':
        user = request.user
        is_staff = getattr(user, 'is_staff', False)
        driver_id = request.query_params.get('driver_id')
        recipient_me = request.query_params.get('recipient') == 'me'

        if is_staff and driver_id:
            try:
                driver_id = int(driver_id)
            except (TypeError, ValueError):
                return Response({'detail': 'Invalid driver_id.'}, status=status.HTTP_400_BAD_REQUEST)
            qs = AdminDriverVoiceMessage.objects.filter(
                Q(sender=user) | Q(recipient=user)
            ).filter(
                Q(sender_id=driver_id) | Q(recipient_id=driver_id)
            ).select_related('sender', 'recipient').order_by('-created_at')[:100]
        elif recipient_me:
            qs = AdminDriverVoiceMessage.objects.filter(
                Q(sender=user) | Q(recipient=user)
            ).select_related('sender', 'recipient').order_by('-created_at')[:100]
        elif is_staff:
            qs = AdminDriverVoiceMessage.objects.all().select_related('sender', 'recipient').order_by('-created_at')[:100]
        else:
            qs = AdminDriverVoiceMessage.objects.filter(
                Q(sender=user) | Q(recipient=user)
            ).select_related('sender', 'recipient').order_by('-created_at')[:100]
        serializer = AdminDriverVoiceMessageSerializer(qs, many=True)
        return Response(serializer.data)

    # POST: create (Node or authenticated user)
    serializer = AdminDriverVoiceMessageCreateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    data = serializer.validated_data
    sender_id = data['sender_id']
    recipient_id = data['recipient_id']
    if request.user.id != sender_id and not getattr(request.user, 'is_staff', False):
        return Response({'detail': 'Can only create as yourself or as staff.'}, status=status.HTTP_403_FORBIDDEN)
    try:
        sender = User.objects.get(pk=sender_id)
        recipient = User.objects.get(pk=recipient_id)
    except User.DoesNotExist:
        return Response({'detail': 'Sender or recipient not found.'}, status=status.HTTP_404_NOT_FOUND)
    is_sender_staff = getattr(sender, 'is_staff', False) or getattr(sender, 'is_superuser', False)
    is_recipient_driver = getattr(recipient, 'is_driver', False)
    if not ((is_sender_staff and is_recipient_driver) or (getattr(recipient, 'is_staff', False) and getattr(sender, 'is_driver', False))):
        return Response({'detail': 'Direct messages are between staff and driver only.'}, status=status.HTTP_400_BAD_REQUEST)
    msg = AdminDriverVoiceMessage.objects.create(
        sender=sender,
        recipient=recipient,
        file_path=data['file_path'],
        duration_seconds=data.get('duration_seconds'),
        sample_rate=data.get('sample_rate'),
    )
    return Response(
        AdminDriverVoiceMessageSerializer(msg).data,
        status=status.HTTP_201_CREATED
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def direct_message_play_view(request, pk):
    """Stream a direct voice message file. User must be sender or recipient."""
    from django.conf import settings
    try:
        msg = AdminDriverVoiceMessage.objects.select_related('sender', 'recipient').get(pk=pk)
    except AdminDriverVoiceMessage.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
    if request.user.id != msg.sender_id and request.user.id != msg.recipient_id:
        return Response({'detail': 'Not allowed.'}, status=status.HTTP_403_FORBIDDEN)
    base_dir = os.path.abspath(settings.WALKIETALKIE_RECORDINGS_DIR)
    full_path, err = _resolve_direct_message_file_path(msg, base_dir)
    if err:
        return err
    return FileResponse(
        open(full_path, 'rb'),
        as_attachment=False,
        content_type='application/octet-stream',
        filename=os.path.basename(full_path),
    )


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def direct_message_partial_update_view(request, pk):
    """Mark message as read (recipient only)."""
    try:
        msg = AdminDriverVoiceMessage.objects.get(pk=pk)
    except AdminDriverVoiceMessage.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
    if request.user.id != msg.recipient_id:
        return Response({'detail': 'Only recipient can mark as read.'}, status=status.HTTP_403_FORBIDDEN)
    msg.read_at = timezone.now()
    msg.save(update_fields=['read_at'])
    return Response(AdminDriverVoiceMessageSerializer(msg).data)
