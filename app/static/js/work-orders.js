"use strict";

document.addEventListener("DOMContentLoaded", () => {
  const rowsContainer = document.querySelector("#product-rows");
  const rowTemplate = document.querySelector("#product-row-template");
  const addButton = document.querySelector("#add-product-row");

  if (rowsContainer && rowTemplate && addButton) {
    addButton.addEventListener("click", () => {
      rowsContainer.appendChild(rowTemplate.content.cloneNode(true));
      rowsContainer.lastElementChild?.querySelector("input")?.focus();
    });
    rowsContainer.addEventListener("click", (event) => {
      const removeButton = event.target.closest(".remove-product-row");
      if (!removeButton) return;
      const row = removeButton.closest(".product-row");
      if (row?.dataset.baseRow === "false") row.remove();
    });
  }

  document.querySelectorAll("form[data-confirm-form]").forEach((form) => {
    form.addEventListener("submit", () => {
      const button = form.querySelector("[data-confirm-button]");
      if (!button || button.disabled) return;
      button.disabled = true;
      button.innerHTML = '<span class="spinner-border spinner-border-sm me-2" aria-hidden="true"></span>Generando OT...';
    });
  });
});
