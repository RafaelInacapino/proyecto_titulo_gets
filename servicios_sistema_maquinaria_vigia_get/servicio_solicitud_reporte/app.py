import json
import logging
import threading
import time
from typing import Any, Dict
import requests
from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException
from flask_cors import CORS


# ============================================================
# LOGGING
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(threadName)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ============================================================
# CONFIG
# ============================================================
CONFIG_PATH = "config.json"
config: Dict[str, Any] = {}

def cargar_configuracion():
    global config
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)
    logger.info("config.json cargado correctamente.")


# ============================================================
# ESTADO GLOBAL ESTANDARIZADO
# ============================================================
def _ts():
    return time.strftime("%Y-%m-%d %H:%M:%S")


state = {
    "service_name": "servicio_solicitud_reporte",
    "running": False,
    "paused": False,
    "uptime_start": None,
    "last_error": None,
    "last_success": None,
    "last_cycle_info": None,
    "thread": None,
    "lock": threading.Lock()
}


# ============================================================
# UTILIDADES
# ============================================================
def contar_dientes(predicciones: Any) -> int:
    return len(predicciones) if isinstance(predicciones, list) else 0


def llamar_servicio(method: str, url: str, *, json_body=None, timeout=30):
    """HTTP con reintentos infinitos (estandarizado)."""
    espera = config.get("retry_delay_seconds", 2)

    while True:
        try:
            logger.info(f"[HTTP] {method} {url}")

            resp = requests.request(
                method=method.upper(),
                url=url,
                json=json_body,
                timeout=timeout
            )

            if 200 <= resp.status_code < 300:
                with state["lock"]:
                    state["last_success"] = _ts()
                return resp.json()

            logger.warning(f"Respuesta no exitosa {resp.status_code}: {resp.text}")

        except Exception as e:
            with state["lock"]:
                state["last_error"] = f"{_ts()} - {e}"
            logger.error(f"Error al llamar {url}: {e}")

        logger.info(f"Reintentando en {espera} segundos...")
        time.sleep(espera)


def encender_sirena():
    """Activación estandarizada del servicio de alerta."""
    try:
        servicios = config["services"]
        url = (
            servicios["servicio_alertador_incidente"]
            + servicios["servicio_alertador_incidente_rutas"][0]
        )
        requests.post(url, json={"accion": "ON"}, timeout=5)
        logger.info("Sirena activada.")
    except Exception as e:
        logger.error(f"Error al activar sirena: {e}")
        state["last_error"] = str(e)


# ============================================================
# ESTADO DEL CICLO INTERNO (igual al tuyo, pero ordenado)
# ============================================================
class EstadoInterno:
    def __init__(self):
        self.numero_ciclo = 0
        self.recurrencia = {
            "ciclos_falla_consecutiva": 0,
            "reportes_enviados": 0,
        }

    def reiniciar(self):
        self.numero_ciclo = 0
        self.recurrencia = {
            "ciclos_falla_consecutiva": 0,
            "reportes_enviados": 0,
        }


estado_interno = EstadoInterno()


# ============================================================
# INDICADORES
# ============================================================
def construir_indicadores(expected, local, nube):
    umbral = config.get("min_consecutive_missing_cycles", 2)

    faltan_local = expected - local
    faltan_nube = expected - nube

    falta_ambos = faltan_local > 0 and faltan_nube > 0

    if falta_ambos:
        estado_interno.recurrencia["ciclos_falla_consecutiva"] += 1
    else:
        estado_interno.recurrencia["ciclos_falla_consecutiva"] = 0

    incidente_real = estado_interno.recurrencia["ciclos_falla_consecutiva"] >= umbral

    return {
        "detecciones_local": local,
        "detecciones_nube": nube,
        "esperado": expected,
        "faltantes_local": faltan_local,
        "faltantes_nube": faltan_nube,
        "ciclos_falla_consecutiva": estado_interno.recurrencia["ciclos_falla_consecutiva"],
        "ciclos_para_incidente": umbral,
        "es_incidente": incidente_real,
        "descripcion": "Sin novedades" if not incidente_real else "Posible incidente"
    }


# ============================================================
# CICLO PRINCIPAL
# ============================================================
def ejecutar_ciclo():
    servicios = config["services"]

    # --------------------------------------------------------
    # 1) SNAPSHOT DESDE EL SERVICIO CAPTURADOR
    # --------------------------------------------------------
    url_snap = servicios["servicio_capturador_imagen"] + servicios["servicio_capturador_imagen_rutas"][0]
    snap = llamar_servicio("GET", url_snap)

    imagen_b64 = snap["image"]
    meta = snap["metadata"]
    expected = meta.get("expected_teeth", config["default_expected_teeth"])

    # --------------------------------------------------------
    # 2) PROCESADOR LOCAL
    # --------------------------------------------------------
    url_local = servicios["servicio_procesador_imagen_modelo_local"] + servicios["servicio_procesador_imagen_modelo_local_rutas"][0]

    proc_local = llamar_servicio("POST", url_local, json_body={"image": imagen_b64})
    dientes_local = contar_dientes(proc_local.get("predicciones", []))

    # --------------------------------------------------------
    # 3) PROCESADOR NUBE
    # --------------------------------------------------------
    url_nube = servicios["servicio_procesador_imagen_modelo_nube"] + servicios["servicio_procesador_imagen_modelo_nube_rutas"][0]

    proc_nube = llamar_servicio("POST", url_nube, json_body={"image": imagen_b64})
    dientes_nube = contar_dientes(proc_nube.get("predicciones", []))

    # --------------------------------------------------------
    # 4) Calcular indicadores y detección de incidente
    # --------------------------------------------------------
    indicadores = construir_indicadores(expected, dientes_local, dientes_nube)
    incidente = indicadores["es_incidente"]

    # --------------------------------------------------------
    # 5) ALMACENAMIENTO LOCAL (siempre)
    # --------------------------------------------------------

    if not imagen_b64:
        logger.error("❌ ERROR: imagen_b64 está vacía ANTES DE ENVIARLA AL LOCAL")
    else:
        logger.info(f"Imagen base64 OK (tamaño={len(imagen_b64)})")
    url_store_local = servicios["servicio_almacenador_imagen_local"] + servicios["servicio_almacenador_imagen_local_rutas"][0]

    ########### JSON REPORTE ESTANDARIZADO #################

    from datetime import datetime

    now_utc = datetime.utcnow().isoformat() + "Z"
    now_local = _ts()  # ya tienes esta función

    # ID único para el reporte
    id_reporte = f"{config.get('idShovel')}-{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}"

    json_reporte = {
        "id_reporte": id_reporte,
        "timestamp_utc": now_utc,
        "timestamp_local": now_local,

        # estado del reporte
        "estado_reporte": "incidente" if incidente else "sin_novedades",

        # datos de maquinaria (desde config.json)
        "maquinaria": {
            "id_shovel": config.get("idShovel"),
            "modelo_maquinaria": config["datos_maquinaria"]["modelo_maquinaria"],
            "marca_maquinaria": config["datos_maquinaria"]["marca_maquinaria"],
            "modelo_pala": config["datos_maquinaria"]["modelo_pala"],
            "marca_pala": config["datos_maquinaria"]["marca_pala"],
            "dientes_pala": config["datos_maquinaria"]["cantidad_dientes_pala"],
            "maquinista_responsable": config["datos_maquinaria"]["maquinista_responsable"]
        },

        # se completa en el almacenador local
        "ruta_imagen_local": None,
        "ruta_imagen_nube": None,

        # resultados de procesamiento
        "resultados_procesamiento_local": proc_local,
        "resultados_procesamiento_nube": proc_nube,

        # indicadores completos
        "resultados_reporte": indicadores
    }

    payload_local = {
        "imagen": imagen_b64,
        "metadatos": {
            "datetimepic": meta.get("datetimepic"),
            "idShovel": config.get("idShovel"),
            "idUser": config.get("idUser"),
            "idStatusIncident": config.get("idStatusIncident")
        },
        "json_reporte": json_reporte,
        "indicadores_recurrencia": indicadores
    }


    try:
        llamar_servicio("POST", url_store_local, json_body=payload_local, timeout=10)
    except Exception as e:
        logger.error(f"Error guardando en LOCAL: {e}")

    # --------------------------------------------------------
    # 6) ALMACENAMIENTO EN LA NUBE SOLO SI ES INCIDENTE
    # --------------------------------------------------------
    if incidente:
        url_store_cloud = servicios["servicio_almacenador_imagen_nube"] + servicios["servicio_almacenador_imagen_nube_rutas"][0]

        payload_cloud = {
            "imagen": imagen_b64,
            "metadatos": payload_local["metadatos"]   # ✔ funciona
        }

        try:
            llamar_servicio("POST", url_store_cloud, json_body=payload_cloud, timeout=10)
        except Exception as e:
            logger.error(f"Error guardando en NUBE: {e}")

    # --------------------------------------------------------
    # 7) Activar sirena si hay incidente
    # --------------------------------------------------------
    if incidente:
        encender_sirena()

    # --------------------------------------------------------
    # 8) Guardar últimos datos para monitoreo SSE/GUI
    # --------------------------------------------------------
    with state["lock"]:
        state["last_cycle_info"] = indicadores
        state["last_success"] = _ts()

    return incidente

# ============================================================
# HILO PRINCIPAL
# ============================================================
def loop_principal():
    while True:
        with state["lock"]:
            if not state["running"]:
                break
            estado_interno.numero_ciclo += 1

        es_incidente = ejecutar_ciclo()

        if es_incidente:
            with state["lock"]:
                state["running"] = False
                state["paused"] = True
                state["last_error"] = "Incidente detectado → pausa automática"
            break

        time.sleep(config["cycle_sleep_seconds"])


# ============================================================
# API
# ============================================================
app = Flask(__name__)
CORS(app)


@app.route("/api/v1/status", methods=["GET"])
def api_status():
    with state["lock"]:
        return jsonify({
            "service": state["service_name"],
            "running": state["running"],
            "paused": state["paused"],
            "uptime_start": state["uptime_start"],
            "last_success": state["last_success"],
            "last_error": state["last_error"],
            "last_cycle_info": state["last_cycle_info"],
            "ciclo_actual": estado_interno.numero_ciclo
        })


@app.route("/start", methods=["POST"])
def start():
    cargar_configuracion()

    with state["lock"]:
        if state["running"]:
            return jsonify({"msg": "Servicio ya en ejecución"}), 400

        estado_interno.reiniciar()
        state["running"] = True
        state["paused"] = False
        state["uptime_start"] = _ts()
        state["thread"] = threading.Thread(target=loop_principal, daemon=True)
        state["thread"].start()

    return jsonify({"msg": "Servicio iniciado"})


@app.route("/resume", methods=["POST"])
def resume():
    cargar_configuracion()

    with state["lock"]:
        if state["running"]:
            return jsonify({"msg": "Ya en ejecución"}), 400

        estado_interno.reiniciar()
        state["running"] = True
        state["paused"] = False
        state["uptime_start"] = _ts()
        state["thread"] = threading.Thread(target=loop_principal, daemon=True)
        state["thread"].start()

    return jsonify({"msg": "Servicio reanudado"})


@app.route("/pause", methods=["POST"])
def pause():
    with state["lock"]:
        state["running"] = False
        state["paused"] = True

    return jsonify({"msg": "Servicio pausado"})


@app.route("/stop", methods=["POST"])
def stop():
    with state["lock"]:
        state["running"] = False
        state["paused"] = False

    return jsonify({"msg": "Servicio detenido"})


@app.errorhandler(Exception)
def handle_error(e):
    with state["lock"]:
        state["last_error"] = str(e)
    return jsonify({"error": str(e)}), 500


# ============================================================
# RUN
# ============================================================
if __name__ == "__main__":
    cargar_configuracion()
    app.run(
        host=config.get("host", "0.0.0.0"),
        port=config.get("service_port", 5008),
        debug=False
    )
