from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from decimal import Decimal
from ..models import SuperSetting


@api_view(['GET'])
def super_setting_list_get_view(request):
    """List all super settings"""
    # Get query parameters
    search = request.query_params.get('search', '')
    
    # Build queryset
    queryset = SuperSetting.objects.all()
    
    # Pagination
    page = int(request.query_params.get('page', 1))
    per_page = int(request.query_params.get('per_page', 10))
    start = (page - 1) * per_page
    end = start + per_page
    
    total = queryset.count()
    settings = queryset[start:end]
    
    # Return data without serializer
    results = []
    for setting in settings:
        results.append({
            'id': str(setting.id),
            'per_km_charge': str(setting.per_km_charge),
            'created_at': setting.created_at.isoformat(),
            'updated_at': setting.updated_at.isoformat(),
        })
    
    return Response({
        'results': results,
        'count': total,
        'page': page,
        'per_page': per_page
    })


@api_view(['POST'])
def super_setting_list_post_view(request):
    """Create a new super setting"""
    # Extract data from request.POST or request.data
    per_km_charge = request.POST.get('per_km_charge') or request.data.get('per_km_charge')
    
    # Validate required fields
    if not per_km_charge:
        return Response({'error': 'Per KM charge is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Convert to Decimal
    try:
        per_km_charge = Decimal(str(per_km_charge))
    except (ValueError, TypeError):
        return Response({'error': 'Invalid per_km_charge value'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Create setting directly without serializer
    setting = SuperSetting.objects.create(
        per_km_charge=per_km_charge,
    )
    
    # Return response
    return Response({
        'id': str(setting.id),
        'per_km_charge': str(setting.per_km_charge),
        'created_at': setting.created_at.isoformat(),
        'updated_at': setting.updated_at.isoformat(),
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
def super_setting_detail_get_view(request, pk):
    """Retrieve a single super setting"""
    try:
        setting = SuperSetting.objects.get(pk=pk)
    except SuperSetting.DoesNotExist:
        return Response({'error': 'Super setting not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Return data without serializer
    return Response({
        'id': str(setting.id),
        'per_km_charge': str(setting.per_km_charge),
        'created_at': setting.created_at.isoformat(),
        'updated_at': setting.updated_at.isoformat(),
    })


@api_view(['POST'])
def super_setting_detail_post_view(request, pk):
    """Update/edit a super setting"""
    try:
        setting = SuperSetting.objects.get(pk=pk)
    except SuperSetting.DoesNotExist:
        return Response({'error': 'Super setting not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Extract data from request.POST or request.data
    if 'per_km_charge' in request.POST or 'per_km_charge' in request.data:
        per_km_charge = request.POST.get('per_km_charge') or request.data.get('per_km_charge')
        try:
            setting.per_km_charge = Decimal(str(per_km_charge))
        except (ValueError, TypeError):
            return Response({'error': 'Invalid per_km_charge value'}, status=status.HTTP_400_BAD_REQUEST)
    
    setting.save()
    
    # Return updated data
    return Response({
        'id': str(setting.id),
        'per_km_charge': str(setting.per_km_charge),
        'created_at': setting.created_at.isoformat(),
        'updated_at': setting.updated_at.isoformat(),
    })


@api_view(['GET'])
def super_setting_delete_get_view(request, pk):
    """Delete a super setting"""
    try:
        setting = SuperSetting.objects.get(pk=pk)
        setting.delete()
        return Response({'message': 'Super setting deleted successfully'})
    except SuperSetting.DoesNotExist:
        return Response({'error': 'Super setting not found'}, status=status.HTTP_404_NOT_FOUND)
