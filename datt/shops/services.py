from datetime import timedelta
from django.db import transaction
from django.utils import timezone
from .models import DownloadGrant

DEFAULT_GRANT_HOURS = 24

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