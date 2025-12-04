import os
import sys
import json
import base64
import time
import requests
from datetime import datetime
from flask import Flask, request, jsonify
from threading import Lock

app = Flask(__name__)

# =====================================================
# Metadatos del servicio
# =====================================================
SERVICE_NAME = "servicio_almacenador_imagen_local"
SERVICE_START_TIME = time.time()

# =====================================================
# Estado global
# =====================================================
state = {
    "config": None,
    "running": False,
    "last_result": None,
    "last_error": None,
    "lock": Lock()
}

# =====================================================
# Configuración
# =====================================================
def load_config():
    base_path = os.path.dirname(
        sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(__file__)
    )
    config_path = os.path.join(base_path, "config.json")

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"No se encontró {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


# =====================================================
# Envía a STORAGE (Django) y luego guarda:
#  - reporte completo
#  - incidente simple (si aplica)
# =====================================================
def enviar_a_web_local(imagen_bytes, metadatos, reporte_json, es_incidente):

    cfg = state["config"]
    storage_url = cfg["storage_url"]
    incidente_url = cfg["django_incidentes_url"]
    reportes_url = cfg["django_reportes_url"]

    # ------------------------------
    # Validar pala
    # ------------------------------
    id_shovel = metadatos.get("idShovel")
    if not id_shovel:
        raise RuntimeError("Falta idShovel en metadatos")

    try:
        id_shovel = int(id_shovel)
    except:
        raise RuntimeError("idShovel inválido")

    # ------------------------------
    # 1) Guardar imagen en Django
    # ------------------------------
    files_storage = {
        "file": ("reporte.jpg", imagen_bytes, "image/jpeg")
    }

    data_storage = {
        "idShovel": str(id_shovel),
        "datetimepic": metadatos.get("datetimepic", "")
    }

    try:
        resp = requests.post(storage_url, files=files_storage, data=data_storage, timeout=15)
        resp.raise_for_status()
        storage_json = resp.json()
    except Exception as e:
        raise RuntimeError(f"Error llamando a storage local: {e}")

    if storage_json.get("status") != "ok":
        raise RuntimeError(f"Respuesta inválida de storage local: {storage_json}")

    ruta_local = storage_json["path"]
    rawname = storage_json["rawname"]

    # ------------------------------
    # 2) Completar JSON del reporte
    # ------------------------------
    reporte_json["ruta_imagen_local"] = ruta_local
    reporte_json["rawname"] = rawname

    # ------------------------------
    # 3) Guardar REPORTE COMPLETO
    # ------------------------------
    try:
        resp2 = requests.post(reportes_url, json=reporte_json, timeout=20)
        resp2.raise_for_status()
        resultado_reporte = resp2.json()
    except Exception as e:
        raise RuntimeError(f"Error enviando reporte a Django: {e}")

    # ------------------------------
    # 4) Guardar INCIDENTE SIMPLE
    # ------------------------------
    resultado_incidente = None
    if es_incidente:
        incidente_payload = {
            "path": ruta_local,
            "rawname": rawname,
            "datetimepic": metadatos.get("datetimepic"),
            "idUser": metadatos.get("idUser"),
            "idShovel": id_shovel,
            "idStatusIncident": metadatos.get("idStatusIncident")
        }

        try:
            resp3 = requests.post(incidente_url, json=incidente_payload, timeout=15)
            resp3.raise_for_status()
            resultado_incidente = resp3.json()
        except Exception as e:
            raise RuntimeError(f"Error enviando incidente a Django/MongoDB: {e}")

    return {
        "reporte": resultado_reporte,
        "incidente": resultado_incidente
    }


# =====================================================
# Endpoint principal
# =====================================================
@app.route("/api/v1/reportes", methods=["POST"])
def crear_reporte():

    data = request.get_json(force=True)
    if "imagen" not in data:
        return jsonify({"error": "Se requiere imagen base64"}), 400

    # Base64 → bytes
    try:
        imagen_bytes = base64.b64decode(data["imagen"])
    except Exception:
        return jsonify({"error": "Imagen base64 inválida"}), 400

    # Metadatos
    metadatos = data.get("metadatos") or data.get("metadata") or {}

    # Reporte completo
    reporte_json = data.get("json_reporte", {})

    # Determinar si es incidente real
    indicadores = data.get("indicadores_recurrencia") or {}
    es_incidente = indicadores.get("es_incidente", False)

    try:
        resultado = enviar_a_web_local(
            imagen_bytes,
            metadatos,
            reporte_json,
            es_incidente
        )
    except Exception as e:
        with state["lock"]:
            state["last_error"] = str(e)
        return jsonify({"error": str(e)}), 500

    with state["lock"]:
        state["last_result"] = resultado
        state["last_error"] = None

    return jsonify({"status": "ok", "resultado": resultado}), 201


# =====================================================
# STATUS estándar para monitoreo GUI
# =====================================================
@app.route("/status", methods=["GET"])
@app.route("/api/v1/status", methods=["GET"])
def status():
    with state["lock"]:
        return jsonify({
            "servicio": SERVICE_NAME,
            "status": "ok" if state["last_error"] is None else "error",
            "running": state["running"],
            "uptime_sec": round(time.time() - SERVICE_START_TIME, 2),
            "ultimo_resultado": state["last_result"],
            "ultimo_error": state["last_error"],
            "timestamp": datetime.utcnow().isoformat()
        }), 200


# =====================================================
# RUN
# =====================================================
def run_service():
    state["config"] = load_config()
    state["running"] = True
    cfg = state["config"]

    app.run(
        host=cfg.get("host", "0.0.0.0"),
        port=cfg.get("service_port", 5005),
        debug=False,
        threaded=True
    )


if __name__ == "__main__":
    run_service()
