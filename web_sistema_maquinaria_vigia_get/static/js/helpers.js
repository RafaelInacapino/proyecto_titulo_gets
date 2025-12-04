/* ============================================================
   HELPERS BÁSICOS
============================================================ */
export function qs(id) { return document.getElementById(id); }

export function updateText(id, txt) {
    const el = qs(id);
    if (el) el.textContent = txt;
}

/* ============================================================
   SWEETALERT ESTILIZADO
============================================================ */
export function vigiaConfirm(title, text, icon = "warning") {

    document.body.classList.add("swal-on");

    return Swal.fire({
        title,
        text,
        icon,
        background: "#1a1d21",
        color: "#fff",
        showCancelButton: true,
        confirmButtonText: "Sí",
        cancelButtonText: "Cancelar",
        confirmButtonColor: "#28a745",
        cancelButtonColor: "#d33",
        heightAuto: false
    }).then(r => {
        document.body.classList.remove("swal-on");
        return r.isConfirmed;
    });
}

export function vigiaAlert(title, text, icon = "info") {

    document.body.classList.add("swal-on");

    return Swal.fire({
        title,
        text,
        icon,
        background: "#1a1d21",
        color: "#fff",
        confirmButtonColor: "#0a6f9f",
        heightAuto: false
    }).then(() => {
        document.body.classList.remove("swal-on");
    });
}
