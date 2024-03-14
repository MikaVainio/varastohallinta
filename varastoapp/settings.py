"""
Django settings for varastoapp project.

Generated by 'django-admin startproject' using Django 4.0.3.

For more information on this file, see
https://docs.djangoproject.com/en/4.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.0/ref/settings/
"""
import os
from pathlib import Path

import environ

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, True),
    SECRET_KEY=(str, ""),
    ALLOWED_HOSTS=(list, []),
    DATABASE_URL=(str, f"postgres:///varasto"),
    EMAIL_URL=(str, "consolemail:"),
    DEFAULT_FROM_EMAIL=(str, "varasto@localhost"),
    STATIC_ROOT=(str, BASE_DIR / "static"),
    MEDIA_ROOT=(str, BASE_DIR / "media"),
    LOG_TO=(str, "console"),
    LOG_LEVEL=(str, "INFO"),
    LOG_LEVELS=(list, [f"django:INFO"]),
)
env.read_env(BASE_DIR / ".env")

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

DEBUG = env.bool("DEBUG")
SECRET_KEY = env.str("SECRET_KEY", default=("xxx" if DEBUG else ""))
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")

EMAIL_BACKEND = env.email("EMAIL_URL")["EMAIL_BACKEND"]
EMAIL_FILE_PATH = env.email("EMAIL_URL")["EMAIL_FILE_PATH"]
EMAIL_HOST = env.email("EMAIL_URL")["EMAIL_HOST"]
EMAIL_PORT = env.email("EMAIL_URL")["EMAIL_PORT"]
EMAIL_HOST_USER = env.email("EMAIL_URL")["EMAIL_HOST_USER"]
EMAIL_HOST_PASSWORD = env.email("EMAIL_URL")["EMAIL_HOST_PASSWORD"]
DEFAULT_FROM_EMAIL = env.str("DEFAULT_FROM_EMAIL")

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'widget_tweaks',
    'varasto',
    'varastoapp',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'varastoapp.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'varastoapp/templates'), ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                "varasto.context_processors.get_rental_events_page",
            ],
        },
    },
]

WSGI_APPLICATION = 'varastoapp.wsgi.application'


# Database
# https://docs.djangoproject.com/en/4.0/ref/settings/#databases

DATABASES = {"default": env.db("DATABASE_URL")}


# Password validation
# https://docs.djangoproject.com/en/4.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.0/topics/i18n/

# LANGUAGE_CODE = 'en-us'
LANGUAGE_CODE = 'fi'

TIME_ZONE = 'Europe/Helsinki'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# and Media files (files updaled by user)
# https://docs.djangoproject.com/en/4.2/howto/static-files/
STATIC_URL = "static/"
STATIC_ROOT = env.str("STATIC_ROOT")
MEDIA_URL = "media/"
MEDIA_ROOT = env.str("MEDIA_ROOT")

# Default primary key field type
# https://docs.djangoproject.com/en/4.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
AUTH_USER_MODEL = 'varasto.CustomUser'
LOGIN_URL = '/login/'

LOG_TO = env.str("LOG_TO")
LOG_LEVEL = env.str("LOG_LEVEL", default=("INFO" if DEBUG else "WARNING"))
LOG_LEVELS = env.list("LOG_LEVELS", default=[
    f"django:{LOG_LEVEL}",
    f"django.request:{'INFO' if DEBUG else 'ERROR'}",
])

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "syslog-format": {
            "format" : "varastoapp[%(process)d]: (%(name)s) %(message)s",
        },
        "ymd": {"datefmt": "%Y-%m-%d %H:%M:%S"}
    },
    "handlers": {
        "console": {"class": "rich.logging.RichHandler", "formatter": "ymd"},
        "syslog": {
            "class": "logging.handlers.SysLogHandler",
            "formatter": "syslog-format",
            "address": "/dev/log",
        },
    },
    "root": {
        "handlers": [LOG_TO],
        "level": LOG_LEVEL,
    },
    "loggers": {
        name: {"level": level}
        for (name, level) in (item.rsplit(":", 1) for item in LOG_LEVELS)
    },
}
