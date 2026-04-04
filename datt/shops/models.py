from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.text import slugify
import uuid

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
    slug = models.SlugField(max_length=250, unique=True, blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    description = models.TextField()
    thumbnail = models.URLField(max_length=500) # Renamed from image_url
    badge = models.CharField(max_length=10, choices=BADGE_CHOICES, default='', blank=True)
    source_file = models.FileField(upload_to='products/sources/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
            # Ensure uniqueness
            original_slug = self.slug
            count = 1
            while Product.objects.filter(slug=self.slug).exists():
                self.slug = f"{original_slug}-{count}"
                count += 1
        super().save(*args, **kwargs)

    def get_cheapest_plan(self):
        return self.plans.filter(is_active=True).order_by('price').first()

    def get_plans_data(self):
        return list(self.plans.values('id', 'plan_name', 'price', 'duration_type', 'duration_value', 'is_renewable', 'is_active'))

    def __str__(self):
        return self.name

class Plan(models.Model):
    DURATION_CHOICES = [
        ('monthly', 'Theo tháng'),
        ('yearly', 'Theo năm'),
        ('lifetime', 'Vĩnh viễn'),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='plans', null=True) # Allow null for migration
    plan_name = models.CharField(max_length=100, default='')
    price = models.FloatField(default=0.0)
    duration_type = models.CharField(max_length=20, choices=DURATION_CHOICES, default='monthly')
    duration_value = models.IntegerField(null=True, blank=True, help_text="Số tháng/năm. Lifetime để trống.")
    is_renewable = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.product.name if self.product else 'N/A'} - {self.plan_name}"

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
        return f"{self.user.username} - {self.plan.plan_name if self.plan else 'N/A'}"
