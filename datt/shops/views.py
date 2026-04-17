import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseForbidden, Http404, FileResponse
from django.views.decorators.http import require_POST, require_http_methods
from django.contrib.auth.decorators import user_passes_test, login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import F
from django.urls import reverse
from django.utils import timezone
from .models import (
    Product, Category, Plan, Cart, CartItem, Order, OrderItem, Coupon, ProductKey, DownloadGrant,
    WishlistItem, FlashSale, Notification
)
from .services import grant_downloads_for_order

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

# Public Category CRUD and Product CRUD removed. Migrated to Dashboard app.

def services(request):
    return render(request, 'shops/services.html')

# --- CART VIEWS ---
def cart_detail(request):
    items, total_price, total_count = get_cart_data(request)
    
    context = {
        'cart_items': items,
        'total_price': total_price,
        'total_count': total_count
    }
    
    if request.user.is_authenticated:
        profile = request.user.profile
        context['user_balance'] = profile.balance
        context['deficit'] = max(0, total_price - profile.balance)
        
    return render(request, 'shops/cart.html', context)

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
                if cart_item.quantity + quantity > plan.stock:
                    return JsonResponse({'status': 'error', 'message': f'Chỉ còn {plan.stock} sản phẩm trong kho.'}, status=400)
                cart_item.quantity += quantity
                cart_item.save()
            else:
                if quantity > plan.stock:
                    cart_item.delete()
                    return JsonResponse({'status': 'error', 'message': f'Chỉ còn {plan.stock} sản phẩm trong kho.'}, status=400)
            cart_count = cart.get_item_count()
        else:
            cart = request.session.get('cart', {})
            key = f"plan_{plan_id}"
            if key in cart:
                if cart[key]['quantity'] + quantity > plan.stock:
                    return JsonResponse({'status': 'error', 'message': f'Chỉ còn {plan.stock} sản phẩm trong kho.'}, status=400)
                cart[key]['quantity'] += quantity
            else:
                if quantity > plan.stock:
                    return JsonResponse({'status': 'error', 'message': f'Chỉ còn {plan.stock} sản phẩm trong kho.'}, status=400)
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
                if cart_item.quantity + 1 > cart_item.plan.stock:
                    return JsonResponse({'status': 'error', 'message': f'Chỉ còn {cart_item.plan.stock} sản phẩm trong kho.'}, status=400)
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
                    plan = Plan.objects.get(id=cart[item_id]['plan_id'])
                    if cart[item_id]['quantity'] + 1 > plan.stock:
                        return JsonResponse({'status': 'error', 'message': f'Chỉ còn {plan.stock} sản phẩm trong kho.'}, status=400)
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


@login_required
@require_POST
def pay_with_balance(request):
    try:
        items, total_price, _ = get_cart_data(request)
        if not items:
            return JsonResponse({'status': 'error', 'message': 'Giỏ hàng trống.'}, status=400)
        
        phone = request.POST.get('phone')
        if not phone:
            return JsonResponse({'status': 'error', 'message': 'Vui lòng nhập số điện thoại liên hệ.'}, status=400)
        
        profile = request.user.profile
        if profile.balance < total_price:
            return JsonResponse({'status': 'error', 'message': 'Số dư tài khoản không đủ. Vui lòng nạp thêm.'}, status=400)
        
        with transaction.atomic():
            # 1. Update Profile (Balance & Phone)
            profile.balance -= total_price
            if not profile.phone or profile.phone != phone:
                profile.phone = phone
            profile.save()
            
            # 2. Create Order
            order = Order.objects.create(
                user=request.user,
                full_name=request.user.get_full_name() or request.user.username,
                email=request.user.email,
                phone=phone,
                total_price=total_price,
                final_price=total_price,
                payment_method='Wallet Balance',
                status='Processing',
                payment_status='Paid'
            )
            
            # 3. Create OrderItems
            for item in items:
                OrderItem.objects.create(
                    order=order, 
                    product=item.product, 
                    plan_name=item.plan.plan_name, 
                    price=item.plan.price, 
                    quantity=item.quantity
                )

            grants = grant_downloads_for_order(order)
            
            # 4. Create Transaction record
            from users.models import Transaction
            Transaction.objects.create(
                user=request.user,
                amount=total_price,
                type='Payment',
                status='Completed',
                method='Wallet',
                transaction_code=f"ORDER_{order.order_id}",
                description=f"Thanh toán đơn hàng #{order.order_id} bằng số dư."
            )
            
            # 5. Clear Cart
            Cart.objects.filter(user=request.user).delete()

            download_urls = [
                reverse('shops:download_by_token', kwargs={'token': grant.token})
                for grant in grants
            ]
            response = {
                'status': 'success',
                'redirect_url': reverse('shops:order_success', kwargs={'order_id': order.id}),
                'download_urls': download_urls,
            }
            if download_urls:
                response['first_download_url'] = download_urls[0]

            return JsonResponse(response)
            
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    download_urls = []
    if order.payment_status == 'Paid' and order.user_id:
        grants = DownloadGrant.objects.filter(order=order, is_active=True, product__source_file__isnull=False)
        download_urls = [
            reverse('shops:download_by_token', kwargs={'token': grant.token})
            for grant in grants
        ]
    return render(request, 'shops/order_success.html', {'order': order, 'download_urls': download_urls})

def download_by_token(request, token):
    try:
        grant = DownloadGrant.objects.select_related('order', 'product', 'user').get(token=token)
    except DownloadGrant.DoesNotExist:
        raise Http404("Download link not found.")

    if not request.user.is_authenticated:
        return HttpResponseForbidden("Login required.")

    if grant.user_id != request.user.id:
        return HttpResponseForbidden("Not allowed.")

    if grant.order.payment_status != 'Paid':
        return HttpResponseForbidden("Payment required.")

    if not grant.can_download():
        return HttpResponseForbidden("Download limit reached or expired.")

    product = grant.product
    if not product or not product.source_file:
        raise Http404("File not found.")

    with transaction.atomic():
        refreshed = DownloadGrant.objects.select_for_update().get(pk=grant.pk)
        if not refreshed.can_download():
            return HttpResponseForbidden("Download limit reached or expired.")
        DownloadGrant.objects.filter(pk=refreshed.pk).update(download_count=F('download_count') + 1)

    filename = f"{product.slug or product.id}.zip"
    return FileResponse(product.source_file.open('rb'), as_attachment=True, filename=filename)

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

# --- PAGES ---
@login_required
def wishlist_page(request):
    return render(request, 'shops/wishlist.html')

@login_required
def notifications_page(request):
    return render(request, 'shops/notifications.html')

# --- WISHLIST APIs ---
@login_required
@require_http_methods(["POST", "DELETE"])
def wishlist_item(request, product_id):
    if request.method == "POST":
        product = get_object_or_404(Product, id=product_id)
        item, created = WishlistItem.objects.get_or_create(user=request.user, product=product)
        return JsonResponse({
            'status': 'success',
            'created': created,
            'item': {
                'id': item.id,
                'product_id': product.id,
                'notify_enabled': item.notify_enabled,
                'min_discount_percent': item.min_discount_percent,
            }
        })

    deleted, _ = WishlistItem.objects.filter(user=request.user, product_id=product_id).delete()
    if not deleted:
        return JsonResponse({'status': 'error', 'message': 'Wishlist item not found.'}, status=404)
    return JsonResponse({'status': 'success'})

@login_required
@require_http_methods(["PATCH"])
def wishlist_update_notify(request, product_id):
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON payload.'}, status=400)

    item = WishlistItem.objects.filter(user=request.user, product_id=product_id).first()
    if not item:
        return JsonResponse({'status': 'error', 'message': 'Wishlist item not found.'}, status=404)

    if 'notify_enabled' in data:
        notify_val = data.get('notify_enabled')
        if isinstance(notify_val, bool):
            item.notify_enabled = notify_val
        elif isinstance(notify_val, str):
            item.notify_enabled = notify_val.strip().lower() in ('true', '1', 'yes')
        elif notify_val is None:
            item.notify_enabled = False
        else:
            item.notify_enabled = bool(notify_val)

    if 'min_discount_percent' in data:
        min_discount = data.get('min_discount_percent')
        if min_discount is None or min_discount == '':
            item.min_discount_percent = None
        else:
            try:
                min_discount = int(min_discount)
            except (ValueError, TypeError):
                return JsonResponse({'status': 'error', 'message': 'min_discount_percent must be an integer.'}, status=400)
            if min_discount < 0 or min_discount > 100:
                return JsonResponse({'status': 'error', 'message': 'min_discount_percent must be between 0 and 100.'}, status=400)
            item.min_discount_percent = min_discount

    item.save()
    return JsonResponse({
        'status': 'success',
        'item': {
            'id': item.id,
            'product_id': item.product_id,
            'notify_enabled': item.notify_enabled,
            'min_discount_percent': item.min_discount_percent,
        }
    })

@login_required
@require_http_methods(["GET"])
def wishlist_list(request):
    items = WishlistItem.objects.filter(user=request.user).select_related('product').order_by('-created_at')
    data = [
        {
            'id': item.id,
            'product_id': item.product_id,
            'product_name': item.product.name,
            'thumbnail': item.product.thumbnail,
            'notify_enabled': item.notify_enabled,
            'min_discount_percent': item.min_discount_percent,
        }
        for item in items
    ]
    return JsonResponse({'status': 'success', 'items': data})

# --- FLASH SALE APIs ---
@require_http_methods(["GET"])
def flash_sales_active(request):
    now = timezone.now()
    sales = FlashSale.objects.filter(status='active', start_at__lte=now, end_at__gte=now).select_related('product')
    data = [
        {
            'id': sale.id,
            'product_id': sale.product_id,
            'product_name': sale.product.name,
            'sale_price': str(sale.sale_price),
            'start_at': sale.start_at.isoformat(),
            'end_at': sale.end_at.isoformat(),
        }
        for sale in sales
    ]
    return JsonResponse({'status': 'success', 'items': data})

# --- NOTIFICATION APIs ---
@login_required
@require_http_methods(["GET"])
def notifications_list(request):
    items = Notification.objects.filter(user=request.user).order_by('-created_at')
    data = [
        {
            'id': item.id,
            'type': item.type,
            'title': item.title,
            'message': item.message,
            'product_id': item.product_id,
            'flash_sale_id': item.flash_sale_id,
            'is_read': item.is_read,
            'sent_via': item.sent_via,
            'created_at': item.created_at.isoformat(),
        }
        for item in items
    ]
    return JsonResponse({'status': 'success', 'items': data})

@login_required
@require_http_methods(["PATCH"])
def notifications_mark_read(request, notification_id):
    updated = Notification.objects.filter(user=request.user, id=notification_id, is_read=False).update(is_read=True)
    if not updated:
        return JsonResponse({'status': 'error', 'message': 'Notification not found.'}, status=404)
    return JsonResponse({'status': 'success'})

@login_required
@require_http_methods(["POST"])
def notifications_mark_all_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return JsonResponse({'status': 'success'})

