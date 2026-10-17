"""Helper to create wallet transactions for every balance change."""
from decimal import Decimal
from ..models import Wallet, Transaction, User


def create_wallet_transaction(
    wallet: Wallet,
    user: User,
    amount: Decimal,
    type: str,
    remarks: str = None,
    status: str = 'success',
    card=None,
    balance_before: Decimal = None,
    balance_after: Decimal = None,
) -> Transaction:
    """
    Create a transaction record for a wallet balance change.
    If balance_before and balance_after are provided, uses them directly;
    otherwise computes from wallet.balance (when called before wallet.save()).
    """
    if balance_before is None:
        balance_before = wallet.balance
    if balance_after is None:
        if type == 'add':
            balance_after = balance_before + amount
        else:
            balance_after = balance_before - amount
    return Transaction.objects.create(
        wallet=wallet,
        user=user,
        card=card,
        status=status,
        balance_before=balance_before,
        balance_after=balance_after,
        amount=amount,
        type=type,
        remarks=remarks or '',
    )

