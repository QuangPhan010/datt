function updateCartItem(itemId, action) {
    fetch(cartConfig.updateCartUrl, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': cartConfig.csrfToken
        },
        body: JSON.stringify({
            item_id: itemId,
            action: action
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            // Update quantity display
            const qtyElement = document.getElementById(`qty-${itemId}`);
            if (qtyElement) qtyElement.innerText = data.quantity;

            // Update item subtotal
            const subtotalElement = document.getElementById(`subtotal-${itemId}`);
            if (subtotalElement) subtotalElement.innerText = `${parseFloat(data.item_total).toFixed(0)} VNĐ`;

            // Update cart summary
            const cartSubtotalElement = document.getElementById('cart-subtotal');
            if (cartSubtotalElement) cartSubtotalElement.innerText = `${parseFloat(data.cart_total).toFixed(0)} VNĐ`;
            
            const cartTotalElement = document.getElementById('cart-total');
            if (cartTotalElement) cartTotalElement.innerText = `${parseFloat(data.cart_total).toFixed(0)} VNĐ`;

            // Update Navbar cart badge (globally if exists)
            const cartBadge = document.getElementById('navbar-cart-count');
            if (cartBadge) cartBadge.innerText = data.cart_count;
        } else {
            alert(data.message);
        }
    })
    .catch(error => {
        console.error('Error updating cart:', error);
    });
}

function removeCartItem(itemId) {
    if (!confirm('Bạn có chắc chắn muốn xóa sản phẩm này?')) return;

    fetch(cartConfig.removeFromCartUrl, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': cartConfig.csrfToken
        },
        body: JSON.stringify({
            item_id: itemId
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            // Remove the item card from DOM
            const itemCard = document.getElementById(`item-${itemId}`);
            if (itemCard) itemCard.style.opacity = '0';
            setTimeout(() => {
                if (itemCard) itemCard.remove();
                
                // If cart is empty, reload to show empty state
                if (data.cart_count === 0) {
                    location.reload();
                }
            }, 300);

            // Update cart summary
            const cartSubtotalElement = document.getElementById('cart-subtotal');
            if (cartSubtotalElement) cartSubtotalElement.innerText = `${parseFloat(data.cart_total).toFixed(0)} VNĐ`;
            
            const cartTotalElement = document.getElementById('cart-total');
            if (cartTotalElement) cartTotalElement.innerText = `${parseFloat(data.cart_total).toFixed(0)} VNĐ`;

            const cartBadge = document.getElementById('navbar-cart-count');
            if (cartBadge) cartBadge.innerText = data.cart_count;
        } else {
            alert(data.message);
        }
    })
    .catch(error => {
        console.error('Error removing from cart:', error);
    });
}