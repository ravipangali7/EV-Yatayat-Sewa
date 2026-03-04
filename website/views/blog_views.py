from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from ..models import Blog
from ..serializers import BlogSerializer
from .utils import get_request_data, paginated_response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def blog_list_get_view(request):
    queryset = Blog.objects.all().order_by('-id')
    data = paginated_response(queryset, BlogSerializer, request)
    return Response(data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def blog_list_post_view(request):
    data = get_request_data(request)
    serializer = BlogSerializer(data=data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    obj = serializer.save()
    return Response(BlogSerializer(obj, context={'request': request}).data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def blog_detail_get_view(request, pk):
    try:
        obj = Blog.objects.get(pk=pk)
    except Blog.DoesNotExist:
        return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
    return Response(BlogSerializer(obj, context={'request': request}).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def blog_detail_post_view(request, pk):
    try:
        obj = Blog.objects.get(pk=pk)
    except Blog.DoesNotExist:
        return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
    data = get_request_data(request)
    serializer = BlogSerializer(obj, data=data, partial=True)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    obj = serializer.save()
    return Response(BlogSerializer(obj, context={'request': request}).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def blog_delete_view(request, pk):
    try:
        obj = Blog.objects.get(pk=pk)
        obj.delete()
        return Response({'message': 'Deleted'})
    except Blog.DoesNotExist:
        return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
