"""NepalPay Gateway QR payment: initiate QR, posting callback, status, list."""
import base64
import uuid
from decimal import Decimal
from django.utils import timezone
from django.db import transaction as db_transaction
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings

from ..models import PaymentTransaction, Wallet, User, Card, Transaction
from ..services.wallet_transaction import create_wallet_transaction
from ..services import nepalpay_gateway_qr
from booking.models import VehicleTicketBooking


STATUS_PENDING = 'pending'
STATUS_SUCCESS = 'success'
STATUS_FAILED = 'failed'


def _mark_pending_wallet_tx_failed(user, reference_id):
    """If a pending wallet Transaction exists for this QR payment reference, mark it failed."""
    if not reference_id:
        return
    Transaction.objects.filter(
        user=user,
        status=STATUS_PENDING,
        remarks__icontains=f"ref {reference_id}",
    ).update(status=STATUS_FAILED, updated_at=timezone.now())


def _format_seat_remarks(seat_field):
    """Format seat field for transaction remarks, e.g. 'A1, B2'."""
    if not seat_field:
        return ''
    if isinstance(seat_field, list):
        seats = [s for s in seat_field if isinstance(s, dict) and s.get('side') is not None and s.get('number') is not None]
    elif isinstance(seat_field, dict) and seat_field.get('side') is not None and seat_field.get('number') is not None:
        seats = [seat_field]
    else:
        return ''
    return ', '.join(f"{s.get('side', '')}{s.get('number', '')}" for s in seats)


MIN_AMOUNT_NPR = 10
PURPOSE_WALLET_DEPOSIT = 'wallet_deposit'
PURPOSE_CARD_TOPUP = 'card_topup'
PURPOSE_VEHICLE_TICKET_BOOKING = 'vehicle_ticket_booking'
PURPOSE_PAY_DUE = 'pay_due'
VALID_PURPOSES = (PURPOSE_WALLET_DEPOSIT, PURPOSE_CARD_TOPUP, PURPOSE_VEHICLE_TICKET_BOOKING, PURPOSE_PAY_DUE)


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
    if not particulars:
        particulars = remarks
    purpose = (data.get('purpose') or PURPOSE_WALLET_DEPOSIT).strip()
    card_id = data.get('card_id')
    vehicle_ticket_booking_id = data.get('vehicle_ticket_booking_id')
    return_to = (data.get('return_to') or '').strip()

    if purpose not in VALID_PURPOSES:
        return Response({'error': 'Invalid purpose'}, status=status.HTTP_400_BAD_REQUEST)
    if purpose == PURPOSE_CARD_TOPUP and not card_id:
        return Response({'error': 'card_id required for card_topup'}, status=status.HTTP_400_BAD_REQUEST)
    if purpose == PURPOSE_VEHICLE_TICKET_BOOKING and not vehicle_ticket_booking_id:
        return Response(
            {'error': 'vehicle_ticket_booking_id required for vehicle_ticket_booking'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if purpose == PURPOSE_PAY_DUE:
        wallet = Wallet.objects.filter(user=request.user).first()
        if not wallet:
            return Response({'error': 'No wallet found'}, status=status.HTTP_400_BAD_REQUEST)
        if amount > wallet.to_pay:
            return Response(
                {'error': f'Amount cannot exceed due amount (Rs. {wallet.to_pay})'},
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
    success_url = f"{frontend_url}/payment/callback/success?TXNID={reference_id}"
    failure_url = f"{frontend_url}/payment/callback/failure?TXNID={reference_id}"
    if return_to:
        success_url += f"&return_to={return_to}"
        failure_url += f"&return_to={return_to}"

    pt = PaymentTransaction.objects.create(
        user=request.user,
        amount=amount,
        amount_paisa=amount_paisa,
        status=STATUS_PENDING,
        reference_id=reference_id,
        purpose=purpose,
        card=card,
        vehicle_ticket_booking=booking,
    )

    pending_wallet_tx = None
    if purpose in (PURPOSE_WALLET_DEPOSIT, PURPOSE_CARD_TOPUP, PURPOSE_PAY_DUE):
        wallet_obj, _ = Wallet.objects.get_or_create(
            user=request.user,
            defaults={'balance': Decimal('0.00'), 'to_pay': Decimal('0.00'), 'to_receive': Decimal('0.00')},
        )
        if purpose == PURPOSE_WALLET_DEPOSIT:
            purpose_label = 'Wallet deposit'
            tx_type = 'add'
        elif purpose == PURPOSE_CARD_TOPUP:
            purpose_label = f"Card topup {card.card_number}" if card else 'Card topup'
            tx_type = 'deducted'
        else:
            purpose_label = 'Pay due'
            tx_type = 'deducted'
        pending_wallet_tx = Transaction.objects.create(
            wallet=wallet_obj,
            user=request.user,
            card=card,
            status=STATUS_PENDING,
            balance_before=wallet_obj.balance,
            balance_after=wallet_obj.balance,
            amount=amount,
            type=tx_type,
            remarks=f"{purpose_label} via QR (ref {reference_id})",
        )

    try:
        qr = nepalpay_gateway_qr.generate_dynamic_qr(
            bill_number=reference_id,
            amount_npr=amount,
            purpose=remarks or purpose,
            reference_label=reference_id,
        )
    except Exception as e:
        pt.status = STATUS_FAILED
        pt.error_message = str(e)
        pt.save(update_fields=['status', 'error_message', 'updated_at'])
        if pending_wallet_tx is not None:
            pending_wallet_tx.status = STATUS_FAILED
            pending_wallet_tx.save(update_fields=['status', 'updated_at'])
        return Response(
            {'error': 'Failed to generate payment QR', 'detail': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    pt.connectips_txn_id = qr.get('validation_trace_id') or ''
    pt.save(update_fields=['connectips_txn_id', 'updated_at'])
    return Response({
        'qr_string': qr['qr_string'],
        'validation_trace_id': qr.get('validation_trace_id') or '',
        'reference_id': reference_id,
        'txn_id': reference_id,
        'payment_id': pt.id,
        'amount': str(amount),
        'success_url': success_url,
        'failure_url': failure_url,
    })


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
    if pt.status == STATUS_SUCCESS:
        return Response(_payment_transaction_to_response(pt))
    if pt.status == STATUS_FAILED:
        _mark_pending_wallet_tx_failed(pt.user, pt.reference_id)
        return Response(
            _payment_transaction_to_response(pt),
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        paid_row = nepalpay_gateway_qr.find_successful_txn(pt.connectips_txn_id or '')
    except Exception as e:
        return Response(
            {'error': 'Could not check payment status', 'detail': str(e), 'payment': _payment_transaction_to_response(pt)},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if not paid_row:
        return Response(
            {'error': 'Payment not completed yet', 'payment': _payment_transaction_to_response(pt)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    pt = _credit_paid_payment(pt, paid_row.get('nQrTxnId') or paid_row.get('instructionId') or '')
    return Response(_payment_transaction_to_response(pt))


def _credit_paid_payment(pt, batch_id=''):
    """Mark a pending payment successful and apply wallet, card, or ticket effects once."""
    with db_transaction.atomic():
        locked = PaymentTransaction.objects.select_for_update().select_related(
            'user', 'card', 'vehicle_ticket_booking'
        ).get(pk=pt.pk)
        if locked.status == STATUS_SUCCESS:
            return locked

        wallet, _ = Wallet.objects.select_for_update().get_or_create(
            user=locked.user,
            defaults={'balance': Decimal('0.00'), 'to_pay': Decimal('0.00'), 'to_receive': Decimal('0.00')},
        )
        amount = locked.amount
        pt = locked

        existing_tx = (
            Transaction.objects.select_for_update()
            .filter(wallet=wallet, remarks__icontains=f"ref {locked.reference_id}")
            .order_by('-created_at')
            .first()
        )

        if pt.purpose == PURPOSE_CARD_TOPUP and not pt.card_id:
            locked.status = STATUS_FAILED
            locked.error_message = 'Card not found for card_topup'
            locked.save(update_fields=['status', 'error_message', 'updated_at'])
            if existing_tx:
                existing_tx.status = STATUS_FAILED
                existing_tx.save(update_fields=['status', 'updated_at'])
            return locked

        locked.connectips_batch_id = batch_id or locked.connectips_batch_id
        locked.status = STATUS_SUCCESS
        locked.completed_at = timezone.now()
        locked.error_message = ''
        locked.save(update_fields=[
            'connectips_batch_id', 'status', 'completed_at', 'error_message', 'updated_at',
        ])

        if pt.purpose == PURPOSE_PAY_DUE:
            balance_before = wallet.balance
            wallet.to_pay = max(Decimal('0.00'), wallet.to_pay - amount)
            wallet.save(update_fields=['to_pay', 'updated_at'])
            remarks_str = f"Pay due via QR (ref {locked.reference_id})"
            if existing_tx:
                existing_tx.status = STATUS_SUCCESS
                existing_tx.type = 'deducted'
                existing_tx.amount = amount
                existing_tx.balance_before = balance_before
                existing_tx.balance_after = wallet.balance
                existing_tx.remarks = remarks_str
                existing_tx.save(update_fields=['status', 'type', 'amount', 'balance_before', 'balance_after', 'remarks', 'updated_at'])
            else:
                create_wallet_transaction(
                    wallet=wallet,
                    user=pt.user,
                    amount=amount,
                    type='deducted',
                    remarks=remarks_str,
                    status=STATUS_SUCCESS,
                    balance_before=balance_before,
                    balance_after=wallet.balance,
                )

        elif pt.purpose == PURPOSE_WALLET_DEPOSIT:
            balance_before = wallet.balance
            wallet.balance += amount
            wallet.save(update_fields=['balance', 'updated_at'])
            remarks_str = f"Wallet deposit via QR (ref {locked.reference_id})"
            if existing_tx:
                existing_tx.status = STATUS_SUCCESS
                existing_tx.type = 'add'
                existing_tx.amount = amount
                existing_tx.balance_before = balance_before
                existing_tx.balance_after = wallet.balance
                existing_tx.remarks = remarks_str
                existing_tx.save(update_fields=['status', 'type', 'amount', 'balance_before', 'balance_after', 'remarks', 'updated_at'])
            else:
                create_wallet_transaction(
                    wallet=wallet,
                    user=pt.user,
                    amount=amount,
                    type='add',
                    remarks=remarks_str,
                    status=STATUS_SUCCESS,
                    balance_before=balance_before,
                    balance_after=wallet.balance,
                )

        elif pt.purpose == PURPOSE_CARD_TOPUP and pt.card_id:
            card = Card.objects.select_for_update().get(pk=pt.card_id)
            balance_before = wallet.balance
            card.balance += amount
            card.save(update_fields=['balance', 'updated_at'])
            remarks_str = f"Card topup via QR {card.card_number} (ref {locked.reference_id})"
            if existing_tx:
                existing_tx.card = card
                existing_tx.status = STATUS_SUCCESS
                existing_tx.type = 'deducted'
                existing_tx.amount = amount
                existing_tx.balance_before = balance_before
                existing_tx.balance_after = wallet.balance
                existing_tx.remarks = remarks_str
                existing_tx.save(update_fields=['card', 'status', 'type', 'amount', 'balance_before', 'balance_after', 'remarks', 'updated_at'])
            else:
                create_wallet_transaction(
                    wallet=wallet,
                    user=pt.user,
                    card=card,
                    amount=amount,
                    type='deducted',
                    remarks=remarks_str,
                    status=STATUS_SUCCESS,
                    balance_before=balance_before,
                    balance_after=wallet.balance,
                )

        elif pt.purpose == PURPOSE_VEHICLE_TICKET_BOOKING:
            deposit_before = wallet.balance
            wallet.balance += amount
            wallet.save(update_fields=['balance', 'updated_at'])
            create_wallet_transaction(
                wallet=wallet,
                user=pt.user,
                amount=amount,
                type='add',
                remarks=f"Wallet deposit via QR (ref {locked.reference_id})",
                status=STATUS_SUCCESS,
                balance_before=deposit_before,
                balance_after=wallet.balance,
            )
            if pt.vehicle_ticket_booking_id:
                b = VehicleTicketBooking.objects.select_for_update().select_related('vehicle_schedule').get(pk=pt.vehicle_ticket_booking_id)
                if not b.is_paid and wallet.balance >= amount:
                    seat_remarks = _format_seat_remarks(b.seat)
                    seat_suffix = f' | Seat(s): {seat_remarks}' if seat_remarks else ''
                    pay_before = wallet.balance
                    wallet.balance -= amount
                    wallet.save(update_fields=['balance', 'updated_at'])
                    create_wallet_transaction(
                        wallet=wallet,
                        user=pt.user,
                        amount=amount,
                        type='deducted',
                        remarks=f'Ticket payment {b.pnr}{seat_suffix}',
                        status=STATUS_SUCCESS,
                        balance_before=pay_before,
                        balance_after=wallet.balance,
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
                        comm_before = wallet.balance
                        wallet.balance += commission
                        wallet.save(update_fields=['balance', 'updated_at'])
                        create_wallet_transaction(
                            wallet=wallet,
                            user=pt.user,
                            amount=commission,
                            type='add',
                            remarks=f'Commission for {b.pnr}{seat_suffix}',
                            status=STATUS_SUCCESS,
                            balance_before=comm_before,
                            balance_after=wallet.balance,
                        )

        return locked



def _nchl_posting_response(code, message, errors=None, http_status=200):
    return Response(
        {
            'responseCode': code,
            'responseMessage': message,
            'classfielderrorlist': errors or [],
        },
        status=http_status,
    )


@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def nchl_payment_posting_view(request):
    """
    NCHL payment posting callback.
    POST /api/nchl/payment/callback
    Basic auth: evyatayatgwqr / password from the mail.
    Signature: HMAC-SHA256(API key, txnId + billNumber).
    """
    header = request.META.get('HTTP_AUTHORIZATION', '')
    if not header.startswith('Basic '):
        return _nchl_posting_response('001', 'Basic authentication required', http_status=401)
    try:
        decoded = base64.b64decode(header.split(' ', 1)[1]).decode('utf-8')
        username, password = decoded.split(':', 1)
    except Exception:
        return _nchl_posting_response('001', 'Invalid basic authentication', http_status=401)
    if not nepalpay_gateway_qr.check_basic_auth(username, password):
        return _nchl_posting_response('001', 'Invalid basic authentication', http_status=401)

    data = request.data if isinstance(request.data, dict) else {}
    txn_id = str(data.get('txnId') or '').strip()
    bill_number = str(data.get('billNumber') or '').strip()
    signature = str(data.get('signature') or '').strip()
    if not nepalpay_gateway_qr.verify_posting_signature(txn_id, bill_number, signature):
        return _nchl_posting_response(
            '001',
            'Invalid signature',
            errors=[{'field': 'signature', 'message': 'HMAC mismatch'}],
        )

    app_id = str(data.get('appId') or '').strip()
    expected_app = getattr(settings, 'NCHL_APP_ID', '')
    if app_id and app_id != expected_app:
        return _nchl_posting_response('001', 'Unknown appId', errors=[{'field': 'appId', 'message': 'Unknown app'}])

    try:
        posted_amount = Decimal(str(data.get('amount')))
    except Exception:
        return _nchl_posting_response(
            '001',
            'Amount is required',
            errors=[{'field': 'amount', 'message': 'Amount is required'}],
        )

    try:
        pt = PaymentTransaction.objects.select_related('user', 'card', 'vehicle_ticket_booking').get(
            reference_id=bill_number
        )
    except PaymentTransaction.DoesNotExist:
        return _nchl_posting_response('001', 'Bill not found', errors=[{'field': 'billNumber', 'message': 'Unknown bill'}])

    if posted_amount != pt.amount:
        return _nchl_posting_response(
            '001',
            'Failed in updating bill amount',
            errors=[{'field': 'amount', 'message': 'Amount does not match the bill'}],
        )

    if pt.status == 'success':
        return _nchl_posting_response('000', 'Success')

    _credit_paid_payment(pt, txn_id)
    return _nchl_posting_response('000', 'Success')


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
    sync = (request.query_params.get('sync') or '').lower() in ('1', 'true', 'yes')
    if sync and pt.status == 'pending' and pt.connectips_txn_id:
        try:
            paid_row = nepalpay_gateway_qr.find_successful_txn(pt.connectips_txn_id)
        except Exception:
            paid_row = None
        if paid_row:
            pt = _credit_paid_payment(pt, paid_row.get('nQrTxnId') or paid_row.get('instructionId') or '')
    return Response(_payment_transaction_to_response(pt))
