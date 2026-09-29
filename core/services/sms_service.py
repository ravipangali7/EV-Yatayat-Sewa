import json

import requests
from urllib.parse import urlencode

# SMS API Configuration
SMS_API_KEY = '36AB90E6EA58F8'
SMS_API_URL = 'https://sms.smspasal.com/smsapi/index.php'
SMS_CAMPAIGN_ID = '9823'
SMS_ROUTE_ID = '10305'
SMS_SENDER_ID = 'Bit_Alert'
SMS_TIMEOUT = 30  # seconds


class SMSService:
    """Service for sending SMS via SMS Pasal API"""

    @staticmethod
    def _is_success(response_text: str) -> tuple:
        """Return (success, detail) for a plain or JSON SMS Pasal body."""
        text = (response_text or '').strip()
        if not text:
            return False, 'Empty SMS API response'
        if 'SMS-SHOOT-ID' in text:
            return True, text
        if 'ERR:' in text:
            return False, text

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            lowered = text.lower()
            if 'success' in lowered and 'error' not in lowered and 'fail' not in lowered:
                return True, text
            return False, text

        payload = data[0] if isinstance(data, list) and data else data
        if not isinstance(payload, dict):
            return False, text

        code = payload.get('response_code', payload.get('statusCode', payload.get('code')))
        status = str(payload.get('status', payload.get('success', ''))).strip().lower()
        detail = str(
            payload.get('response')
            or payload.get('message')
            or payload.get('reason')
            or text
        )
        if status in ('error', 'failed', 'fail', 'false'):
            return False, detail
        if str(code) in ('200', '202', '0') or status in ('success', 'true', 'ok', 'sent'):
            return True, detail
        if 'success' in detail.lower() and 'error' not in detail.lower():
            return True, detail
        return False, detail
    
    @staticmethod
    def send_sms(phone_number: str, message: str) -> dict:
        """
        Send a generic SMS message to a phone number.
        
        Args:
            phone_number: Phone number in international format (e.g., '01712345678')
            message: Message content to send
            
        Returns:
            dict: Response with success status and message
        """
        try:
            params = {
                'key': SMS_API_KEY,
                'campaign': SMS_CAMPAIGN_ID,
                'routeid': SMS_ROUTE_ID,
                'type': 'text',
                'contacts': phone_number,
                'senderid': SMS_SENDER_ID,
                'msg': message,
            }
            
            url = f"{SMS_API_URL}?{urlencode(params)}"
            
            response = requests.get(url, timeout=SMS_TIMEOUT)
            response_text = response.text.strip()
            success, detail = SMSService._is_success(response_text)
            if success:
                return {
                    'success': True,
                    'message': 'SMS sent successfully',
                    'response': response_text
                }
            return {
                'success': False,
                'message': f'SMS service error: {detail}',
                'response': response_text
            }
                
        except requests.exceptions.Timeout:
            return {
                'success': False,
                'message': 'SMS service timeout - request took too long'
            }
        except requests.exceptions.ConnectionError:
            return {
                'success': False,
                'message': 'SMS service connection error - unable to reach API'
            }
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'message': f'SMS service error: {str(e)}'
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Unexpected error: {str(e)}'
            }
    
    @staticmethod
    def send_otp(phone_number: str, otp: str) -> dict:
        """
        Send OTP verification code via SMS.
        
        Args:
            phone_number: Phone number in international format
            otp: 6-digit OTP code
            
        Returns:
            dict: Response with success status and message
        """
        message = f"Your EV Yatayat Sewa verification code is: {otp}. Valid for 10 minutes."
        return SMSService.send_sms(phone_number, message)


# Create a singleton instance
sms_service = SMSService()
