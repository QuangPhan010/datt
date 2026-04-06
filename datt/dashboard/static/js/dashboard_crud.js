// Nexora Dashboard CRUD Helper - Managed URLs

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function toSlug(str) {
    str = str.toLowerCase();
    str = str.normalize('NFD').replace(/[\u0300-\u036f]/g, '');
    str = str.replace(/[đĐ]/g, 'd');
    str = str.replace(/[^a-z0-9\s-]/g, '');
    str = str.replace(/[\s-]+/g, '-');
    str = str.replace(/^-+|-+$/g, '');
    return str;
}

window.addPlanRow = function(data = null) {
    const plansContainer = document.getElementById('plansContainer');
    if (!plansContainer) return;

    const rowId = 'plan_' + Date.now() + Math.floor(Math.random() * 1000);
    const row = document.createElement('div');
    row.className = 'plan-row mb-3 p-3 rounded position-relative';
    row.id = rowId;
    
    row.innerHTML = `
        <input type="hidden" class="p-plan-id" value="${data ? data.id : ''}">
        <div class="row g-2">
            <div class="col-md-4">
                <label class="form-label small text-secondary">Tên gói</label>
                <input type="text" class="form-control form-control-sm bg-dark text-white border-secondary p-plan-name" value="${data ? data.plan_name : ''}" required>
            </div>
            <div class="col-md-3">
                <label class="form-label small text-secondary">Giá (VNĐ)</label>
                <input type="number" step="1" min="0" class="form-control form-control-sm bg-dark text-white border-secondary p-plan-price" value="${data ? Math.round(data.price) : ''}" required>
            </div>
            <div class="col-md-3">
                <label class="form-label small text-secondary">Loại</label>
                <select class="form-select form-select-sm bg-dark text-white border-secondary p-plan-type" onchange="updateDurationVisibility(this)" required>
                    <option value="monthly" ${data && data.duration_type === 'monthly' ? 'selected' : ''}>Theo tháng</option>
                    <option value="yearly" ${data && data.duration_type === 'yearly' ? 'selected' : ''}>Theo năm</option>
                    <option value="lifetime" ${data && data.duration_type === 'lifetime' ? 'selected' : ''}>Vĩnh viễn</option>
                </select>
            </div>
            <div class="col-md-2 p-duration-wrapper" style="${data && data.duration_type === 'lifetime' ? 'display: none;' : ''}">
                <label class="form-label small text-secondary">Hạn</label>
                <input type="number" class="form-control form-control-sm bg-dark text-white border-secondary p-plan-duration" value="${data ? data.duration_value : '1'}">
            </div>
        </div>
        <div class="d-flex gap-3 mt-2">
            <div class="form-check">
                <input class="form-check-input p-plan-renewable" type="checkbox" ${!data || data.is_renewable ? 'checked' : ''}>
                <label class="form-check-label small">Gia hạn</label>
            </div>
            <div class="form-check">
                <input class="form-check-input p-plan-active" type="checkbox" ${!data || data.is_active ? 'checked' : ''}>
                <label class="form-check-label small">Active</label>
            </div>
        </div>
        <button type="button" class="btn btn-sm position-absolute top-0 end-0 m-2" onclick="removePlanRow('${rowId}')">
            <i class="bi bi-x text-danger"></i>
        </button>
    `;
    plansContainer.appendChild(row);
};

window.removePlanRow = function(rowId) {
    const plansContainer = document.getElementById('plansContainer');
    if (plansContainer.children.length > 1) {
        document.getElementById(rowId).remove();
    } else {
        alert('Sản phẩm phải có ít nhất một gói bán.');
    }
};

window.updateDurationVisibility = function(selectEl) {
    const wrapper = selectEl.closest('.plan-row').querySelector('.p-duration-wrapper');
    wrapper.style.display = selectEl.value === 'lifetime' ? 'none' : 'block';
};

window.deleteProduct = function(id) {
    if (!confirm('Xác nhận xóa sản phẩm này?')) return;
    fetch(`/dashboard/products/delete/${id}/`, {
        method: 'POST',
        headers: { 'X-CSRFToken': getCookie('csrftoken') }
    })
    .then(res => res.json())
    .then(data => data.status === 'success' ? location.reload() : alert(data.message));
};

window.deleteCategory = function(id) {
    if (!confirm('Xác nhận xóa danh mục? Lưu ý: Mọi sản phẩm thuộc danh mục này cũng sẽ bị xóa.')) return;
    fetch(`/dashboard/categories/delete/${id}/`, {
        method: 'POST',
        headers: { 'X-CSRFToken': getCookie('csrftoken') }
    })
    .then(res => res.json())
    .then(data => data.status === 'success' ? location.reload() : alert(data.message));
};

document.addEventListener('DOMContentLoaded', function() {
    const csrftoken = getCookie('csrftoken');

    // Product CRUD
    const productModalEl = document.getElementById('productModal');
    if (productModalEl) {
        const productModal = new bootstrap.Modal(productModalEl);
        const productForm = document.getElementById('productForm');
        let currentId = null;

        window.openAddModal = function() {
            currentId = null;
            productForm.reset();
            document.getElementById('modalTitle').textContent = 'Thêm sản phẩm mới';
            document.getElementById('p_current_source').style.display = 'none';
            document.getElementById('plansContainer').innerHTML = '';
            addPlanRow();
            productModal.show();
        };

        window.openEditModal = function(id, name, catId, desc, img, badge, isActive, hasSource, slug) {
            currentId = id;
            document.getElementById('modalTitle').textContent = 'Chỉnh sửa sản phẩm';
            document.getElementById('p_name').value = name;
            document.getElementById('p_slug').value = slug || '';
            document.getElementById('p_category').value = catId;
            document.getElementById('p_description').value = desc;
            document.getElementById('p_thumbnail').value = img;
            document.getElementById('p_badge').value = badge;
            document.getElementById('p_is_active').checked = isActive;
            
            const sourceDisplay = document.getElementById('p_current_source');
            sourceDisplay.innerHTML = hasSource ? '<i class="bi bi-file-check me-2"></i>Đã có file nguồn.' : '';
            sourceDisplay.style.display = hasSource ? 'block' : 'none';

            const plansContainer = document.getElementById('plansContainer');
            plansContainer.innerHTML = '';
            const scriptTag = document.getElementById('plans-data-' + slug);
            const plansData = scriptTag ? JSON.parse(scriptTag.textContent) : [];
            plansData.length > 0 ? plansData.forEach(p => addPlanRow(p)) : addPlanRow();
            
            productModal.show();
        };

        document.getElementById('p_name').addEventListener('input', function() {
            if (!currentId) document.getElementById('p_slug').value = toSlug(this.value);
        });

        productForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const url = currentId ? `/dashboard/products/edit/${currentId}/` : '/dashboard/products/add/';
            const plans = [];
            document.querySelectorAll('.plan-row').forEach(row => {
                plans.push({
                    id: row.querySelector('.p-plan-id').value || null,
                    plan_name: row.querySelector('.p-plan-name').value,
                    price: row.querySelector('.p-plan-price').value,
                    duration_type: row.querySelector('.p-plan-type').value,
                    duration_value: row.querySelector('.p-plan-duration').value,
                    is_renewable: row.querySelector('.p-plan-renewable').checked,
                    is_active: row.querySelector('.p-plan-active').checked
                });
            });

            const formData = new FormData();
            formData.append('name', document.getElementById('p_name').value);
            formData.append('slug', document.getElementById('p_slug').value);
            formData.append('category_id', document.getElementById('p_category').value);
            formData.append('description', document.getElementById('p_description').value);
            formData.append('thumbnail', document.getElementById('p_thumbnail').value);
            formData.append('badge', document.getElementById('p_badge').value);
            formData.append('is_active', document.getElementById('p_is_active').checked);
            formData.append('plans', JSON.stringify(plans));

            const sourceFile = document.getElementById('p_source_file').files[0];
            if (sourceFile) formData.append('source_file', sourceFile);

            fetch(url, {
                method: 'POST',
                headers: { 'X-CSRFToken': csrftoken },
                body: formData
            })
            .then(res => res.json())
            .then(data => data.status === 'success' ? location.reload() : alert('Lỗi: ' + data.message));
        });
    }

    // Category CRUD
    const categoryModalEl = document.getElementById('categoryModal');
    if (categoryModalEl) {
        const categoryModal = new bootstrap.Modal(categoryModalEl);
        const categoryForm = document.getElementById('categoryForm');
        let currentCatId = null;

        window.openAddCategoryModal = function() {
            currentCatId = null;
            categoryForm.reset();
            document.getElementById('catModalTitle').textContent = 'Thêm danh mục';
            categoryModal.show();
        };

        window.openEditCategoryModal = function(id, name) {
            currentCatId = id;
            document.getElementById('catModalTitle').textContent = 'Chỉnh sửa danh mục';
            document.getElementById('cat_name').value = name;
            categoryModal.show();
        };

        categoryForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const url = currentCatId ? `/dashboard/categories/edit/${currentCatId}/` : '/dashboard/categories/add/';
            fetch(url, {
                method: 'POST',
                headers: { 'X-CSRFToken': csrftoken, 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: document.getElementById('cat_name').value })
            })
            .then(res => res.json())
            .then(data => data.status === 'success' ? location.reload() : alert('Lỗi: ' + data.message));
        });
    }
});
