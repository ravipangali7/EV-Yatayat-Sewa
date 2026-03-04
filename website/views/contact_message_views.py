from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from ..models import ContactMessage
from ..serializers import ContactMessageSerializer
from .utils import get_request_data, paginated_response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def contact_message_list_get_view(request):
    queryset = ContactMessage.objects.all().order_by('-created_at')
    data = paginated_response(queryset, ContactMessageSerializer, request)
    return Response(data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def contact_message_detail_get_view(request, pk):
    try:
        obj = ContactMessage.objects.get(pk=pk)
    except ContactMessage.DoesNotExist:
        return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
    return Response(ContactMessageSerializer(obj, context={'request': request}).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def contact_message_detail_post_view(request, pk):
    try:
        obj = ContactMessage.objects.get(pk=pk)
    except ContactMessage.DoesNotExist:
        return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
    data = get_request_data(request)
    serializer = ContactMessageSerializer(obj, data=data, partial=True)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    obj = serializer.save()
    return Response(ContactMessageSerializer(obj, context={'request': request}).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def contact_message_delete_view(request, pk):
    try:
        obj = ContactMessage.objects.get(pk=pk)
        obj.delete()
        return Response({'message': 'Deleted'})
    except ContactMessage.DoesNotExist:
        return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
