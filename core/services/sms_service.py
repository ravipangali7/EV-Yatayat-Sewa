import requests
from django.conf import settings
from urllib.parse import urlencode

# SMS API Configuration
SMS_API_KEY = '568383D0C5AA82'
SMS_API_URL = 'https://sms.kaichogroup.com/smsapi/index.php'
SMS_CAMPAIGN_ID = '9148'
SMS_ROUTE_ID = '130'
SMS_SENDER_ID = 'SMSBit'
SMS_TIMEOUT = 30  # seconds


class SMSService:
    """Service for sending SMS via Kaicho Group API"""
    
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
                'msg': message
            }
            
            url = f"{SMS_API_URL}?{urlencode(params)}"
            
            response = requests.get(url, timeout=SMS_TIMEOUT)
            response_text = response.text.strip()
            
            # Check if response indicates success
            if 'SMS-SHOOT-ID' in response_text:
                return {
                    'success': True,
                    'message': 'SMS sent successfully',
                    'response': response_text
                }
            elif 'ERR:' in response_text:
                return {
                    'success': False,
                    'message': f'SMS service error: {response_text}',
                    'response': response_text
                }
            else:
                return {
                    'success': False,
                    'message': f'Unexpected SMS API response: {response_text}',
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
