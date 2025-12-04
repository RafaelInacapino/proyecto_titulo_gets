import { qs, updateText, vigiaAlert, vigiaConfirm } from "./helpers.js";

export let incidenteActivo = false;
export let ultimoIncidenteMostrado = null;

/* ============================================================
   MOSTRAR MODAL INCIDENTE
============================================================ */
export function mostrarModalIncidente(rep) {

    incidenteActivo = true;
    ultimoIncidenteMostrado = rep.id;

    qs("modalIncidenteImg").src = rep.ruta_imagen_local || "";
    updateText("modalIncidenteId", rep.id_reporte ?? "-");
    updateText("modalIncidenteEstado", rep.estado?.toUpperCase() ?? "-");
    updateText("modalIncidenteSeveridad", rep.severidad ?? "-");
    updateText(
        "modalIncidenteFaltantes",
        `${rep.faltantes_local ?? "-"} / ${rep.faltantes_nube ?? "-"}`
    );
    updateText("modalIncidenteResumen", rep.resumen || "");

    qs("modalIncidente").style.display = "flex";
}

/* ============================================================
   PAUSAR ALARMA
============================================================ */
export function bindPausarAlarma() {

    qs("btnPausarAlarma").onclick = function () {

        vigiaConfirm("Pausar alarma", "¿Confirmar el incidente y detener la alarma?", "warning")
            .then(ok => {
                if (!ok) return;

                fetch("/monitoreo/detener_alarma/", {
                    method: "POST",
                    headers: { "X-Requested-With": "XMLHttpRequest" }
                })
                    .then(r => r.json())
                    .then(() => {
                        vigiaAlert("Alarma pausada", "Incidente confirmado.", "success");
                        qs("modalIncidente").style.display = "none";
                        incidenteActivo = false;
                    })
                    .catch(() => {
                        vigiaAlert("Error", "No se pudo pausar la alarma.", "error");
                    });
            });
    };
}

/* ============================================================
   EVITAR CIERRE DEL MODAL
============================================================ */
export function bloquearCierreManual() {
    qs("modalIncidente").onclick = e => {
        if (e.target.id === "modalIncidente") {
            vigiaAlert(
                "Incidente activo",
                "Debes pausar la alarma para cerrar el incidente.",
                "warning"
            );
        }
    }
}
