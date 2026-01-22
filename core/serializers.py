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


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model"""
    class Meta:
        model = User
        fields = [
            'id', 'username', 'phone', 'email', 'name', 
            'profile_picture', 'fcm_token', 'token', 'biometric_token',
            'is_driver', 'is_superuser', 'is_staff', 'is_active',
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
            'id', 'user', 'user_details', 'balance', 'to_be_pay', 
            'to_be_received', 'created_at', 'updated_at'
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
        fields = ['id', 'per_km_charge', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
