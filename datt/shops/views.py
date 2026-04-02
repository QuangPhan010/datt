import json
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import user_passes_test
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
        data = json.loads(request.body)
        product = Product.objects.create(
            name=data.get('name'),
            category_id=data.get('category_id'),
            description=data.get('description'),
            price=data.get('price'),
            image_url=data.get('image_url'),
            badge=data.get('badge', '')
        )
        return JsonResponse({'status': 'success', 'id': product.id})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

@superuser_required_ajax
@require_POST
def product_edit(request, pk):
    try:
        product = Product.objects.get(pk=pk)
        data = json.loads(request.body)
        product.name = data.get('name', product.name)
        product.category_id = data.get('category_id', product.category_id)
        product.description = data.get('description', product.description)
        product.price = data.get('price', product.price)
        product.image_url = data.get('image_url', product.image_url)
        product.badge = data.get('badge', product.badge)
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
