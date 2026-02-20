from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q, F
from django.db import transaction as db_transaction
from django.utils import timezone
from decimal import Decimal
from ..models import Wallet, User
from ..services.wallet_transaction import create_wallet_transaction


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
    
    from django.db.models import Sum
    total = queryset.count()
    balance_agg = queryset.aggregate(s=Sum('balance'))
    total_balance = balance_agg['s'] or 0
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
            'to_pay': str(wallet.to_pay),
            'to_receive': str(wallet.to_receive),
            'created_at': wallet.created_at.isoformat(),
            'updated_at': wallet.updated_at.isoformat(),
        })
    
    return Response({
        'results': results,
        'count': total,
        'page': page,
        'per_page': per_page,
        'stats': {'total_count': total, 'total_balance': str(total_balance)},
    })


@api_view(['POST'])
def wallet_list_post_view(request):
    """Create a new wallet"""
    # Extract data from request.POST or request.data
    user_id = request.POST.get('user') or request.data.get('user')
    balance = request.POST.get('balance') or request.data.get('balance', '0')
    to_pay = request.POST.get('to_pay') or request.data.get('to_pay', '0')
    to_receive = request.POST.get('to_receive') or request.data.get('to_receive', '0')
    
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
        to_pay = Decimal(str(to_pay))
        to_receive = Decimal(str(to_receive))
    except (ValueError, TypeError):
        return Response({'error': 'Invalid decimal values'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Create wallet directly without serializer
    wallet = Wallet.objects.create(
        user=user,
        balance=balance,
        to_pay=to_pay,
        to_receive=to_receive,
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
        'to_pay': str(wallet.to_pay),
        'to_receive': str(wallet.to_receive),
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
        'to_pay': str(wallet.to_pay),
        'to_receive': str(wallet.to_receive),
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
    
    if 'to_pay' in request.POST or 'to_pay' in request.data:
        to_pay = request.POST.get('to_pay') or request.data.get('to_pay')
        try:
            wallet.to_pay = Decimal(str(to_pay))
        except (ValueError, TypeError):
            return Response({'error': 'Invalid to_pay value'}, status=status.HTTP_400_BAD_REQUEST)
    
    if 'to_receive' in request.POST or 'to_receive' in request.data:
        to_receive = request.POST.get('to_receive') or request.data.get('to_receive')
        try:
            wallet.to_receive = Decimal(str(to_receive))
        except (ValueError, TypeError):
            return Response({'error': 'Invalid to_receive value'}, status=status.HTTP_400_BAD_REQUEST)
    
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
        'to_pay': str(wallet.to_pay),
        'to_receive': str(wallet.to_receive),
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


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def wallet_my_deposit_view(request):
    """Deposit/recharge current user's wallet. Adds amount and creates an 'add' transaction."""
    data = request.data or request.POST
    amount = data.get('amount')
    if amount is None:
        return Response({'error': 'amount is required'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        amount = Decimal(str(amount))
    except (ValueError, TypeError):
        return Response({'error': 'Invalid amount'}, status=status.HTTP_400_BAD_REQUEST)
    if amount <= 0:
        return Response({'error': 'Amount must be positive'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        wallet = Wallet.objects.get(user=request.user)
    except Wallet.DoesNotExist:
        return Response({'error': 'Wallet not found'}, status=status.HTTP_400_BAD_REQUEST)
    wallet.balance += amount
    wallet.save(update_fields=['balance', 'updated_at'])
    create_wallet_transaction(
        wallet=wallet,
        user=request.user,
        amount=amount,
        type='add',
        remarks='Deposit',
        status='success',
    )
    return Response({
        'id': str(wallet.id),
        'balance': str(wallet.balance),
        'message': 'Deposit successful',
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def wallet_my_transfer_view(request):
    """Transfer from current user's wallet to another user by phone or user id."""
    data = request.data or request.POST
    amount = data.get('amount')
    recipient_phone = data.get('recipient_phone') or data.get('recipient_phone_number')
    recipient_user_id = data.get('recipient_user_id')

    if amount is None:
        return Response({'error': 'amount is required'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        amount = Decimal(str(amount))
    except (ValueError, TypeError):
        return Response({'error': 'Invalid amount'}, status=status.HTTP_400_BAD_REQUEST)
    if amount <= 0:
        return Response({'error': 'Amount must be positive'}, status=status.HTTP_400_BAD_REQUEST)

    if not recipient_phone and not recipient_user_id:
        return Response(
            {'error': 'recipient_phone or recipient_user_id is required'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    recipient = None
    if recipient_user_id:
        try:
            recipient = User.objects.get(pk=recipient_user_id)
        except (User.DoesNotExist, ValueError):
            return Response({'error': 'Recipient user not found'}, status=status.HTTP_400_BAD_REQUEST)
    else:
        phone = (recipient_phone or '').strip()
        if not phone:
            return Response({'error': 'Recipient phone is required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            recipient = User.objects.get(phone=phone)
        except User.DoesNotExist:
            return Response({'error': 'No user found with this phone number'}, status=status.HTTP_404_NOT_FOUND)

    if recipient.id == request.user.id:
        return Response({'error': 'Cannot transfer to yourself'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        sender_wallet = Wallet.objects.get(user=request.user)
    except Wallet.DoesNotExist:
        return Response({'error': 'Wallet not found'}, status=status.HTTP_400_BAD_REQUEST)

    if sender_wallet.balance < amount:
        return Response(
            {'error': 'Insufficient balance', 'balance': str(sender_wallet.balance)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    recipient_wallet, _ = Wallet.objects.get_or_create(
        user=recipient,
        defaults={'balance': 0, 'to_pay': 0, 'to_receive': 0},
    )

    with db_transaction.atomic():
        create_wallet_transaction(
            wallet=sender_wallet,
            user=request.user,
            amount=amount,
            type='deducted',
            remarks=f'Transfer to {recipient.name or recipient.phone}',
            status='success',
        )
        create_wallet_transaction(
            wallet=recipient_wallet,
            user=recipient,
            amount=amount,
            type='add',
            remarks=f'Transfer from {request.user.name or request.user.phone}',
            status='success',
        )
        Wallet.objects.filter(pk=sender_wallet.pk).update(
            balance=F('balance') - amount,
            updated_at=timezone.now(),
        )
        Wallet.objects.filter(pk=recipient_wallet.pk).update(
            balance=F('balance') + amount,
            updated_at=timezone.now(),
        )
        sender_wallet.refresh_from_db()
        recipient_wallet.refresh_from_db()

    return Response({
        'message': 'Transfer successful',
        'balance': str(sender_wallet.balance),
        'recipient_name': recipient.name or recipient.phone,
        'recipient_phone': recipient.phone,
    })
