// Helper to get CSRF token
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

// Slugify function with Vietnamese support
function toSlug(str) {
    str = str.toLowerCase();
    // remove accents
    str = str.normalize('NFD').replace(/[\u0300-\u036f]/g, '');
    // replace đ
    str = str.replace(/[đĐ]/g, 'd');
    // keep only alphanumeric and space
    str = str.replace(/[^a-z0-9\s-]/g, '');
    // replace space with hyphen
    str = str.replace(/[\s-]+/g, '-');
    // trim hyphens
    str = str.replace(/^-+|-+$/g, '');
    return str;
}

// Global functions for onclick handlers (Products)
window.addPlanRow = function(data = null) {
    const plansContainer = document.getElementById('plansContainer');
    if (!plansContainer) return;

    const rowId = 'plan_' + Date.now() + Math.floor(Math.random() * 1000);
    const row = document.createElement('div');
    row.className = 'plan-row mb-3 p-3 border border-secondary rounded position-relative bg-dark bg-opacity-25';
    row.id = rowId;
    
    row.innerHTML = `
        <input type="hidden" class="p-plan-id" value="${data ? data.id : ''}">
        <div class="row g-2">
            <div class="col-md-4">
                <label class="form-label small">Tên gói (VD: 1 tháng)</label>
                <input type="text" class="form-control form-control-sm bg-dark text-white border-secondary p-plan-name" value="${data ? data.plan_name : ''}" required>
            </div>
            <div class="col-md-3">
                <label class="form-label small">Giá (VNĐ)</label>
                <input type="number" step="1000" class="form-control form-control-sm bg-dark text-white border-secondary p-plan-price" value="${data ? data.price : ''}" required>
            </div>
            <div class="col-md-3">
                <label class="form-label small">Loại</label>
                <select class="form-select form-select-sm bg-dark text-white border-secondary p-plan-type" onchange="updateDurationVisibility(this)" required>
                    <option value="monthly" ${data && data.duration_type === 'monthly' ? 'selected' : ''}>Theo tháng</option>
                    <option value="yearly" ${data && data.duration_type === 'yearly' ? 'selected' : ''}>Theo năm</option>
                    <option value="lifetime" ${data && data.duration_type === 'lifetime' ? 'selected' : ''}>Vĩnh viễn</option>
                </select>
            </div>
            <div class="col-md-2 p-duration-wrapper" style="${data && data.duration_type === 'lifetime' ? 'display: none;' : ''}">
                <label class="form-label small">Thời hạn</label>
                <input type="number" class="form-control form-control-sm bg-dark text-white border-secondary p-plan-duration" value="${data ? data.duration_value : '1'}">
            </div>
        </div>
        <div class="d-flex gap-3 mt-2">
            <div class="form-check">
                <input class="form-check-input p-plan-renewable" type="checkbox" ${!data || data.is_renewable ? 'checked' : ''}>
                <label class="form-check-label small">Cho phép gia hạn</label>
            </div>
            <div class="form-check">
                <input class="form-check-input p-plan-active" type="checkbox" ${!data || data.is_active ? 'checked' : ''}>
                <label class="form-check-label small">Kích hoạt</label>
            </div>
        </div>
        <button type="button" class="btn btn-sm btn-outline-secondary position-absolute top-0 end-0 m-2 border-0" onclick="removePlanRow('${rowId}')">
            <i class="bi bi-x-lg text-danger"></i>
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
    if (selectEl.value === 'lifetime') {
        wrapper.style.display = 'none';
    } else {
        wrapper.style.display = 'block';
    }
};

// Global functions (Products)

window.deleteProduct = function(id) {
    if (!confirm('Bạn có chắc chắn muốn xóa sản phẩm này?')) return;
    
    fetch(`/shops/products/delete/${id}/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            location.reload();
        } else {
            alert('Lỗi: ' + data.message);
        }
    })
    .catch(err => alert('Lỗi kết nối: ' + err.message));
};

// Global functions (Categories)
window.toggleCategoryHide = function(id) {
    fetch(`/shops/categories/toggle-hide/${id}/`, {
        method: 'POST',
        headers: { 'X-CSRFToken': getCookie('csrftoken') }
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            location.reload();
        } else {
            alert('Lỗi: ' + data.message);
        }
    });
};

window.deleteCategory = function(id) {
    if (!confirm('Xóa danh mục sẽ xóa tất cả sản phẩm thuộc danh mục này. Bạn có chắc chắn?')) return;
    
    fetch(`/shops/categories/delete/${id}/`, {
        method: 'POST',
        headers: { 'X-CSRFToken': getCookie('csrftoken') }
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            location.reload();
        } else {
            alert('Lỗi: ' + data.message);
        }
    });
};

document.addEventListener('DOMContentLoaded', function() {
    const csrftoken = getCookie('csrftoken');

    // --- PRODUCT ACTIONS ---
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
            const plansContainer = document.getElementById('plansContainer');
            if (plansContainer) {
                plansContainer.innerHTML = '';
                addPlanRow(); // Add one default plan
            }
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
            if (hasSource) {
                sourceDisplay.textContent = 'Đã có file source. Tải lên file mới để thay thế.';
                sourceDisplay.style.display = 'block';
            } else {
                sourceDisplay.style.display = 'none';
            }

            document.getElementById('p_source_file').value = '';
            // Populate plans
            const plansContainer = document.getElementById('plansContainer');
            if (plansContainer) {
                plansContainer.innerHTML = '';
                const scriptTag = document.getElementById('plans-data-' + id);
                const plansData = scriptTag ? JSON.parse(scriptTag.textContent) : [];
                
                if (plansData.length > 0) {
                    plansData.forEach(p => addPlanRow(p));
                } else {
                    addPlanRow();
                }
            }
            
            productModal.show();
        };

        // Real-time slug generation
        document.getElementById('p_name').addEventListener('input', function() {
            if (!currentId) { // Only auto-generate for new products
                const slugInput = document.getElementById('p_slug');
                if (slugInput) {
                    slugInput.value = toSlug(this.value);
                }
            }
        });

        productForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const url = currentId ? `/shops/products/edit/${currentId}/` : '/shops/products/add/';
            const plansContainer = document.getElementById('plansContainer');
            if (!plansContainer) return;
            
            const plans = [];
            plansContainer.querySelectorAll('.plan-row').forEach(row => {
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
            if (sourceFile) {
                formData.append('source_file', sourceFile);
            }

            fetch(url, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrftoken || getCookie('csrftoken'),
                },
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    location.reload();
                } else {
                    alert('Lỗi: ' + data.message);
                }
            })
            .catch(err => alert('Lỗi kết nối: ' + err.message));
        });
    }

    // --- CATEGORY ACTIONS ---
    const categoryModalEl = document.getElementById('categoryModal');
    if (categoryModalEl) {
        const categoryModal = new bootstrap.Modal(categoryModalEl);
        const categoryForm = document.getElementById('categoryForm');
        let currentCatId = null;

        window.openAddCategoryModal = function() {
            currentCatId = null;
            categoryForm.reset();
            document.getElementById('catModalTitle').textContent = 'Thêm danh mục mới';
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
            const url = currentCatId ? `/shops/categories/edit/${currentCatId}/` : '/shops/categories/add/';
            const data = { name: document.getElementById('cat_name').value };

            fetch(url, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrftoken || getCookie('csrftoken'),
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    location.reload();
                } else {
                    alert('Lỗi: ' + data.message);
                }
            })
            .catch(err => alert('Lỗi kết nối: ' + err.message));
        });
    }
});
