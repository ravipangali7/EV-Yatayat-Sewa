from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from datetime import timedelta


class User(AbstractUser):
    """Custom User model with phone as primary identifier"""
    id = models.BigAutoField(primary_key=True)
    username = models.CharField(max_length=100, unique=True)  # Will store phone number
    phone = models.CharField(max_length=100, unique=True)
    email = models.EmailField(max_length=100, blank=True, null=True)
    name = models.CharField(max_length=100, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='uploads/avatars/', blank=True, null=True)
    fcm_token = models.CharField(max_length=500, null=True, blank=True, db_column='fcm_token')
    token = models.CharField(max_length=500, null=True, blank=True)
    biometric_token = models.CharField(max_length=500, null=True, blank=True, db_column='biometric_token')
    is_driver = models.BooleanField(default=False)
    # License and ticket dealer
    license_no = models.CharField(max_length=100, blank=True, null=True)
    license_image = models.ImageField(upload_to='uploads/licenses/', blank=True, null=True)
    license_type = models.CharField(max_length=50, blank=True, null=True)
    license_expiry_date = models.DateField(null=True, blank=True)
    is_ticket_dealer = models.BooleanField(default=False)
    ticket_commission = models.DecimalField(max_digits=10, decimal_places=2, default=0, null=True, blank=True)
    
    first_name = None
    last_name = None
    
    USERNAME_FIELD = 'phone'
    REQUIRED_FIELDS = ['username']
    
    # Timestamps matching Prisma
    created_at = models.DateTimeField(auto_now_add=True, db_column='created_at')
    updated_at = models.DateTimeField(auto_now=True, db_column='updated_at')
    
    class Meta:
        db_table = 'users'
        indexes = [
            models.Index(fields=['phone', 'username', 'fcm_token']),
            models.Index(fields=['biometric_token']),
        ]

    def save(self, *args, **kwargs):
        # Automatically set username to phone value
        self.username = self.phone
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name or self.username} ({self.phone})"

    @property
    def is_authenticated(self):
        return True
    
    @property
    def is_anonymous(self):
        return False


class SuperSetting(models.Model):
    """Super settings for the application"""
    id = models.BigAutoField(primary_key=True)
    per_km_charge = models.DecimalField(max_digits=10, decimal_places=2)
    gps_threshold = models.DecimalField(max_digits=10, decimal_places=2, default=5)  # km radius for destination check
    seat_layout = models.JSONField(default=list, blank=True)  # e.g. ["x","-","-","y",":", ...]
    created_at = models.DateTimeField(auto_now_add=True, db_column='created_at')
    updated_at = models.DateTimeField(auto_now=True, db_column='updated_at')
    
    class Meta:
        db_table = 'super_settings'
    
    def __str__(self):
        return f"Super Setting (Per KM: {self.per_km_charge})"


class Wallet(models.Model):
    """Wallet model for user balance management"""
    id = models.BigAutoField(primary_key=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    to_pay = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    to_receive = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True, db_column='created_at')
    updated_at = models.DateTimeField(auto_now=True, db_column='updated_at')
    
    class Meta:
        db_table = 'wallets'
        indexes = [
            models.Index(fields=['user']),
        ]
    
    def __str__(self):
        return f"Wallet for {self.user.name or self.user.username} (Balance: {self.balance})"


class Transaction(models.Model):
    """Transaction model for wallet transactions"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    ]
    
    TYPE_CHOICES = [
        ('add', 'Add'),
        ('deducted', 'Deducted'),
    ]
    
    id = models.BigAutoField(primary_key=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    balance_before = models.DecimalField(max_digits=10, decimal_places=2)
    balance_after = models.DecimalField(max_digits=10, decimal_places=2)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    card = models.ForeignKey('Card', on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    remarks = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, db_column='created_at')
    updated_at = models.DateTimeField(auto_now=True, db_column='updated_at')
    
    class Meta:
        db_table = 'transactions'
        indexes = [
            models.Index(fields=['wallet', 'user']),
            models.Index(fields=['card']),
            models.Index(fields=['status']),
            models.Index(fields=['type']),
        ]
    
    def __str__(self):
        return f"Transaction {self.id} - {self.type} {self.amount} ({self.status})"


class Card(models.Model):
    """Card model for user card balance"""
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='cards')
    card_number = models.CharField(max_length=100, unique=True, db_index=True)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, db_column='created_at')
    updated_at = models.DateTimeField(auto_now=True, db_column='updated_at')

    class Meta:
        db_table = 'cards'
        indexes = [
            models.Index(fields=['card_number']),
            models.Index(fields=['user']),
        ]

    def __str__(self):
        return f"Card {self.card_number} (Balance: {self.balance})"


class OTPVerification(models.Model):
    """OTP Verification model for password reset and phone verification"""
    id = models.BigAutoField(primary_key=True)
    phone = models.CharField(max_length=100, db_index=True)
    otp_code = models.CharField(max_length=6)
    expires_at = models.DateTimeField(db_index=True)
    is_used = models.BooleanField(default=False)
    reset_token = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_column='created_at')
    
    class Meta:
        db_table = 'otp_verifications'
        indexes = [
            models.Index(fields=['phone', 'is_used']),
            models.Index(fields=['reset_token']),
        ]
    
    def __str__(self):
        return f"OTP for {self.phone} - {'Used' if self.is_used else 'Active'}"
    
    def is_expired(self):
        """Check if OTP has expired"""
        return timezone.now() > self.expires_at
    
    def is_valid(self):
        """Check if OTP is valid (not used and not expired)"""
        return not self.is_used and not self.is_expired()
    
    @classmethod
    def create_otp(cls, phone: str, reset_token: str = None):
        """Create a new OTP for a phone number"""
        import random
        otp_code = str(random.randint(100000, 999999))  # 6-digit OTP
        expires_at = timezone.now() + timedelta(minutes=10)  # 10 minutes expiration
        
        # Invalidate any existing unused OTPs for this phone
        cls.objects.filter(phone=phone, is_used=False).update(is_used=True)
        
        return cls.objects.create(
            phone=phone,
            otp_code=otp_code,
            expires_at=expires_at,
            reset_token=reset_token
        )
