from django.urls import path
from shops import views

app_name = 'shops'

urlpatterns = [
    path('', views.index, name='index'),
    path('contact/', views.contact, name='contact'),
    path('products/', views.products, name='products'),
    path('products/<slug:slug>/', views.product_detail, name='product_detail'),
    path('services/', views.services, name='services'),
    
    # Cart URLs
    path('cart/', views.cart_detail, name='cart_detail'),
    path('cart/add/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/', views.update_cart, name='update_cart'),
    path('cart/remove/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/get-count/', views.get_cart_count, name='get_cart_count'),
    path('cart/validate-coupon/', views.validate_coupon, name='validate_coupon'),
    path('cart/pay-with-balance/', views.pay_with_balance, name='pay_with_balance'),
    path('order-success/<int:order_id>/', views.order_success, name='order_success'),
    path('download/<uuid:token>/', views.download_by_token, name='download_by_token'),

]
