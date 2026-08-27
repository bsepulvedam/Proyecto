"use strict";

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("form[data-import-form]").forEach((form) => {
    form.addEventListener("submit", () => {
      const button = form.querySelector("[data-import-button]");
      if (!button || button.disabled) return;
      button.disabled = true;
      button.innerHTML = '<span class="spinner-border spinner-border-sm me-2" aria-hidden="true"></span>Importando productos...';
    });
  });
});
