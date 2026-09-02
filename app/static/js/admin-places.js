"use strict";

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-app-toast]").forEach((element) => {
    window.bootstrap?.Toast.getOrCreateInstance(element).show();
  });

  const modalElement = document.querySelector("#place-state-confirmation");
  const message = modalElement?.querySelector("[data-place-state-message]");
  const confirmButton = modalElement?.querySelector("[data-place-state-confirm]");
  if (!modalElement || !message || !confirmButton || !window.bootstrap) return;

  const modal = window.bootstrap.Modal.getOrCreateInstance(modalElement);
  let pendingForm = null;

  document.querySelectorAll("[data-place-state-trigger]").forEach((button) => {
    button.addEventListener("click", () => {
      pendingForm = button.form;
      const action = button.dataset.placeStateAction;
      const name = button.dataset.placeName;
      message.textContent = `¿Deseas ${action} "${name}"?`;
      confirmButton.disabled = false;
      modal.show();
    });
  });

  confirmButton.addEventListener("click", () => {
    if (!pendingForm) return;
    confirmButton.disabled = true;
    pendingForm.requestSubmit();
  });

  modalElement.addEventListener("hidden.bs.modal", () => {
    pendingForm = null;
    confirmButton.disabled = false;
  });
});
