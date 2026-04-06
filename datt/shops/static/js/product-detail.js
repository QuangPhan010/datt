let currentPrice = 0;

function selectPlan(el) {
    // UI
    document.querySelectorAll('.plan-option').forEach(opt => opt.classList.remove('active'));
    el.classList.add('active');

    // Update data
    currentPrice = parseFloat(el.getAttribute('data-price'));
    const planId = el.getAttribute('data-id');

    document.getElementById('selectedPlanId').value = planId;
    updateTotal();
}

function updateTotal() {
    const qty = parseInt(document.getElementById('purchaseQty').value) || 1;
    const total = currentPrice * qty;
    document.getElementById('displayTotal').textContent = total.toFixed(0) + ' VNĐ';

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
