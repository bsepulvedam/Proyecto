"use strict";

document.addEventListener("DOMContentLoaded", () => {
  const form = document.querySelector("#attendance-mark-form");
  if (!form) return;

  const button = form.querySelector('button[type="submit"]');
  const status = form.querySelector("[data-attendance-status]");
  const fields = {
    latitude: form.querySelector('[data-gps-field="latitude"]'),
    longitude: form.querySelector('[data-gps-field="longitude"]'),
    accuracy: form.querySelector('[data-gps-field="accuracy"]'),
    capturedAt: form.querySelector('[data-gps-field="captured-at"]'),
  };
  const idleLabel = button.dataset.idleLabel;
  let submitting = false;

  const restore = (message) => {
    submitting = false;
    button.disabled = false;
    button.textContent = idleLabel;
    status.textContent = message;
  };

  const geolocationErrorMessage = (error) => {
    if (error.code === error.PERMISSION_DENIED) {
      return "Debes permitir el acceso a tu ubicación para registrar asistencia.";
    }
    if (error.code === error.POSITION_UNAVAILABLE) {
      return "No fue posible obtener tu ubicación. Revisa la señal e inténtalo nuevamente.";
    }
    if (error.code === error.TIMEOUT) {
      return "La ubicación tardó demasiado. Inténtalo nuevamente.";
    }
    return "No fue posible obtener una ubicación válida. Inténtalo nuevamente.";
  };

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    if (submitting) return;
    submitting = true;
    button.disabled = true;
    button.textContent = "Obteniendo ubicación...";
    status.textContent = "Solicitando tu ubicación para este marcaje.";

    if (!("geolocation" in navigator)) {
      restore("Este navegador no permite obtener ubicación. Usa un navegador compatible e inténtalo nuevamente.");
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const { latitude, longitude, accuracy } = position.coords;
        if (
          !Number.isFinite(latitude) ||
          !Number.isFinite(longitude) ||
          !Number.isFinite(accuracy) ||
          accuracy <= 0 ||
          (latitude === 0 && longitude === 0)
        ) {
          restore("El navegador entregó una ubicación inválida. Inténtalo nuevamente.");
          return;
        }
        fields.latitude.value = latitude.toFixed(9);
        fields.longitude.value = longitude.toFixed(9);
        fields.accuracy.value = accuracy.toFixed(2);
        fields.capturedAt.value = new Date(position.timestamp).toISOString();
        button.textContent = "Registrando...";
        status.textContent = "Registrando el marcaje de forma segura.";
        form.submit();
      },
      (error) => restore(geolocationErrorMessage(error)),
      { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 },
    );
  });
});
