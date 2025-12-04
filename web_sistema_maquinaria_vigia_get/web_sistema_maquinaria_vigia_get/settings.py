"""
Django settings for web_sistema_maquinaria_vigia_get project.
"""

import os
import json
from pathlib import Path

# ======================================================
# BASE PATHS
# ======================================================

BASE_DIR = Path(__file__).resolve().parent.parent


# ======================================================
# CORE DJANGO SETTINGS
# ======================================================

SECRET_KEY = 'django-insecure-%&2a^nlu@ma4x&+)hcsxdm@)fz5-hfsjqkn^3_ci4%&mhd4)!='
DEBUG = True
ALLOWED_HOSTS = ['*']


# ======================================================
# APPS
# ======================================================

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Tus apps
    'monitoreo',
    'reportes',
    'incidentes',
    'storage',
]


# ======================================================
# MIDDLEWARE
# ======================================================

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


# ======================================================
# TEMPLATE ENGINE
# ======================================================

ROOT_URLCONF = 'web_sistema_maquinaria_vigia_get.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'web_sistema_maquinaria_vigia_get.wsgi.application'


# ======================================================
# DATABASE (DUMMY — SOLO USAS MONGO)
# ======================================================

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.dummy",
    }
}


# ======================================================
# AUTH PASSWORD VALIDATORS
# ======================================================

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# ======================================================
# INTERNATIONALIZATION
# ======================================================

LANGUAGE_CODE = 'es-cl'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


# ======================================================
# STATIC & MEDIA
# ======================================================

STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / "static",
]

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, "media")


# ======================================================
# MONGO — PARA USAR EN TUS VIEWS (Pymongo)
# ======================================================

# URI que usan tus views para conectar:
MONGO_URI = "mongodb://127.0.0.1:27017/"

# Tus views ya usan client["vigia_gets"], así que NO agregamos nada más.


# ======================================================
# SYSTEM CONFIG — config.json
# ======================================================

CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

try:
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        SERVICES_CONFIG = json.load(f)
except Exception:
    SERVICES_CONFIG = {}
    print("⚠ WARNING: NO config.json LOADED")


# ======================================================
# FIN DE SETTINGS
# ======================================================
