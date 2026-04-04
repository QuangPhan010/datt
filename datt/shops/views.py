import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import user_passes_test, login_required
from django.contrib import messages
from django.db import transaction
from .models import Product, Category

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
    
    # If not superuser, check if category is hidden
    if not request.user.is_superuser and product.category.is_hidden:
        from django.http import Http404
        raise Http404("Sản phẩm không tồn tại hoặc đã bị ẩn.")
        
    return render(request, 'shops/product_detail.html', {
        'product': product,
    })

# --- CATEGORY CRUD ---
from django.core.exceptions import PermissionDenied

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
        # FormData sends fields individually
        name = request.POST.get('name')
        slug = request.POST.get('slug')
        category_id = request.POST.get('category_id')
        description = request.POST.get('description')
        thumbnail = request.POST.get('thumbnail')
        badge = request.POST.get('badge', '')
        is_active = request.POST.get('is_active') == 'true'
        source_file = request.FILES.get('source_file')
        
        with transaction.atomic():
            product = Product.objects.create(
                name=name,
                slug=slug,
                category_id=category_id,
                description=description,
                thumbnail=thumbnail,
                badge=badge,
                is_active=is_active,
                source_file=source_file
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
