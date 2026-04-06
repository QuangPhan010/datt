from django.db import transaction
from django.db.models import F
from .models import Transaction, TopUpRequest
from django.utils import timezone

@transaction.atomic
def process_topup_confirmation(topup_id, payment_method=None):
    """
    Atomically confirm a top-up request, update user balance, and log transaction.
    """
    # Select for update to lock the row
    topup = TopUpRequest.objects.select_for_update().get(id=topup_id)
    
    if topup.status != 'Pending':
        return False, "Yêu cầu đã được xử lý trước đó."
        
    user_profile = topup.user.profile
    
    # Update TopUpRequest status
    topup.status = 'Completed'
    if payment_method:
        topup.payment_method = payment_method
    topup.save()
    
    # Update User Balance atomically
    user_profile.balance = F('balance') + topup.amount
    user_profile.save()
    
    # Create Transaction Log
    Transaction.objects.create(
        user=topup.user,
        amount=topup.amount,
        type='Deposit',
        status='Completed',
        method=topup.payment_method,
        transaction_code=f"TOPUP_{topup.id}_{timezone.now().strftime('%y%m%d%H%M%S')}",
        description=f"Nạp tiền qua {topup.payment_method}. Nội dung: {topup.note}"
    )
    
    return True, "Nạp tiền thành công."

@transaction.atomic
def process_payment_with_balance(user, amount, description=""):
    """
    Atomically deduct balance for a payment.
    """
    user_profile = user.profile
    # Lock the profile row
    profile = user.profile.__class__.objects.select_for_update().get(id=user_profile.id)
    
    if profile.balance < amount:
        return False, "Số dư không đủ."
        
    profile.balance = F('balance') - amount
    profile.save()
    
    Transaction.objects.create(
        user=user,
        amount=amount,
        type='Payment',
        status='Completed',
        transaction_code=f"PAY_{timezone.now().strftime('%y%m%d%H%M%S')}",
        description=description
    )
    
    return True, "Thanh toán thành công."
