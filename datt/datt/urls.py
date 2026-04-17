from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path
from dashboard import views as dashboard_views
from shops import views as shops_views

urlpatterns = [
    path('admin/flash-sales', dashboard_views.flash_sales_create, name='flash_sales_create'),
    path('admin/flash-sales/<int:pk>', dashboard_views.flash_sales_update, name='flash_sales_update'),
    path('admin/', admin.site.urls),
    path('wishlist/<int:product_id>', shops_views.wishlist_item, name='wishlist_item'),
    path('wishlist/<int:product_id>/notify', shops_views.wishlist_update_notify, name='wishlist_update_notify'),
    path('wishlist', shops_views.wishlist_list, name='wishlist_list'),
    path('flash-sales/active', shops_views.flash_sales_active, name='flash_sales_active'),
    path('notifications', shops_views.notifications_list, name='notifications_list'),
    path('notifications/read-all', shops_views.notifications_mark_all_read, name='notifications_mark_all_read'),
    path('notifications/<int:notification_id>/read', shops_views.notifications_mark_read, name='notifications_mark_read'),
    path('users/', include(('users.urls', 'users'))),
    path('shops/', include(('shops.urls', 'shops'))),
    path('dashboard/', include(('dashboard.urls', 'dashboard'))),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
