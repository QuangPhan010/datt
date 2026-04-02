from .models import Profile, FavoriteMusic
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

class FavoriteMusicForm(forms.ModelForm):
    class Meta:
        model = FavoriteMusic
        fields = ('title', 'artist', 'audio_file', 'spotify_url', 'youtube_url')
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'Song title', 'class': 'form-control'}),
            'artist': forms.TextInput(attrs={'placeholder': 'Artist name', 'class': 'form-control'}),
            'audio_file': forms.FileInput(attrs={'class': 'form-control', 'accept': 'audio/*'}),
            'spotify_url': forms.URLInput(attrs={'placeholder': 'Spotify URL (optional)', 'class': 'form-control'}),
            'youtube_url': forms.URLInput(attrs={'placeholder': 'YouTube URL (optional)', 'class': 'form-control'}),
        }

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
