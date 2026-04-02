(function () {
  const csrftoken = (() => {
    const name = "csrftoken";
    const cookies = document.cookie ? document.cookie.split(";") : [];
    for (let i = 0; i < cookies.length; i += 1) {
      const cookie = cookies[i].trim();
      if (cookie.startsWith(name + "=")) {
        return decodeURIComponent(cookie.substring(name.length + 1));
      }
    }
    return "";
  })();

  const modalBackdrop = document.createElement("div");
  modalBackdrop.className = "cms-modal__backdrop";

  const modal = document.createElement("div");
  modal.className = "cms-modal";
  modal.innerHTML = `
    <div class="cms-modal__header">
      <h5 class="cms-modal__title">Inline CMS Editor</h5>
      <button type="button" class="cms-modal__btn cms-modal__btn--cancel" data-cms-close>Đóng</button>
    </div>
    <textarea id="cms-editor" rows="10"></textarea>
    <div class="cms-modal__actions">
      <button type="button" class="cms-modal__btn cms-modal__btn--cancel" data-cms-cancel>Hủy</button>
      <button type="button" class="cms-modal__btn cms-modal__btn--save" data-cms-save>Lưu thay đổi</button>
    </div>
  `;

  document.body.appendChild(modalBackdrop);
  document.body.appendChild(modal);

  let activeBlock = null;
  let editorInstance = null;

  const openModal = (block) => {
    activeBlock = block;
    const contentEl = block.querySelector(".cms-edit__content");
    const currentHtml = contentEl ? contentEl.innerHTML : block.innerHTML;

    modalBackdrop.style.display = "block";
    modal.style.display = "block";

    const textarea = modal.querySelector("#cms-editor");
    textarea.value = currentHtml.trim();

    if (window.CKEDITOR) {
      if (editorInstance) {
        editorInstance.destroy(true);
      }
      editorInstance = window.CKEDITOR.replace("cms-editor", {
        height: 320,
        removePlugins: "exportpdf"
      });
    }
  };

  const closeModal = () => {
    modalBackdrop.style.display = "none";
    modal.style.display = "none";
    if (editorInstance) {
      editorInstance.destroy(true);
      editorInstance = null;
    }
    activeBlock = null;
  };

  const saveContent = async () => {
    if (!activeBlock) {
      return;
    }
    const page = activeBlock.dataset.page;
    const key = activeBlock.dataset.key;
    const textarea = modal.querySelector("#cms-editor");
    const html = editorInstance ? editorInstance.getData() : textarea.value;

    const response = await fetch("/cms/update/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrftoken
      },
      body: JSON.stringify({ page, key, content: html })
    });

    if (!response.ok) {
      alert("Không thể lưu nội dung. Vui lòng thử lại.");
      return;
    }

    const data = await response.json();
    const contentEl = activeBlock.querySelector(".cms-edit__content");
    if (contentEl) {
      contentEl.innerHTML = data.content;
    } else {
      activeBlock.innerHTML = data.content;
    }
    closeModal();
  };

  document.addEventListener("click", (event) => {
    const target = event.target;
    if (target.matches("[data-cms-close], [data-cms-cancel]")) {
      closeModal();
    }
    if (target.matches("[data-cms-save]")) {
      saveContent();
    }
  });

  modalBackdrop.addEventListener("click", closeModal);

  const blocks = document.querySelectorAll(".cms-edit");
  blocks.forEach((block) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "cms-edit__btn";
    btn.textContent = "✏️";
    btn.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      openModal(block);
    });
    block.appendChild(btn);
  });
})();
