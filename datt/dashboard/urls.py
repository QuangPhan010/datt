from django.urls import path
from dashboard import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.index, name='index'),
    
    # Product Management
    path('products/', views.products, name='products'),
    path('products/add/', views.product_add, name='product_add'),
    path('products/edit/<int:pk>/', views.product_edit, name='product_edit'),
    path('products/delete/<int:pk>/', views.product_delete, name='product_delete'),
    
    # Category Management
    path('categories/add/', views.category_add, name='category_add'),
    path('categories/edit/<int:pk>/', views.category_edit, name='category_edit'),
    path('categories/delete/<int:pk>/', views.category_delete, name='category_delete'),
    path('categories/toggle-hide/<int:pk>/', views.category_toggle_hide, name='category_toggle_hide'),

    # Transaction Management (Top-ups)
    path('transactions/', views.transactions_list, name='transactions_list'),
    path('transactions/approve/<int:pk>/', views.transaction_approve, name='transaction_approve'),
    path('transactions/reject/<int:pk>/', views.transaction_reject, name='transaction_reject'),
    
    # Order Management
    path('orders/', views.orders_list, name='orders_list'),
]
