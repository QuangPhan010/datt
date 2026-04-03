from django.urls import path, reverse_lazy
from shops import views
from django.contrib.auth import views as auth_view

app_name = 'shops'

urlpatterns = [
    path('', views.index, name ='index'),
    path('contact/', views.contact, name='contact'),
    path('products/', views.products, name='products'),
    path('products/add/', views.product_add, name='product_add'),
    path('products/edit/<int:pk>/', views.product_edit, name='product_edit'),
    path('products/delete/<int:pk>/', views.product_delete, name='product_delete'),
    
    path('categories/add/', views.category_add, name='category_add'),
    path('categories/edit/<int:pk>/', views.category_edit, name='category_edit'),
    path('categories/delete/<int:pk>/', views.category_delete, name='category_delete'),
    path('categories/toggle-hide/<int:pk>/', views.category_toggle_hide, name='category_toggle_hide'),
    
    # Pricing & Subscription
    path('pricing/', views.pricing, name='pricing'),
    path('subscribe/<int:plan_id>/', views.subscribe, name='subscribe'),
    path('dashboard/', views.dashboard, name='dashboard'),
]
