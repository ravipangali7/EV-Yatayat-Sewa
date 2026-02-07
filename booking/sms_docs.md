# SMS Kaicho Group API Documentation

## API Configuration

- **API Key**: `568383D0C5AA82`
- **Base URL**: `https://sms.kaichogroup.com/smsapi/index.php`
- **Campaign ID**: `9148`
- **Route ID**: `130`
- **Sender ID**: `SMSBit`

## API Endpoint

### Send SMS

**URL**: `https://sms.kaichogroup.com/smsapi/index.php`

**Method**: `GET`

**Request Parameters**:

| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `key` | string | Yes | API Key | `568383D0C5AA82` |
| `campaign` | string | Yes | Campaign ID | `9148` |
| `routeid` | string | Yes | Route ID | `130` |
| `type` | string | Yes | Message type | `text` |
| `contacts` | string | Yes | Phone number(s) | `01712345678` |
| `senderid` | string | Yes | Sender ID | `SMSBit` |
| `msg` | string | Yes | Message content | `Your message here` |

**Request Example**:

```
GET https://sms.kaichogroup.com/smsapi/index.php?key=568383D0C5AA82&campaign=9148&routeid=130&type=text&contacts=01712345678&senderid=SMSBit&msg=Your%20message%20here
```

**Success Response**:

```
SMS-SHOOT-ID/123456789
```

**Error Response**:

```
ERR: Error message here
```

**Response Format**:

The API returns a plain text response:
- **Success**: Contains `SMS-SHOOT-ID` followed by the transaction ID
- **Error**: Contains `ERR:` followed by the error message

## SMS Service Methods

### 1. Send SMS (Generic)

**Method**: `send_sms(phone_number: str, message: str)`

**Description**: Send a generic SMS message to a phone number.

**Request**:
```python
sms_service.send_sms("01712345678", "Hello, this is a test message")
```

**Response**:
```json
{
    "success": true,
    "message": "SMS sent successfully",
    "response": "SMS-SHOOT-ID/123456789"
}
```

### 2. Send OTP

**Method**: `send_otp(phone_number: str, otp: str)`

**Description**: Send OTP verification code via SMS.

**Message Format**: `"Your Luna IoT verification code is: {otp}. Valid for 10 minutes."`

**Request**:
```python
sms_service.send_otp("01712345678", "123456")
```

**Response**:
```json
{
    "success": true,
    "message": "SMS sent successfully",
    "response": "SMS-SHOOT-ID/123456789"
}
```

### 3. Send Server Point Command

**Method**: `send_server_point_command(phone_number: str, server_ip: str = "38.54.71.218", port: str = "6666")`

**Description**: Send server point configuration command via SMS to a device.

**Message Format**: `"SERVER,1,tcp.mylunago.com,6699,0#"`

**Request**:
```python
sms_service.send_server_point_command("01712345678")
```

**Response**:
```json
{
    "success": true,
    "message": "SMS sent successfully",
    "response": "SMS-SHOOT-ID/123456789"
}
```

### 4. Send Reset Command

**Method**: `send_reset_command(phone_number: str)`

**Description**: Send reset command via SMS to a device.

**Message Format**: `"RESET#"`

**Request**:
```python
sms_service.send_reset_command("01712345678")
```

**Response**:
```json
{
    "success": true,
    "message": "SMS sent successfully",
    "response": "SMS-SHOOT-ID/123456789"
}
```

## Error Handling

### Timeout Error
```json
{
    "success": false,
    "message": "SMS service timeout - request took too long"
}
```

### Connection Error
```json
{
    "success": false,
    "message": "SMS service connection error - unable to reach API"
}
```

### API Error Response
```json
{
    "success": false,
    "message": "SMS service error: ERR: Error message",
    "response": "ERR: Error message"
}
```

### HTTP Error
```json
{
    "success": false,
    "message": "SMS API returned status code: 500",
    "response": "Error response text"
}
```

## Usage in Project

### School SMS Module
- **Location**: `school/views/school_sms_views.py`
- **Endpoint**: Creates school SMS and sends to multiple recipients
- **Method**: Uses `sms_service.send_sms()` for bulk messaging

### Device Commands
- **Location**: `device/views/device_views.py`
- **Endpoints**:
  - `send_server_point`: Sends server point command
  - `send_reset`: Sends reset command
- **Methods**: 
  - `sms_service.send_server_point_command()`
  - `sms_service.send_reset_command()`

## Configuration Location

SMS configuration is stored in:
- **File**: `luna_iot_py/settings.py`
- **Variables**:
  - `SMS_API_KEY = '568383D0C5AA82'`
  - `SMS_API_URL = 'https://sms.kaichogroup.com/smsapi/index.php'`
  - `SMS_CAMPAIGN_ID = '9148'`
  - `SMS_ROUTE_ID = '130'`
  - `SMS_SENDER_ID = 'SMSBit'`

## Notes

- Request timeout is set to 30 seconds
- All requests use GET method with URL-encoded parameters
- Phone numbers should be in international format (e.g., `01712345678`)
- The API returns plain text responses, not JSON
- Success is determined by checking if response contains `SMS-SHOOT-ID`
- Errors are identified by checking if response contains `ERR:`
