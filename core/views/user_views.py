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
            'license_no': getattr(user, 'license_no', None) or '',
            'license_type': getattr(user, 'license_type', None) or '',
            'license_expiry_date': user.license_expiry_date.isoformat() if getattr(user, 'license_expiry_date', None) else None,
            'is_ticket_dealer': getattr(user, 'is_ticket_dealer', False),
            'ticket_commission': str(user.ticket_commission) if getattr(user, 'ticket_commission', None) is not None else None,
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
    license_image = request.FILES.get('license_image')
    license_no = request.POST.get('license_no') or request.data.get('license_no') or None
    license_type = request.POST.get('license_type') or request.data.get('license_type') or None
    license_expiry_date = request.POST.get('license_expiry_date') or request.data.get('license_expiry_date')
    is_ticket_dealer = request.POST.get('is_ticket_dealer') or request.data.get('is_ticket_dealer', 'false')
    ticket_commission = request.POST.get('ticket_commission') or request.data.get('ticket_commission', '0')
    
    # Validate required fields
    if not phone:
        return Response({'error': 'Phone is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Check if phone already exists
    if User.objects.filter(phone=phone).exists():
        return Response({'error': 'User with this phone already exists'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Convert boolean strings
    is_driver = is_driver.lower() == 'true' if isinstance(is_driver, str) else bool(is_driver)
    is_active = is_active.lower() == 'true' if isinstance(is_active, str) else bool(is_active)
    is_ticket_dealer = is_ticket_dealer.lower() == 'true' if isinstance(is_ticket_dealer, str) else bool(is_ticket_dealer)
    try:
        from decimal import Decimal
        ticket_commission = Decimal(str(ticket_commission)) if ticket_commission else Decimal('0')
    except (ValueError, TypeError):
        ticket_commission = Decimal('0')
    from datetime import datetime
    license_expiry_date_parsed = None
    if license_expiry_date:
        try:
            license_expiry_date_parsed = datetime.strptime(str(license_expiry_date)[:10], '%Y-%m-%d').date()
        except ValueError:
            pass
    
    # Create user directly without serializer
    user = User.objects.create(
        phone=phone,
        username=phone,  # Will be set automatically in save(), but set explicitly
        name=name,
        email=email,
        profile_picture=profile_picture,
        is_driver=is_driver,
        is_active=is_active,
        license_no=license_no,
        license_image=license_image,
        license_type=license_type,
        license_expiry_date=license_expiry_date_parsed,
        is_ticket_dealer=is_ticket_dealer,
        ticket_commission=ticket_commission,
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
        'license_no': user.license_no or '',
        'license_image': user.license_image.url if user.license_image else None,
        'license_type': user.license_type or '',
        'license_expiry_date': user.license_expiry_date.isoformat() if user.license_expiry_date else None,
        'is_ticket_dealer': user.is_ticket_dealer,
        'ticket_commission': str(user.ticket_commission) if user.ticket_commission is not None else None,
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
        'license_no': user.license_no or '',
        'license_image': user.license_image.url if user.license_image else None,
        'license_type': user.license_type or '',
        'license_expiry_date': user.license_expiry_date.isoformat() if user.license_expiry_date else None,
        'is_ticket_dealer': user.is_ticket_dealer,
        'ticket_commission': str(user.ticket_commission) if user.ticket_commission is not None else None,
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
    
    if 'license_no' in request.POST or 'license_no' in request.data:
        user.license_no = request.POST.get('license_no') or request.data.get('license_no') or None
    if 'license_type' in request.POST or 'license_type' in request.data:
        user.license_type = request.POST.get('license_type') or request.data.get('license_type') or None
    if 'license_expiry_date' in request.POST or 'license_expiry_date' in request.data:
        val = request.POST.get('license_expiry_date') or request.data.get('license_expiry_date')
        if val:
            try:
                from datetime import datetime
                user.license_expiry_date = datetime.strptime(str(val)[:10], '%Y-%m-%d').date()
            except ValueError:
                pass
        else:
            user.license_expiry_date = None
    if 'is_ticket_dealer' in request.POST or 'is_ticket_dealer' in request.data:
        val = request.POST.get('is_ticket_dealer') or request.data.get('is_ticket_dealer')
        user.is_ticket_dealer = val.lower() == 'true' if isinstance(val, str) else bool(val)
    if 'ticket_commission' in request.POST or 'ticket_commission' in request.data:
        try:
            from decimal import Decimal
            user.ticket_commission = Decimal(str(request.POST.get('ticket_commission') or request.data.get('ticket_commission') or '0'))
        except (ValueError, TypeError):
            pass
    
    # Handle file uploads - save immediately to ensure database field is updated
    if 'profile_picture' in request.FILES:
        user.profile_picture = request.FILES['profile_picture']
        user.save(update_fields=['profile_picture'])  # Save immediately to database
    if 'license_image' in request.FILES:
        user.license_image = request.FILES['license_image']
        user.save(update_fields=['license_image'])
    
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
        'license_no': user.license_no or '',
        'license_image': user.license_image.url if user.license_image else None,
        'license_type': user.license_type or '',
        'license_expiry_date': user.license_expiry_date.isoformat() if user.license_expiry_date else None,
        'is_ticket_dealer': user.is_ticket_dealer,
        'ticket_commission': str(user.ticket_commission) if user.ticket_commission is not None else None,
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
