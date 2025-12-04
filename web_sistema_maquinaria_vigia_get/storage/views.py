import os
from datetime import datetime
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt


def _generar_nombre(id_shovel: str, datetimepic: str | None, original_name: str):
    """
    Genera:
      rawname: <idShovel>_<YYYYMMDDHHMMSS>
      filename: rawname + extensión
    """
    if not id_shovel:
        id_shovel = "unknown"

    ts = None
    if datetimepic:
        safe = "".join(c for c in datetimepic if c.isdigit())
        if len(safe) >= 14:
            ts = safe[:14]

    if not ts:
        ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")

    ext = os.path.splitext(original_name)[1].lower()
    if not ext:
        ext = ".jpg"

    rawname = f"{id_shovel}_{ts}"
    filename = rawname + ext
    return rawname, filename


@csrf_exempt
def upload_image_reporte(request):
    """
    Guarda una imagen de reporte o incidente.

    POST multipart/form-data:
      - file o image
      - idShovel
      - datetimepic (ISO, opcional)
      - folder_type = reportes | incidentes (default: reportes)
      - otros campos → van en "extra"

    Respuesta JSON:
    {
      "status": "ok",
      "folder": "reportes" | "incidentes",
      "path": "http://.../media/reportes/22_2025....jpg",
      "rawname": "22_2025....",
      "idShovel": "22",
      "datetimepic": "2025-03-30T01:00:00Z",
      "extra": { ... }
    }
    """
    if request.method != "POST":
        return JsonResponse({"error": "Método no permitido"}, status=405)

    image = request.FILES.get("file") or request.FILES.get("image")
    if not image:
        return JsonResponse({"error": "Se requiere 'file' o 'image'"}, status=400)

    id_shovel = request.POST.get("idShovel")
    datetimepic = request.POST.get("datetimepic")
    folder_type = (request.POST.get("folder_type") or "reportes").lower()

    if folder_type not in ["reportes", "incidentes"]:
        folder_type = "reportes"

    if not id_shovel:
        return JsonResponse({"error": "Debe incluir idShovel"}, status=400)

    rawname, filename = _generar_nombre(id_shovel, datetimepic, image.name)

    dest_dir = os.path.join(settings.MEDIA_ROOT, folder_type)
    os.makedirs(dest_dir, exist_ok=True)

    file_path = os.path.join(dest_dir, filename)
    with open(file_path, "wb+") as dest:
        for chunk in image.chunks():
            dest.write(chunk)

    relative_url = f"{settings.MEDIA_URL}{folder_type}/{filename}"
    full_url = request.build_absolute_uri(relative_url)

    extra = {
        key: value
        for key, value in request.POST.items()
        if key not in ["idShovel", "datetimepic", "folder_type"]
    }

    return JsonResponse(
        {
            "status": "ok",
            "folder": folder_type,
            "path": full_url,
            "rawname": rawname,
            "idShovel": id_shovel,
            "datetimepic": datetimepic,
            "extra": extra,
        },
        status=201,
    )
