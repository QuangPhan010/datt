const csrfInput = document.querySelector('[name=csrfmiddlewaretoken]');
const cartConfig = {
    updateCartUrl: "/shops/cart/update/",
    removeFromCartUrl: "/shops/cart/remove/",
    payWithBalanceUrl: "/shops/cart/pay-with-balance/",
    csrfToken: csrfInput ? csrfInput.value : ''
};

function formatVN(num) {
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ".");
}

function updateCartItem(itemId, action) {
    const qtyInput = document.getElementById(`qty-${itemId}`);
    const currentQty = parseInt(qtyInput.value);
    const stock = parseInt(qtyInput.getAttribute('data-stock')) || 0;

    if (action === 'increase' && currentQty >= stock) {
        Swal.fire({
            title: 'Hết hàng',
            text: `Số lượng tối đa có sẵn là ${stock}`,
            icon: 'warning',
            confirmButtonColor: '#ff0000'
        });
        return;
    }

    fetch(cartConfig.updateCartUrl, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': cartConfig.csrfToken
        },
        body: JSON.stringify({ item_id: itemId, action: action })
    })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                document.getElementById(`qty-${itemId}`).value = data.quantity;
                document.getElementById(`subtotal-${itemId}`).innerText = formatVN(data.item_total) + 'đ';
                updateSummary(data.cart_total);
            } else {
                Swal.fire('Lỗi', data.message, 'error');
            }
        });
}

function removeCartItem(itemId) {
    Swal.fire({
        title: 'Xóa sản phẩm?',
        text: "Bạn có chắc chắn muốn xóa sản phẩm này khỏi giỏ hàng?",
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#ff0000',
        confirmButtonText: 'Xóa ngay',
        cancelButtonText: 'Hủy'
    }).then((result) => {
        if (result.isConfirmed) {
            fetch(cartConfig.removeFromCartUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': cartConfig.csrfToken
                },
                body: JSON.stringify({ item_id: itemId })
            })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        document.getElementById(`item-${itemId}`).remove();
                        updateSummary(data.cart_total);
                        if (data.cart_count === 0) {
                            location.reload();
                        }
                    }
                });
        }
    });
}

function updateSummary(total) {
    const subtotalEl = document.getElementById('summary-subtotal');
    const totalEl = document.getElementById('summary-total');
    
    if (subtotalEl) subtotalEl.innerText = formatVN(total) + 'đ';
    if (totalEl) totalEl.innerText = formatVN(total) + 'đ';

    const balanceEl = document.getElementById('user-balance-val');
    if (balanceEl) {
        const balance = parseInt(balanceEl.getAttribute('data-balance'));
        const deficit = Math.max(0, total - balance);
        document.getElementById('summary-deficit').innerText = formatVN(deficit) + 'đ';

        // Toggle Buttons
        const payBtn = document.getElementById('btn-pay-balance');
        const topupBtns = document.getElementById('topup-actions');

        if (deficit === 0) {
            if (payBtn) payBtn.classList.remove('d-none');
            if (topupBtns) topupBtns.classList.add('d-none');
        } else {
            if (payBtn) payBtn.classList.add('d-none');
            if (topupBtns) topupBtns.classList.remove('d-none');
        }
    }
}

function processBalancePayment() {
    const phone = document.getElementById('contact-phone').value;
    if (!phone || phone.length < 10) {
        Swal.fire('Thông báo', 'Vui lòng nhập số điện thoại liên hệ hợp lệ.', 'info');
        return;
    }

    Swal.fire({
        title: 'Xác nhận thanh toán',
        text: "Hệ thống sẽ trừ tiền trực tiếp từ số dư tài khoản của bạn.",
        icon: 'question',
        showCancelButton: true,
        confirmButtonColor: '#007bff',
        confirmButtonText: 'Thanh toán ngay'
    }).then((result) => {
        if (result.isConfirmed) {
            const formData = new FormData();
            formData.append('phone', phone);

            fetch(cartConfig.payWithBalanceUrl, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': cartConfig.csrfToken
                },
                body: formData
            })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        window.location.href = data.redirect_url;
                    } else {
                        Swal.fire('Thanh toán thất bại', data.message, 'error');
                    }
                });
        }
    });
}
