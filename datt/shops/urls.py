from django.urls import path, reverse_lazy
from shops import views
from django.contrib.auth import views as auth_view

app_name = 'shops'

urlpatterns = [
    path('', views.index, name ='index'),
]