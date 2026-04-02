from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("update/", views.cms_update, name="cms_update"),
]
