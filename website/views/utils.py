"""Shared helpers for website views."""


def get_request_data(request):
    """Return mutable dict from request.data (JSON) or request.POST, merged with request.FILES."""
    if request.content_type and 'application/json' in request.content_type and request.data:
        data = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)
    else:
        data = request.POST.copy()
    if request.FILES:
        for key in request.FILES:
            data[key] = request.FILES[key]
    return data


def paginated_response(queryset, serializer_class, request, per_page_default=25):
    """Return paginated list response using serializer_class."""
    page = int(request.query_params.get('page', 1))
    per_page = int(request.query_params.get('per_page', per_page_default))
    start = (page - 1) * per_page
    end = start + per_page
    total = queryset.count()
    items = queryset[start:end]
    serializer = serializer_class(items, many=True, context={'request': request})
    return {
        'results': serializer.data,
        'count': total,
        'page': page,
        'per_page': per_page,
        'stats': {'total_count': total},
    }
