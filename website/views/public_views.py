from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from ..models import Slider, CMSPage, Team, Testimonial, Service, FAQ, Blog, SiteSetting, ContactMessage
from ..serializers import (
    SliderSerializer, CMSPagePublicSerializer, CMSPageChildSerializer,
    TeamSerializer, TestimonialSerializer, ServiceSerializer, FAQSerializer,
    BlogSerializer, SiteSettingSerializer, ContactMessageCreateSerializer,
)


@api_view(['GET'])
@permission_classes([AllowAny])
def public_sliders_view(request):
    qs = Slider.objects.filter(is_active=True).order_by('id')
    data = SliderSerializer(qs, many=True, context={'request': request}).data
    return Response(data)


@api_view(['GET'])
@permission_classes([AllowAny])
def public_site_setting_view(request):
    obj = SiteSetting.objects.first()
    if not obj:
        return Response({})
    return Response(SiteSettingSerializer(obj, context={'request': request}).data)


@api_view(['GET'])
@permission_classes([AllowAny])
def public_cms_about_view(request):
    obj = CMSPage.objects.filter(is_active=True, is_about=True).order_by('id').first()
    if not obj:
        return Response(None)
    return Response(CMSPagePublicSerializer(obj, context={'request': request}).data)


@api_view(['GET'])
@permission_classes([AllowAny])
def public_cms_by_slug_view(request, slug):
    try:
        obj = CMSPage.objects.get(slug=slug, is_active=True)
    except CMSPage.DoesNotExist:
        return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
    return Response(CMSPagePublicSerializer(obj, context={'request': request}).data)


@api_view(['GET'])
@permission_classes([AllowAny])
def public_cms_header_view(request):
    qs = CMSPage.objects.filter(is_active=True, is_header=True).order_by('id')
    data = CMSPageChildSerializer(qs, many=True, context={'request': request}).data
    return Response(data)


@api_view(['GET'])
@permission_classes([AllowAny])
def public_services_view(request):
    qs = Service.objects.filter(is_active=True).order_by('order', 'id')
    data = ServiceSerializer(qs, many=True, context={'request': request}).data
    return Response(data)


@api_view(['GET'])
@permission_classes([AllowAny])
def public_team_view(request):
    qs = Team.objects.filter(is_active=True).order_by('order', 'id')
    data = TeamSerializer(qs, many=True, context={'request': request}).data
    return Response(data)


@api_view(['GET'])
@permission_classes([AllowAny])
def public_testimonials_view(request):
    qs = Testimonial.objects.filter(is_active=True).order_by('id')
    data = TestimonialSerializer(qs, many=True, context={'request': request}).data
    return Response(data)


@api_view(['GET'])
@permission_classes([AllowAny])
def public_blogs_view(request):
    qs = Blog.objects.filter(is_active=True).order_by('-id')
    data = BlogSerializer(qs, many=True, context={'request': request}).data
    return Response(data)


@api_view(['GET'])
@permission_classes([AllowAny])
def public_blog_by_slug_view(request, slug):
    try:
        obj = Blog.objects.get(slug=slug, is_active=True)
    except Blog.DoesNotExist:
        return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
    return Response(BlogSerializer(obj, context={'request': request}).data)


@api_view(['GET'])
@permission_classes([AllowAny])
def public_faqs_view(request):
    qs = FAQ.objects.filter(is_active=True).order_by('order', 'id')
    data = FAQSerializer(qs, many=True, context={'request': request}).data
    return Response(data)


@api_view(['POST'])
@permission_classes([AllowAny])
def public_contact_message_create_view(request):
    data = request.data if request.data else request.POST.copy()
    serializer = ContactMessageCreateSerializer(data=data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    serializer.save()
    return Response({'message': 'Message sent'}, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([AllowAny])
def public_vehicles_view(request):
    """Public list of active vehicles (from booking app) for website home."""
    from booking.models import Vehicle
    qs = Vehicle.objects.filter(is_active=True).order_by('id')
    results = []
    for v in qs:
        results.append({
            'id': v.id,
            'name': v.name,
            'vehicle_no': v.vehicle_no,
            'vehicle_type': v.vehicle_type,
            'description': v.description or '',
            'featured_image': request.build_absolute_uri(v.featured_image.url) if v.featured_image else None,
        })
    return Response(results)
