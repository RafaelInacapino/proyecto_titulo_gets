# 🛠️ Sistema GETS – Ground Engagement Teeth System  
**Monitoreo inteligente de desgaste y pérdida de dientes en palas mineras**

Este repositorio contiene el sistema completo GETS, compuesto por 8 microservicios Python y 2 aplicaciones Django que permiten capturar imágenes desde cámara, procesarlas con IA, almacenar reportes y activar alertas físicas mediante Arduino.

---

## 📦 1. Requisitos del sistema

### Software obligatorio
- **Python 3.11.0**
- **MongoDB 7.0.26**
- **Mongosh 2.5.x** (para administrar MongoDB)
- Pip actualizado
- Drivers del Arduino (CH340 u otros)

### Librerías clave (Python)
A instalar manualmente en el entorno virtual:

- Flask  
- Flask-CORS  
- NumPy **1.26.4** (no usar NumPy 2.x)  
- OpenCV  
- Requests  
- PyMongo  
- Roboflow Inference SDK  
- PySerial  

---

## ⚙️ 2. Instalación

### 2.1 Crear entorno virtual
```bash
python -m venv venv
```

Activar:

**Windows**
```bash
venv\Scripts\activate
```

### 2.2 Instalar dependencias
```bash
pip install flask flask-cors numpy==1.26.4 opencv-python requests pymongo inference-sdk pyserial
```

Flask==3.0.3
flask-cors==4.0.0
opencv-python==4.9.0.80
numpy==1.26.4
inference-sdk==0.62.2
django==4.2.16
pymongo==4.6.3
pyserial==3.5
requests==2.32.3


### 2.3 Instalar MongoDB + Mongosh
- **MongoDB 7.0.26:**  
  https://www.mongodb.com/try/download/community

- **Mongosh 2.5.x:**  
  https://www.mongodb.com/try/download/shell

Verificar:
```bash
mongod --version
mongosh --version
```

---

## 🔌 3. Puertos del sistema GETS

| Servicio | Puerto |
|---------|--------|
| Stream de cámara | **5001** |
| Capturador de imágenes | **5002** |
| Procesador IA local | **5003** |
| Procesador IA nube | **5004** |
| Almacenador local | **5005** |
| Almacenador nube | **5006** |
| Alertador (Arduino) | **5007** |
| Servicio Solicitud de Reporte (SSR) | **5008** |
| Web Vigía GETS (Django) | **8000** |

---

## 🚀 4. Ejecución de microservicios

Cada servicio tiene su propio `config.json`.

Para iniciarlo:

```bash
cd servicio_xxx
venv\Scripts\activate
python app.py
```

Ejemplo:
```bash
cd servicio_procesador_imagen_modelo_local
python app.py
```

---

## 🌐 5. Iniciar la web del maquinista (Vigía GETS)

```bash
cd web_sistema_maquinaria_vigia_gets
venv\Scripts\activate
python manage.py runserver
```

Panel disponible en:

👉 **http://localhost:8000/monitoreo/**

---

## 🧪 6. Pruebas rápidas

### Estado del SSR
```bash
curl http://localhost:5008/api/v1/status
```

### Ver estado alarma física (Arduino)
```bash
curl -X POST http://localhost:5007/api/v1/status \
     -H "Content-Type: application/json" \
     -d "{\"accion\":\"STATUS\"}"
```

---

## 🧩 7. Resumen del funcionamiento general

- **Servicio de Cámara (5001):** transmite video en tiempo real.  
- **Capturador (5002):** toma snapshots bajo demanda.  
- **Procesadores (5003/5004):** analizan la imagen con IA (local y nube).  
- **Almacenadores (5005/5006):** guardan imágenes y reportes.  
- **Alertador (5007):** activa/desactiva sirena y luces vía Arduino.  
- **SSR (5008):** coordina todo el ciclo de reporte e incidentes.  
- **Web Django (8000):** dashboard para maquinistas y supervisores.  
