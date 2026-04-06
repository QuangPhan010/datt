"""
URL configuration for socialproject project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path, reverse_lazy
from users import views
from django.contrib.auth import views as auth_view

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.user_login, name ='login'),
    path('logout/', auth_view.LogoutView.as_view(template_name='users/logout.html'), name='logout'),
    path('password_change/', auth_view.PasswordChangeView.as_view(template_name='users/password_change_form.html', success_url=reverse_lazy('password_change_done')), name='password_change'),
    path('password_change/done/', auth_view.PasswordChangeDoneView.as_view(template_name='users/password_change_done.html'), name='password_change_done'),

    # Password reset OTP flow
    path('password_reset/', views.password_reset_request, name='password_reset'),
    path('password_reset/verify/', views.password_reset_verify, name='password_reset_verify'),
    path('password_reset/new/', views.password_reset_new, name='password_reset_new'),
    path('register/', views.register, name='register'),

    path('profile/', views.profile, name='profile'),
    path('edit/', views.edit, name='edit'),

    # Wallet URLs
    path('wallet/', views.wallet_index, name='wallet_index'),
    path('wallet/topup/', views.topup_index, name='topup_index'),
    path('wallet/topup/create/', views.topup_create, name='topup_create'),
    path('wallet/topup/<int:pk>/', views.topup_detail, name='topup_detail'),
    path('wallet/topup/<int:pk>/check/', views.check_topup_status, name='check_topup_status'),

]
