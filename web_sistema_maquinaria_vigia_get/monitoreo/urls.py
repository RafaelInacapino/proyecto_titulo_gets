from django.urls import path
from .views import (
    dashboard,
    dashboard_data,
    detener_alarma,
    reanudar_ssr,
)

urlpatterns = [
    path("", dashboard, name="dashboard_monitoreo"),
    path('dashboard_data/', dashboard_data, name='dashboard_data'),
    path("detener_alarma/", detener_alarma, name="detener_alarma"),
    path("reanudar_ssr/", reanudar_ssr, name="reanudar_ssr"),
]
