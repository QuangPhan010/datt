function selectPlan(el) {
    // UI
    document.querySelectorAll('.plan-option').forEach(opt => opt.classList.remove('active'));
    el.classList.add('active');

    // Update data
    const price = el.getAttribute('data-price');
    const planId = el.getAttribute('data-id');

    document.getElementById('displayTotal').textContent = '$' + parseFloat(price).toFixed(2);
    document.getElementById('selectedPlanId').value = planId;
}

// Initialize on load
document.addEventListener('DOMContentLoaded', () => {
    const activePlan = document.querySelector('.plan-option.active');
    if (activePlan) {
        selectPlan(activePlan);
    }
});