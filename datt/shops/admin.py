from django.contrib import admin
from .models import Category, Product, Plan, Cart, CartItem, Order, OrderItem, Coupon, ProductKey
from django.contrib import messages

# --- Product Management Inlines & Admins ---

class PlanInline(admin.TabularInline):
    model = Plan
    extra = 1

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'is_active', 'created_at')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [PlanInline]

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_hidden')

# --- Order Management Inlines & Admins ---

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'plan_name', 'price', 'quantity')

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_id', 'user', 'full_name', 'final_price', 'status', 'created_at')
    list_filter = ('status', 'payment_method', 'created_at')
    search_fields = ('order_id', 'full_name', 'email', 'phone')
    inlines = [OrderItemInline]

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product', 'plan_name', 'price', 'quantity')

# --- Shop Extras ---

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_type', 'discount_value', 'is_active', 'valid_to', 'used_count')
    list_filter = ('is_active', 'discount_type')
    search_fields = ('code',)

@admin.register(ProductKey)
class ProductKeyAdmin(admin.ModelAdmin):
    list_display = ('key_data', 'product', 'is_sold', 'order_item')
    list_filter = ('is_sold', 'product')
    search_fields = ('key_data',)

# --- Cart System ---

admin.site.register(Cart)
admin.site.register(CartItem)
