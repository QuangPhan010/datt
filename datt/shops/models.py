from django.db import models

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
