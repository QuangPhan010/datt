from django.conf import settings
from django.db import models
from django.contrib.auth.models import User


# Create your models here.
class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL , on_delete=models.CASCADE)
    photo = models.ImageField(upload_to='users/%Y/%m/%d/', blank=True)

    def __str__(self):
            return self.user.username


class FavoriteMusic(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='favorite_music')
    title = models.CharField(max_length=200)
    artist = models.CharField(max_length=200)
    audio_file = models.FileField(upload_to='music/%Y/%m/%d/', blank=True, help_text='MP3, WAV, or OGG file')
    spotify_url = models.URLField(blank=True)
    youtube_url = models.URLField(blank=True)
    created = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s favorite: {self.title} - {self.artist}"

    class Meta:
        verbose_name_plural = "Favorite Music"