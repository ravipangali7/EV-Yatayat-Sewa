"""NCHL ConnectIPS payment: initiate, validate, callback, list transactions."""
import uuid
from decimal import Decimal
from django.utils import timezone
from django.db import transaction as db_transaction
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings

from ..models import PaymentTransaction, Wallet, User, Card
from ..services.wallet_transaction import create_wallet_transaction
from ..services import nchl_connectips
from booking.models import VehicleTicketBooking


MIN_AMOUNT_NPR = 10
PURPOSE_WALLET_DEPOSIT = 'wallet_deposit'
PURPOSE_CARD_TOPUP = 'card_topup'
PURPOSE_VEHICLE_TICKET_BOOKING = 'vehicle_ticket_booking'


def _payment_transaction_to_response(pt):
    return {
        'id': str(pt.id),
        'user': str(pt.user_id),
        'amount': str(pt.amount),
        'amount_paisa': pt.amount_paisa,
        'status': pt.status,
        'reference_id': pt.reference_id,
        'txn_id': pt.reference_id,
        'connectips_txn_id': pt.connectips_txn_id,
        'connectips_batch_id': pt.connectips_batch_id,
        'error_message': pt.error_message,
        'purpose': pt.purpose,
        'card': str(pt.card_id) if pt.card_id else None,
        'vehicle_ticket_booking': str(pt.vehicle_ticket_booking_id) if pt.vehicle_ticket_booking_id else None,
        'created_at': pt.created_at.isoformat(),
        'updated_at': pt.updated_at.isoformat(),
        'completed_at': pt.completed_at.isoformat() if pt.completed_at else None,
    }


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def payment_initiate_view(request):
    """
    Create PENDING PaymentTransaction and return form data for NCHL gateway.
    Body: amount (NPR, min 10), remarks?, particulars?, purpose?, card_id?, vehicle_ticket_booking_id?
    """
    data = request.data or request.POST
    amount = data.get('amount')
    if amount is None:
        return Response({'error': 'amount is required'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        amount = Decimal(str(amount))
    except (ValueError, TypeError):
        return Response({'error': 'Invalid amount'}, status=status.HTTP_400_BAD_REQUEST)
    if amount < MIN_AMOUNT_NPR:
        return Response(
            {'error': f'Minimum amount is {MIN_AMOUNT_NPR} NPR'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    remarks = (data.get('remarks') or '').strip()
    particulars = (data.get('particulars') or '').strip()
    purpose = (data.get('purpose') or PURPOSE_WALLET_DEPOSIT).strip()
    card_id = data.get('card_id')
    vehicle_ticket_booking_id = data.get('vehicle_ticket_booking_id')

    if purpose not in (PURPOSE_WALLET_DEPOSIT, PURPOSE_CARD_TOPUP, PURPOSE_VEHICLE_TICKET_BOOKING):
        return Response({'error': 'Invalid purpose'}, status=status.HTTP_400_BAD_REQUEST)
    if purpose == PURPOSE_CARD_TOPUP and not card_id:
        return Response({'error': 'card_id required for card_topup'}, status=status.HTTP_400_BAD_REQUEST)
    if purpose == PURPOSE_VEHICLE_TICKET_BOOKING and not vehicle_ticket_booking_id:
        return Response(
            {'error': 'vehicle_ticket_booking_id required for vehicle_ticket_booking'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    card = None
    if card_id:
        try:
            card = Card.objects.get(pk=card_id, is_active=True)
        except Card.DoesNotExist:
            return Response({'error': 'Card not found'}, status=status.HTTP_400_BAD_REQUEST)

    booking = None
    if vehicle_ticket_booking_id:
        try:
            booking = VehicleTicketBooking.objects.get(pk=vehicle_ticket_booking_id)
        except VehicleTicketBooking.DoesNotExist:
            return Response({'error': 'Vehicle ticket booking not found'}, status=status.HTTP_400_BAD_REQUEST)
        if booking.is_paid:
            return Response({'error': 'Booking is already paid'}, status=status.HTTP_400_BAD_REQUEST)
        if booking.user_id != request.user.id and (not booking.booked_by_id or booking.booked_by_id != request.user.id):
            if not request.user.is_superuser:
                return Response({'error': 'Not your booking'}, status=status.HTTP_403_FORBIDDEN)

    reference_id = f"TXN-{uuid.uuid4().hex[:12].upper()}"
    amount_paisa = int(amount * 100)
    frontend_url = (getattr(settings, 'FRONTEND_URL', '') or '').strip()
    if not frontend_url and request.build_absolute_uri:
        try:
            frontend_url = request.build_absolute_uri('/').rstrip('/').replace('/api', '')
        except Exception:
            pass
    callback_path = '/app/payment/callback'
    success_url = f"{frontend_url}{callback_path}?txn_id={reference_id}&status=success"
    failure_url = f"{frontend_url}{callback_path}?txn_id={reference_id}&status=failure"

    try:
        form_data = nchl_connectips.build_initiate_form_data(
            reference_id=reference_id,
            amount_npr=float(amount),
            remarks=remarks,
            particulars=particulars,
            success_url=success_url,
            failure_url=failure_url,
        )
    except Exception as e:
        return Response(
            {'error': 'Failed to build payment form', 'detail': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    pt = PaymentTransaction.objects.create(
        user=request.user,
        amount=amount,
        amount_paisa=amount_paisa,
        status='pending',
        reference_id=reference_id,
        purpose=purpose,
        card=card,
        vehicle_ticket_booking=booking,
    )
    return Response(form_data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def payment_validate_view(request):
    """
    Validate by txn_id (reference_id). Call NCHL validatetxn; on success credit wallet
    and optionally perform card topup or ticket booking pay.
    """
    data = request.data or request.POST
    qp = getattr(request, 'query_params', None) or request.GET
    txn_id = (
        (data.get('txn_id') or data.get('TXNID'))
        or (qp.get('txn_id') or qp.get('TXNID'))
        or ''
    )
    if isinstance(txn_id, list):
        txn_id = (txn_id[0] or '').strip()
    else:
        txn_id = (txn_id or '').strip()
    if not txn_id:
        return Response({'error': 'txn_id is required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        pt = PaymentTransaction.objects.select_related('user', 'card', 'vehicle_ticket_booking').get(
            reference_id=txn_id
        )
    except PaymentTransaction.DoesNotExist:
        return Response({'error': 'Payment transaction not found'}, status=status.HTTP_404_NOT_FOUND)
    if pt.user_id != request.user.id and not request.user.is_superuser:
        return Response({'error': 'Not your payment'}, status=status.HTTP_403_FORBIDDEN)
    if pt.status == 'success':
        return Response(_payment_transaction_to_response(pt))
    if pt.status == 'failed':
        return Response(
            _payment_transaction_to_response(pt),
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        nchl_resp = nchl_connectips.validatetxn(pt.reference_id, pt.amount_paisa)
    except Exception as e:
        pt.status = 'failed'
        pt.error_message = str(e)
        pt.save(update_fields=['status', 'error_message', 'updated_at'])
        return Response(
            {'error': 'Validation failed', 'detail': str(e), 'payment': _payment_transaction_to_response(pt)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    nchl_status = (nchl_resp.get('status') or nchl_resp.get('Status') or '').upper()
    if nchl_status != 'SUCCESS':
        pt.status = 'failed'
        pt.error_message = nchl_resp.get('responseMessage') or nchl_resp.get('message') or str(nchl_resp)
        pt.save(update_fields=['status', 'error_message', 'updated_at'])
        return Response(
            {'error': 'Payment not successful', 'payment': _payment_transaction_to_response(pt)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    pt.connectips_txn_id = nchl_resp.get('transactionId') or nchl_resp.get('transactionID') or ''
    pt.connectips_batch_id = nchl_resp.get('batchId') or nchl_resp.get('batchID') or ''
    pt.status = 'success'
    pt.completed_at = timezone.now()
    pt.save(update_fields=['connectips_txn_id', 'connectips_batch_id', 'status', 'completed_at', 'updated_at'])

    wallet, _ = Wallet.objects.get_or_create(user=pt.user, defaults={'balance': 0, 'to_pay': 0, 'to_receive': 0})
    amount = pt.amount

    with db_transaction.atomic():
        wallet.balance += amount
        wallet.save(update_fields=['balance', 'updated_at'])
        create_wallet_transaction(
            wallet=wallet,
            user=pt.user,
            amount=amount,
            type='add',
            remarks='NCHL ConnectIPS payment',
            status='success',
        )

        if pt.purpose == PURPOSE_CARD_TOPUP and pt.card_id:
            card = Card.objects.get(pk=pt.card_id)
            if wallet.balance >= amount:
                wallet.balance -= amount
                wallet.save(update_fields=['balance', 'updated_at'])
                create_wallet_transaction(
                    wallet=wallet,
                    user=pt.user,
                    amount=amount,
                    type='deducted',
                    remarks=f'Card topup {card.card_number}',
                    status='success',
                )
                card.balance += amount
                card.save(update_fields=['balance', 'updated_at'])
                from ..models import Transaction
                Transaction.objects.create(
                    wallet=wallet,
                    user=pt.user,
                    card=card,
                    status='success',
                    balance_before=wallet.balance,
                    balance_after=wallet.balance,
                    amount=amount,
                    type='deducted',
                    remarks=f'Card topup {card.card_number}',
                )

        if pt.purpose == PURPOSE_VEHICLE_TICKET_BOOKING and pt.vehicle_ticket_booking_id:
            b = VehicleTicketBooking.objects.select_related('vehicle_schedule').get(pk=pt.vehicle_ticket_booking_id)
            if not b.is_paid and wallet.balance >= amount:
                wallet.balance -= amount
                wallet.save(update_fields=['balance', 'updated_at'])
                create_wallet_transaction(
                    wallet=wallet,
                    user=pt.user,
                    amount=amount,
                    type='deducted',
                    remarks=f'Ticket payment {b.pnr}',
                    status='success',
                )
                b.is_paid = True
                b.save(update_fields=['is_paid', 'updated_at'])
                commission = Decimal('0')
                if getattr(pt.user, 'is_ticket_dealer', False) and getattr(pt.user, 'ticket_commission', None):
                    try:
                        commission = amount * (pt.user.ticket_commission / Decimal('100'))
                    except (TypeError, ValueError):
                        pass
                if commission > 0:
                    wallet.balance += commission
                    wallet.save(update_fields=['balance', 'updated_at'])
                    create_wallet_transaction(
                        wallet=wallet,
                        user=pt.user,
                        amount=commission,
                        type='add',
                        remarks=f'Commission for {b.pnr}',
                        status='success',
                    )

    pt.refresh_from_db()
    return Response(_payment_transaction_to_response(pt))


@api_view(['GET'])
@permission_classes([AllowAny])
def payment_callback_get_view(request):
    """
    Optional GET callback when redirect goes to backend. Query: txn_id, status.
    If authenticated, runs validation and returns JSON; else 401.
    Frontend typically redirects to its own callback page and calls POST validate.
    """
    txn_id = request.query_params.get('txn_id') or request.query_params.get('TXNID', '')
    if not txn_id:
        return Response({'error': 'txn_id required'}, status=status.HTTP_400_BAD_REQUEST)
    if not request.user.is_authenticated:
        return Response(
            {'error': 'Authentication required. Use frontend callback page or POST /api/payment/validate/ with txn_id.'},
            status=status.HTTP_401_UNAUTHORIZED,
        )
    return payment_validate_view(request)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def payment_transaction_list_view(request):
    """List payment transactions for current user; superuser sees all."""
    queryset = PaymentTransaction.objects.filter(user=request.user).order_by('-created_at')
    if getattr(request.user, 'is_superuser', False):
        queryset = PaymentTransaction.objects.all().order_by('-created_at')
    page = int(request.query_params.get('page', 1))
    per_page = int(request.query_params.get('per_page', 10))
    start = (page - 1) * per_page
    end = start + per_page
    total = queryset.count()
    items = queryset[start:end]
    return Response({
        'results': [_payment_transaction_to_response(pt) for pt in items],
        'count': total,
        'page': page,
        'per_page': per_page,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def payment_transaction_detail_view(request, pk):
    """Get single payment transaction."""
    try:
        pt = PaymentTransaction.objects.get(pk=pk)
    except PaymentTransaction.DoesNotExist:
        return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
    if pt.user_id != request.user.id and not getattr(request.user, 'is_superuser', False):
        return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
    return Response(_payment_transaction_to_response(pt))
