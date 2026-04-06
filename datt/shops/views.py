import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import user_passes_test, login_required
from django.contrib import messages
from django.db import transaction
from django.urls import reverse
from django.utils import timezone
from .models import Product, Category, Plan, Cart, CartItem, Order, OrderItem, Coupon, ProductKey

def get_cart_data(request):
    """Hybrid cart helper: handles session for guests and DB for users."""
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
        items = cart.items.all()
        total_price = cart.get_total_price()
        total_count = cart.get_item_count()
        return items, total_price, total_count
    else:
        cart_session = request.session.get('cart', {})
        items = []
        total_price = 0
        total_count = 0
        for key, item in cart_session.items():
            try:
                plan = Plan.objects.get(id=item['plan_id'])
                qty = item['quantity']
                row_total = plan.price * qty
                # Wrap session item in a pseudo-object for template compatibility
                items.append({
                    'id': key,
                    'product': plan.product,
                    'plan': plan,
                    'quantity': qty,
                    'get_total_price': row_total
                })
                total_price += row_total
                total_count += qty
            except Plan.DoesNotExist:
                continue
        return items, total_price, total_count

def index(request):
    return render(request, 'shops/index.html')

def contact(request):
    return render(request, 'shops/contact.html')

def products(request):
    if request.user.is_superuser:
        categories = Category.objects.all().order_by('name')
        product_list = Product.objects.all().order_by('-created_at')
    else:
        categories = Category.objects.filter(is_hidden=False).order_by('name')
        product_list = Product.objects.filter(category__is_hidden=False).order_by('-created_at')
    
    return render(request, 'shops/products.html', {
        'products': product_list,
        'categories': categories
    })

def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug)
    if not request.user.is_superuser and product.category.is_hidden:
        from django.http import Http404
        raise Http404("Sản phẩm không tồn tại hoặc đã bị ẩn.")
        
    return render(request, 'shops/product_detail.html', {
        'product': product,
    })

# --- SUPERUSER AJAX DECORATOR ---
def superuser_required_ajax(view_func):
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_superuser:
            return JsonResponse({'status': 'error', 'message': 'Bạn không có quyền thực hiện hành động này.'}, status=403)
        return view_func(request, *args, **kwargs)
    return _wrapped_view

# --- CATEGORY CRUD ---
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

# --- PRODUCT CRUD ---
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

def services(request):
    return render(request, 'shops/services.html')

# --- CART VIEWS ---
def cart_detail(request):
    items, total_price, total_count = get_cart_data(request)
    return render(request, 'shops/cart.html', {
        'cart_items': items,
        'total_price': total_price,
        'total_count': total_count
    })

@require_POST
def add_to_cart(request):
    try:
        data = json.loads(request.body)
        plan_id = data.get('plan_id')
        quantity = int(data.get('quantity', 1))
        plan = get_object_or_404(Plan, id=plan_id)
        
        if request.user.is_authenticated:
            cart, _ = Cart.objects.get_or_create(user=request.user)
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart, product=plan.product, plan=plan, defaults={'quantity': quantity}
            )
            if not created:
                cart_item.quantity += quantity
                cart_item.save()
            cart_count = cart.get_item_count()
        else:
            cart = request.session.get('cart', {})
            key = f"plan_{plan_id}"
            if key in cart:
                cart[key]['quantity'] += quantity
            else:
                cart[key] = {'plan_id': plan_id, 'quantity': quantity}
            request.session['cart'] = cart
            request.session.modified = True
            cart_count = sum(item['quantity'] for item in cart.values())

        return JsonResponse({'status': 'success', 'message': 'Đã thêm!', 'cart_count': cart_count})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

@require_POST
def update_cart(request):
    try:
        data = json.loads(request.body)
        item_id = data.get('item_id')
        action = data.get('action')
        
        if request.user.is_authenticated:
            cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
            if action == 'increase':
                cart_item.quantity += 1
            elif action == 'decrease' and cart_item.quantity > 1:
                cart_item.quantity -= 1
            else:
                return JsonResponse({'status': 'error', 'message': 'Min 1'}, status=400)
            cart_item.save()
            quantity = cart_item.quantity
            item_total = cart_item.get_total_price()
            cart_total = cart_item.cart.get_total_price()
            cart_count = cart_item.cart.get_item_count()
        else:
            cart = request.session.get('cart', {})
            if item_id in cart:
                if action == 'increase':
                    cart[item_id]['quantity'] += 1
                elif action == 'decrease' and cart[item_id]['quantity'] > 1:
                    cart[item_id]['quantity'] -= 1
                else:
                    return JsonResponse({'status': 'error', 'message': 'Min 1'}, status=400)
                request.session['cart'] = cart
                request.session.modified = True
                plan = Plan.objects.get(id=cart[item_id]['plan_id'])
                quantity = cart[item_id]['quantity']
                item_total = plan.price * quantity
                _, cart_total, cart_count = get_cart_data(request)
            else:
                return JsonResponse({'status': 'error', 'message': 'Not found'}, status=404)
        
        return JsonResponse({'status': 'success', 'quantity': quantity, 'item_total': item_total, 'cart_total': cart_total, 'cart_count': cart_count})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

@require_POST
def remove_from_cart(request):
    try:
        data = json.loads(request.body)
        item_id = data.get('item_id')
        
        if request.user.is_authenticated:
            cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
            cart = cart_item.cart
            cart_item.delete()
            cart_total = cart.get_total_price()
            cart_count = cart.get_item_count()
        else:
            cart = request.session.get('cart', {})
            if item_id in cart:
                del cart[item_id]
                request.session['cart'] = cart
                request.session.modified = True
                _, cart_total, cart_count = get_cart_data(request)
            else:
                 return JsonResponse({'status': 'error', 'message': 'Not found'}, status=404)
        return JsonResponse({'status': 'success', 'cart_total': cart_total, 'cart_count': cart_count})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

@require_POST
def validate_coupon(request):
    try:
        data = json.loads(request.body)
        code = data.get('code')
        total_price = float(data.get('total_price', 0))
        coupon = Coupon.objects.filter(code__iexact=code, is_active=True).first()
        if not coupon:
            return JsonResponse({'status': 'error', 'message': 'Mã không tồn tại.'})
        if not coupon.is_valid(total_price):
            return JsonResponse({'status': 'error', 'message': 'Mã không hợp lệ hoặc hết hạn.'})
        discount = (coupon.discount_value / 100) * total_price if coupon.discount_type == 'Percentage' else min(coupon.discount_value, total_price)
        return JsonResponse({'status': 'success', 'discount': discount, 'final_total': total_price - discount, 'message': 'Áp dụng thành công!'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

def checkout(request):
    items, total_price, total_count = get_cart_data(request)
    if not items:
        messages.warning(request, "Giỏ hàng trống.")
        return redirect('shops:products')
    return render(request, 'shops/checkout.html', {'cart_items': items, 'total_price': total_price, 'total_count': total_count})

@require_POST
def place_order(request):
    try:
        items, total_price, _ = get_cart_data(request)
        if not items:
            return JsonResponse({'status': 'error', 'message': 'Trống.'}, status=400)
        
        full_name = request.POST.get('full_name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        note = request.POST.get('note', '')
        payment_method = request.POST.get('payment_method', 'Bank Transfer')
        coupon_code = request.POST.get('coupon_code')
        
        discount_amount = 0
        applied_coupon = None
        if coupon_code:
            coupon = Coupon.objects.filter(code__iexact=coupon_code, is_active=True).first()
            if coupon and coupon.is_valid(total_price):
                applied_coupon = coupon
                discount_amount = (coupon.discount_value / 100) * float(total_price) if coupon.discount_type == 'Percentage' else min(coupon.discount_value, float(total_price))
        
        final_price = float(total_price) - discount_amount
        
        with transaction.atomic():
            order = Order.objects.create(
                user=request.user if request.user.is_authenticated else None,
                full_name=full_name, email=email, phone=phone, note=note,
                total_price=total_price, discount_amount=discount_amount,
                final_price=final_price, coupon=applied_coupon,
                payment_method=payment_method, status='Pending'
            )
            for item in items:
                plan = item.plan if hasattr(item, 'plan') else item['plan']
                qty = item.quantity if hasattr(item, 'plan') else item['quantity']
                OrderItem.objects.create(order=order, product=plan.product, plan_name=plan.plan_name, price=plan.price, quantity=qty)
            
            if request.user.is_authenticated:
                Cart.objects.filter(user=request.user).delete()
            else:
                request.session['cart'] = {}
                request.session.modified = True
                
            if applied_coupon:
                applied_coupon.used_count += 1
                applied_coupon.save()

            return JsonResponse({'status': 'success', 'redirect_url': reverse('shops:order_success', kwargs={'order_id': order.id})})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'shops/order_success.html', {'order': order})

def get_cart_count(request):
    if request.user.is_authenticated:
        try:
            count = request.user.cart.get_item_count()
        except Exception:
            count = 0
    else:
        cart = request.session.get('cart', {})
        count = sum(item['quantity'] for item in cart.values())
    return JsonResponse({'status': 'success', 'count': count})

