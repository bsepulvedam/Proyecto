"use strict";

document.addEventListener("DOMContentLoaded", () => {
  const sidebar = document.querySelector("#sidebar");
  const openButton = document.querySelector("#sidebar-open");
  const closeButton = document.querySelector("#sidebar-close");
  const backdrop = document.querySelector("#sidebar-backdrop");

  if (!sidebar || !openButton || !closeButton || !backdrop) return;

  const setMenuState = (isOpen) => {
    sidebar.classList.toggle("is-open", isOpen);
    backdrop.classList.toggle("is-visible", isOpen);
    document.body.classList.toggle("menu-open", isOpen);
    openButton.setAttribute("aria-expanded", String(isOpen));
  };

  openButton.addEventListener("click", () => setMenuState(true));
  closeButton.addEventListener("click", () => setMenuState(false));
  backdrop.addEventListener("click", () => setMenuState(false));
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") setMenuState(false);
  });
  window.addEventListener("resize", () => {
    if (window.innerWidth >= 992) setMenuState(false);
  });
});
