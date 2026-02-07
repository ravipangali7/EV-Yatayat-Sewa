from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q
from django.contrib.auth.hashers import make_password
from ..models import User


@api_view(['GET'])
def user_list_get_view(request):
    """List all users"""
    # Get query parameters
    search = request.query_params.get('search', '')
    is_driver = request.query_params.get('is_driver', None)
    is_active = request.query_params.get('is_active', None)
    
    # Build queryset
    queryset = User.objects.all()
    
    if search:
        queryset = queryset.filter(
            Q(name__icontains=search) |
            Q(phone__icontains=search) |
            Q(email__icontains=search) |
            Q(username__icontains=search)
        )
    
    if is_driver is not None:
        queryset = queryset.filter(is_driver=is_driver.lower() == 'true')
    
    if is_active is not None:
        queryset = queryset.filter(is_active=is_active.lower() == 'true')
    
    # Pagination
    page = int(request.query_params.get('page', 1))
    per_page = int(request.query_params.get('per_page', 10))
    start = (page - 1) * per_page
    end = start + per_page
    
    total = queryset.count()
    users = queryset[start:end]
    
    # Return data without serializer
    results = []
    for user in users:
        results.append({
            'id': str(user.id),
            'username': user.username,
            'phone': user.phone,
            'email': user.email or '',
            'name': user.name or '',
            'is_driver': user.is_driver,
            'is_active': user.is_active,
        })
    
    return Response({
        'results': results,
        'count': total,
        'page': page,
        'per_page': per_page
    })


@api_view(['POST'])
def user_list_post_view(request):
    """Create a new user"""
    # Extract data from request.POST or request.data
    phone = request.POST.get('phone') or request.data.get('phone')
    name = request.POST.get('name') or request.data.get('name')
    email = request.POST.get('email') or request.data.get('email') or None
    password = request.POST.get('password') or request.data.get('password')
    is_driver = request.POST.get('is_driver') or request.data.get('is_driver', 'false')
    is_active = request.POST.get('is_active') or request.data.get('is_active', 'true')
    
    # Handle file uploads
    profile_picture = request.FILES.get('profile_picture')
    
    # Validate required fields
    if not phone:
        return Response({'error': 'Phone is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Check if phone already exists
    if User.objects.filter(phone=phone).exists():
        return Response({'error': 'User with this phone already exists'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Convert boolean strings
    is_driver = is_driver.lower() == 'true' if isinstance(is_driver, str) else bool(is_driver)
    is_active = is_active.lower() == 'true' if isinstance(is_active, str) else bool(is_active)
    
    # Create user directly without serializer
    user = User.objects.create(
        phone=phone,
        username=phone,  # Will be set automatically in save(), but set explicitly
        name=name,
        email=email,
        profile_picture=profile_picture,
        is_driver=is_driver,
        is_active=is_active,
    )
    
    # Set password if provided
    if password:
        user.set_password(password)
        user.save()
    
    # Return response
    return Response({
        'id': str(user.id),
        'username': user.username,
        'phone': user.phone,
        'email': user.email or '',
        'name': user.name or '',
        'profile_picture': user.profile_picture.url if user.profile_picture else None,
        'fcm_token': user.fcm_token or '',
        'token': user.token or '',
        'biometric_token': user.biometric_token or '',
        'is_driver': user.is_driver,
        'is_superuser': user.is_superuser,
        'is_staff': user.is_staff,
        'is_active': user.is_active,
        'created_at': user.created_at.isoformat(),
        'updated_at': user.updated_at.isoformat(),
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
def user_detail_get_view(request, pk):
    """Retrieve a single user"""
    try:
        user = User.objects.get(pk=pk)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Return data without serializer
    return Response({
        'id': str(user.id),
        'username': user.username,
        'phone': user.phone,
        'email': user.email or '',
        'name': user.name or '',
        'profile_picture': user.profile_picture.url if user.profile_picture else None,
        'fcm_token': user.fcm_token or '',
        'token': user.token or '',
        'biometric_token': user.biometric_token or '',
        'is_driver': user.is_driver,
        'is_superuser': user.is_superuser,
        'is_staff': user.is_staff,
        'is_active': user.is_active,
        'created_at': user.created_at.isoformat(),
        'updated_at': user.updated_at.isoformat(),
    })


@api_view(['POST'])
def user_detail_post_view(request, pk):
    """Update/edit a user"""
    try:
        user = User.objects.get(pk=pk)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Extract data from request.POST or request.data
    if 'name' in request.POST or 'name' in request.data:
        user.name = request.POST.get('name') or request.data.get('name') or None
    
    if 'email' in request.POST or 'email' in request.data:
        email = request.POST.get('email') or request.data.get('email')
        user.email = email if email else None
    
    if 'phone' in request.POST or 'phone' in request.data:
        phone = request.POST.get('phone') or request.data.get('phone')
        if phone and phone != user.phone:
            # Check if new phone already exists
            if User.objects.filter(phone=phone).exclude(pk=pk).exists():
                return Response({'error': 'User with this phone already exists'}, status=status.HTTP_400_BAD_REQUEST)
            user.phone = phone
            user.username = phone  # Will be set automatically in save(), but set explicitly
    
    if 'password' in request.POST or 'password' in request.data:
        password = request.POST.get('password') or request.data.get('password')
        if password:
            user.set_password(password)
    
    if 'is_driver' in request.POST or 'is_driver' in request.data:
        is_driver = request.POST.get('is_driver') or request.data.get('is_driver')
        user.is_driver = is_driver.lower() == 'true' if isinstance(is_driver, str) else bool(is_driver)
    
    if 'is_active' in request.POST or 'is_active' in request.data:
        is_active = request.POST.get('is_active') or request.data.get('is_active')
        user.is_active = is_active.lower() == 'true' if isinstance(is_active, str) else bool(is_active)
    
    # Handle file uploads - save immediately to ensure database field is updated
    if 'profile_picture' in request.FILES:
        user.profile_picture = request.FILES['profile_picture']
        user.save(update_fields=['profile_picture'])  # Save immediately to database
    
    user.save()
    
    # Return updated data
    return Response({
        'id': str(user.id),
        'username': user.username,
        'phone': user.phone,
        'email': user.email or '',
        'name': user.name or '',
        'profile_picture': user.profile_picture.url if user.profile_picture else None,
        'fcm_token': user.fcm_token or '',
        'token': user.token or '',
        'biometric_token': user.biometric_token or '',
        'is_driver': user.is_driver,
        'is_superuser': user.is_superuser,
        'is_staff': user.is_staff,
        'is_active': user.is_active,
        'created_at': user.created_at.isoformat(),
        'updated_at': user.updated_at.isoformat(),
    })


@api_view(['GET'])
def user_delete_get_view(request, pk):
    """Delete a user"""
    try:
        user = User.objects.get(pk=pk)
        user.delete()
        return Response({'message': 'User deleted successfully'})
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
