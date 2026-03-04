from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from ..models import Service
from ..serializers import ServiceSerializer, ReorderSerializer
from .utils import get_request_data, paginated_response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def service_list_get_view(request):
    queryset = Service.objects.all().order_by('order', 'id')
    data = paginated_response(queryset, ServiceSerializer, request)
    return Response(data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def service_list_post_view(request):
    data = get_request_data(request)
    serializer = ServiceSerializer(data=data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    obj = serializer.save()
    return Response(ServiceSerializer(obj, context={'request': request}).data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def service_detail_get_view(request, pk):
    try:
        obj = Service.objects.get(pk=pk)
    except Service.DoesNotExist:
        return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
    return Response(ServiceSerializer(obj, context={'request': request}).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def service_detail_post_view(request, pk):
    try:
        obj = Service.objects.get(pk=pk)
    except Service.DoesNotExist:
        return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
    data = get_request_data(request)
    serializer = ServiceSerializer(obj, data=data, partial=True)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    obj = serializer.save()
    return Response(ServiceSerializer(obj, context={'request': request}).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def service_delete_view(request, pk):
    try:
        obj = Service.objects.get(pk=pk)
        obj.delete()
        return Response({'message': 'Deleted'})
    except Service.DoesNotExist:
        return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def service_reorder_view(request):
    items = request.data if isinstance(request.data, list) else request.data.get('items', [])
    ser = ReorderSerializer(data=items, many=True)
    if not ser.is_valid():
        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
    for row in ser.validated_data:
        Service.objects.filter(pk=row['id']).update(order=row['order'])
    return Response({'message': 'Order updated'})
