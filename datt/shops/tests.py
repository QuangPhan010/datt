import json
import shutil
import tempfile
import uuid
from decimal import Decimal
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import (
    Category, Product, Order, OrderItem, DownloadGrant, Plan,
    WishlistItem, FlashSale, Notification
)
from .services import grant_downloads_for_order, create_flash_sale_notifications, activate_due_flash_sales

class DownloadGrantTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._media_root = tempfile.mkdtemp()
        cls._override = override_settings(MEDIA_ROOT=cls._media_root)
        cls._override.enable()

    @classmethod
    def tearDownClass(cls):
        cls._override.disable()
        shutil.rmtree(cls._media_root, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.user = User.objects.create_user(username='tester', email='tester@example.com', password='pass1234')
        self.category = Category.objects.create(name='Tools')
        self.product = Product.objects.create(
            name='Sample',
            category=self.category,
            description='Sample product',
            thumbnail='https://example.com/thumb.png',
            source_file=SimpleUploadedFile('sample.zip', b'zipdata', content_type='application/zip'),
        )
        self.order = Order.objects.create(
            order_id=f"T{uuid.uuid4().hex[:10]}",
            user=self.user,
            full_name='Test User',
            email='tester@example.com',
            phone='123456789',
            total_price=1000,
            final_price=1000,
            payment_method='Wallet Balance',
            status='Processing',
            payment_status='Paid',
        )
        self.order_item = OrderItem.objects.create(
            order=self.order,
            product=self.product,
            plan_name='Plan',
            price=1000,
            quantity=1,
        )

    def test_paid_order_can_download(self):
        grants = grant_downloads_for_order(self.order)
        self.assertEqual(len(grants), 1)
        grant = grants[0]

        self.client.login(username='tester', password='pass1234')
        url = reverse('shops:download_by_token', kwargs={'token': grant.token})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('attachment', response.get('Content-Disposition', ''))

        grant.refresh_from_db()
        self.assertEqual(grant.download_count, 1)

    def test_unpaid_order_blocked(self):
        self.order.payment_status = 'Pending'
        self.order.save()
        grant = grant_downloads_for_order(self.order)[0]

        self.client.login(username='tester', password='pass1234')
        url = reverse('shops:download_by_token', kwargs={'token': grant.token})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_expired_link_blocked(self):
        grant = grant_downloads_for_order(self.order)[0]
        grant.expires_at = timezone.now() - timezone.timedelta(hours=1)
        grant.save(update_fields=['expires_at'])

        self.client.login(username='tester', password='pass1234')
        url = reverse('shops:download_by_token', kwargs={'token': grant.token})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_max_downloads_blocked(self):
        grant = grant_downloads_for_order(self.order)[0]
        grant.download_count = grant.max_downloads
        grant.save(update_fields=['download_count'])

        self.client.login(username='tester', password='pass1234')
        url = reverse('shops:download_by_token', kwargs={'token': grant.token})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_no_source_file_no_grant(self):
        no_file_product = Product.objects.create(
            name='NoFile',
            category=self.category,
            description='No file',
            thumbnail='https://example.com/thumb2.png',
        )
        order = Order.objects.create(
            order_id=f"T{uuid.uuid4().hex[:10]}",
            user=self.user,
            full_name='Test User',
            email='tester@example.com',
            phone='123456789',
            total_price=1000,
            final_price=1000,
            payment_method='Wallet Balance',
            status='Processing',
            payment_status='Paid',
        )
        OrderItem.objects.create(
            order=order,
            product=no_file_product,
            plan_name='Plan',
            price=1000,
            quantity=1,
        )

        grants = grant_downloads_for_order(order)
        self.assertEqual(len(grants), 0)
        self.assertEqual(DownloadGrant.objects.filter(order=order).count(), 0)


class FlashSaleNotificationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='buyer', password='pass1234')
        self.user2 = User.objects.create_user(username='buyer2', password='pass1234')
        self.user3 = User.objects.create_user(username='buyer3', password='pass1234')
        self.category = Category.objects.create(name='Games')
        self.product = Product.objects.create(
            name='Pro Tool',
            category=self.category,
            description='Pro tool',
            thumbnail='https://example.com/thumb.png',
        )
        self.plan = Plan.objects.create(product=self.product, plan_name='Base', price=100, stock=10, is_active=True)

    def test_flash_sale_notification_rules_and_dedupe(self):
        WishlistItem.objects.create(user=self.user, product=self.product, notify_enabled=True)
        WishlistItem.objects.create(user=self.user2, product=self.product, notify_enabled=True, min_discount_percent=50)
        WishlistItem.objects.create(user=self.user3, product=self.product, notify_enabled=False)

        now = timezone.now()
        flash_sale = FlashSale.objects.create(
            product=self.product,
            sale_price=Decimal('60.00'),
            start_at=now - timezone.timedelta(minutes=5),
            end_at=now + timezone.timedelta(hours=1),
            status='active',
        )

        result = create_flash_sale_notifications(flash_sale)
        self.assertEqual(result['created_notifications'], 1)
        self.assertEqual(Notification.objects.filter(flash_sale=flash_sale).count(), 1)

        result_again = create_flash_sale_notifications(flash_sale)
        self.assertEqual(result_again['created_notifications'], 0)
        self.assertEqual(Notification.objects.filter(flash_sale=flash_sale).count(), 1)

    def test_flash_sale_activation_job_creates_notifications(self):
        WishlistItem.objects.create(user=self.user, product=self.product, notify_enabled=True)
        now = timezone.now()
        flash_sale = FlashSale.objects.create(
            product=self.product,
            sale_price=Decimal('70.00'),
            start_at=now - timezone.timedelta(minutes=1),
            end_at=now + timezone.timedelta(hours=2),
            status='scheduled',
        )

        activation = activate_due_flash_sales(now=now)
        self.assertIn(flash_sale.id, activation['activated_ids'])

        flash_sale.refresh_from_db()
        self.assertEqual(flash_sale.status, 'active')

        result = create_flash_sale_notifications(flash_sale)
        self.assertEqual(result['created_notifications'], 1)


class WishlistFlashSaleNotificationApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='apiuser', password='pass1234')
        self.admin = User.objects.create_superuser(username='admin', password='pass1234', email='admin@example.com')
        self.category = Category.objects.create(name='Utilities')
        self.product = Product.objects.create(
            name='Utility Pro',
            category=self.category,
            description='Utility',
            thumbnail='https://example.com/thumb.png',
        )
        self.plan = Plan.objects.create(product=self.product, plan_name='Base', price=100, stock=5, is_active=True)

    def test_wishlist_api_flow(self):
        self.client.login(username='apiuser', password='pass1234')
        response = self.client.post(f"/wishlist/{self.product.id}")
        self.assertEqual(response.status_code, 200)

        response = self.client.patch(
            f"/wishlist/{self.product.id}/notify",
            data=json.dumps({'notify_enabled': True, 'min_discount_percent': 20}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)

        response = self.client.get("/wishlist")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json().get('items', [])), 1)

        response = self.client.delete(f"/wishlist/{self.product.id}")
        self.assertEqual(response.status_code, 200)

    def test_flash_sale_admin_api_and_notifications(self):
        self.client.login(username='admin', password='pass1234')
        now = timezone.now()
        payload = {
            'product_id': self.product.id,
            'sale_price': '80.00',
            'start_at': (now - timezone.timedelta(minutes=1)).isoformat(),
            'end_at': (now + timezone.timedelta(hours=1)).isoformat(),
        }
        response = self.client.post("/admin/flash-sales", data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 200)

        self.client.login(username='apiuser', password='pass1234')
        response = self.client.post(f"/wishlist/{self.product.id}")
        self.assertEqual(response.status_code, 200)

        response = self.client.get("/flash-sales/active")
        self.assertEqual(response.status_code, 200)

    def test_notifications_api(self):
        self.client.login(username='apiuser', password='pass1234')
        now = timezone.now()
        flash_sale = FlashSale.objects.create(
            product=self.product,
            sale_price=Decimal('80.00'),
            start_at=now - timezone.timedelta(minutes=1),
            end_at=now + timezone.timedelta(hours=1),
            status='active',
        )
        notification = Notification.objects.create(
            user=self.user,
            type=Notification.TYPE_FLASH_SALE_WISHLIST,
            title='Flash sale',
            message='Message',
            product=self.product,
            flash_sale=flash_sale,
            sent_via=Notification.SENT_VIA_IN_APP,
        )

        response = self.client.get("/notifications")
        self.assertEqual(response.status_code, 200)

        response = self.client.patch(f"/notifications/{notification.id}/read")
        self.assertEqual(response.status_code, 200)

        response = self.client.post("/notifications/read-all")
        self.assertEqual(response.status_code, 200)
