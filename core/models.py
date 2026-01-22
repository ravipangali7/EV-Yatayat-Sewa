from django.db import models
from django.contrib.auth.models import AbstractUser


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
    to_be_pay = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    to_be_received = models.DecimalField(max_digits=10, decimal_places=2, default=0)
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
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    remarks = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, db_column='created_at')
    updated_at = models.DateTimeField(auto_now=True, db_column='updated_at')
    
    class Meta:
        db_table = 'transactions'
        indexes = [
            models.Index(fields=['wallet', 'user']),
            models.Index(fields=['status']),
            models.Index(fields=['type']),
        ]
    
    def __str__(self):
        return f"Transaction {self.id} - {self.type} {self.amount} ({self.status})"
