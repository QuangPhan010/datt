from datetime import timedelta
import logging
from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone
from .models import DownloadGrant, FlashSale, Notification, NotificationLog, WishlistItem, Plan

DEFAULT_GRANT_HOURS = 24
FLASH_SALE_NOTIFICATION_COOLDOWN_HOURS = 6
logger = logging.getLogger(__name__)

def grant_downloads_for_order(order):
    """
    Create download grants for order items that have a source file.
    Idempotent: avoids duplicates if called multiple times.
    Returns a list of DownloadGrant objects.
    """
    if order is None or order.user is None:
        return []

    grants = []
    expires_at = timezone.now() + timedelta(hours=DEFAULT_GRANT_HOURS)

    with transaction.atomic():
        for item in order.items.select_related('product').all():
            product = item.product
            if not product or not product.source_file:
                continue
            grant, _ = DownloadGrant.objects.get_or_create(
                order_item=item,
                defaults={
                    'order': order,
                    'user': order.user,
                    'product': product,
                    'expires_at': expires_at,
                }
            )
            grants.append(grant)

    return grants

def get_product_original_price(product):
    plan = Plan.objects.filter(product=product, is_active=True).order_by('price').first()
    if not plan:
        return None
    return plan.price

def get_product_active_stock(product):
    return (
        Plan.objects.filter(product=product, is_active=True)
        .aggregate(total=Sum('stock'))
        .get('total')
        or 0
    )

def compute_discount_percent(original_price, sale_price):
    if original_price is None or original_price <= 0:
        return None
    sale_value = float(sale_price)
    discount = ((original_price - sale_value) / float(original_price)) * 100
    return max(0, round(discount))

def flash_sale_is_active(flash_sale, now=None):
    now = now or timezone.now()
    return (
        flash_sale.status == 'active'
        and flash_sale.start_at <= now <= flash_sale.end_at
    )

def create_flash_sale_notifications(flash_sale):
    now = timezone.now()
    if not flash_sale_is_active(flash_sale, now=now):
        return {
            'matched_users': 0,
            'created_notifications': 0,
            'sent_notifications': 0,
            'failed_notifications': 0,
        }

    product = flash_sale.product
    original_price = get_product_original_price(product)
    if original_price is None:
        logger.info(
            "flash_sale_activation_skipped_no_price",
            extra={'flash_sale_id': flash_sale.id, 'product_id': product.id},
        )
        return {
            'matched_users': 0,
            'created_notifications': 0,
            'sent_notifications': 0,
            'failed_notifications': 0,
        }

    if get_product_active_stock(product) <= 0:
        logger.info(
            "flash_sale_activation_skipped_no_stock",
            extra={'flash_sale_id': flash_sale.id, 'product_id': product.id},
        )
        return {
            'matched_users': 0,
            'created_notifications': 0,
            'sent_notifications': 0,
            'failed_notifications': 0,
        }

    discount_percent = compute_discount_percent(original_price, flash_sale.sale_price)
    if discount_percent is None:
        return {
            'matched_users': 0,
            'created_notifications': 0,
            'sent_notifications': 0,
            'failed_notifications': 0,
        }

    wishlist_qs = WishlistItem.objects.filter(product=product, notify_enabled=True)
    wishlist_qs = wishlist_qs.filter(
        Q(min_discount_percent__isnull=True) | Q(min_discount_percent__lte=discount_percent)
    )
    user_ids = list(wishlist_qs.values_list('user_id', flat=True))
    matched_users = len(user_ids)
    if not user_ids:
        return {
            'matched_users': 0,
            'created_notifications': 0,
            'sent_notifications': 0,
            'failed_notifications': 0,
        }

    cooldown_cutoff = now - timedelta(hours=FLASH_SALE_NOTIFICATION_COOLDOWN_HOURS)
    existing_ids = set(
        Notification.objects.filter(
            user_id__in=user_ids,
            product=product,
            flash_sale=flash_sale,
            type=Notification.TYPE_FLASH_SALE_WISHLIST,
        ).values_list('user_id', flat=True)
    )
    recent_ids = set(
        Notification.objects.filter(
            user_id__in=user_ids,
            product=product,
            flash_sale=flash_sale,
            type=Notification.TYPE_FLASH_SALE_WISHLIST,
            created_at__gte=cooldown_cutoff,
        ).values_list('user_id', flat=True)
    )
    skip_ids = existing_ids | recent_ids
    target_user_ids = [uid for uid in user_ids if uid not in skip_ids]
    if not target_user_ids:
        return {
            'matched_users': matched_users,
            'created_notifications': 0,
            'sent_notifications': 0,
            'failed_notifications': 0,
        }

    created_notifications = []
    title = f"Flash sale: {product.name}"
    message = f"{product.name} is now {discount_percent}% off. Deal ends at {flash_sale.end_at:%Y-%m-%d %H:%M}."

    with transaction.atomic():
        for user_id in target_user_ids:
            notification, created = Notification.objects.get_or_create(
                user_id=user_id,
                product=product,
                flash_sale=flash_sale,
                type=Notification.TYPE_FLASH_SALE_WISHLIST,
                defaults={
                    'title': title,
                    'message': message,
                    'sent_via': Notification.SENT_VIA_IN_APP,
                },
            )
            if created:
                created_notifications.append(notification)

        NotificationLog.objects.bulk_create(
            [
                NotificationLog(
                    notification=notification,
                    channel=Notification.SENT_VIA_IN_APP,
                    status='sent',
                    sent_at=now,
                )
                for notification in created_notifications
            ]
        )

    created_count = len(created_notifications)
    logger.info(
        "flash_sale_notifications_created",
        extra={
            'flash_sale_id': flash_sale.id,
            'product_id': product.id,
            'matched_users': matched_users,
            'created_notifications': created_count,
        },
    )
    logger.info(
        "flash_sale_notifications_sent",
        extra={
            'flash_sale_id': flash_sale.id,
            'product_id': product.id,
            'sent_notifications': created_count,
        },
    )
    logger.info(
        "metrics flashsale_notifications_created=%s",
        created_count,
    )
    logger.info(
        "metrics flashsale_notifications_sent=%s",
        created_count,
    )

    return {
        'matched_users': matched_users,
        'created_notifications': created_count,
        'sent_notifications': created_count,
        'failed_notifications': 0,
    }

def activate_due_flash_sales(now=None):
    now = now or timezone.now()
    ended_active = FlashSale.objects.filter(status='active', end_at__lte=now).update(status='ended', updated_at=now)
    ended_scheduled = FlashSale.objects.filter(status='scheduled', end_at__lte=now).update(status='ended', updated_at=now)

    to_activate = list(
        FlashSale.objects.filter(status='scheduled', start_at__lte=now, end_at__gt=now).values_list('id', flat=True)
    )
    if to_activate:
        FlashSale.objects.filter(id__in=to_activate).update(status='active', updated_at=now)

    return {
        'activated_ids': to_activate,
        'ended_active': ended_active,
        'ended_scheduled': ended_scheduled,
    }
