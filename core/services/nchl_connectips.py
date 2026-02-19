"""
NCHL ConnectIPS payment gateway: PFX signing, form build, validatetxn, gettxndetail.
Credentials and PFX stay in Django settings; this module uses them only.
"""
import base64
import requests
from datetime import date
from django.conf import settings
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend


def _load_private_key():
    """Load private key from PFX file. Raises if file missing or password wrong."""
    pfx_path = getattr(settings, 'NCHL_PFX_PATH', '')
    pfx_password = (getattr(settings, 'NCHL_PFX_PASSWORD', '') or '').encode('utf-8')
    if not pfx_path:
        raise ValueError("NCHL_PFX_PATH is not set")
    with open(pfx_path, 'rb') as f:
        pfx_data = f.read()
    from cryptography.hazmat.primitives.serialization import pkcs12
    private_key, certificate, additional_certs = pkcs12.load_key_and_certificates(
        pfx_data, pfx_password, default_backend()
    )
    return private_key


def _sign_message(message: str) -> str:
    """Sign message with SHA256withRSA using PFX private key; return Base64."""
    private_key = _load_private_key()
    signature = private_key.sign(
        message.encode('utf-8'),
        padding.PKCS1v15(),
        hashes.SHA256(),
    )
    return base64.b64encode(signature).decode('ascii')


def build_validation_token(reference_id: str, amount_paisa: int) -> str:
    """Token for validatetxn / gettxndetail. Message: MERCHANTID=...,APPID=...,REFERENCEID=...,TXNAMT=..."""
    mid = getattr(settings, 'NCHL_MERCHANT_ID', 3856)
    app_id = getattr(settings, 'NCHL_APP_ID', '')
    message = f"MERCHANTID={mid},APPID={app_id},REFERENCEID={reference_id},TXNAMT={amount_paisa}"
    return _sign_message(message)


def build_form_token(txn_id: str, txndate: str, txncrncy: str, txnamt_paisa: int,
                     reference_id: str, remarks: str, particulars: str) -> str:
    """Payment form token. Literal TOKEN=TOKEN at end."""
    mid = getattr(settings, 'NCHL_MERCHANT_ID', 3856)
    app_id = getattr(settings, 'NCHL_APP_ID', '')
    app_name = getattr(settings, 'NCHL_APP_NAME', '')
    remarks = remarks or ''
    particulars = particulars or ''
    message = (
        f"MERCHANTID={mid},APPID={app_id},APPNAME={app_name},"
        f"TXNID={txn_id},TXNDATE={txndate},TXNCRNCY={txncrncy},TXNAMT={txnamt_paisa},"
        f"REFERENCEID={reference_id},REMARKS={remarks},PARTICULARS={particulars},TOKEN=TOKEN"
    )
    return _sign_message(message)


def get_gateway_url() -> str:
    base = getattr(settings, 'NCHL_BASE_URL', 'https://login.connectips.com').rstrip('/')
    return f"{base}/connectipswebgw/loginpage"


def build_initiate_form_data(
    reference_id: str,
    amount_npr: float,
    remarks: str = '',
    particulars: str = '',
    success_url: str = '',
    failure_url: str = '',
) -> dict:
    """
    Build form fields for POST to gateway login page.
    reference_id is used as TXNID. amount_npr converted to paisa.
    Returns dict with MERCHANTID, APPID, APPNAME, TXNID, TXNDATE, TXNCRNCY, TXNAMT,
    REFERENCEID, REMARKS, PARTICULARS, TOKEN, plus gateway_url, success_url, failure_url.
    """
    mid = getattr(settings, 'NCHL_MERCHANT_ID', 3856)
    app_id = getattr(settings, 'NCHL_APP_ID', '')
    app_name = getattr(settings, 'NCHL_APP_NAME', '')
    amount_paisa = int(round(amount_npr * 100))
    txndate = date.today().strftime('%Y%m%d')
    txncrncy = 'NPR'
    token = build_form_token(
        txn_id=reference_id,
        txndate=txndate,
        txncrncy=txncrncy,
        txnamt_paisa=amount_paisa,
        reference_id=reference_id,
        remarks=remarks,
        particulars=particulars,
    )
    return {
        'MERCHANTID': str(mid),
        'APPID': app_id,
        'APPNAME': app_name,
        'TXNID': reference_id,
        'TXNDATE': txndate,
        'TXNCRNCY': txncrncy,
        'TXNAMT': str(amount_paisa),
        'REFERENCEID': reference_id,
        'REMARKS': remarks or '',
        'PARTICULARS': particulars or '',
        'TOKEN': token,
        'gateway_url': get_gateway_url(),
        'success_url': success_url or '',
        'failure_url': failure_url or '',
    }


def validatetxn(reference_id: str, amount_paisa: int) -> dict:
    """
    POST to NCHL validatetxn. Returns response JSON.
    """
    base = getattr(settings, 'NCHL_BASE_URL', 'https://login.connectips.com').rstrip('/')
    url = f"{base}/connectipswebws/api/creditor/validatetxn"
    app_id = getattr(settings, 'NCHL_APP_ID', '')
    app_password = getattr(settings, 'NCHL_APP_PASSWORD', '')
    mid = getattr(settings, 'NCHL_MERCHANT_ID', 3856)
    token = build_validation_token(reference_id, amount_paisa)
    payload = {
        'merchantId': mid,
        'appId': app_id,
        'referenceId': reference_id,
        'txnAmt': amount_paisa,
        'token': token,
    }
    resp = requests.post(
        url,
        json=payload,
        auth=(app_id, app_password),
        headers={'Content-Type': 'application/json'},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def gettxndetail(reference_id: str, amount_paisa: int) -> dict:
    """POST to NCHL gettxndetail. Returns response JSON."""
    base = getattr(settings, 'NCHL_BASE_URL', 'https://login.connectips.com').rstrip('/')
    url = f"{base}/connectipswebws/api/creditor/gettxndetail"
    app_id = getattr(settings, 'NCHL_APP_ID', '')
    app_password = getattr(settings, 'NCHL_APP_PASSWORD', '')
    mid = getattr(settings, 'NCHL_MERCHANT_ID', 3856)
    token = build_validation_token(reference_id, amount_paisa)
    payload = {
        'merchantId': mid,
        'appId': app_id,
        'referenceId': reference_id,
        'txnAmt': amount_paisa,
        'token': token,
    }
    resp = requests.post(
        url,
        json=payload,
        auth=(app_id, app_password),
        headers={'Content-Type': 'application/json'},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()
