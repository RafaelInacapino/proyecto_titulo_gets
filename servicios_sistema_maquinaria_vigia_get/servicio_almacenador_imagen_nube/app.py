import os
import sys
import json
import base64
import time
import requests
from datetime import datetime
from flask import Flask, request, jsonify
from threading import Lock
from werkzeug.exceptions import HTTPException

app = Flask(__name__)

# =====================================================
# Metadatos del servicio
# =====================================================
SERVICE_NAME = "servicio_almacenador_imagen_nube"
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
# Cargar configuración
# =====================================================
def load_config():
    base_path = os.path.dirname(
        sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(__file__)
    )
    config_path = os.path.join(base_path, "config.json")

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"No se encontró config.json en {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


# =====================================================
# ENVÍO A DJANGO + ENVÍO A NUBE
# =====================================================
def enviar_a_nube(imagen_bytes: bytes, metadatos: dict):

    cfg = state["config"]

    storage_url = cfg.get("storage_url")         # Django
    api_url = cfg.get("nube_url")               # Azure Function / API
    api_key = cfg.get("nube_api_key")           # Opcional

    if not storage_url:
        raise RuntimeError("Falta storage_url en config.json")

    if not api_url:
        raise RuntimeError("Falta nube_url en config.json")

    # -----------------------------
    # VALIDACIONES
    # -----------------------------
    id_shovel = metadatos.get("idShovel")
    if not id_shovel:
        raise RuntimeError(f"Falta idShovel en metadatos: {metadatos}")

    datetimepic = metadatos.get("datetimepic")
    id_user = metadatos.get("idUser")
    id_status = metadatos.get("idStatusIncident")

    # =====================================================
    # 1) SUBIR IMAGEN A DJANGO (upload_image_reporte)
    # =====================================================
    data_storage = {
        "idShovel": str(id_shovel),
        "datetimepic": datetimepic,
        "folder_type": "incidentes"
    }

    files_storage = {
        "file": ("incident.jpg", imagen_bytes, "image/jpeg")
    }

    try:
        resp_storage = requests.post(
            storage_url,
            files=files_storage,
            data=data_storage,
            timeout=15
        )
        resp_storage.raise_for_status()
        storage_json = resp_storage.json()
    except Exception as e:
        raise RuntimeError(f"Error llamando a storage_url: {e}")

    if storage_json.get("status") != "ok":
        raise RuntimeError(f"Respuesta inválida del storage: {storage_json}")

    ruta_nube = storage_json["path"]
    rawname = storage_json["rawname"]

    # =====================================================
    # 2) PAYLOAD EXACTO HACIA AZURE
    # =====================================================
    payload = {
        "path": ruta_nube,
        "rawname": rawname,
        "datetimepic": datetimepic,
        "idUser": id_user,
        "idShovel": int(id_shovel),
        "idStatusIncident": id_status
    }

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    # =====================================================
    # 3) ENVIAR A SERVICIO EN LA NUBE
    # =====================================================
    try:
        resp_api = requests.post(api_url, json=payload, headers=headers, timeout=15)
        resp_api.raise_for_status()
        api_json = resp_api.json()
    except Exception as e:
        raise RuntimeError(f"Error enviando JSON a nube_url: {e}")

    # =====================================================
    # 4) RETORNAR OBJETO COMPLETO
    # =====================================================
    return {
        "ruta_imagen_nube": ruta_nube,
        "rawname_nube": rawname,
        "payload_enviado": payload,
        "respuesta_api_nube": api_json
    }


# =====================================================
# Manejo de errores global
# =====================================================
@app.errorhandler(Exception)
def handle_exception(e):
    if isinstance(e, HTTPException):
        return jsonify({"error": e.description}), e.code

    with state["lock"]:
        state["last_error"] = str(e)

    return jsonify({"error": str(e)}), 500


# =====================================================
# ENDPOINT principal
# =====================================================
@app.route("/api/v1/reportes", methods=["POST"])
def crear_reporte():

    data = request.get_json(force=True, silent=True)

    if not data:
        return jsonify({"error": "JSON inválido"}), 400

    metadatos = data.get("metadatos") or data.get("metadata")
    imagen_b64 = data.get("imagen")

    if not metadatos:
        return jsonify({"error": "Falta metadatos"}), 400

    if not imagen_b64:
        return jsonify({"error": "Falta imagen base64"}), 400

    try:
        imagen_bytes = base64.b64decode(imagen_b64)
    except:
        return jsonify({"error": "Imagen base64 inválida"}), 400

    try:
        resultado = enviar_a_nube(imagen_bytes, metadatos)
    except Exception as e:
        with state["lock"]:
            state["last_error"] = str(e)
        return jsonify({"error": str(e)}), 500

    with state["lock"]:
        state["last_result"] = resultado
        state["last_error"] = None

    return jsonify({"status": "ok", "resultado": resultado}), 201


# =====================================================
# STATUS
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
        port=cfg.get("service_port", 5006),
        debug=False,
        threaded=True
    )


if __name__ == "__main__":
    run_service()
