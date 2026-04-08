import random
import uuid
import datetime
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Sum
from shops.models import Order, OrderItem, Product, Plan, Category
from users.models import Transaction, TopUpRequest, Profile

User = get_user_model()

class Command(BaseCommand):
    help = "Seed realistic data daily from 2026-01-01 to now"

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true", help="Clear existing data before seeding")

    def handle(self, *args, **options):
        if options["clear"]:
            self.stdout.write("Clearing existing data and resetting balances...")
            Order.objects.all().delete()
            TopUpRequest.objects.all().delete()
            Transaction.objects.all().delete()
            Profile.objects.all().update(balance=0)

        users = list(User.objects.filter(is_superuser=False))
        plans = list(Plan.objects.filter(is_active=True).select_related('product'))
        
        if not users:
            self.stdout.write(self.style.ERROR("No regular users found. Please create some users first."))
            return
        if not plans:
            self.stdout.write(self.style.ERROR("No active plans found. Please create some products and plans first."))
            return

        now = timezone.now()
        start_date = timezone.make_aware(datetime.datetime(2026, 1, 1))
        
        user_spent = {u.id: 0 for u in users}
        user_deposited = {u.id: 0 for u in users}

        current_date = start_date
        total_orders = 0
        total_topups = 0

        self.stdout.write(f"Generating daily data from {start_date.date()} to {now.date()}...")

        methods = ['Bank Transfer', 'Momo', 'ZaloPay', 'VNPAY']
        topup_statuses = ['Completed', 'Completed', 'Completed', 'Pending', 'Failed', 'Expired']
        order_statuses = ['Completed', 'Completed', 'Paid', 'Paid', 'Pending', 'Cancelled']
        payment_statuses = ['Paid', 'Paid', 'Paid', 'Paid', 'Pending', 'Pending']

        while current_date <= now:
            # Randomize time within the day
            base_time = current_date.replace(hour=random.randint(8, 22), minute=random.randint(0, 59))
            
            # --- Generate 2-3 Orders per day ---
            daily_orders = random.randint(2, 4)
            for _ in range(daily_orders):
                user = random.choice(users)
                num_items = random.randint(1, 2)
                selected_plans = random.sample(plans, min(num_items, len(plans)))
                
                created_at = base_time + timedelta(minutes=random.randint(-30, 30))
                if created_at > now: created_at = now

                order = Order.objects.create(
                    user=user,
                    full_name=user.get_full_name() or user.username,
                    email=user.email,
                    phone="09" + "".join([str(random.randint(0, 9)) for _ in range(8)]),
                    address="Mock Address, Street " + str(random.randint(1, 100)),
                    payment_method=random.choice(['Bank Transfer', 'Momo']),
                    status=random.choice(order_statuses),
                    payment_status=random.choice(payment_statuses)
                )

                total_price = 0
                for plan in selected_plans:
                    qty = random.randint(1, 2)
                    OrderItem.objects.create(
                        order=order, product=plan.product, plan_name=plan.plan_name,
                        price=plan.price, quantity=qty
                    )
                    total_price += plan.price * qty
                    if plan.stock >= qty:
                        plan.stock -= qty
                        plan.save()

                order.total_price = total_price
                order.final_price = total_price
                order.save()
                
                # FORCE update created_at for Order
                Order.objects.filter(id=order.id).update(created_at=created_at)

                if order.payment_status == 'Paid':
                    user_spent[user.id] += order.final_price
                    txn = Transaction.objects.create(
                        user=user, amount=order.final_price, type='Payment',
                        status='Completed', transaction_code=f"PAY_{order.order_id}",
                        description=f"Thanh toán đơn hàng {order.order_id}"
                    )
                    # FORCE update created_at for Transaction
                    Transaction.objects.filter(id=txn.id).update(created_at=created_at)
                total_orders += 1

            # --- Generate 1-3 Top-ups per day ---
            daily_topups = random.randint(1, 4)
            for _ in range(daily_topups):
                user = random.choice(users)
                amount = random.randint(10, 200) * 10000
                status = random.choice(topup_statuses)
                created_at = base_time + timedelta(minutes=random.randint(-30, 30))
                if created_at > now: created_at = now

                topup = TopUpRequest.objects.create(
                    user=user, amount=amount, payment_method=random.choice(methods),
                    status=status, note=f"NAPTIEN_{user.id}_{uuid.uuid4().hex[:6].upper()}",
                    created_at=created_at, expired_at=created_at + timedelta(hours=2)
                )
                TopUpRequest.objects.filter(id=topup.id).update(created_at=created_at)

                if status == 'Completed':
                    user_deposited[user.id] += amount
                    txn = Transaction.objects.create(
                        user=user, amount=amount, type='Deposit', status='Completed',
                        method=topup.payment_method, transaction_code=f"TXN_{uuid.uuid4().hex[:8].upper()}",
                        description=f"Nạp tiền qua {topup.payment_method}"
                    )
                    # FORCE update created_at for Transaction
                    Transaction.objects.filter(id=txn.id).update(created_at=created_at)
                total_topups += 1

            current_date += timedelta(days=1)

        # --- Financial Balancing Pass ---
        self.stdout.write("Final balancing pass...")
        for user in users:
            spent = user_spent[user.id]
            deposited = user_deposited[user.id]
            if deposited < spent:
                extra = spent - deposited + (random.randint(10, 100) * 10000)
                date = now - timedelta(days=random.randint(0, (now-start_date).days))
                
                topup = TopUpRequest.objects.create(
                    user=user, amount=extra, payment_method='Bank Transfer',
                    status='Completed', note=f"NX_BAL_{user.id}_{uuid.uuid4().hex[:4].upper()}",
                    created_at=date, expired_at=date + timedelta(hours=2)
                )
                TopUpRequest.objects.filter(id=topup.id).update(created_at=date)

                txn = Transaction.objects.create(
                    user=user, amount=extra, type='Deposit', status='Completed',
                    method='Bank Transfer', transaction_code=f"TXN_AUTO_{uuid.uuid4().hex[:8].upper()}",
                    description="Cân bằng tự động hệ thống"
                )
                Transaction.objects.filter(id=txn.id).update(created_at=date)
                user_deposited[user.id] += extra

            profile, _ = Profile.objects.get_or_create(user=user)
            profile.balance = user_deposited[user.id] - user_spent[user.id]
            profile.save()

        self.stdout.write(self.style.SUCCESS(f"Finished! Created {total_orders} orders and {total_topups} top-ups across { (now-start_date).days } days."))
