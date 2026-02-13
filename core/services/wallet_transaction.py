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
) -> Transaction:
    """
    Create a transaction record for a wallet balance change.
    Does NOT modify wallet.balance; caller must update wallet and save.
    """
    balance_before = wallet.balance
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
