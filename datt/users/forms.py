from .models import Profile
from django import forms
from django.contrib.auth.models import User



class UserEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email')

class ProfileEditForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ('photo',)

class ProfileUpdateForm(forms.ModelForm):
    email = forms.EmailField(required=True, label="Email")
    
    class Meta:
        model = Profile
        fields = ('fullname', 'phone', 'photo')

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user:
            self.fields['email'].initial = self.user.email

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exclude(pk=self.user.pk).exists():
            raise forms.ValidationError("Email này đã được sử dụng bởi một tài khoản khác.")
        return email

    def save(self, commit=True):
        profile = super().save(commit=False)
        if commit:
            profile.save()
            # Update user email
            user = self.user
            user.email = self.cleaned_data['email']
            user.save()
        return profile

class LoginForm(forms.Form):
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)

class UserRegistrationForm(forms.ModelForm):
    password = forms.CharField(label='Password', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Repeat password', widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ('username', 'first_name', 'email')

    def clean_password2(self):
        cd = self.cleaned_data
        if cd['password'] != cd['password2']:
            raise forms.ValidationError('Passwords don\'t match.')
        return cd['password2']


class PasswordResetRequestForm(forms.Form):
    email = forms.EmailField(label='Email', widget=forms.EmailInput(attrs={'placeholder': 'email@example.com'}))


class OTPVerifyForm(forms.Form):
    otp = forms.CharField(label='OTP', max_length=6, min_length=6)
