import json
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Sum

from shops.models import Product, Category, Plan, Order
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

# --- DASHBOARD OVERVIEW ---
@superuser_required
def index(request):
    total_users = User.objects.count()
    total_orders = Order.objects.count()
    total_revenue = Order.objects.filter(payment_status='Paid').aggregate(Sum('final_price'))['final_price__sum'] or 0
    total_products = Product.objects.count()
    
    recent_orders = Order.objects.all().order_by('-created_at')[:10]
    
    context = {
        'total_users': total_users,
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'total_products': total_products,
        'recent_orders': recent_orders,
    }
    return render(request, 'dashboard/index.html', context)

# --- PRODUCT MANAGEMENT ---
@superuser_required
def products(request):
    product_list = Product.objects.all().order_by('-created_at')
    categories = Category.objects.all().order_by('name')
    return render(request, 'dashboard/products.html', {
        'products': product_list,
        'categories': categories
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
                    price=p.get('price'), duration_type=p.get('duration_type'),
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
                    plan.duration_type = p_data.get('duration_type', plan.duration_type)
                    plan.duration_value = p_data.get('duration_value') if p_data.get('duration_type') != 'lifetime' else None
                    plan.is_renewable = p_data.get('is_renewable', plan.is_renewable)
                    plan.is_active = p_data.get('is_active', plan.is_active)
                    plan.save()
                    updated_plan_ids.append(plan.id)
                else:
                    new_plan = Plan.objects.create(
                        product=product, plan_name=p_data.get('plan_name'),
                        price=p_data.get('price'), duration_type=p_data.get('duration_type'),
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
    topup_requests = TopUpRequest.objects.all().order_by('-created_at')
    return render(request, 'dashboard/transactions.html', {'requests': topup_requests})

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
    orders = Order.objects.all().order_by('-created_at')
    return render(request, 'dashboard/order.html', {'orders': orders})