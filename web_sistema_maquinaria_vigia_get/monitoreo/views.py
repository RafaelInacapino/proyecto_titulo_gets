from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt

from pymongo import MongoClient
import requests
import json


# =====================================================
# 🧠 ESTADO EN MEMORIA (solo Django)
# =====================================================

ALARMA_ACTIVA = False       # True si la alarma física está encendida
SSR_DETENIDO = False        # True si el SSR está detenido (popup ya manejado)


# =====================================================
# 🔗 MONGO
# =====================================================

def get_mongo_client():
    uri = settings.SERVICES_CONFIG.get("mongo_uri", "mongodb://127.0.0.1:27017/")
    return MongoClient(uri)


def get_db():
    db_name = settings.SERVICES_CONFIG.get("mongo_db", "vigia_gets")
    return get_mongo_client()[db_name]


# =====================================================
# 🧹 NORMALIZAR REPORTE
# =====================================================

def normalizar_reporte(raw):
    if not raw:
        return {}

    rr = raw.get("resultados_reporte", {})
    maq = raw.get("maquinaria", {})

    return {
        "id": str(raw.get("_id")),

        "id_reporte": raw.get("id_reporte"),
        "timestamp_utc": raw.get("timestamp_utc"),
        "timestamp_local": raw.get("timestamp_local"),

        "estado": raw.get("estado_reporte", "N/D"),
        "severidad": "ALTA" if rr.get("es_incidente") else "BAJA",
        "resumen": rr.get("descripcion", "Sin descripción disponible."),
        "tiempo_proceso_ms": raw.get("tiempo_ms", "-"),

        "ruta_imagen_local": raw.get("ruta_imagen_local"),
        "ruta_imagen_nube": raw.get("ruta_imagen_nube"),

        "detecciones_local": rr.get("detecciones_local"),
        "detecciones_nube": rr.get("detecciones_nube"),
        "esperado": rr.get("esperado"),
        "faltantes_local": rr.get("faltantes_local"),
        "faltantes_nube": rr.get("faltantes_nube"),

        "ciclos_falla_consecutiva": rr.get("ciclos_falla_consecutiva"),
        "ciclos_para_incidente": rr.get("ciclos_para_incidente"),
        "es_incidente": rr.get("es_incidente", False),

        "idShovel": maq.get("id_shovel"),
        "modelo_maquinaria": maq.get("modelo_maquinaria"),
        "marca_maquinaria": maq.get("marca_maquinaria"),
        "modelo_pala": maq.get("modelo_pala"),
        "marca_pala": maq.get("marca_pala"),
        "dientes_pala": maq.get("dientes_pala"),
        "maquinista_responsable": maq.get("maquinista_responsable"),

        "rawname": raw.get("rawname"),

        # AHORA ES PARTE DEL REPORTE
        "confirmado": raw.get("confirmado", False)
    }

def normalizar_incidente(raw):
    if not raw:
        return {}

    return {
        "id": str(raw.get("_id")),
        "path": raw.get("path"),
        "rawname": raw.get("rawname"),
        "datetimepic": raw.get("datetimepic"),
        "idUser": raw.get("idUser"),
        "idShovel": raw.get("idShovel"),
        "idStatusIncident": raw.get("idStatusIncident"),
        "confirmado": raw.get("confirmado", False)
    }


# =====================================================
# 📊 DASHBOARD PRINCIPAL
# =====================================================

def dashboard(request):
    db = get_db()

    reportes = db["reportes"]
    incidentes = db["incidentes"]
    logs = db["logs_solicitudes"]

    # Último reporte normalizado
    last_raw = reportes.find_one(sort=[("_id", -1)])
    last_report = normalizar_reporte(last_raw)

    # Últimos 10 reportes
    raw_reports = reportes.find().sort("_id", -1).limit(10)
    last_reports = [normalizar_reporte(r) for r in raw_reports]

    # Snapshot
    snapshot = last_report.get("ruta_imagen_local") or "/static/img/no_image.png"

    # Cámara
    camera_cfg = settings.SERVICES_CONFIG.get("camera", {})
    camera_url = (
        f"{camera_cfg.get('host', 'http://127.0.0.1:5001')}"
        f"{camera_cfg.get('stream_route', '/video_feed')}"
    )

    # Datos maquinaria
    datos_maquinaria = settings.SERVICES_CONFIG.get("datos_maquinaria", {})

    shovel_info = {
        "marca_maquinaria": datos_maquinaria.get("marca_maquinaria", "N/D"),
        "modelo_maquinaria": datos_maquinaria.get("modelo_maquinaria", "N/D"),
        "marca_pala": datos_maquinaria.get("marca_pala", "N/D"),
        "modelo_pala": datos_maquinaria.get("modelo_pala", "N/D"),
        "cantidad_dientes": datos_maquinaria.get("cantidad_dientes_pala", "N/D"),
        "maquinista": datos_maquinaria.get("maquinista_responsable", "N/D"),
        "ubicacion": datos_maquinaria.get("ubicacion", "N/D"),
        "codigo": "SHV-001",
        "estado": "En operación",
    }

    # NO DEVOLVEMOS estados de SSR ni alarma → ahora vienen del fetch (dashboard_data)
    return render(request, "monitoreo/dashboard.html", {
        "last_report": last_report,
        "last_reports": last_reports,
        "last_snapshot_url": snapshot,
        "camera_stream_url": camera_url,
        "shovel": shovel_info,
    })

# =====================================================
# DASHBOARD DATA
# =====================================================
def dashboard_data(request):
    db = get_db()
    reportes = db["reportes"]
    incidentes = db["incidentes"]

    raw_last = reportes.find_one(sort=[("_id", -1)])
    last_report = normalizar_reporte(raw_last)

    raw_list = reportes.find().sort("_id", -1).limit(10)
    last_reports = [normalizar_reporte(r) for r in raw_list]

    # 👇 AQUÍ: último incidente con confirmado
    inc_last = incidentes.find_one(sort=[("_id", -1)])
    incidente_confirmado = False
    if inc_last:
        incidente_confirmado = inc_last.get("confirmado", False)

    # SSR real
    ssr_status = {"running": False, "paused": True}
    try:
        r = requests.get("http://127.0.0.1:5008/api/v1/status", timeout=3)
        if r.status_code == 200:
            d = r.json()
            ssr_status["running"] = d.get("running", False)
            ssr_status["paused"] = d.get("paused", True)
    except:
        pass

    # --- info pala ---
    datos_maquinaria = settings.SERVICES_CONFIG.get("datos_maquinaria", {})
    shovel = {
        "marca_maquinaria": datos_maquinaria.get("marca_maquinaria"),
        "modelo_maquinaria": datos_maquinaria.get("modelo_maquinaria"),
        "marca_pala": datos_maquinaria.get("marca_pala"),
        "modelo_pala": datos_maquinaria.get("modelo_pala"),
        "cantidad_dientes": datos_maquinaria.get("cantidad_dientes_pala"),
        "maquinista": datos_maquinaria.get("maquinista_responsable"),
        "ubicacion": datos_maquinaria.get("ubicacion"),
        "codigo": "SHV-001",
        "estado": "En operación"
    }

    return JsonResponse({
        "last_report": last_report,
        "last_reports": last_reports,
        "shovel": shovel,
        "ssr_status": ssr_status,
        "incidente_confirmado": incidente_confirmado,  # 👈 clave que usa JS
    })

# =====================================================
# 🛑 PAUSAR ALARMA (CONFIRMAR INCIDENTE)
# =====================================================

@csrf_exempt
def detener_alarma(request):
    global ALARMA_ACTIVA, SSR_DETENIDO

    db = get_db()
    incidentes = db["incidentes"]

    # Marcar último incidente como confirmado = True
    ultimo = incidentes.find_one(sort=[("_id", -1)])
    if ultimo:
        incidentes.update_one(
            {"_id": ultimo["_id"]},
            {"$set": {"confirmado": True}}
        )

    ALARMA_ACTIVA = False
    SSR_DETENIDO = True   # DETENIDO hasta que usuario haga clic en "Reanudar"

    # Apagar alarma física
    alert_cfg = settings.SERVICES_CONFIG.get("alert_service", {})
    url_alerta = alert_cfg.get("url", "http://127.0.0.1:5007/api/v1/alerta")

    try:
        requests.post(url_alerta, json={"accion": "OFF"}, timeout=5)
    except Exception as e:
        print(f"⚠ Error al apagar alarma física: {e}")

    return JsonResponse({"status": "ok"})


# =====================================================
# 🔄 REANUDAR SSR — botón amarillo del dashboard
# =====================================================

@csrf_exempt
def reanudar_ssr(request):
    global SSR_DETENIDO
    SSR_DETENIDO = False
    return JsonResponse({"status": "ok"})
