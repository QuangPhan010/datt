import json
from decimal import Decimal, InvalidOperation
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_http_methods
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Sum, Count, F, Q, OuterRef, Subquery
from django.db.models.functions import Coalesce, TruncDate

from shops.models import Product, Category, Plan, Order, OrderItem, FlashSale
from shops.services import get_product_original_price
from django.utils.dateparse import parse_datetime
from users.models import Transaction, TopUpRequest

# --- HELPERS ---
def superuser_required(view_func):
    return user_passes_test(lambda u: u.is_superuser)(view_func)

def superuser_required_ajax(view_func):
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_superuser:
            return JsonResponse({'status': 'error', 'message': 'Bạn không có quyền thực hiện hành động này.'}, status=403)
        return view_func(request, *args, **kwargs)
    return _wrapped_view

import datetime
from django.utils import timezone
import calendar

@superuser_required
def index(request):
    now = timezone.now()
    
    # --- Filter Inputs ---
    q_month = int(request.GET.get('month', now.month))
    q_year = int(request.GET.get('year', now.year))
    
    # Range of selected month
    _, last_day = calendar.monthrange(q_year, q_month)
    start_date = timezone.make_aware(datetime.datetime(q_year, q_month, 1))
    end_date = timezone.make_aware(datetime.datetime(q_year, q_month, last_day, 23, 59, 59))
    
    # Range of PREVIOUS month (for comparison)
    prev_month = q_month - 1 or 12
    prev_year = q_year if q_month > 1 else q_year - 1
    _, prev_last_day = calendar.monthrange(prev_year, prev_month)
    prev_start_date = timezone.make_aware(datetime.datetime(prev_year, prev_month, 1))
    prev_end_date = timezone.make_aware(datetime.datetime(prev_year, prev_month, prev_last_day, 23, 59, 59))

    # --- Metrics for Selected Month ---
    current_sales = Order.objects.filter(payment_status='Paid', created_at__range=(start_date, end_date)).aggregate(Sum('final_price'))['final_price__sum'] or 0
    current_purchase = Transaction.objects.filter(type='Deposit', status='Completed', created_at__range=(start_date, end_date)).aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Total historical (for summary)
    total_sales_val = Order.objects.filter(payment_status='Paid').aggregate(Sum('final_price'))['final_price__sum'] or 0
    total_purchase_val = Transaction.objects.filter(type='Deposit', status='Completed').aggregate(Sum('amount'))['amount__sum'] or 0
    total_expenses_val = Transaction.objects.filter(type='Refund', status='Completed').aggregate(Sum('amount'))['amount__sum'] or 0

    # --- Metrics for Previous Month (Comparison) ---
    past_sales = Order.objects.filter(payment_status='Paid', created_at__range=(prev_start_date, prev_end_date)).aggregate(Sum('final_price'))['final_price__sum'] or 0
    past_purchase = Transaction.objects.filter(type='Deposit', status='Completed', created_at__range=(prev_start_date, prev_end_date)).aggregate(Sum('amount'))['amount__sum'] or 0

    # Calculate Comparison Percentages
    def get_trend(curr, past):
        if past == 0: return 100 if curr > 0 else 0
        return round(((curr - past) / past) * 100, 1)

    sales_trend = get_trend(current_sales, past_sales)
    purchase_trend = get_trend(current_purchase, past_purchase)

    # --- Chart Data (Daily for Selected Month) ---
    date_labels = []
    for day in range(1, last_day + 1):
        date_labels.append(f"{day:02d}/{q_month:02d}")

    # Aggregations
    sales_data_raw = Order.objects.filter(payment_status='Paid', created_at__range=(start_date, end_date)) \
        .annotate(date=TruncDate('created_at')) \
        .values('date') \
        .annotate(total=Sum('final_price')) \
        .order_by('date')
    
    deposits_data_raw = Transaction.objects.filter(type='Deposit', status='Completed', created_at__range=(start_date, end_date)) \
        .annotate(date=TruncDate('created_at')) \
        .values('date') \
        .annotate(total=Sum('amount')) \
        .order_by('date')

    # Fill data for N days
    chart_sales = []
    chart_purchases = []
    for day in range(1, last_day + 1):
        target_date = datetime.date(q_year, q_month, day)
        s_val = next((item['total'] for item in sales_data_raw if item['date'] == target_date), 0)
        p_val = next((item['total'] for item in deposits_data_raw if item['date'] == target_date), 0)
        chart_sales.append(int(s_val))
        chart_purchases.append(int(p_val))

    # --- Overall Stats ---
    pending_orders = Order.objects.filter(payment_status='Pending')
    invoice_due_val = pending_orders.aggregate(Sum('final_price'))['final_price__sum'] or 0
    pending_count = pending_orders.count()

    total_customers = User.objects.count()
    users_with_orders = User.objects.annotate(order_count=Count('orders')).filter(order_count__gt=0)
    returning_customers = users_with_orders.filter(order_count__gt=1).count()
    first_time_customers = users_with_orders.filter(order_count=1).count()
    no_order_users = total_customers - users_with_orders.count()

    top_selling = OrderItem.objects.values('product__name', 'product__thumbnail', 'product__category__name') \
        .annotate(total_sold=Sum('quantity'), total_revenue=Sum(F('price') * F('quantity'))) \
        .order_by('-total_sold')[:4]
    
    low_stock = Plan.objects.filter(stock__lt=10, is_active=True).select_related('product')[:4]
    recent_orders = Order.objects.all().order_by('-created_at')[:5]
    
    context = {
        'q_month': q_month, 'q_year': q_year,
        'month_choices': [(i, calendar.month_name[i]) for i in range(1, 13)],
        'years': range(now.year - 5, now.year + 2),
        
        # Monthly Stats (Comparison)
        'curr_month_sales': current_sales,
        'curr_month_purchase': current_purchase,
        'sales_trend': sales_trend,
        'purchase_trend': purchase_trend,
        'prev_month_name': calendar.month_name[prev_month],

        # Card Stats (Lifetime/Overall)
        'total_sales': total_sales_val,
        'total_purchase': total_purchase_val,
        'total_expenses': total_expenses_val,
        'invoice_due': invoice_due_val,
        'pending_count': pending_count,
        'total_profit': total_sales_val - total_expenses_val,
        'payment_returns': total_expenses_val,
        
        # Chart JSON
        'chart_labels': date_labels,
        'chart_sales': chart_sales,
        'chart_purchases': chart_purchases,
        
        # Customer Chart
        'cust_first_time': first_time_customers,
        'cust_returning': returning_customers,
        'cust_no_order': no_order_users,
        
        # Lists
        'top_selling': top_selling,
        'low_stock_plans': low_stock,
        'recent_orders': recent_orders,
        'total_products': Product.objects.count(),
    }
    return render(request, 'dashboard/index.html', context)

# --- PRODUCT MANAGEMENT ---
@superuser_required
def products(request):
    search_query = request.GET.get('search', '')
    category_id = request.GET.get('category', '')
    status = request.GET.get('status', '')

    product_list = Product.objects.all().order_by('-created_at')

    if search_query:
        product_list = product_list.filter(Q(name__icontains=search_query) | Q(slug__icontains=search_query))
    
    if category_id:
        product_list = product_list.filter(category_id=category_id)
        
    if status:
        is_active = status == 'active'
        product_list = product_list.filter(is_active=is_active)

    categories = Category.objects.all().order_by('name')
    low_stock_plans = Plan.objects.filter(stock__lt=10, is_active=True).select_related('product')
    
    return render(request, 'dashboard/products.html', {
        'products': product_list,
        'categories': categories,
        'low_stock_plans': low_stock_plans,
        'filters': {
            'search': search_query,
            'category': category_id,
            'status': status
        }
    })

@superuser_required_ajax
@require_POST
def product_add(request):
    try:
        name = request.POST.get('name')
        slug = request.POST.get('slug')
        category_id = request.POST.get('category_id')
        description = request.POST.get('description')
        thumbnail = request.POST.get('thumbnail')
        badge = request.POST.get('badge', '')
        is_active = request.POST.get('is_active') == 'true'
        source_file = request.FILES.get('source_file')
        
        plans_data = json.loads(request.POST.get('plans', '[]'))
        if not plans_data:
            raise Exception("Sản phẩm phải có ít nhất một gói bán.")

        with transaction.atomic():
            product = Product.objects.create(
                name=name, slug=slug, category_id=category_id,
                description=description, thumbnail=thumbnail,
                badge=badge, is_active=is_active, source_file=source_file
            )
            for p in plans_data:
                Plan.objects.create(
                    product=product, plan_name=p.get('plan_name'),
                    price=p.get('price'), stock=p.get('stock', 0),
                    duration_type=p.get('duration_type'),
                    duration_value=p.get('duration_value') if p.get('duration_type') != 'lifetime' else None,
                    is_renewable=p.get('is_renewable', True), is_active=p.get('is_active', True)
                )
        return JsonResponse({'status': 'success', 'id': product.id})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

@superuser_required_ajax
@require_POST
def product_edit(request, pk):
    try:
        product = get_object_or_404(Product, pk=pk)
        name = request.POST.get('name')
        slug = request.POST.get('slug')
        category_id = request.POST.get('category_id')
        description = request.POST.get('description')
        thumbnail = request.POST.get('thumbnail')
        badge = request.POST.get('badge', '')
        is_active = request.POST.get('is_active') == 'true'
        source_file = request.FILES.get('source_file')
        
        plans_data = json.loads(request.POST.get('plans', '[]'))
        if not plans_data:
            raise Exception("Sản phẩm phải có ít nhất một gói bán.")

        with transaction.atomic():
            product.name = name
            product.slug = slug
            product.category_id = category_id
            product.description = description
            product.thumbnail = thumbnail
            product.badge = badge
            product.is_active = is_active
            if source_file:
                product.source_file = source_file
            product.save()
            
            updated_plan_ids = []
            for p_data in plans_data:
                plan_id = p_data.get('id')
                if plan_id:
                    plan = Plan.objects.get(pk=plan_id, product=product)
                    plan.plan_name = p_data.get('plan_name', plan.plan_name)
                    plan.price = p_data.get('price', plan.price)
                    plan.stock = p_data.get('stock', plan.stock)
                    plan.duration_type = p_data.get('duration_type', plan.duration_type)
                    plan.duration_value = p_data.get('duration_value') if p_data.get('duration_type') != 'lifetime' else None
                    plan.is_renewable = p_data.get('is_renewable', plan.is_renewable)
                    plan.is_active = p_data.get('is_active', plan.is_active)
                    plan.save()
                    updated_plan_ids.append(plan.id)
                else:
                    new_plan = Plan.objects.create(
                        product=product, plan_name=p_data.get('plan_name'),
                        price=p_data.get('price'), stock=p_data.get('stock', 0),
                        duration_type=p_data.get('duration_type'),
                        duration_value=p_data.get('duration_value') if p_data.get('duration_type') != 'lifetime' else None,
                        is_renewable=p_data.get('is_renewable', True), is_active=p_data.get('is_active', True)
                    )
                    updated_plan_ids.append(new_plan.id)
            product.plans.exclude(id__in=updated_plan_ids).delete()

        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

@superuser_required_ajax
@require_POST
def product_delete(request, pk):
    try:
        Product.objects.get(pk=pk).delete()
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

# --- CATEGORY MANAGEMENT ---
@superuser_required_ajax
@require_POST
def category_add(request):
    try:
        data = json.loads(request.body)
        cat = Category.objects.create(name=data.get('name'))
        return JsonResponse({'status': 'success', 'id': cat.id, 'name': cat.name})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

@superuser_required_ajax
@require_POST
def category_edit(request, pk):
    try:
        cat = Category.objects.get(pk=pk)
        data = json.loads(request.body)
        cat.name = data.get('name', cat.name)
        cat.save()
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

@superuser_required_ajax
@require_POST
def category_delete(request, pk):
    try:
        Category.objects.get(pk=pk).delete()
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

@superuser_required_ajax
@require_POST
def category_toggle_hide(request, pk):
    try:
        cat = Category.objects.get(pk=pk)
        cat.is_hidden = not cat.is_hidden
        cat.save()
        return JsonResponse({'status': 'success', 'is_hidden': cat.is_hidden})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

# --- TRANSACTION MANAGEMENT ---
@superuser_required
def transactions_list(request):
    search_query = request.GET.get('search', '')
    status = request.GET.get('status', '')
    method = request.GET.get('method', '')

    topup_requests = TopUpRequest.objects.all().order_by('-created_at')

    if search_query:
        topup_requests = topup_requests.filter(
            Q(user__username__icontains=search_query) | 
            Q(user__email__icontains=search_query) | 
            Q(note__icontains=search_query)
        )
    
    if status:
        topup_requests = topup_requests.filter(status=status)
    
    if method:
        topup_requests = topup_requests.filter(payment_method=method)

    return render(request, 'dashboard/transactions.html', {
        'requests': topup_requests,
        'filters': {
            'search': search_query,
            'status': status,
            'method': method
        }
    })

@superuser_required_ajax
@require_POST
def transaction_approve(request, pk):
    try:
        topup = get_object_or_404(TopUpRequest, pk=pk)
        if topup.status != 'Pending':
            return JsonResponse({'status': 'error', 'message': 'Giao dịch này đã được xử lý trước đó.'}, status=400)

        with transaction.atomic():
            # 1. Update TopUpRequest
            topup.status = 'Completed'
            topup.save()

            # 2. Create Transaction record
            Transaction.objects.create(
                user=topup.user,
                amount=topup.amount,
                type='Deposit',
                status='Completed',
                method=topup.payment_method,
                transaction_code=topup.note,
                description=f"Nạp tiền qua {topup.payment_method} (Approved by Admin)"
            )

            # 3. Update User Profile Balance
            profile = topup.user.profile
            profile.balance += topup.amount
            profile.save()

        return JsonResponse({'status': 'success', 'message': f'Đã duyệt nạp tiền {topup.amount} VNĐ cho {topup.user.username}'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

@superuser_required_ajax
@require_POST
def transaction_reject(request, pk):
    try:
        topup = get_object_or_404(TopUpRequest, pk=pk)
        if topup.status != 'Pending':
            return JsonResponse({'status': 'error', 'message': 'Giao dịch này đã được xử lý trước đó.'}, status=400)

        topup.status = 'Failed'
        topup.save()

        return JsonResponse({'status': 'success', 'message': 'Đã từ chối giao dịch.'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

@superuser_required
def orders_list(request):
    search_query = request.GET.get('search', '')

    orders = Order.objects.all().order_by('-created_at')

    if search_query:
        orders = orders.filter(
            Q(order_id__icontains=search_query) | 
            Q(email__icontains=search_query) | 
            Q(phone__icontains=search_query) |
            Q(full_name__icontains=search_query)
        )

    return render(request, 'dashboard/order.html', {
        'orders': orders,
        'filters': {
            'search': search_query
        }
    })

@superuser_required
def users_list(request):
    search_query = request.GET.get('search', '')
    
    # Subqueries for metrics
    paid_orders = Order.objects.filter(user=OuterRef('pk'), payment_status='Paid')
    order_count_sq = Subquery(
        paid_orders.values('user').annotate(cnt=Count('id')).values('cnt')
    )
    total_spent_sq = Subquery(
        paid_orders.values('user').annotate(total=Sum('final_price')).values('total')
    )
    total_deposited_sq = Subquery(
        Transaction.objects.filter(user=OuterRef('pk'), type='Deposit', status='Completed')
        .values('user').annotate(total=Sum('amount')).values('total')
    )

    users = User.objects.filter(is_superuser=False).select_related('profile').annotate(
        order_count=Coalesce(order_count_sq, 0),
        total_spent=Coalesce(total_spent_sq, 0),
        total_deposited=Coalesce(total_deposited_sq, 0)
    ).order_by('-date_joined')

    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) | 
            Q(email__icontains=search_query)
        )

    return render(request, 'dashboard/users.html', {
        'users': users,
        'filters': {
            'search': search_query
        }
    })

# --- FLASH SALE MANAGEMENT API ---
@superuser_required_ajax
@require_http_methods(["POST"])
def flash_sales_create(request):
    try:
        data = json.loads(request.body or "{}")
        product_id = data.get('product_id')
        sale_price = data.get('sale_price')
        start_at_raw = data.get('start_at')
        end_at_raw = data.get('end_at')

        if not product_id or sale_price is None or not start_at_raw or not end_at_raw:
            return JsonResponse({'status': 'error', 'message': 'Missing required fields.'}, status=400)

        product = get_object_or_404(Product, pk=product_id)
        start_at = parse_datetime(start_at_raw)
        end_at = parse_datetime(end_at_raw)
        if not start_at or not end_at:
            return JsonResponse({'status': 'error', 'message': 'Invalid datetime format.'}, status=400)
        if timezone.is_naive(start_at):
            start_at = timezone.make_aware(start_at)
        if timezone.is_naive(end_at):
            end_at = timezone.make_aware(end_at)

        if end_at <= start_at:
            return JsonResponse({'status': 'error', 'message': 'end_at must be after start_at.'}, status=400)

        original_price = get_product_original_price(product)
        if original_price is None:
            return JsonResponse({'status': 'error', 'message': 'Product has no active price.'}, status=400)

        try:
            sale_price_val = Decimal(str(sale_price))
        except (InvalidOperation, TypeError):
            return JsonResponse({'status': 'error', 'message': 'Invalid sale_price.'}, status=400)
        if sale_price_val >= Decimal(str(original_price)):
            return JsonResponse({'status': 'error', 'message': 'sale_price must be less than original price.'}, status=400)

        now = timezone.now()
        status = 'scheduled'
        if start_at <= now <= end_at:
            status = 'active'
        elif end_at <= now:
            status = 'ended'

        flash_sale = FlashSale.objects.create(
            product=product,
            sale_price=sale_price_val,
            start_at=start_at,
            end_at=end_at,
            status=status,
        )

        return JsonResponse({'status': 'success', 'id': flash_sale.id, 'flash_sale_status': flash_sale.status})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

@superuser_required_ajax
@require_http_methods(["PATCH"])
def flash_sales_update(request, pk):
    try:
        flash_sale = get_object_or_404(FlashSale, pk=pk)
        data = json.loads(request.body or "{}")

        if 'sale_price' in data:
            try:
                sale_price_val = Decimal(str(data.get('sale_price')))
            except (InvalidOperation, TypeError):
                return JsonResponse({'status': 'error', 'message': 'Invalid sale_price.'}, status=400)
            original_price = get_product_original_price(flash_sale.product)
            if original_price is None:
                return JsonResponse({'status': 'error', 'message': 'Product has no active price.'}, status=400)
            if sale_price_val >= Decimal(str(original_price)):
                return JsonResponse({'status': 'error', 'message': 'sale_price must be less than original price.'}, status=400)
            flash_sale.sale_price = sale_price_val

        if 'start_at' in data:
            start_at = parse_datetime(data.get('start_at'))
            if not start_at:
                return JsonResponse({'status': 'error', 'message': 'Invalid start_at.'}, status=400)
            if timezone.is_naive(start_at):
                start_at = timezone.make_aware(start_at)
            flash_sale.start_at = start_at

        if 'end_at' in data:
            end_at = parse_datetime(data.get('end_at'))
            if not end_at:
                return JsonResponse({'status': 'error', 'message': 'Invalid end_at.'}, status=400)
            if timezone.is_naive(end_at):
                end_at = timezone.make_aware(end_at)
            flash_sale.end_at = end_at

        if flash_sale.end_at <= flash_sale.start_at:
            return JsonResponse({'status': 'error', 'message': 'end_at must be after start_at.'}, status=400)

        if 'status' in data:
            status = data.get('status')
            if status not in dict(FlashSale.STATUS_CHOICES):
                return JsonResponse({'status': 'error', 'message': 'Invalid status.'}, status=400)
            flash_sale.status = status

        flash_sale.save()
        return JsonResponse({'status': 'success', 'flash_sale_status': flash_sale.status})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
