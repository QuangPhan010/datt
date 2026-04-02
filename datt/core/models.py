from django.db import models


class ContentBlock(models.Model):
    page = models.CharField(max_length=100)
    key = models.CharField(max_length=100)
    content = models.TextField()

    class Meta:
        unique_together = ('page', 'key')

    def __str__(self):
        return f'{self.page}:{self.key}'
