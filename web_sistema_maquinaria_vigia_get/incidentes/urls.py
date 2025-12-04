from django.urls import path
from . import views

urlpatterns = [
    path("crear/", views.crear_incidente, name="crear_incidente"),
]
