from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from ..models import CMSPage
from ..serializers import CMSPageSerializer, CMSPageListSerializer
from .utils import get_request_data, paginated_response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def cms_page_list_get_view(request):
    queryset = CMSPage.objects.all().order_by('-id')
    data = paginated_response(queryset, CMSPageSerializer, request)
    return Response(data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cms_page_list_post_view(request):
    data = get_request_data(request)
    if data.get('section_in') == '':
        data['section_in'] = None
    serializer = CMSPageSerializer(data=data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    obj = serializer.save()
    return Response(CMSPageSerializer(obj, context={'request': request}).data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def cms_page_detail_get_view(request, pk):
    try:
        obj = CMSPage.objects.get(pk=pk)
    except CMSPage.DoesNotExist:
        return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
    return Response(CMSPageSerializer(obj, context={'request': request}).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cms_page_detail_post_view(request, pk):
    try:
        obj = CMSPage.objects.get(pk=pk)
    except CMSPage.DoesNotExist:
        return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
    data = get_request_data(request)
    if data.get('section_in') == '':
        data['section_in'] = None
    serializer = CMSPageSerializer(obj, data=data, partial=True)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    obj = serializer.save()
    return Response(CMSPageSerializer(obj, context={'request': request}).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def cms_page_delete_view(request, pk):
    try:
        obj = CMSPage.objects.get(pk=pk)
        obj.delete()
        return Response({'message': 'Deleted'})
    except CMSPage.DoesNotExist:
        return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
