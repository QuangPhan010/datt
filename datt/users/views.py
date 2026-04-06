import hashlib
import secrets
from datetime import datetime, timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.models import Group, User
from django.core.mail import send_mail
from django.shortcuts import render, redirect
from django.utils import timezone

from .forms import (
    LoginForm,
    UserRegistrationForm,
    UserEditForm,
    ProfileEditForm,
    ProfileUpdateForm,
    PasswordResetRequestForm,
    OTPVerifyForm,
)
from .models import Profile, Transaction, TopUpRequest

import random
import string
from django.urls import reverse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.db import transaction

OTP_TTL_MINUTES = 10
OTP_SESSION_HASH = 'password_reset_otp_hash'
OTP_SESSION_EMAIL = 'password_reset_email'
OTP_SESSION_USER = 'password_reset_user'
OTP_SESSION_EXPIRES = 'password_reset_expires'
OTP_SESSION_VERIFIED = 'password_reset_verified'


def _hash_otp(code):
    return hashlib.sha256(f'{code}{settings.SECRET_KEY}'.encode('utf-8')).hexdigest()


def _clear_reset_session(request):
    for key in (
        OTP_SESSION_HASH,
        OTP_SESSION_EMAIL,
        OTP_SESSION_USER,
        OTP_SESSION_EXPIRES,
        OTP_SESSION_VERIFIED,
    ):
        request.session.pop(key, None)



# Create your views here.
def user_login(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            user = authenticate(request, username=data['username'], password=data['password'])
            if user is not None:
                login(request, user)
                return redirect('shops:index')
            else:
                messages.error(request, 'Invalid username or password.')
                return render(request, 'users/login.html', {'form': form})
    else:
        form = LoginForm()
    return render(request, 'users/login.html', {'form': form})

def index(request):
    return render(request, 'users/index.html')

def register(request):
    if request.method == 'POST':
        user_form = UserRegistrationForm(request.POST)
        if user_form.is_valid():
            new_user = user_form.save(commit=False)
            new_user.set_password(user_form.cleaned_data['password'])

            new_user.is_staff = False
            new_user.is_superuser = False

            new_user.save()

            Profile.objects.create(user=new_user)

            try:
                customer_group = Group.objects.get(name='Customer')
                new_user.groups.add(customer_group)
            except Group.DoesNotExist:
                pass

            return render(request, 'users/register_done.html', {'new_user': new_user})
    else:
        user_form = UserRegistrationForm()

    return render(request, 'users/register.html', {'user_form': user_form})


@login_required
def edit(request):
    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        profile = Profile.objects.create(user=request.user)
    if request.method == 'POST':
        user_form = UserEditForm(instance=request.user, data=request.POST)
        profile_form = ProfileEditForm(instance=profile, data=request.POST, files=request.FILES)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Profile updated successfully')
            return redirect('shops:index')
        else:
            messages.error(request, 'Error updating your profile')
    else:
        user_form = UserEditForm(instance=request.user)
        profile_form = ProfileEditForm(instance=profile)
    return render(request, 'users/edit.html', {'user_form': user_form, 'profile_form': profile_form})

def profile(request):
    return render(request, 'users/profile.html')


def password_reset_request(request):
    if request.method == 'POST':
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email'].strip()
            user = User.objects.filter(email__iexact=email).first()
            if not user or not user.email:
                form.add_error('email', 'Email khong ton tai trong he thong.')
            else:
                code = f"{secrets.randbelow(1000000):06d}"
                request.session[OTP_SESSION_HASH] = _hash_otp(code)
                request.session[OTP_SESSION_EMAIL] = user.email
                request.session[OTP_SESSION_USER] = user.id
                request.session[OTP_SESSION_EXPIRES] = (timezone.now() + timedelta(minutes=OTP_TTL_MINUTES)).isoformat()
                request.session[OTP_SESSION_VERIFIED] = False

                subject = 'Ma OTP khoi phuc mat khau TechStore'
                message = f"Ma OTP cua ban la: {code}\nMa se het han sau {OTP_TTL_MINUTES} phut."
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=False,
                )
                return redirect('users:password_reset_verify')
    else:
        form = PasswordResetRequestForm()

    return render(request, 'users/password_reset_form.html', {'form': form})


def password_reset_verify(request):
    if not request.session.get(OTP_SESSION_HASH):
        return redirect('users:password_reset')

    if request.method == 'POST':
        form = OTPVerifyForm(request.POST)
        if form.is_valid():
            submitted = form.cleaned_data['otp'].strip()
            expires_raw = request.session.get(OTP_SESSION_EXPIRES)
            if not expires_raw:
                form.add_error('otp', 'Ma OTP da het han. Vui long thu lai.')
            else:
                expires_at = datetime.fromisoformat(expires_raw)
                if timezone.now() > expires_at:
                    _clear_reset_session(request)
                    form.add_error('otp', 'Ma OTP da het han. Vui long thu lai.')
                elif _hash_otp(submitted) != request.session.get(OTP_SESSION_HASH):
                    form.add_error('otp', 'Ma OTP khong dung.')
                else:
                    request.session[OTP_SESSION_VERIFIED] = True
                    return redirect('users:password_reset_new')
    else:
        form = OTPVerifyForm()

    return render(request, 'users/password_reset_verify.html', {'form': form})


def password_reset_new(request):
    if not request.session.get(OTP_SESSION_VERIFIED):
        return redirect('users:password_reset')

    user_id = request.session.get(OTP_SESSION_USER)
    user = User.objects.filter(id=user_id).first()
    if not user:
        _clear_reset_session(request)
        return redirect('users:password_reset')

    if request.method == 'POST':
        form = SetPasswordForm(user, request.POST)
        if form.is_valid():
            form.save()
            _clear_reset_session(request)
            messages.success(request, 'Mat khau da duoc cap nhat. Vui long dang nhap lai.')
            return redirect('users:login')
    else:
        form = SetPasswordForm(user)

    return render(request, 'users/password_reset_new.html', {'form': form})

@login_required
def wallet_index(request):
    transactions = request.user.transactions.all().order_by('-created_at')
    context = {
        'transactions': transactions,
        'balance': request.user.profile.balance
    }
    return render(request, 'users/wallet/index.html', context)

@login_required
def topup_index(request):
    return render(request, 'users/wallet/topup.html')

@login_required
@require_POST
def topup_create(request):
    amount = request.POST.get('amount')
    method = request.POST.get('method')
    
    if not amount or not method:
        return JsonResponse({'status': 'error', 'message': 'Dữ liệu không hợp lệ.'})
        
    try:
        amount = float(amount)
        if amount < 10000:
            return JsonResponse({'status': 'error', 'message': 'Số tiền tối thiểu là 10,000 VNĐ.'})
    except ValueError:
        return JsonResponse({'status': 'error', 'message': 'Số tiền không hợp lệ.'})

    # Generate Note
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    note = f"NAPTIEN {request.user.id} {random_str}"
    
    # Expiry 15 mins
    expired_at = timezone.now() + timezone.timedelta(minutes=15)
    
    # Generate QR (Example for MB Bank)
    qr_url = f"https://img.vietqr.io/image/MB-0123456789-compact.png?amount={int(amount)}&addInfo={note}&accountName=PHAN%20CONG%20QUANG"

    topup = TopUpRequest.objects.create(
        user=request.user,
        amount=amount,
        payment_method=method,
        note=note,
        qr_url=qr_url,
        expired_at=expired_at
    )
    
    return JsonResponse({
        'status': 'success',
        'redirect_url': reverse('users:topup_detail', args=[topup.id])
    })

@login_required
def topup_detail(request, pk):
    topup = get_object_or_404(TopUpRequest, pk=pk, user=request.user)
    if topup.is_expired():
        topup.status = 'Expired'
        topup.save()
        
    return render(request, 'users/wallet/topup_detail.html', {'topup': topup})

@login_required
def check_topup_status(request, pk):
    topup = get_object_or_404(TopUpRequest, pk=pk, user=request.user)
    return JsonResponse({
        'status': topup.status,
        'is_expired': topup.is_expired()
    })
