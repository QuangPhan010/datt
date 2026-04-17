chia thành ba giao diện: cho key admin, key manage, key emloyee
có notifacation : thông báo, hoạt động đăng kí dịch vụ , lịch sự thay đổi tồn kho(user thay đổi), đơn hàng đặt
thống kê thông báo: tồn kho , danh thu, tình hình hoạt động của từng loại dịch vụ, số lượng hàng xuất kho , dịch vụ được ưa thích.
## Wishlist ? Flash Sale ? Notification

### Migration
```bash
python manage.py makemigrations
python manage.py migrate
```

### Cron/Job
Ch?y command `flash_sale_tick` m?i 1 ph�t d? active flash sale v� g?i notification:
```bash
python manage.py flash_sale_tick
```

### Tests
```bash
python manage.py test
```
