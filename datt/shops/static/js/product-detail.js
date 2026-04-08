let currentPrice = 0;
let currentStock = 0;
function formatVN(num) {
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

function selectPlan(el) {
    // UI
    document.querySelectorAll('.plan-option').forEach(opt => opt.classList.remove('active'));
    el.classList.add('active');

    // Update data
    currentPrice = parseFloat(el.getAttribute('data-price'));
    currentStock = parseInt(el.getAttribute('data-stock')) || 0;
    const planId = el.getAttribute('data-id');

    document.getElementById('selectedPlanId').value = planId;

    // Reset quantity if it exceeds new stock
    const qtyInput = document.getElementById('purchaseQty');
    if (parseInt(qtyInput.value) > currentStock) {
        qtyInput.value = currentStock > 0 ? 1 : 0;
    }

    updateTotal();
}

function changeQty(delta) {
    const input = document.getElementById('purchaseQty');
    let val = parseInt(input.value) + delta;
    
    if (val < 1) val = 1;

    if (val > currentStock) {
        if (typeof Swal !== 'undefined') {
            Swal.fire({
                title: 'Hết hàng',
                text: `Số lượng tối đa có sẵn là ${currentStock}`,
                icon: 'warning',
                confirmButtonColor: '#ff0000'
            });
        } else {
            alert(`Chỉ còn ${currentStock} sản phẩm trong kho.`);
        }
        return;
    }

    input.value = val;
    updateTotal();
}

function updateTotal() {
    const qty = parseInt(document.getElementById('purchaseQty').value) || 1;
    const total = currentPrice * qty;
    document.getElementById('displayTotal').textContent = formatVN(Math.round(total)) + ' VNĐ';

    // Update hidden quantity field for form submission if used
    const finalQty = document.getElementById('finalQty');
    if (finalQty) finalQty.value = qty;
}

// Initialize on load
document.addEventListener('DOMContentLoaded', () => {
    const activePlan = document.querySelector('.plan-option.active');
    if (activePlan) {
        selectPlan(activePlan);
    }
});
