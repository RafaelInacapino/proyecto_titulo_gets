from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from pymongo import MongoClient
import json


# ============================================
# CONEXIÓN A MONGO — SIEMPRE USAR CONFIG.JSON
# ============================================

def get_mongo_client():
    try:
        uri = settings.SERVICES_CONFIG.get("mongo_uri", "mongodb://127.0.0.1:27017")
    except:
        uri = "mongodb://127.0.0.1:27017"

    return MongoClient(uri)


def get_db():
    """
    Obtiene la BD real desde el archivo de configuración.
    """
    client = get_mongo_client()

    # Nombre de la BD puede venir desde config.json
    db_name = settings.SERVICES_CONFIG.get("mongo_db", "vigia_gets")

    return client[db_name]


# ============================================
#  ENDPOINT: CREAR INCIDENTE
# ============================================

@csrf_exempt
def crear_incidente(request):
    """
    Recibe un payload simple de incidente ya confirmado
    y lo guarda en MongoDB en la colección 'incidentes'.
    """

    if request.method != "POST":
        return JsonResponse({"error": "Método no permitido"}, status=405)

    # ---- Leer JSON recibido ----
    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception as e:
        return JsonResponse({"error": f"JSON inválido: {e}"}, status=400)

    # ---- Insertar en la BD ----
    db = get_db()
    result = db["incidentes"].insert_one(data)

    return JsonResponse(
        {
            "status": "ok",
            "inserted_id": str(result.inserted_id),
            "message": "Incidente almacenado correctamente."
        },
        status=201,
    )
