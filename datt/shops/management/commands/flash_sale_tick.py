import logging
from django.core.management.base import BaseCommand
from django.utils import timezone

from shops.models import FlashSale
from shops.services import activate_due_flash_sales, create_flash_sale_notifications

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Activate flash sales and send wishlist notifications."

    def handle(self, *args, **options):
        now = timezone.now()
        result = activate_due_flash_sales(now=now)
        activated_ids = result.get('activated_ids', [])

        for flash_sale_id in activated_ids:
            flash_sale = FlashSale.objects.select_related('product').get(id=flash_sale_id)
            logger.info(
                "flash_sale_activated",
                extra={'flash_sale_id': flash_sale.id, 'product_id': flash_sale.product_id},
            )
            create_flash_sale_notifications(flash_sale)

        active_sales = list(
            FlashSale.objects.filter(status='active', start_at__lte=now, end_at__gte=now).select_related('product')
        )
        for flash_sale in active_sales:
            create_flash_sale_notifications(flash_sale)

        self.stdout.write(
            self.style.SUCCESS(
                f"Flash sale tick complete. Activated={len(activated_ids)}, active_processed={len(active_sales)}, ended_active={result.get('ended_active')}, ended_scheduled={result.get('ended_scheduled')}"
            )
        )
