from django.db import migrations, models
import django.db.models.deletion
import uuid

class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('shops', '0010_alter_order_discount_amount_alter_order_final_price_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='DownloadGrant',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ('is_active', models.BooleanField(default=True)),
                ('max_downloads', models.IntegerField(default=3)),
                ('download_count', models.IntegerField(default=0)),
                ('expires_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='download_grants', to='shops.order')),
                ('order_item', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='download_grants', to='shops.orderitem')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='download_grants', to='shops.product')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='download_grants', to='auth.user')),
            ],
        ),
        migrations.AddConstraint(
            model_name='downloadgrant',
            constraint=models.UniqueConstraint(fields=('order_item',), name='unique_download_grant_per_item'),
        ),
    ]