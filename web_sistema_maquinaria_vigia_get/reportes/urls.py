from django.urls import path
from . import views

urlpatterns = [
    path("crear/", views.crear_reporte, name="crear_reporte"),
]
