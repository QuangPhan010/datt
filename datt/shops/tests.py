import shutil
import tempfile
import uuid
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import Category, Product, Order, OrderItem, DownloadGrant
from .services import grant_downloads_for_order

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