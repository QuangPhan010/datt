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

            const formData = new FormData();
            formData.append('name', document.getElementById('p_name').value);
            formData.append('slug', document.getElementById('p_slug').value);
            formData.append('category_id', document.getElementById('p_category').value);
            formData.append('description', document.getElementById('p_description').value);
            formData.append('thumbnail', document.getElementById('p_thumbnail').value);
            formData.append('badge', document.getElementById('p_badge').value);
            formData.append('is_active', document.getElementById('p_is_active').checked);

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
