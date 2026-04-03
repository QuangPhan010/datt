from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    is_hidden = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Product(models.Model):
    BADGE_CHOICES = [
        ('New', 'Mới'),
        ('Hot', 'Nổi bật'),
        ('', 'Không có'),
    ]

    name = models.CharField(max_length=200)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image_url = models.URLField(max_length=500)
    badge = models.CharField(max_length=10, choices=BADGE_CHOICES, default='', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Plan(models.Model):
    name = models.CharField(max_length=100)
    price_monthly = models.DecimalField(max_digits=10, decimal_places=0) # Using 0 for VND
    price_yearly = models.DecimalField(max_digits=10, decimal_places=0)
    features = models.TextField(help_text="Enter features separated by commas")
    is_popular = models.BooleanField(default=False)
    description = models.TextField(blank=True, null=True)

    def get_features_list(self):
        return [f.strip() for f in self.features.split(',')]

    def __str__(self):
        return self.name

class Subscription(models.Model):
    STATUS_CHOICES = [
        ('active', 'Đang hoạt động'),
        ('expired', 'Hết hạn'),
        ('canceled', 'Đã hủy'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subscriptions')
    plan = models.ForeignKey(Plan, on_delete=models.SET_NULL, null=True)
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')

    def is_active(self):
        return self.status == 'active' and self.end_date > timezone.now()

    def __str__(self):
        return f"{self.user.username} - {self.plan.name if self.plan else 'N/A'}"
