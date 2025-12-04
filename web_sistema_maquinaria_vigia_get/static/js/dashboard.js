// static/js/dashboard.js
import { qs, updateText, vigiaAlert, vigiaConfirm } from "./helpers.js";
import { bindCine } from "./cine.js";
import {
    mostrarModalIncidente,
    bindPausarAlarma,
    bloquearCierreManual,
    incidenteActivo,
    ultimoIncidenteMostrado
} from "./incidente.js";

// Estado interno del dashboard
let intervaloDashboard = null;
let ssrEstaPausado = false;
let ssrPopupMostrado = false;   // 👈 para mostrar solo 1 vez el popup de reanudar SSR

/* ============================================================
   CONTROL DE POLLING
============================================================ */
function iniciarDashboard() {
    if (!intervaloDashboard) {
        intervaloDashboard = setInterval(updateDashboard, 5000);
    }
}

function detenerDashboard() {
    if (intervaloDashboard) {
        clearInterval(intervaloDashboard);
        intervaloDashboard = null;
    }
}

/* ============================================================
   REANUDAR SSR (FUNCION REUTILIZABLE)
============================================================ */
function reanudarSSR() {
    return fetch("http://127.0.0.1:5008/resume", { method: "POST" })
        .then(r => {
            if (!r.ok) throw new Error();
            return r.json();
        })
        .then(() => {
            vigiaAlert("SSR reanudado", "El monitoreo está activo nuevamente.", "success");
            const panel = qs("panelReanudar");
            if (panel) panel.style.display = "none";
            ssrEstaPausado = false;
        })
        .catch(() => {
            vigiaAlert("Error", "No se pudo reanudar el SSR.", "error");
        });
}

/* ============================================================
   BIND BOTÓN “REANUDAR MONITOREO”
============================================================ */
function bindReanudarSSR() {
    const btn = qs("btnReanudarSSR");
    if (!btn) return;

    btn.onclick = () => {
        vigiaConfirm(
            "Reanudar monitoreo",
            "El incidente fue gestionado. ¿Deseas reactivar el SSR?",
            "question"
        ).then(ok => {
            if (!ok) return;
            reanudarSSR();
        });
    };
}

/* ============================================================
   UPDATE DASHBOARD (FETCH PRINCIPAL)
============================================================ */
function updateDashboard() {

    // Si el modal de incidente está activo, NO actualizamos nada
    if (incidenteActivo) return;

    fetch("/monitoreo/dashboard_data/")
        .then(r => r.json())
        .then(data => {

            const rep = data.last_report || {};
            const ssr = data.ssr_status || {};
            const incidenteConfirmado = data.incidente_confirmado === true;

            const esIncidente = (rep.estado === "incidente") || (rep.es_incidente === true);

            // Estado SSR (real)
            ssrEstaPausado = (!ssr.running || ssr.paused);

            // Mostrar u ocultar panel amarillo de “Monitoreo detenido”
            const panel = qs("panelReanudar");
            if (panel) {
                panel.style.display = ssrEstaPausado ? "block" : "none";
            }

            /* =====================================================
               1) SI SSR ESTÁ ACTIVO → NO HAY POPUPS ESPECIALES
            ===================================================== */
            if (!ssrEstaPausado) {
                // Solo actualizamos info visual
            } else {

                /* =================================================
                   2) INCIDENTE SIN CONFIRMAR → MODAL INCIDENTE
                ================================================= */
                if (esIncidente && !incidenteConfirmado) {

                    // Evitar repetir el mismo incidente
                    if (ultimoIncidenteMostrado !== rep.id) {
                        mostrarModalIncidente(rep);   // esto pone incidenteActivo = true
                        // detenemos el resto del update, el modal manda
                        return;
                    }

                /* =================================================
                   3) INCIDENTE CONFIRMADO + SSR PAUSADO
                      → POPUP “¿REANUDAR SSR?” SOLO 1 VEZ
                ================================================= */
                } else if (esIncidente && incidenteConfirmado && ssrEstaPausado && !ssrPopupMostrado) {

                    ssrPopupMostrado = true;  // nunca más en este reload

                    vigiaConfirm(
                        "Reanudar monitoreo",
                        "El último incidente ya fue confirmado. ¿Deseas reactivar el SSR?",
                        "question"
                    ).then(ok => {
                        if (!ok) return;
                        reanudarSSR();
                    });
                }
            }

            /* =================================================
               4) ACTUALIZAR DATOS VISUALES (si no hubo modal nuevo)
            ================================================= */

            // Snapshot
            if (rep.ruta_imagen_local) {
                const cineImg = qs("cineSnapshotImage");
                if (cineImg) cineImg.src = rep.ruta_imagen_local;

                const thumb = document.querySelector("#snapshotThumbnail img");
                if (thumb) thumb.src = rep.ruta_imagen_local;
            }

            // Estado del reporte
            updateText("estado-reporte", rep.estado ?? "-");
            updateText("sev-reporte", rep.severidad ?? "-");
            updateText("tiempo-proceso", (rep.tiempo_proceso_ms ?? "-") + " ms");
            updateText("det-local", rep.detecciones_local ?? "-");
            updateText("det-nube", rep.detecciones_nube ?? "-");
            updateText("det-esperado", rep.esperado ?? "-");

            // Tabla de reportes
            const tb = qs("tabla-reportes-body");
            if (tb) {
                tb.innerHTML = "";
                (data.last_reports || []).forEach((r, i) => {
                    const badge =
                        r.estado === "incidente" ? "danger" :
                        r.estado === "sin_novedades" ? "success" : "secondary";

                    tb.innerHTML += `
                        <tr>
                            <td>${i + 1}</td>
                            <td>${r.timestamp_local || ""}</td>
                            <td>${r.id_reporte || ""}</td>
                            <td>${r.idShovel || ""}</td>
                            <td><span class="badge badge-${badge}">${(r.estado || "").toUpperCase()}</span></td>
                            <td>${r.severidad || ""}</td>
                            <td>${r.detecciones_local ?? "-"}/${r.detecciones_nube ?? "-"}/${r.esperado ?? "-"}</td>
                            <td>${r.faltantes_local ?? "-"}/${r.faltantes_nube ?? "-"}</td>
                        </tr>`;
                });
            }
        });
}

/* ============================================================
   INICIO
============================================================ */
document.addEventListener("DOMContentLoaded", () => {

    // Modo cine cámara y snapshot
    bindCine("cameraThumbnail", "cineModal", "cerrarCine", "cineImage");
    bindCine("snapshotThumbnail", "cineSnapshot", "cerrarSnapshot", "cineSnapshotImage");

    // Botón “Pausar alarma” y bloqueo de cierre del modal
    bindPausarAlarma("/monitoreo/detener_alarma/");
    bloquearCierreManual();

    // Botón “Reanudar SSR”
    bindReanudarSSR();

    // Polling del dashboard
    iniciarDashboard();
    updateDashboard(); // primer fetch inmediato
});
