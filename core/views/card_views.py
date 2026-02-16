"""Card list, search, topup, and admin CRUD (create, update, delete)."""
from decimal import Decimal
from django.db import transaction as db_transaction
from django.db.models import Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from ..models import Card, Wallet, Transaction
from ..services.wallet_transaction import create_wallet_transaction


def _card_to_response(card):
    """Build card dict; include user_details when user is loaded (select_related)."""
    data = {
        'id': str(card.id),
        'user': str(card.user_id) if card.user_id else None,
        'card_number': card.card_number,
        'balance': str(card.balance),
        'is_active': card.is_active,
        'created_at': card.created_at.isoformat(),
        'updated_at': card.updated_at.isoformat(),
    }
    if getattr(card, 'user', None):
        u = card.user
        data['user_details'] = {
            'id': str(u.id),
            'name': u.name or '',
            'phone': u.phone or '',
        }
    else:
        data['user_details'] = None
    return data


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def card_list_get_view(request):
    """List cards. Non-superuser: only own cards. Superuser: all cards. Supports search (card_number, user phone/name)."""
    user_id = request.query_params.get('user')
    search = (request.query_params.get('search') or '').strip()
    is_superuser = getattr(request.user, 'is_superuser', False)
    if user_id and not is_superuser and request.user.is_authenticated:
        if str(request.user.id) != str(user_id):
            user_id = str(request.user.id)
    if not user_id and request.user.is_authenticated and not is_superuser:
        user_id = str(request.user.id)
    queryset = Card.objects.select_related('user').all()
    if not is_superuser:
        queryset = queryset.filter(is_active=True)
    if user_id:
        queryset = queryset.filter(user_id=user_id)
    if search:
        queryset = queryset.filter(
            Q(card_number__icontains=search) |
            Q(user__phone__icontains=search) |
            Q(user__name__icontains=search)
        )
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
        'stats': {'total_count': total},
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def card_detail_get_view(request, pk):
    """Get single card by id. Include user_details."""
    try:
        card = Card.objects.select_related('user').get(pk=pk)
    except Card.DoesNotExist:
        return Response({'error': 'Card not found'}, status=status.HTTP_404_NOT_FOUND)
    if card.user_id and request.user.is_authenticated and not getattr(request.user, 'is_superuser', False):
        if card.user_id != request.user.id:
            return Response({'error': 'Card not found'}, status=status.HTTP_404_NOT_FOUND)
    return Response(_card_to_response(card))


@api_view(['POST'])
def card_list_post_view(request):
    """Create a new card (admin). Body: user (optional), card_number, balance, is_active."""
    user_id = request.POST.get('user') or (request.data.get('user') if request.data else None)
    card_number = (request.POST.get('card_number') or (request.data.get('card_number') if request.data else None) or '')
    card_number = card_number.strip()
    balance = request.POST.get('balance') or (request.data.get('balance') if request.data else '0')
    is_active = request.POST.get('is_active') or (request.data.get('is_active') if request.data else 'true')
    if not card_number:
        return Response({'error': 'card_number is required'}, status=status.HTTP_400_BAD_REQUEST)
    if Card.objects.filter(card_number=card_number).exists():
        return Response({'error': 'A card with this card_number already exists'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        balance = Decimal(str(balance))
    except (ValueError, TypeError):
        return Response({'error': 'Invalid balance'}, status=status.HTTP_400_BAD_REQUEST)
    is_active = is_active.lower() == 'true' if isinstance(is_active, str) else bool(is_active)
    user = None
    if user_id:
        try:
            from ..models import User
            user = User.objects.get(pk=user_id)
        except Exception:
            return Response({'error': 'User not found'}, status=status.HTTP_400_BAD_REQUEST)
    card = Card.objects.create(
        user=user,
        card_number=card_number,
        balance=balance,
        is_active=is_active,
    )
    return Response(_card_to_response(card), status=status.HTTP_201_CREATED)


@api_view(['POST'])
def card_detail_put_or_patch_view(request, pk):
    """Update card (admin). Body: user, card_number, balance, is_active."""
    try:
        card = Card.objects.select_related('user').get(pk=pk)
    except Card.DoesNotExist:
        return Response({'error': 'Card not found'}, status=status.HTTP_404_NOT_FOUND)
    data = request.data if request.data else request.POST
    if 'card_number' in data:
        val = (data.get('card_number') or '').strip()
        if val and val != card.card_number:
            if Card.objects.filter(card_number=val).exclude(pk=pk).exists():
                return Response({'error': 'A card with this card_number already exists'}, status=status.HTTP_400_BAD_REQUEST)
            card.card_number = val
    if 'balance' in data:
        try:
            card.balance = Decimal(str(data.get('balance') or 0))
        except (ValueError, TypeError):
            return Response({'error': 'Invalid balance'}, status=status.HTTP_400_BAD_REQUEST)
    if 'is_active' in data:
        card.is_active = (str(data.get('is_active')).lower() == 'true')
    if 'user' in data:
        user_id = data.get('user')
        if user_id:
            try:
                from ..models import User
                card.user = User.objects.get(pk=user_id)
            except Exception:
                return Response({'error': 'User not found'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            card.user = None
    card.save()
    return Response(_card_to_response(card))


@api_view(['GET'])
def card_delete_get_view(request, pk):
    """Delete card (hard delete). Admin only recommended."""
    try:
        card = Card.objects.get(pk=pk)
    except Card.DoesNotExist:
        return Response({'error': 'Card not found'}, status=status.HTTP_404_NOT_FOUND)
    card.delete()
    return Response({'message': 'Card deleted'}, status=status.HTTP_200_OK)


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
