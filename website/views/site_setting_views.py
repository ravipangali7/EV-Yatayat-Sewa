from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
import json

from ..models import SiteSetting
from ..serializers import SiteSettingSerializer


def _form_value_to_string(val):
    """Normalize form value to string so CharFields never receive a list."""
    if val is None:
        return ''
    if isinstance(val, str):
        return val
    if isinstance(val, (list, tuple)) and len(val) == 1:
        return _form_value_to_string(val[0])
    return ''


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
    # Build payload explicitly so CharFields get strings and ImageFields get real files only
    data = {}
    for key in request.POST:
        data[key] = _form_value_to_string(request.POST.get(key))

    for key in request.FILES:
        f = request.FILES[key]
        if f and getattr(f, 'name', None):
            data[key] = f

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
