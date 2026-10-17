from decimal import Decimal
import json
from django.test import TestCase
from rest_framework.test import APIClient

from core.models import User, Wallet, Transaction, Card, PaymentTransaction
from core.views.payment_views import (
    _credit_paid_payment,
    PURPOSE_WALLET_DEPOSIT,
    PURPOSE_PAY_DUE,
    PURPOSE_CARD_TOPUP,
    STATUS_PENDING,
)


class WalletAndTransactionIntegrityTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            phone='9800000001',
            username='9800000001',
            name='Admin User',
            password='password123',
            is_staff=True,
            is_superuser=True,
        )
        self.passenger = User.objects.create_user(
            phone='9800000002',
            username='9800000002',
            name='Passenger User',
            password='password123',
        )
        self.driver = User.objects.create_user(
            phone='9800000003',
            username='9800000003',
            name='Driver User',
            password='password123',
            is_driver=True,
        )

    def test_admin_wallet_create_and_edit_creates_credit_and_debit_transactions(self):
        self.client.force_authenticate(user=self.admin)

        # 1. Create wallet with initial balance > 0
        res = self.client.post(
            '/api/wallets/create/',
            data={'user': str(self.passenger.id), 'balance': '500.00', 'to_pay': '0', 'to_receive': '0'},
            format='json',
        )
        self.assertEqual(res.status_code, 201)
        wallet = Wallet.objects.get(user=self.passenger)
        self.assertEqual(wallet.balance, Decimal('500.00'))

        txs = list(Transaction.objects.filter(wallet=wallet).order_by('created_at', 'id'))
        self.assertEqual(len(txs), 1)
        self.assertEqual(txs[0].type, 'add')
        self.assertEqual(txs[0].amount, Decimal('500.00'))
        self.assertEqual(txs[0].balance_before, Decimal('0.00'))
        self.assertEqual(txs[0].balance_after, Decimal('500.00'))
        self.assertEqual(txs[0].status, 'success')

        # 2. Admin adds credit (+250.00 -> 750.00)
        res = self.client.post(
            f'/api/wallets/{wallet.id}/edit/',
            data={'balance': '750.00', 'remarks': 'Admin bonus credit'},
            format='json',
        )
        self.assertEqual(res.status_code, 200)
        wallet.refresh_from_db()
        self.assertEqual(wallet.balance, Decimal('750.00'))

        txs = list(Transaction.objects.filter(wallet=wallet).order_by('created_at', 'id'))
        self.assertEqual(len(txs), 2)
        self.assertEqual(txs[1].type, 'add')
        self.assertEqual(txs[1].amount, Decimal('250.00'))
        self.assertEqual(txs[1].balance_before, Decimal('500.00'))
        self.assertEqual(txs[1].balance_after, Decimal('750.00'))
        self.assertEqual(txs[1].remarks, 'Admin bonus credit')

        # 3. Admin deducts balance (-150.00 -> 600.00)
        res = self.client.post(
            f'/api/wallets/{wallet.id}/edit/',
            data={'balance': '600.00', 'remarks': 'Admin correction debit'},
            format='json',
        )
        self.assertEqual(res.status_code, 200)
        wallet.refresh_from_db()
        self.assertEqual(wallet.balance, Decimal('600.00'))

        txs = list(Transaction.objects.filter(wallet=wallet).order_by('created_at', 'id'))
        self.assertEqual(len(txs), 3)
        self.assertEqual(txs[2].type, 'deducted')
        self.assertEqual(txs[2].amount, Decimal('150.00'))
        self.assertEqual(txs[2].balance_before, Decimal('750.00'))
        self.assertEqual(txs[2].balance_after, Decimal('600.00'))
        self.assertEqual(txs[2].remarks, 'Admin correction debit')

    def test_wallet_deposit_and_card_topup_reconcile_without_duplicates(self):
        wallet = Wallet.objects.create(user=self.passenger, balance=Decimal('100.00'))
        card = Card.objects.create(user=self.passenger, card_number='CARD-1001', balance=Decimal('0.00'), is_active=True)
        self.client.force_authenticate(user=self.passenger)

        # Deposit 200.00 -> balance should be 300.00, balance_before=100, balance_after=300
        res = self.client.post('/api/wallets/my/deposit/', data={'amount': '200.00'}, format='json')
        self.assertEqual(res.status_code, 200)
        wallet.refresh_from_db()
        self.assertEqual(wallet.balance, Decimal('300.00'))
        deposit_tx = Transaction.objects.filter(wallet=wallet).latest('id')
        self.assertEqual(deposit_tx.balance_before, Decimal('100.00'))
        self.assertEqual(deposit_tx.balance_after, Decimal('300.00'))
        self.assertEqual(deposit_tx.type, 'add')

        # Card topup 50.00 -> creates exactly ONE transaction (not two duplicates)
        res = self.client.post(f'/api/cards/{card.id}/topup/', data={'amount': '50.00'}, format='json')
        self.assertEqual(res.status_code, 200)
        wallet.refresh_from_db()
        card.refresh_from_db()
        self.assertEqual(wallet.balance, Decimal('250.00'))
        self.assertEqual(card.balance, Decimal('50.00'))

        all_txs = list(Transaction.objects.filter(wallet=wallet).order_by('id'))
        self.assertEqual(len(all_txs), 2)
        topup_tx = all_txs[1]
        self.assertEqual(topup_tx.type, 'deducted')
        self.assertEqual(topup_tx.amount, Decimal('50.00'))
        self.assertEqual(topup_tx.balance_before, Decimal('300.00'))
        self.assertEqual(topup_tx.balance_after, Decimal('250.00'))
        self.assertEqual(topup_tx.card_id, card.id)

    def test_qr_payment_settlement_updates_pending_transaction_and_records_pay_due(self):
        driver_wallet = Wallet.objects.create(
            user=self.driver,
            balance=Decimal('100.00'),
            to_pay=Decimal('80.00'),
            to_receive=Decimal('0.00'),
        )
        # 1. Pending QR wallet deposit transitions to success without duplicating
        pt_deposit = PaymentTransaction.objects.create(
            user=self.driver,
            amount=Decimal('300.00'),
            amount_paisa=30000,
            reference_id='EYS_DEP_001',
            status=STATUS_PENDING,
            purpose=PURPOSE_WALLET_DEPOSIT,
        )
        pending_tx = Transaction.objects.create(
            wallet=driver_wallet,
            user=self.driver,
            status='pending',
            balance_before=Decimal('100.00'),
            balance_after=Decimal('100.00'),
            amount=Decimal('300.00'),
            type='add',
            remarks='Wallet deposit via QR (ref EYS_DEP_001)',
        )
        _credit_paid_payment(pt_deposit)
        driver_wallet.refresh_from_db()
        pending_tx.refresh_from_db()
        self.assertEqual(driver_wallet.balance, Decimal('400.00'))
        self.assertEqual(pending_tx.status, 'success')
        self.assertEqual(pending_tx.balance_before, Decimal('100.00'))
        self.assertEqual(pending_tx.balance_after, Decimal('400.00'))
        self.assertEqual(Transaction.objects.filter(wallet=driver_wallet).count(), 1)

        # Idempotent retry of _credit_paid_payment does not credit again
        _credit_paid_payment(pt_deposit)
        driver_wallet.refresh_from_db()
        self.assertEqual(driver_wallet.balance, Decimal('400.00'))

        # 2. QR Pay Due creates/updates ledger transaction and reduces to_pay
        pt_due = PaymentTransaction.objects.create(
            user=self.driver,
            amount=Decimal('80.00'),
            amount_paisa=8000,
            reference_id='EYS_DUE_001',
            status=STATUS_PENDING,
            purpose=PURPOSE_PAY_DUE,
        )
        _credit_paid_payment(pt_due)
        driver_wallet.refresh_from_db()
        self.assertEqual(driver_wallet.to_pay, Decimal('0.00'))
        due_tx = Transaction.objects.filter(wallet=driver_wallet, remarks__contains='EYS_DUE_001').first()
        self.assertIsNotNone(due_tx)
        self.assertEqual(due_tx.status, 'success')
        self.assertEqual(due_tx.amount, Decimal('80.00'))

