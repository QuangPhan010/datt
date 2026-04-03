from django.contrib import admin
from .models import Category, Product, Plan, Subscription

admin.site.register(Category)
admin.site.register(Product)
admin.site.register(Plan)

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'start_date', 'end_date', 'status')
    list_filter = ('status', 'plan')
    search_fields = ('user__username', 'plan__name')
