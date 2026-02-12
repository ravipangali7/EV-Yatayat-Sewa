from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q
from decimal import Decimal
from ..models import Transaction, Wallet, User


@api_view(['GET'])
def transaction_list_get_view(request):
    """List all transactions"""
    # Get query parameters
    search = request.query_params.get('search', '')
    status_filter = request.query_params.get('status', None)
    type_filter = request.query_params.get('type', None)
    wallet_id = request.query_params.get('wallet', None)
    user_id = request.query_params.get('user', None)
    
    # Build queryset
    queryset = Transaction.objects.select_related('wallet', 'user').all()
    
    if search:
        queryset = queryset.filter(
            Q(remarks__icontains=search) |
            Q(user__name__icontains=search) |
            Q(user__phone__icontains=search)
        )
    
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    
    if type_filter:
        queryset = queryset.filter(type=type_filter)
    
    if wallet_id:
        queryset = queryset.filter(wallet_id=wallet_id)
    
    if user_id:
        queryset = queryset.filter(user_id=user_id)
    
    # Pagination
    page = int(request.query_params.get('page', 1))
    per_page = int(request.query_params.get('per_page', 10))
    start = (page - 1) * per_page
    end = start + per_page
    
    total = queryset.count()
    transactions = queryset[start:end]
    
    # Return data without serializer
    results = []
    for transaction in transactions:
        results.append({
            'id': str(transaction.id),
            'status': transaction.status,
            'balance_before': str(transaction.balance_before),
            'balance_after': str(transaction.balance_after),
            'amount': str(transaction.amount),
            'wallet': str(transaction.wallet.id),
            'wallet_details': {
                'id': str(transaction.wallet.id),
                'user': str(transaction.wallet.user.id),
                'balance': str(transaction.wallet.balance),
                'to_pay': str(transaction.wallet.to_pay),
                'to_receive': str(transaction.wallet.to_receive),
            },
            'user': str(transaction.user.id),
            'user_details': {
                'id': str(transaction.user.id),
                'username': transaction.user.username,
                'phone': transaction.user.phone,
                'email': transaction.user.email or '',
                'name': transaction.user.name or '',
                'is_driver': transaction.user.is_driver,
                'is_active': transaction.user.is_active,
            },
            'type': transaction.type,
            'remarks': transaction.remarks or '',
            'created_at': transaction.created_at.isoformat(),
            'updated_at': transaction.updated_at.isoformat(),
        })
    
    return Response({
        'results': results,
        'count': total,
        'page': page,
        'per_page': per_page
    })


@api_view(['POST'])
def transaction_list_post_view(request):
    """Create a new transaction"""
    # Extract data from request.POST or request.data
    wallet_id = request.POST.get('wallet') or request.data.get('wallet')
    user_id = request.POST.get('user') or request.data.get('user')
    status_val = request.POST.get('status') or request.data.get('status', 'pending')
    balance_before = request.POST.get('balance_before') or request.data.get('balance_before')
    balance_after = request.POST.get('balance_after') or request.data.get('balance_after')
    amount = request.POST.get('amount') or request.data.get('amount')
    type_val = request.POST.get('type') or request.data.get('type')
    remarks = request.POST.get('remarks') or request.data.get('remarks') or None
    
    # Validate required fields
    if not wallet_id:
        return Response({'error': 'Wallet is required'}, status=status.HTTP_400_BAD_REQUEST)
    if not user_id:
        return Response({'error': 'User is required'}, status=status.HTTP_400_BAD_REQUEST)
    if not amount:
        return Response({'error': 'Amount is required'}, status=status.HTTP_400_BAD_REQUEST)
    if not type_val:
        return Response({'error': 'Type is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Check if wallet exists
    try:
        wallet = Wallet.objects.get(pk=wallet_id)
    except Wallet.DoesNotExist:
        return Response({'error': 'Wallet not found'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Check if user exists
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Validate status and type
    valid_statuses = ['pending', 'success', 'failed']
    valid_types = ['add', 'deducted']
    if status_val not in valid_statuses:
        return Response({'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'}, status=status.HTTP_400_BAD_REQUEST)
    if type_val not in valid_types:
        return Response({'error': f'Invalid type. Must be one of: {", ".join(valid_types)}'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Convert to Decimal
    try:
        amount = Decimal(str(amount))
        if balance_before:
            balance_before = Decimal(str(balance_before))
        else:
            balance_before = wallet.balance
        if balance_after:
            balance_after = Decimal(str(balance_after))
        else:
            balance_after = wallet.balance
    except (ValueError, TypeError):
        return Response({'error': 'Invalid decimal values'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Create transaction directly without serializer
    transaction = Transaction.objects.create(
        wallet=wallet,
        user=user,
        status=status_val,
        balance_before=balance_before,
        balance_after=balance_after,
        amount=amount,
        type=type_val,
        remarks=remarks,
    )
    
    # Return response
    return Response({
        'id': str(transaction.id),
        'status': transaction.status,
        'balance_before': str(transaction.balance_before),
        'balance_after': str(transaction.balance_after),
        'amount': str(transaction.amount),
        'wallet': str(transaction.wallet.id),
        'wallet_details': {
            'id': str(transaction.wallet.id),
            'user': str(transaction.wallet.user.id),
            'balance': str(transaction.wallet.balance),
            'to_pay': str(transaction.wallet.to_pay),
            'to_receive': str(transaction.wallet.to_receive),
        },
        'user': str(transaction.user.id),
        'user_details': {
            'id': str(transaction.user.id),
            'username': transaction.user.username,
            'phone': transaction.user.phone,
            'email': transaction.user.email or '',
            'name': transaction.user.name or '',
            'is_driver': transaction.user.is_driver,
            'is_active': transaction.user.is_active,
        },
        'type': transaction.type,
        'remarks': transaction.remarks or '',
        'created_at': transaction.created_at.isoformat(),
        'updated_at': transaction.updated_at.isoformat(),
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
def transaction_detail_get_view(request, pk):
    """Retrieve a single transaction"""
    try:
        transaction = Transaction.objects.select_related('wallet', 'user').get(pk=pk)
    except Transaction.DoesNotExist:
        return Response({'error': 'Transaction not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Return data without serializer
    return Response({
        'id': str(transaction.id),
        'status': transaction.status,
        'balance_before': str(transaction.balance_before),
        'balance_after': str(transaction.balance_after),
        'amount': str(transaction.amount),
        'wallet': str(transaction.wallet.id),
        'wallet_details': {
            'id': str(transaction.wallet.id),
            'user': str(transaction.wallet.user.id),
            'balance': str(transaction.wallet.balance),
            'to_pay': str(transaction.wallet.to_pay),
            'to_receive': str(transaction.wallet.to_receive),
        },
        'user': str(transaction.user.id),
        'user_details': {
            'id': str(transaction.user.id),
            'username': transaction.user.username,
            'phone': transaction.user.phone,
            'email': transaction.user.email or '',
            'name': transaction.user.name or '',
            'is_driver': transaction.user.is_driver,
            'is_active': transaction.user.is_active,
        },
        'type': transaction.type,
        'remarks': transaction.remarks or '',
        'created_at': transaction.created_at.isoformat(),
        'updated_at': transaction.updated_at.isoformat(),
    })


@api_view(['POST'])
def transaction_detail_post_view(request, pk):
    """Update/edit a transaction"""
    try:
        transaction = Transaction.objects.select_related('wallet', 'user').get(pk=pk)
    except Transaction.DoesNotExist:
        return Response({'error': 'Transaction not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Extract data from request.POST or request.data
    if 'status' in request.POST or 'status' in request.data:
        status_val = request.POST.get('status') or request.data.get('status')
        valid_statuses = ['pending', 'success', 'failed']
        if status_val not in valid_statuses:
            return Response({'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'}, status=status.HTTP_400_BAD_REQUEST)
        transaction.status = status_val
    
    if 'balance_before' in request.POST or 'balance_before' in request.data:
        balance_before = request.POST.get('balance_before') or request.data.get('balance_before')
        try:
            transaction.balance_before = Decimal(str(balance_before))
        except (ValueError, TypeError):
            return Response({'error': 'Invalid balance_before value'}, status=status.HTTP_400_BAD_REQUEST)
    
    if 'balance_after' in request.POST or 'balance_after' in request.data:
        balance_after = request.POST.get('balance_after') or request.data.get('balance_after')
        try:
            transaction.balance_after = Decimal(str(balance_after))
        except (ValueError, TypeError):
            return Response({'error': 'Invalid balance_after value'}, status=status.HTTP_400_BAD_REQUEST)
    
    if 'amount' in request.POST or 'amount' in request.data:
        amount = request.POST.get('amount') or request.data.get('amount')
        try:
            transaction.amount = Decimal(str(amount))
        except (ValueError, TypeError):
            return Response({'error': 'Invalid amount value'}, status=status.HTTP_400_BAD_REQUEST)
    
    if 'type' in request.POST or 'type' in request.data:
        type_val = request.POST.get('type') or request.data.get('type')
        valid_types = ['add', 'deducted']
        if type_val not in valid_types:
            return Response({'error': f'Invalid type. Must be one of: {", ".join(valid_types)}'}, status=status.HTTP_400_BAD_REQUEST)
        transaction.type = type_val
    
    if 'remarks' in request.POST or 'remarks' in request.data:
        remarks = request.POST.get('remarks') or request.data.get('remarks')
        transaction.remarks = remarks if remarks else None
    
    if 'wallet' in request.POST or 'wallet' in request.data:
        wallet_id = request.POST.get('wallet') or request.data.get('wallet')
        try:
            wallet = Wallet.objects.get(pk=wallet_id)
            transaction.wallet = wallet
        except Wallet.DoesNotExist:
            return Response({'error': 'Wallet not found'}, status=status.HTTP_400_BAD_REQUEST)
    
    if 'user' in request.POST or 'user' in request.data:
        user_id = request.POST.get('user') or request.data.get('user')
        try:
            user = User.objects.get(pk=user_id)
            transaction.user = user
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_400_BAD_REQUEST)
    
    transaction.save()
    
    # Return updated data
    return Response({
        'id': str(transaction.id),
        'status': transaction.status,
        'balance_before': str(transaction.balance_before),
        'balance_after': str(transaction.balance_after),
        'amount': str(transaction.amount),
        'wallet': str(transaction.wallet.id),
        'wallet_details': {
            'id': str(transaction.wallet.id),
            'user': str(transaction.wallet.user.id),
            'balance': str(transaction.wallet.balance),
            'to_pay': str(transaction.wallet.to_pay),
            'to_receive': str(transaction.wallet.to_receive),
        },
        'user': str(transaction.user.id),
        'user_details': {
            'id': str(transaction.user.id),
            'username': transaction.user.username,
            'phone': transaction.user.phone,
            'email': transaction.user.email or '',
            'name': transaction.user.name or '',
            'is_driver': transaction.user.is_driver,
            'is_active': transaction.user.is_active,
        },
        'type': transaction.type,
        'remarks': transaction.remarks or '',
        'created_at': transaction.created_at.isoformat(),
        'updated_at': transaction.updated_at.isoformat(),
    })


@api_view(['GET'])
def transaction_delete_get_view(request, pk):
    """Delete a transaction"""
    try:
        transaction = Transaction.objects.get(pk=pk)
        transaction.delete()
        return Response({'message': 'Transaction deleted successfully'})
    except Transaction.DoesNotExist:
        return Response({'error': 'Transaction not found'}, status=status.HTTP_404_NOT_FOUND)
