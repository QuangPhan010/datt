document.addEventListener('DOMContentLoaded', function() {
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
    const csrftoken = getCookie('csrftoken') || (document.querySelector('[name=csrfmiddlewaretoken]') ? document.querySelector('[name=csrfmiddlewaretoken]').value : '');

    // --- PRODUCT ACTIONS ---
    window.deleteProduct = function(id) {
        if (!confirm('Bạn có chắc chắn muốn xóa sản phẩm này?')) return;
        
        fetch(`/shops/products/delete/${id}/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrftoken,
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

    const productModalEl = document.getElementById('productModal');
    if (productModalEl) {
        const productModal = new bootstrap.Modal(productModalEl);
        const productForm = document.getElementById('productForm');
        let currentId = null;

        window.openAddModal = function() {
            currentId = null;
            productForm.reset();
            document.getElementById('modalTitle').textContent = 'Thêm sản phẩm mới';
            productModal.show();
        };

        window.openEditModal = function(id, name, catId, desc, price, img, badge) {
            currentId = id;
            document.getElementById('modalTitle').textContent = 'Chỉnh sửa sản phẩm';
            document.getElementById('p_name').value = name;
            document.getElementById('p_category').value = catId;
            document.getElementById('p_description').value = desc;
            document.getElementById('p_price').value = price;
            document.getElementById('p_image_url').value = img;
            document.getElementById('p_badge').value = badge;
            productModal.show();
        };

        productForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const url = currentId ? `/shops/products/edit/${currentId}/` : '/shops/products/add/';
            
            const data = {
                name: document.getElementById('p_name').value,
                category_id: document.getElementById('p_category').value,
                description: document.getElementById('p_description').value,
                price: document.getElementById('p_price').value,
                image_url: document.getElementById('p_image_url').value,
                badge: document.getElementById('p_badge').value
            };

            fetch(url, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrftoken,
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
                    'X-CSRFToken': csrftoken,
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

    window.toggleCategoryHide = function(id) {
        fetch(`/shops/categories/toggle-hide/${id}/`, {
            method: 'POST',
            headers: { 'X-CSRFToken': csrftoken }
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
            headers: { 'X-CSRFToken': csrftoken }
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
});
