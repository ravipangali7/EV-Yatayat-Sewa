from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q
from decimal import Decimal
from ..models import Wallet, User


@api_view(['GET'])
def wallet_list_get_view(request):
    """List all wallets"""
    # Get query parameters
    search = request.query_params.get('search', '')
    user_id = request.query_params.get('user', None)
    
    # Build queryset
    queryset = Wallet.objects.select_related('user').all()
    
    if search:
        queryset = queryset.filter(
            Q(user__name__icontains=search) |
            Q(user__phone__icontains=search) |
            Q(user__email__icontains=search)
        )
    
    if user_id:
        queryset = queryset.filter(user_id=user_id)
    
    # Pagination
    page = int(request.query_params.get('page', 1))
    per_page = int(request.query_params.get('per_page', 10))
    start = (page - 1) * per_page
    end = start + per_page
    
    total = queryset.count()
    wallets = queryset[start:end]
    
    # Return data without serializer
    results = []
    for wallet in wallets:
        results.append({
            'id': str(wallet.id),
            'user': str(wallet.user.id),
            'user_details': {
                'id': str(wallet.user.id),
                'username': wallet.user.username,
                'phone': wallet.user.phone,
                'email': wallet.user.email or '',
                'name': wallet.user.name or '',
                'is_driver': wallet.user.is_driver,
                'is_active': wallet.user.is_active,
            },
            'balance': str(wallet.balance),
            'to_be_pay': str(wallet.to_be_pay),
            'to_be_received': str(wallet.to_be_received),
            'created_at': wallet.created_at.isoformat(),
            'updated_at': wallet.updated_at.isoformat(),
        })
    
    return Response({
        'results': results,
        'count': total,
        'page': page,
        'per_page': per_page
    })


@api_view(['POST'])
def wallet_list_post_view(request):
    """Create a new wallet"""
    # Extract data from request.POST or request.data
    user_id = request.POST.get('user') or request.data.get('user')
    balance = request.POST.get('balance') or request.data.get('balance', '0')
    to_be_pay = request.POST.get('to_be_pay') or request.data.get('to_be_pay', '0')
    to_be_received = request.POST.get('to_be_received') or request.data.get('to_be_received', '0')
    
    # Validate required fields
    if not user_id:
        return Response({'error': 'User is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Check if user exists
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Check if wallet already exists for this user
    if Wallet.objects.filter(user=user).exists():
        return Response({'error': 'Wallet already exists for this user'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Convert to Decimal
    try:
        balance = Decimal(str(balance))
        to_be_pay = Decimal(str(to_be_pay))
        to_be_received = Decimal(str(to_be_received))
    except (ValueError, TypeError):
        return Response({'error': 'Invalid decimal values'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Create wallet directly without serializer
    wallet = Wallet.objects.create(
        user=user,
        balance=balance,
        to_be_pay=to_be_pay,
        to_be_received=to_be_received,
    )
    
    # Return response
    return Response({
        'id': str(wallet.id),
        'user': str(wallet.user.id),
        'user_details': {
            'id': str(wallet.user.id),
            'username': wallet.user.username,
            'phone': wallet.user.phone,
            'email': wallet.user.email or '',
            'name': wallet.user.name or '',
            'is_driver': wallet.user.is_driver,
            'is_active': wallet.user.is_active,
        },
        'balance': str(wallet.balance),
        'to_be_pay': str(wallet.to_be_pay),
        'to_be_received': str(wallet.to_be_received),
        'created_at': wallet.created_at.isoformat(),
        'updated_at': wallet.updated_at.isoformat(),
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
def wallet_detail_get_view(request, pk):
    """Retrieve a single wallet"""
    try:
        wallet = Wallet.objects.select_related('user').get(pk=pk)
    except Wallet.DoesNotExist:
        return Response({'error': 'Wallet not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Return data without serializer
    return Response({
        'id': str(wallet.id),
        'user': str(wallet.user.id),
        'user_details': {
            'id': str(wallet.user.id),
            'username': wallet.user.username,
            'phone': wallet.user.phone,
            'email': wallet.user.email or '',
            'name': wallet.user.name or '',
            'is_driver': wallet.user.is_driver,
            'is_active': wallet.user.is_active,
        },
        'balance': str(wallet.balance),
        'to_be_pay': str(wallet.to_be_pay),
        'to_be_received': str(wallet.to_be_received),
        'created_at': wallet.created_at.isoformat(),
        'updated_at': wallet.updated_at.isoformat(),
    })


@api_view(['POST'])
def wallet_detail_post_view(request, pk):
    """Update/edit a wallet"""
    try:
        wallet = Wallet.objects.select_related('user').get(pk=pk)
    except Wallet.DoesNotExist:
        return Response({'error': 'Wallet not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Extract data from request.POST or request.data
    if 'balance' in request.POST or 'balance' in request.data:
        balance = request.POST.get('balance') or request.data.get('balance')
        try:
            wallet.balance = Decimal(str(balance))
        except (ValueError, TypeError):
            return Response({'error': 'Invalid balance value'}, status=status.HTTP_400_BAD_REQUEST)
    
    if 'to_be_pay' in request.POST or 'to_be_pay' in request.data:
        to_be_pay = request.POST.get('to_be_pay') or request.data.get('to_be_pay')
        try:
            wallet.to_be_pay = Decimal(str(to_be_pay))
        except (ValueError, TypeError):
            return Response({'error': 'Invalid to_be_pay value'}, status=status.HTTP_400_BAD_REQUEST)
    
    if 'to_be_received' in request.POST or 'to_be_received' in request.data:
        to_be_received = request.POST.get('to_be_received') or request.data.get('to_be_received')
        try:
            wallet.to_be_received = Decimal(str(to_be_received))
        except (ValueError, TypeError):
            return Response({'error': 'Invalid to_be_received value'}, status=status.HTTP_400_BAD_REQUEST)
    
    if 'user' in request.POST or 'user' in request.data:
        user_id = request.POST.get('user') or request.data.get('user')
        try:
            user = User.objects.get(pk=user_id)
            wallet.user = user
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_400_BAD_REQUEST)
    
    wallet.save()
    
    # Return updated data
    return Response({
        'id': str(wallet.id),
        'user': str(wallet.user.id),
        'user_details': {
            'id': str(wallet.user.id),
            'username': wallet.user.username,
            'phone': wallet.user.phone,
            'email': wallet.user.email or '',
            'name': wallet.user.name or '',
            'is_driver': wallet.user.is_driver,
            'is_active': wallet.user.is_active,
        },
        'balance': str(wallet.balance),
        'to_be_pay': str(wallet.to_be_pay),
        'to_be_received': str(wallet.to_be_received),
        'created_at': wallet.created_at.isoformat(),
        'updated_at': wallet.updated_at.isoformat(),
    })


@api_view(['GET'])
def wallet_delete_get_view(request, pk):
    """Delete a wallet"""
    try:
        wallet = Wallet.objects.get(pk=pk)
        wallet.delete()
        return Response({'message': 'Wallet deleted successfully'})
    except Wallet.DoesNotExist:
        return Response({'error': 'Wallet not found'}, status=status.HTTP_404_NOT_FOUND)
