from django.core.management.base import BaseCommand
from shops.models import Plan

class Command(BaseCommand):
    help = 'Populate initial plans for Nexora'

    def handle(self, *args, **kwargs):
        plans_data = [
            {
                'name': 'Bản Cơ Bản (Basic)',
                'price_monthly': 499000,
                'price_yearly': 4790000, # ~20% discount
                'features': '1 website, basic hosting, 1 email, SSL miễn phí, sao lưu hàng tuần',
                'is_popular': False,
                'description': 'Giải pháp kinh tế cho cá nhân và khởi nghiệp'
            },
            {
                'name': 'Bản Chuyên Nghiệp (Pro)',
                'price_monthly': 1990000,
                'price_yearly': 19100000,
                'features': 'Website nâng cao, VPS hosting, 10 email, sao lưu hàng ngày, tối ưu SEO cơ bản, hỗ trợ 24/7',
                'is_popular': True,
                'description': 'Lựa chọn tốt nhất cho doanh nghiệp đang phát triển'
            },
            {
                'name': 'Gói Doanh Nghiệp (Enterprise)',
                'price_monthly': 9900000, # Custom pricing placeholder
                'price_yearly': 95000000,
                'features': 'Hệ thống tùy chỉnh, Cloud Server, bảo mật toàn diện, email không giới hạn, tích hợp API, quản lý riêng',
                'is_popular': False,
                'description': 'Sức mạnh tối thượng cho quy mô lớn'
            },
        ]

        for data in plans_data:
            plan, created = Plan.objects.get_or_create(name=data['name'], defaults=data)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created plan: {plan.name}'))
            else:
                for key, value in data.items():
                    setattr(plan, key, value)
                plan.save()
                self.stdout.write(self.style.SUCCESS(f'Updated plan: {plan.name}'))
