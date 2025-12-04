import { qs } from "./helpers.js";

export function bindCine(triggerId, modalId, closeId, imgId) {
    const trigger = qs(triggerId);
    const modal = qs(modalId);
    const close = qs(closeId);

    if (!trigger || !modal || !close) return;

    // Abrir modal
    trigger.onclick = () => {
        modal.classList.add("show");
    };

    // Cerrar modal
    close.onclick = () => {
        modal.classList.remove("show");
    };
}
