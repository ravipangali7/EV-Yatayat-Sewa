from rest_framework import serializers
from django.contrib.auth import authenticate
from django.core.files.uploadedfile import UploadedFile
from .models import User, Wallet, Transaction, SuperSetting


class LoginSerializer(serializers.Serializer):
    """Serializer for user login"""
    phone = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True, style={'input_type': 'password'})
    
    def validate(self, attrs):
        phone = attrs.get('phone')
        password = attrs.get('password')
        
        if phone and password:
            user = authenticate(username=phone, password=password)
            if not user:
                raise serializers.ValidationError('Invalid phone number or password.')
            if not user.is_active:
                raise serializers.ValidationError('User account is disabled.')
            attrs['user'] = user
        else:
            raise serializers.ValidationError('Must include "phone" and "password".')
        return attrs


class RegisterSerializer(serializers.Serializer):
    """Serializer for user registration"""
    phone = serializers.CharField(required=True, max_length=100)
    name = serializers.CharField(required=True, max_length=100)
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    password = serializers.CharField(required=True, write_only=True, min_length=6, style={'input_type': 'password'})
    
    def validate_phone(self, value):
        """Validate phone number"""
        if User.objects.filter(phone=value).exists():
            raise serializers.ValidationError('User with this phone number already exists.')
        return value


class RegisterRequestOtpSerializer(serializers.Serializer):
    """Serializer for requesting OTP during registration (phone only)"""
    phone = serializers.CharField(required=True, max_length=100)
    
    def validate_phone(self, value):
        if User.objects.filter(phone=value).exists():
            raise serializers.ValidationError('User with this phone number already exists.')
        return value


class RegisterVerifyOtpSerializer(serializers.Serializer):
    """Serializer for verifying OTP and completing registration"""
    phone = serializers.CharField(required=True, max_length=100)
    otp_code = serializers.CharField(required=True, max_length=6, min_length=6)
    name = serializers.CharField(required=True, max_length=100)
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    password = serializers.CharField(required=True, write_only=True, min_length=6, style={'input_type': 'password'})
    
    def validate(self, attrs):
        from .models import OTPVerification
        phone = attrs.get('phone')
        otp_code = attrs.get('otp_code')
        try:
            otp_obj = OTPVerification.objects.filter(
                phone=phone,
                otp_code=otp_code,
                is_used=False
            ).order_by('-created_at').first()
            if not otp_obj:
                raise serializers.ValidationError('Invalid OTP code.')
            if otp_obj.is_expired():
                raise serializers.ValidationError('OTP code has expired.')
            attrs['otp_obj'] = otp_obj
        except serializers.ValidationError:
            raise
        except Exception:
            raise serializers.ValidationError('Invalid OTP code.')
        if User.objects.filter(phone=phone).exists():
            raise serializers.ValidationError('User with this phone number already exists.')
        return attrs


class ForgotPasswordSerializer(serializers.Serializer):
    """Serializer for forgot password request"""
    phone = serializers.CharField(required=True, max_length=100)
    
    def validate_phone(self, value):
        """Validate phone number exists"""
        if not User.objects.filter(phone=value).exists():
            raise serializers.ValidationError('User with this phone number does not exist.')
        return value


class VerifyOTPSerializer(serializers.Serializer):
    """Serializer for OTP verification"""
    phone = serializers.CharField(required=True, max_length=100)
    otp_code = serializers.CharField(required=True, max_length=6, min_length=6)
    
    def validate(self, attrs):
        """Validate OTP code"""
        from .models import OTPVerification
        phone = attrs.get('phone')
        otp_code = attrs.get('otp_code')
        
        try:
            otp_obj = OTPVerification.objects.filter(
                phone=phone,
                otp_code=otp_code,
                is_used=False
            ).order_by('-created_at').first()
            
            if not otp_obj:
                raise serializers.ValidationError('Invalid OTP code.')
            
            if otp_obj.is_expired():
                raise serializers.ValidationError('OTP code has expired.')
            
            attrs['otp_obj'] = otp_obj
        except Exception as e:
            raise serializers.ValidationError('Invalid OTP code.')
        
        return attrs


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for changing password with reset token"""
    reset_token = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, write_only=True, min_length=6, style={'input_type': 'password'})
    
    def validate_reset_token(self, value):
        """Validate reset token"""
        from .models import OTPVerification
        try:
            otp_obj = OTPVerification.objects.filter(
                reset_token=value,
                is_used=False
            ).order_by('-created_at').first()
            
            if not otp_obj:
                raise serializers.ValidationError('Invalid reset token.')
            
            if otp_obj.is_expired():
                raise serializers.ValidationError('Reset token has expired.')
            
            return value
        except serializers.ValidationError:
            raise
        except Exception:
            raise serializers.ValidationError('Invalid reset token.')


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model"""
    class Meta:
        model = User
        fields = [
            'id', 'username', 'phone', 'email', 'name',
            'profile_picture', 'fcm_token', 'token', 'biometric_token',
            'is_driver', 'is_superuser', 'is_staff', 'is_active',
            'license_no', 'license_image', 'license_type', 'license_expiry_date',
            'is_ticket_dealer', 'ticket_commission',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'is_superuser', 'is_staff', 'username']
        extra_kwargs = {
            'password': {'write_only': True, 'required': False},
            'email': {'required': False, 'allow_blank': True, 'allow_null': True},
            'phone': {'required': True},
            'profile_picture': {'required': False, 'allow_null': True}
        }

    def validate_profile_picture(self, value):
        """Validate profile_picture field - accept valid file objects or None"""
        if value is None:
            return None
        # If it's an empty dict or invalid data, return None
        if isinstance(value, dict) and not value:
            return None
        # If it's a string (like 'null' or empty string), return None
        if isinstance(value, str) and (value == '' or value == 'null' or value.lower() == 'none'):
            return None
        # Accept any file-like object (has read method) or UploadedFile
        if hasattr(value, 'read') or isinstance(value, UploadedFile):
            return value
        # If it's not a file-like object, return None (will be ignored)
        return None

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        # Remove username from validated_data if present - it will be auto-generated from phone
        validated_data.pop('username', None)
        # Ensure username is set to phone (will be done in model.save() but set it explicitly)
        phone = validated_data.get('phone')
        if phone:
            validated_data['username'] = phone
        user = User.objects.create(**validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        # Don't allow username to be updated - it's auto-generated from phone
        validated_data.pop('username', None)
        # Handle profile_picture - only update if it's a valid file object
        profile_picture = validated_data.pop('profile_picture', None)
        
        # Update profile_picture if a valid file was provided
        if profile_picture is not None:
            # The validation method already ensures it's a valid file or None
            # So if we get here and it's not None, it's a valid file
            instance.profile_picture = profile_picture
        # If profile_picture is None, we don't update it (keeps existing value for partial updates)
        
        # Update all other fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class UserListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for user lists"""
    class Meta:
        model = User
        fields = ['id', 'username', 'phone', 'email', 'name', 'is_driver', 'is_active']


class WalletSerializer(serializers.ModelSerializer):
    """Serializer for Wallet model"""
    user_details = UserListSerializer(source='user', read_only=True)
    
    class Meta:
        model = Wallet
        fields = [
            'id', 'user', 'user_details', 'balance', 'to_pay', 
            'to_receive', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class TransactionSerializer(serializers.ModelSerializer):
    """Serializer for Transaction model"""
    wallet_details = WalletSerializer(source='wallet', read_only=True)
    user_details = UserListSerializer(source='user', read_only=True)
    
    class Meta:
        model = Transaction
        fields = [
            'id', 'status', 'balance_before', 'balance_after', 'amount',
            'wallet', 'wallet_details', 'user', 'user_details', 'type',
            'remarks', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class SuperSettingSerializer(serializers.ModelSerializer):
    """Serializer for SuperSetting model"""
    class Meta:
        model = SuperSetting
        fields = ['id', 'per_km_charge', 'gps_threshold_second', 'point_cover_radius', 'minute_coverage_schedule', 'seat_layout', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
