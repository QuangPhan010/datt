from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


# Create your models here.
class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL , on_delete=models.CASCADE)
    photo = models.ImageField(upload_to='users/%Y/%m/%d/', blank=True)
    balance = models.BigIntegerField(default=0)
    fullname = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=20, blank=True)

    def __str__(self):
            return self.user.username


class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ('Deposit', 'Nạp tiền'),
        ('Payment', 'Thanh toán'),
        ('Refund', 'Hoàn tiền'),
    ]
    STATUS_CHOICES = [
        ('Pending', 'Đang xử lý'),
        ('Completed', 'Thành công'),
        ('Failed', 'Thất bại'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='transactions')
    amount = models.BigIntegerField(default=0)
    type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    method = models.CharField(max_length=50, blank=True, null=True)
    transaction_code = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.type} - {self.amount} - {self.user.username}"

class TopUpRequest(models.Model):
    METHOD_CHOICES = [
        ('Bank Transfer', 'Chuyển khoản ngân hàng'),
        ('Momo', 'Ví MoMo'),
        ('ZaloPay', 'Ví ZaloPay'),
        ('VNPAY', 'Cổng VNPAY'),
    ]
    STATUS_CHOICES = [
        ('Pending', 'Chờ thanh toán'),
        ('Completed', 'Đã nạp tiền'),
        ('Expired', 'Hết hạn'),
        ('Failed', 'Thất bại'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='topup_requests')
    amount = models.BigIntegerField(default=0)
    payment_method = models.CharField(max_length=50, choices=METHOD_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    note = models.CharField(max_length=100, unique=True) # E.g. NAPTIEN_1_ABC123
    qr_url = models.URLField(max_length=500, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expired_at = models.DateTimeField()

    def is_expired(self):
        return timezone.now() > self.expired_at and self.status == 'Pending'

    def __str__(self):
        return f"TopUp {self.amount} - {self.user.username} ({self.status})"