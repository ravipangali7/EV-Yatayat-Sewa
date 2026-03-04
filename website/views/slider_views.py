from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from ..models import Slider
from ..serializers import SliderSerializer
from .utils import get_request_data, paginated_response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def slider_list_get_view(request):
    queryset = Slider.objects.all().order_by('-id')
    data = paginated_response(queryset, SliderSerializer, request)
    return Response(data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def slider_list_post_view(request):
    data = get_request_data(request)
    serializer = SliderSerializer(data=data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    obj = serializer.save()
    return Response(SliderSerializer(obj, context={'request': request}).data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def slider_detail_get_view(request, pk):
    try:
        obj = Slider.objects.get(pk=pk)
    except Slider.DoesNotExist:
        return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
    return Response(SliderSerializer(obj, context={'request': request}).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def slider_detail_post_view(request, pk):
    try:
        obj = Slider.objects.get(pk=pk)
    except Slider.DoesNotExist:
        return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
    data = get_request_data(request)
    serializer = SliderSerializer(obj, data=data, partial=True)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    obj = serializer.save()
    return Response(SliderSerializer(obj, context={'request': request}).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def slider_delete_view(request, pk):
    try:
        obj = Slider.objects.get(pk=pk)
        obj.delete()
        return Response({'message': 'Deleted'})
    except Slider.DoesNotExist:
        return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
