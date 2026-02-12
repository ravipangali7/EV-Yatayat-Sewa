from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authtoken.models import Token
from django.contrib.auth import logout
import secrets
from ..models import User, Wallet, OTPVerification
from ..serializers import (
    LoginSerializer, UserSerializer, RegisterSerializer,
    ForgotPasswordSerializer, VerifyOTPSerializer, ChangePasswordSerializer
)
from ..services.sms_service import sms_service


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """Login endpoint - authenticate user and return token"""
    serializer = LoginSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        user_serializer = UserSerializer(user)
        return Response({
            'token': token.key,
            'user': user_serializer.data
        }, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """Logout endpoint - delete user's token"""
    try:
        request.user.auth_token.delete()
    except:
        pass  # Token doesn't exist or already deleted
    logout(request)
    return Response({'message': 'Successfully logged out'}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me_view(request):
    """Get current authenticated user"""
    serializer = UserSerializer(request.user)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def register_view(request):
    """Register endpoint - create new user with is_driver=false"""
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        phone = serializer.validated_data['phone']
        name = serializer.validated_data['name']
        email = serializer.validated_data.get('email')
        password = serializer.validated_data['password']
        
        # Create user with is_driver=False by default
        user = User.objects.create(
            phone=phone,
            username=phone,
            name=name,
            email=email,
            is_driver=False  # Default to False, no option for user to set
        )
        user.set_password(password)
        user.save()
        
        # Create wallet for the user
        Wallet.objects.create(user=user, balance=0, to_pay=0, to_receive=0)
        
        # Generate token
        token, created = Token.objects.get_or_create(user=user)
        user_serializer = UserSerializer(user)
        
        return Response({
            'token': token.key,
            'user': user_serializer.data,
            'message': 'User registered successfully'
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def forgot_password_view(request):
    """Forgot password endpoint - send OTP via SMS"""
    serializer = ForgotPasswordSerializer(data=request.data)
    if serializer.is_valid():
        phone = serializer.validated_data['phone']
        
        # Generate reset token
        reset_token = secrets.token_urlsafe(32)
        
        # Create OTP
        otp_obj = OTPVerification.create_otp(phone=phone, reset_token=reset_token)
        
        # Send OTP via SMS
        sms_result = sms_service.send_otp(phone, otp_obj.otp_code)
        
        if sms_result['success']:
            return Response({
                'message': 'OTP sent successfully to your phone number',
                'phone': phone  # Return phone for verification screen
            }, status=status.HTTP_200_OK)
        else:
            # Even if SMS fails, we still return success to prevent phone enumeration
            # In production, you might want to log this
            return Response({
                'message': 'OTP sent successfully to your phone number',
                'phone': phone
            }, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_otp_view(request):
    """Verify OTP endpoint - verify OTP and return reset token"""
    serializer = VerifyOTPSerializer(data=request.data)
    if serializer.is_valid():
        otp_obj = serializer.validated_data['otp_obj']
        phone = serializer.validated_data['phone']
        
        # Mark OTP as used
        otp_obj.is_used = True
        otp_obj.save()
        
        # Return reset token
        return Response({
            'message': 'OTP verified successfully',
            'reset_token': otp_obj.reset_token,
            'phone': phone
        }, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def change_password_view(request):
    """Change password endpoint - update password using reset token"""
    serializer = ChangePasswordSerializer(data=request.data)
    if serializer.is_valid():
        reset_token = serializer.validated_data['reset_token']
        new_password = serializer.validated_data['new_password']
        
        # Get OTP object with reset token
        otp_obj = OTPVerification.objects.filter(
            reset_token=reset_token,
            is_used=False
        ).order_by('-created_at').first()
        
        if not otp_obj or otp_obj.is_expired():
            return Response({
                'error': 'Invalid or expired reset token'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get user by phone
        try:
            user = User.objects.get(phone=otp_obj.phone)
            user.set_password(new_password)
            user.save()
            
            # Mark OTP as used
            otp_obj.is_used = True
            otp_obj.save()
            
            return Response({
                'message': 'Password changed successfully'
            }, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({
                'error': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
