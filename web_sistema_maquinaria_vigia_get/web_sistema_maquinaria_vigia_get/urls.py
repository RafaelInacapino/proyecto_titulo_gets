# web_sistema_imagenes_reportes/urls.py  (nombre de carpeta según tu proyecto)
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
  
    # Web
    path("monitoreo/", include("monitoreo.urls")),

    # APIs internas
    path("api/storage/", include("storage.urls")),
    path("api/reportes/", include("reportes.urls")),
    path("api/incidentes/", include("incidentes.urls")),
]

# Servir archivos de media en desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
