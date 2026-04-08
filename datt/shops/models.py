from django.db import models
from django.db.models import Sum
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.text import slugify
import uuid

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=150, unique=True, blank=True, null=True)
    is_hidden = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
            # Ensure uniqueness
            original_slug = self.slug
            count = 1
            while Category.objects.filter(slug=self.slug).exists():
                self.slug = f"{original_slug}-{count}"
                count += 1
        super().save(*args, **kwargs)

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
        return list(self.plans.values('id', 'plan_name', 'price', 'stock', 'duration_type', 'duration_value', 'is_renewable', 'is_active'))

    @property
    def total_stock(self):
        return self.plans.aggregate(Sum('stock'))['stock__sum'] or 0

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
    price = models.BigIntegerField(default=0)
    stock = models.PositiveIntegerField(default=0)
    duration_type = models.CharField(max_length=20, choices=DURATION_CHOICES, default='monthly')
    duration_value = models.IntegerField(null=True, blank=True, help_text="Số tháng/năm. Lifetime để trống.")
    is_renewable = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.product.name if self.product else 'N/A'} - {self.plan_name}"

class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart of {self.user.username}"

    def get_total_price(self):
        return sum(item.get_total_price() for item in self.items.all())

    def get_item_count(self):
        return sum(item.quantity for item in self.items.all())

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.quantity} x {self.product.name} ({self.plan.plan_name})"

    def get_total_price(self):
        return self.plan.price * self.quantity

class Coupon(models.Model):
    DISCOUNT_TYPES = [
        ('Percentage', 'Phần trăm (%)'),
        ('Fixed', 'Số tiền cố định ($)'),
    ]
    code = models.CharField(max_length=50, unique=True)
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPES, default='Percentage')
    discount_value = models.FloatField()
    min_purchase = models.FloatField(default=0.0)
    valid_from = models.DateTimeField(default=timezone.now)
    valid_to = models.DateTimeField()
    usage_limit = models.IntegerField(default=100)
    used_count = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    def is_valid(self, total_price):
        now = timezone.now()
        return (self.is_active and 
                self.valid_from <= now <= self.valid_to and 
                self.used_count < self.usage_limit and 
                total_price >= self.min_purchase)

    def __str__(self):
        return self.code

class Order(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Chờ thanh toán'),
        ('Paid', 'Đã thanh toán'),
        ('Processing', 'Đang xử lý'),
        ('Completed', 'Hoàn thành'),
        ('Cancelled', 'Đã hủy'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('Bank Transfer', 'Chuyển khoản ngân hàng'),
        ('Momo', 'Ví điện tử Momo'),
        ('ZaloPay', 'Ví điện tử ZaloPay'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('Pending', 'Chờ thanh toán'),
        ('Paid', 'Đã thanh toán'),
    ]
    
    order_id = models.CharField(max_length=20, unique=True, editable=False, null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders', null=True, blank=True)
    full_name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    address = models.TextField(blank=True, null=True)
    note = models.TextField(blank=True, null=True)
    
    total_price = models.BigIntegerField(default=0)
    discount_amount = models.BigIntegerField(default=0)
    final_price = models.BigIntegerField(default=0)
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='Bank Transfer')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='Pending')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.order_id:
            import random
            import string
            random_suffix = ''.join(random.choices(string.digits, k=4))
            self.order_id = f"NX{timezone.now().strftime('%y%m%d%H%M%S')}{random_suffix}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Order {self.order_id} by {self.email}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    plan_name = models.CharField(max_length=100)
    price = models.BigIntegerField(default=0)
    quantity = models.PositiveIntegerField(default=1)

    def get_total_price(self):
        return self.price * self.quantity

    def __str__(self):
        return f"{self.quantity} x {self.plan_name} for order {self.order.order_id}"

class ProductKey(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='keys')
    key_data = models.TextField(help_text="Định dạng: account:password hoặc license_key")
    is_sold = models.BooleanField(default=False)
    order_item = models.ForeignKey(OrderItem, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_keys')
    assigned_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Key for {self.product.name} (Sold: {self.is_sold})"

class DownloadGrant(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='download_grants')
    order_item = models.ForeignKey(OrderItem, on_delete=models.CASCADE, related_name='download_grants')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='download_grants')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='download_grants')
    token = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True, editable=False)
    is_active = models.BooleanField(default=True)
    max_downloads = models.IntegerField(default=3)
    download_count = models.IntegerField(default=0)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['order_item'], name='unique_download_grant_per_item'),
        ]

    def can_download(self):
        if not self.is_active:
            return False
        if self.expires_at and self.expires_at <= timezone.now():
            return False
        return self.download_count < self.max_downloads

    def __str__(self):
        return f"DownloadGrant {self.token} for order {self.order.order_id}"

