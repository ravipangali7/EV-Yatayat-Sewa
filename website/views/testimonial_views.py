from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from ..models import Testimonial
from ..serializers import TestimonialSerializer
from .utils import get_request_data, paginated_response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def testimonial_list_get_view(request):
    queryset = Testimonial.objects.all().order_by('-id')
    data = paginated_response(queryset, TestimonialSerializer, request)
    return Response(data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def testimonial_list_post_view(request):
    data = get_request_data(request)
    serializer = TestimonialSerializer(data=data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    obj = serializer.save()
    return Response(TestimonialSerializer(obj, context={'request': request}).data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def testimonial_detail_get_view(request, pk):
    try:
        obj = Testimonial.objects.get(pk=pk)
    except Testimonial.DoesNotExist:
        return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
    return Response(TestimonialSerializer(obj, context={'request': request}).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def testimonial_detail_post_view(request, pk):
    try:
        obj = Testimonial.objects.get(pk=pk)
    except Testimonial.DoesNotExist:
        return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
    data = get_request_data(request)
    serializer = TestimonialSerializer(obj, data=data, partial=True)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    obj = serializer.save()
    return Response(TestimonialSerializer(obj, context={'request': request}).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def testimonial_delete_view(request, pk):
    try:
        obj = Testimonial.objects.get(pk=pk)
        obj.delete()
        return Response({'message': 'Deleted'})
    except Testimonial.DoesNotExist:
        return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
