from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q
from decimal import Decimal
from ..models import Transaction, Wallet, User


def _transaction_to_response(transaction):
    """Build transaction dict for API response including optional card."""
    data = {
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
    }
    data['card'] = str(transaction.card_id) if transaction.card_id else None
    if transaction.card_id and getattr(transaction, 'card', None):
        data['card_details'] = {
            'id': str(transaction.card.id),
            'card_number': transaction.card.card_number,
            'balance': str(transaction.card.balance),
            'is_active': transaction.card.is_active,
        }
    else:
        data['card_details'] = None
    return data


@api_view(['GET'])
def transaction_list_get_view(request):
    """List all transactions"""
    # Get query parameters
    search = request.query_params.get('search', '')
    status_filter = request.query_params.get('status', None)
    type_filter = request.query_params.get('type', None)
    wallet_id = request.query_params.get('wallet', None)
    user_id = request.query_params.get('user', None)
    card_id = request.query_params.get('card', None)
    
    # Build queryset
    queryset = Transaction.objects.select_related('wallet', 'user', 'card').all()
    
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
    
    if card_id:
        queryset = queryset.filter(card_id=card_id)
    
    # Pagination
    page = int(request.query_params.get('page', 1))
    per_page = int(request.query_params.get('per_page', 10))
    start = (page - 1) * per_page
    end = start + per_page
    
    total = queryset.count()
    transactions = queryset[start:end]
    
    results = [_transaction_to_response(t) for t in transactions]
    return Response({
        'results': results,
        'count': total,
        'page': page,
        'per_page': per_page
    })


@api_view(['POST'])
def transaction_list_post_view(request):
    """Create a new transaction"""
    from ..models import Card
    data = request.data or request.POST
    wallet_id = request.POST.get('wallet') or data.get('wallet')
    user_id = request.POST.get('user') or data.get('user')
    card_id = request.POST.get('card') or data.get('card')
    status_val = request.POST.get('status') or data.get('status', 'pending')
    balance_before = request.POST.get('balance_before') or data.get('balance_before')
    balance_after = request.POST.get('balance_after') or data.get('balance_after')
    amount = request.POST.get('amount') or data.get('amount')
    type_val = request.POST.get('type') or data.get('type')
    remarks = request.POST.get('remarks') or data.get('remarks') or None
    
    if not wallet_id:
        return Response({'error': 'Wallet is required'}, status=status.HTTP_400_BAD_REQUEST)
    if not user_id:
        return Response({'error': 'User is required'}, status=status.HTTP_400_BAD_REQUEST)
    if not amount:
        return Response({'error': 'Amount is required'}, status=status.HTTP_400_BAD_REQUEST)
    if not type_val:
        return Response({'error': 'Type is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        wallet = Wallet.objects.get(pk=wallet_id)
    except Wallet.DoesNotExist:
        return Response({'error': 'Wallet not found'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_400_BAD_REQUEST)
    
    card = None
    if card_id:
        try:
            card = Card.objects.get(pk=card_id)
        except Card.DoesNotExist:
            return Response({'error': 'Card not found'}, status=status.HTTP_400_BAD_REQUEST)
    
    valid_statuses = ['pending', 'success', 'failed']
    valid_types = ['add', 'deducted']
    if status_val not in valid_statuses:
        return Response({'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'}, status=status.HTTP_400_BAD_REQUEST)
    if type_val not in valid_types:
        return Response({'error': f'Invalid type. Must be one of: {", ".join(valid_types)}'}, status=status.HTTP_400_BAD_REQUEST)
    
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
    
    transaction = Transaction.objects.create(
        wallet=wallet,
        user=user,
        card=card,
        status=status_val,
        balance_before=balance_before,
        balance_after=balance_after,
        amount=amount,
        type=type_val,
        remarks=remarks,
    )
    return Response(_transaction_to_response(transaction), status=status.HTTP_201_CREATED)


@api_view(['GET'])
def transaction_detail_get_view(request, pk):
    """Retrieve a single transaction"""
    try:
        transaction = Transaction.objects.select_related('wallet', 'user', 'card').get(pk=pk)
    except Transaction.DoesNotExist:
        return Response({'error': 'Transaction not found'}, status=status.HTTP_404_NOT_FOUND)
    return Response(_transaction_to_response(transaction))


@api_view(['POST'])
def transaction_detail_post_view(request, pk):
    """Update/edit a transaction"""
    from ..models import Card
    try:
        transaction = Transaction.objects.select_related('wallet', 'user', 'card').get(pk=pk)
    except Transaction.DoesNotExist:
        return Response({'error': 'Transaction not found'}, status=status.HTTP_404_NOT_FOUND)
    data = request.data or request.POST
    if 'status' in request.POST or 'status' in data:
        status_val = request.POST.get('status') or data.get('status')
        valid_statuses = ['pending', 'success', 'failed']
        if status_val not in valid_statuses:
            return Response({'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'}, status=status.HTTP_400_BAD_REQUEST)
        transaction.status = status_val
    
    if 'balance_before' in request.POST or 'balance_before' in data:
        balance_before = request.POST.get('balance_before') or data.get('balance_before')
        try:
            transaction.balance_before = Decimal(str(balance_before))
        except (ValueError, TypeError):
            return Response({'error': 'Invalid balance_before value'}, status=status.HTTP_400_BAD_REQUEST)
    
    if 'balance_after' in request.POST or 'balance_after' in data:
        balance_after = request.POST.get('balance_after') or data.get('balance_after')
        try:
            transaction.balance_after = Decimal(str(balance_after))
        except (ValueError, TypeError):
            return Response({'error': 'Invalid balance_after value'}, status=status.HTTP_400_BAD_REQUEST)
    
    if 'amount' in request.POST or 'amount' in data:
        amount = request.POST.get('amount') or data.get('amount')
        try:
            transaction.amount = Decimal(str(amount))
        except (ValueError, TypeError):
            return Response({'error': 'Invalid amount value'}, status=status.HTTP_400_BAD_REQUEST)
    
    if 'type' in request.POST or 'type' in data:
        type_val = request.POST.get('type') or data.get('type')
        valid_types = ['add', 'deducted']
        if type_val not in valid_types:
            return Response({'error': f'Invalid type. Must be one of: {", ".join(valid_types)}'}, status=status.HTTP_400_BAD_REQUEST)
        transaction.type = type_val
    
    if 'remarks' in request.POST or 'remarks' in data:
        remarks = request.POST.get('remarks') or data.get('remarks')
        transaction.remarks = remarks if remarks else None
    
    if 'card' in request.POST or 'card' in data:
        card_id = request.POST.get('card') or data.get('card')
        if card_id:
            try:
                transaction.card = Card.objects.get(pk=card_id)
            except Card.DoesNotExist:
                return Response({'error': 'Card not found'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            transaction.card = None
    
    if 'wallet' in request.POST or 'wallet' in data:
        wallet_id = request.POST.get('wallet') or data.get('wallet')
        try:
            wallet = Wallet.objects.get(pk=wallet_id)
            transaction.wallet = wallet
        except Wallet.DoesNotExist:
            return Response({'error': 'Wallet not found'}, status=status.HTTP_400_BAD_REQUEST)
    
    if 'user' in request.POST or 'user' in data:
        user_id = request.POST.get('user') or data.get('user')
        try:
            user = User.objects.get(pk=user_id)
            transaction.user = user
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_400_BAD_REQUEST)
    
    transaction.save()
    return Response(_transaction_to_response(transaction))


@api_view(['GET'])
def transaction_delete_get_view(request, pk):
    """Delete a transaction"""
    try:
        transaction = Transaction.objects.get(pk=pk)
        transaction.delete()
        return Response({'message': 'Transaction deleted successfully'})
    except Transaction.DoesNotExist:
        return Response({'error': 'Transaction not found'}, status=status.HTTP_404_NOT_FOUND)
