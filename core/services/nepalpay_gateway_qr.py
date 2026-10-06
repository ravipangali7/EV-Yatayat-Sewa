"""
NCHL NepalPay Gateway QR (test).

QR generate: POST /qr/generateQR/gateway
Payment posting signature: HMAC-SHA256(api_key, txnId + billNumber)
Status: POST /nQR/v1/merchanttxnreport
"""
import base64
import hmac
import hashlib
from datetime import timedelta

import requests
from django.conf import settings
from django.utils import timezone
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding


def _basic_auth():
    return (
        getattr(settings, 'NCHL_BASIC_AUTH_USERNAME', ''),
        getattr(settings, 'NCHL_BASIC_AUTH_PASSWORD', ''),
    )


def _load_private_key():
    pfx_path = getattr(settings, 'NCHL_PFX_PATH', '')
    pfx_password = (getattr(settings, 'NCHL_PFX_PASSWORD', '') or '').encode('utf-8')
    if not pfx_path:
        raise ValueError('NCHL_PFX_PATH is not set')
    try:
        with open(pfx_path, 'rb') as f:
            pfx_data = f.read()
    except FileNotFoundError as exc:
        raise ValueError(
            'NPI.pfx was not in the forwarded mail. Place NCHL\'s NPI.pfx at '
            f'{pfx_path} (password from the mail).'
        ) from exc
    private_key, _certificate, _extra = serialization.pkcs12.load_key_and_certificates(
        pfx_data, pfx_password, default_backend()
    )
    if private_key is None:
        raise ValueError('NPI.pfx does not contain a private key')
    return private_key


def _sign_token(message: str) -> str:
    """SHA256withRSA over the token string, Base64. Matches the Gateway QR spec."""
    private_key = _load_private_key()
    signature = private_key.sign(
        message.encode('utf-8'),
        padding.PKCS1v15(),
        hashes.SHA256(),
    )
    return base64.b64encode(signature).decode('ascii')


def _token_string(amount: str, bill_number: str) -> str:
    """
    acquirerId,merchantId,merchantCategoryCode,transactionCurrency,transactionAmount, billNumber, userId
    The Gateway QR spec puts a space before billNumber and userId.
    merchantId in this API is the app id (MER-8027-APP-1), not the numeric merchant id.
    """
    acquirer_id = getattr(settings, 'NCHL_ACQUIRER_ID', '00000000')
    merchant_id = getattr(settings, 'NCHL_APP_ID', '')
    mcc = getattr(settings, 'NCHL_MERCHANT_CATEGORY_CODE', '')
    user_id = getattr(settings, 'NCHL_USER_ID', '')
    return f'{acquirer_id},{merchant_id},{mcc},524,{amount}, {bill_number}, {user_id}'


def generate_dynamic_qr(bill_number: str, amount_npr, purpose: str = '', reference_label: str = '') -> dict:
    """
    Ask NCHL for a dynamic gateway QR.
    Returns {'qr_string', 'validation_trace_id'}.
    """
    amount = f'{amount_npr:.2f}'
    token = _sign_token(_token_string(amount, bill_number))
    expires = timezone.localtime(timezone.now()) + timedelta(minutes=15)
    payload = {
        'billNumber': bill_number,
        'referenceLabel': (reference_label or bill_number)[:25],
        'qrExpirationDate': expires.strftime('%Y-%m-%dT%H:%M:%S'),
        'merchantId': getattr(settings, 'NCHL_APP_ID', ''),
        'merchantName': (getattr(settings, 'NCHL_APP_NAME', '') or '')[:25],
        'merchantCategoryCode': str(getattr(settings, 'NCHL_MERCHANT_CATEGORY_CODE', '')),
        'merchantCountry': getattr(settings, 'NCHL_MERCHANT_COUNTRY', 'NP'),
        'merchantCity': getattr(settings, 'NCHL_MERCHANT_CITY', 'Kathmandu'),
        'merchantPostalCode': getattr(settings, 'NCHL_MERCHANT_POSTAL_CODE', '44600'),
        'merchantLanguage': getattr(settings, 'NCHL_MERCHANT_LANGUAGE', 'en'),
        'transactionCurrency': 524,
        'transactionAmount': float(amount),
        'purposeOfTransaction': (purpose or 'Payment')[:25],
        'token': token,
    }
    url = getattr(settings, 'NCHL_QR_GENERATE_URL', '')
    resp = requests.post(
        url,
        json=payload,
        auth=_basic_auth(),
        headers={'Content-Type': 'application/json'},
        timeout=30,
    )
    try:
        body = resp.json()
    except ValueError:
        body = {'responseMessage': resp.text[:500]}
    if resp.status_code >= 400 or str(body.get('responseCode') or '') not in ('000', '200'):
        message = body.get('responseMessage') or body.get('responseStatus') or resp.text[:300]
        raise ValueError(f'QR generation failed: {message}')
    data = body.get('data') or {}
    qr_string = data.get('qrString') or ''
    trace_id = data.get('validationTraceId') or ''
    if not qr_string:
        raise ValueError('NCHL did not return a QR string')
    return {'qr_string': qr_string, 'validation_trace_id': trace_id}


def verify_posting_signature(txn_id: str, bill_number: str, signature: str) -> bool:
    """HMAC-SHA256 of txnId + billNumber, keyed with the API key from the NCHL mail."""
    api_key = getattr(settings, 'NCHL_API_KEY', '') or ''
    if not api_key or not signature:
        return False
    digest = hmac.new(
        api_key.encode('utf-8'),
        f'{txn_id}{bill_number}'.encode('utf-8'),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(digest, signature.strip().lower())


def check_basic_auth(username: str, password: str) -> bool:
    expected_user = getattr(settings, 'NCHL_BASIC_AUTH_USERNAME', '')
    expected_pass = getattr(settings, 'NCHL_BASIC_AUTH_PASSWORD', '')
    user_ok = hmac.compare_digest(username or '', expected_user)
    pass_ok = hmac.compare_digest(password or '', expected_pass)
    return user_ok and pass_ok


def _is_paid_record(row: dict) -> bool:
    debit = str(row.get('debitStatus') or '')
    credit = str(row.get('creditStatus') or '')
    return debit == '000' and credit in ('000', 'DEFER', '999')


def find_successful_txn(validation_trace_id: str) -> dict | None:
    """Return the successful report row for this QR, or None if not paid yet."""
    if not validation_trace_id:
        return None
    payload = {
        'validationTraceId': validation_trace_id,
        'merchantId': getattr(settings, 'NCHL_APP_ID', ''),
        'acquirerId': getattr(settings, 'NCHL_ACQUIRER_ID', '00000000'),
    }
    url = getattr(settings, 'NCHL_TXN_REPORT_URL', '')
    resp = requests.post(
        url,
        json=payload,
        auth=_basic_auth(),
        headers={'Content-Type': 'application/json'},
        timeout=30,
    )
    if resp.status_code >= 400:
        return None
    try:
        body = resp.json()
    except ValueError:
        return None
    rows = body.get('responseBody') or body.get('data') or []
    if isinstance(rows, dict):
        rows = [rows]
    for row in rows:
        if isinstance(row, dict) and _is_paid_record(row):
            return row
    return None
