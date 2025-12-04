from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from pymongo import MongoClient
import json


def get_db():
    client = MongoClient(settings.MONGO_URI)
    return client["vigia_gets"]


@csrf_exempt
def crear_reporte(request):
    """
    Recibe un JSON maestro de reporte y lo guarda tal cual
    en la colección 'reportes'.

    NO modificamos el contenido, solo lo insertamos.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Método no permitido"}, status=405)

    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception as e:
        return JsonResponse({"error": f"JSON inválido: {e}"}, status=400)

    db = get_db()
    result = db["reportes"].insert_one(data)

    return JsonResponse(
        {
            "status": "ok",
            "inserted_id": str(result.inserted_id),
        },
        status=201,
    )
