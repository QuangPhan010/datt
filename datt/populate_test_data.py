import os
import django
import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'datt.settings')
django.setup()

from shops.models import Product, Coupon, ProductKey

def populate():
    # 1. Create Coupons
    Coupon.objects.update_or_create(
        code='NEXORA10',
        defaults={
            'discount_type': 'Percentage',
            'discount_value': 10,
            'min_purchase': 0,
            'is_active': True,
            'valid_to': datetime.date.today() + datetime.timedelta(days=30)
        }
    )
    
    Coupon.objects.update_or_create(
        code='FIXED5',
        defaults={
            'discount_type': 'Fixed',
            'discount_value': 5,
            'min_purchase': 20,
            'is_active': True,
            'valid_to': datetime.date.today() + datetime.timedelta(days=30)
        }
    )
    print("Coupons created: NEXORA10 (10%), FIXED5 ($5 off > $20)")

    # 2. Add Keys for existing products
    products = Product.objects.all()
    if not products.exists():
        print("No products found to add keys to.")
        return

    for product in products:
        for i in range(5):
            ProductKey.objects.get_or_create(
                product=product,
                key_data=f"KEY-{product.id}-TEST-{i+1000}"
            )
        print(f"Added 5 test keys for: {product.name}")

if __name__ == '__main__':
    populate()
