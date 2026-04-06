# Register your models here.
from django.contrib import admin
from .models import Profile, Transaction, TopUpRequest
from .services import process_topup_confirmation
from django.contrib import messages

# Register your models here.
admin.site.register(Profile)

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('transaction_code', 'user', 'type', 'amount', 'status', 'created_at')
    list_filter = ('type', 'status', 'created_at')
    search_fields = ('transaction_code', 'user__username', 'description')

@admin.register(TopUpRequest)
class TopUpRequestAdmin(admin.ModelAdmin):
    list_display = ('note', 'user', 'amount', 'payment_method', 'status', 'created_at')
    list_filter = ('status', 'payment_method', 'created_at')
    search_fields = ('note', 'user__username')
    actions = ['confirm_payment']

    def confirm_payment(self, request, queryset):
        success_count = 0
        for topup in queryset:
            if topup.status == 'Pending':
                success, msg = process_topup_confirmation(topup.id)
                if success:
                    success_count += 1
        self.message_user(request, f"Đã xác nhận thành công {success_count} yêu cầu nạp tiền.", messages.SUCCESS)
    confirm_payment.short_description = "Xác nhận nạp tiền (Cộng số dư)"    
