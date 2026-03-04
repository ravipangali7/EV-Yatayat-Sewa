from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
import json

from ..models import SiteSetting
from ..serializers import SiteSettingSerializer
from .utils import get_request_data


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def site_setting_get_view(request):
    """Get single site setting (first or create one)."""
    obj = SiteSetting.objects.first()
    if not obj:
        obj = SiteSetting.objects.create(name='', tagline='', phones=[], emails=[], stats={'stats': []})
    return Response(SiteSettingSerializer(obj, context={'request': request}).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def site_setting_post_view(request):
    """Create or update the single site setting."""
    raw = get_request_data(request)
    # Use a plain dict so parsed JSON stays as list/dict (QueryDict can break JSONField)
    data = dict(raw)

    obj = SiteSetting.objects.first()
    if not obj:
        obj = SiteSetting.objects.create(name='', tagline='', phones=[], emails=[], stats={'stats': []})

    # Parse JSON fields from form strings so serializer gets list/dict, not string
    for field in ('phones', 'emails', 'stats'):
        if field in data:
            val = data[field]
            if isinstance(val, str):
                try:
                    data[field] = json.loads(val) if val.strip() else ([] if field != 'stats' else {'stats': []})
                except (json.JSONDecodeError, AttributeError):
                    data[field] = {'stats': []} if field == 'stats' else []
            elif val is None or val == '':
                data[field] = [] if field != 'stats' else {'stats': []}

    serializer = SiteSettingSerializer(obj, data=data, partial=True)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    obj = serializer.save()
    return Response(SiteSettingSerializer(obj, context={'request': request}).data)
