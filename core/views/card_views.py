"""Card list, search, and topup (wallet -> card)."""
from decimal import Decimal
from django.db import transaction as db_transaction
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from ..models import Card, Wallet, Transaction
from ..services.wallet_transaction import create_wallet_transaction


def _card_to_response(card):
    return {
        'id': str(card.id),
        'user': str(card.user_id) if card.user_id else None,
        'card_number': card.card_number,
        'balance': str(card.balance),
        'is_active': card.is_active,
        'created_at': card.created_at.isoformat(),
        'updated_at': card.updated_at.isoformat(),
    }


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def card_list_get_view(request):
    """List cards; default to current user's cards."""
    user_id = request.query_params.get('user')
    if user_id and request.user.is_authenticated and not getattr(request.user, 'is_superuser', False):
        if str(request.user.id) != str(user_id):
            user_id = str(request.user.id)
    if not user_id and request.user.is_authenticated:
        user_id = str(request.user.id)
    queryset = Card.objects.filter(is_active=True)
    if user_id:
        queryset = queryset.filter(user_id=user_id)
    page = int(request.query_params.get('page', 1))
    per_page = int(request.query_params.get('per_page', 20))
    start = (page - 1) * per_page
    end = start + per_page
    total = queryset.count()
    cards = queryset.order_by('-updated_at')[start:end]
    return Response({
        'results': [_card_to_response(c) for c in cards],
        'count': total,
        'page': page,
        'per_page': per_page,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def card_detail_get_view(request, pk):
    """Get single card by id."""
    try:
        card = Card.objects.get(pk=pk)
    except Card.DoesNotExist:
        return Response({'error': 'Card not found'}, status=status.HTTP_404_NOT_FOUND)
    if card.user_id and request.user.is_authenticated and not getattr(request.user, 'is_superuser', False):
        if card.user_id != request.user.id:
            return Response({'error': 'Card not found'}, status=status.HTTP_404_NOT_FOUND)
    return Response(_card_to_response(card))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def card_search_by_number_view(request):
    """Search card by number (query param card_number). For topup flow."""
    card_number = (request.query_params.get('card_number') or '').strip()
    if not card_number:
        return Response({'error': 'card_number is required'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        card = Card.objects.get(card_number=card_number, is_active=True)
    except Card.DoesNotExist:
        return Response({'error': 'Card not found'}, status=status.HTTP_404_NOT_FOUND)
    return Response(_card_to_response(card))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def card_topup_view(request, pk):
    """Topup card from current user's wallet. Deducts wallet, adds to card, creates both transactions."""
    amount = request.data.get('amount') if request.data else request.POST.get('amount')
    if amount is None:
        return Response({'error': 'amount is required'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        amount = Decimal(str(amount))
    except (ValueError, TypeError):
        return Response({'error': 'Invalid amount'}, status=status.HTTP_400_BAD_REQUEST)
    if amount <= 0:
        return Response({'error': 'Amount must be positive'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        card = Card.objects.get(pk=pk, is_active=True)
    except Card.DoesNotExist:
        return Response({'error': 'Card not found'}, status=status.HTTP_404_NOT_FOUND)
    try:
        wallet = Wallet.objects.get(user=request.user)
    except Wallet.DoesNotExist:
        return Response({'error': 'Wallet not found'}, status=status.HTTP_400_BAD_REQUEST)
    if wallet.balance < amount:
        return Response(
            {'error': 'Insufficient wallet balance', 'code': 'insufficient_balance'},
            status=status.HTTP_400_BAD_REQUEST
        )
    with db_transaction.atomic():
        wallet.balance -= amount
        wallet.save(update_fields=['balance', 'updated_at'])
        create_wallet_transaction(
            wallet=wallet,
            user=request.user,
            amount=amount,
            type='deducted',
            remarks=f'Card topup {card.card_number}',
            status='success',
        )
        card.balance += amount
        card.save(update_fields=['balance', 'updated_at'])
        # Record card-side transaction (wallet already deducted; this is for card history)
        Transaction.objects.create(
            wallet=wallet,
            user=request.user,
            card=card,
            status='success',
            balance_before=wallet.balance,
            balance_after=wallet.balance,
            amount=amount,
            type='deducted',
            remarks=f'Card topup {card.card_number}',
        )
    card.refresh_from_db()
    return Response(_card_to_response(card))
