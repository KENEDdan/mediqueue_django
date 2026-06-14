from pathlib import Path
from decouple import config
import dj_database_url
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY   = config('SECRET_KEY', default='dev-key-change-me')
DEBUG        = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1').split(',')

INSTALLED_APPS = [
    # Django built-ins — DO NOT REMOVE THESE
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',

    # Third-party packages
    'crispy_forms',
    'crispy_bootstrap5',
    'widget_tweaks',
    'django_celery_beat',
    'django_celery_results',
    'rest_framework',
    'rest_framework.authtoken',

    # MediQueue apps — simple string notation (not AppConfig)
    'apps.accounts',
    'apps.clinics',
    'apps.appointments',
    'apps.doctors',
    'apps.notifications',
    'apps.superadmin',
    'apps.records',
    'apps.finance',
    'apps.api',
    'apps.security',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'mediqueue.urls'

TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [BASE_DIR / 'templates'],
    'APP_DIRS': True,
    'OPTIONS': {
        'context_processors': [
            'django.template.context_processors.debug',
            'django.template.context_processors.request',
            'django.contrib.auth.context_processors.auth',
            'django.contrib.messages.context_processors.messages',
            'apps.clinics.context_processors.subscription_context',
        ],
    },
}]

WSGI_APPLICATION = 'mediqueue.wsgi.application'

# ── Database — MySQL via Docker ───────────────────────────────
DATABASES = {
    'default': dj_database_url.config(
        default=f"mysql://{config('MYSQL_USER', default='root')}:{config('MYSQL_PASSWORD', default='root')}@{config('MYSQL_HOST', default='localhost')}:{config('MYSQL_PORT', default='3306')}/{config('MYSQL_DATABASE', default='mediqueue')}",
        conn_max_age=600,
    )
}

# ── Auth ──────────────────────────────────────────────────────
AUTH_USER_MODEL = 'accounts.User'
AUTHENTICATION_BACKENDS = [
    'apps.accounts.backends.MediQueueAuthBackend',
    'django.contrib.auth.backends.ModelBackend',
]
LOGIN_URL           = '/login/'
LOGIN_REDIRECT_URL  = '/dashboard/'
LOGOUT_REDIRECT_URL = '/'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
     'OPTIONS': {'min_length': 8}},
]

# ── Internationalisation ──────────────────────────────────────
LANGUAGE_CODE = 'en-us'
TIME_ZONE     = 'Africa/Kigali'
USE_I18N = USE_TZ = True

# ── Static & Media ────────────────────────────────────────────
STATIC_URL   = '/static/'
STATIC_ROOT  = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL  = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ── Crispy Forms ──────────────────────────────────────────────
CRISPY_ALLOWED_TEMPLATE_PACKS = 'bootstrap5'
CRISPY_TEMPLATE_PACK          = 'bootstrap5'

# ── Email ─────────────────────────────────────────────────────
EMAIL_BACKEND       = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST          = 'smtp.gmail.com'
EMAIL_PORT          = 587
EMAIL_USE_TLS       = True
EMAIL_HOST_USER     = config('EMAIL_HOST_USER',     default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL  = f"MediQueue <{config('EMAIL_HOST_USER', default='')}>"
ADMIN_EMAIL         = config('ADMIN_EMAIL', default='admin@mediqueue.com')

# ── Celery — Redis via Docker ─────────────────────────────────
CELERY_BROKER_URL         = config('REDIS_URL', default='redis://127.0.0.1:6379/0')
CELERY_RESULT_BACKEND     = 'django-db'          # stores results in MySQL
CELERY_CACHE_BACKEND      = 'django-cache'
CELERY_ACCEPT_CONTENT     = ['json']
CELERY_TASK_SERIALIZER    = 'json'
CELERY_RESULT_SERIALIZER  = 'json'
CELERY_TIMEZONE           = TIME_ZONE
CELERY_BEAT_SCHEDULER     = 'django_celery_beat.schedulers:DatabaseScheduler'
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT    = 30 * 60   # 30 minutes max per task

# ── Cache — Redis ─────────────────────────────────────────────
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': config('REDIS_URL', default='redis://127.0.0.1:6379/0'),
    }
}

# ── Sessions — stored in cache (Redis) ───────────────────────
SESSION_ENGINE         = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS    = 'default'
SESSION_COOKIE_AGE     = 86400 * 7   # 7 days
SESSION_SAVE_EVERY_REQUEST = True

# ── MediQueue Constants ───────────────────────────────────────
APP_NAME = 'MediQueue'

SUBSCRIPTION_PLANS = {
    'starter': {
        'name': 'Starter', 'tagline': 'Perfect for small clinics',
        'price_monthly': 19, 'price_annual': 190,
        'max_doctors': 10, 'color': '#1A7A9E', 'icon': '🏥',
        'features': ['Up to 10 doctors', 'Unlimited appointments',
                     'All platform features', 'Email support', 'Monthly billing'],
    },
    'growth': {
        'name': 'Growth', 'tagline': 'For growing hospitals',
        'price_monthly': 49, 'price_annual': 490,
        'max_doctors': 30, 'color': '#E05C2A', 'icon': '🚀',
        'popular': True,
        'features': ['Up to 30 doctors', 'Unlimited appointments',
                     'Priority support', 'Appointment analytics', 'Save 17% annually'],
    },
    'enterprise': {
        'name': 'Enterprise', 'tagline': 'For large hospital networks',
        'price_monthly': 99, 'price_annual': 990,
        'max_doctors': 9999, 'color': '#0B4F6C', 'icon': '🏨',
        'features': ['Unlimited doctors', 'Unlimited appointments',
                     '24/7 dedicated support', 'Advanced analytics', 'Custom integrations'],
    },
}

SECURITY_QUESTIONS = [
    'What is the name of your first pet?',
    'What city were you born in?',
    "What is your mother's maiden name?",
    'What was the name of your primary school?',
    'What is your favourite childhood movie?',
    'What street did you grow up on?',
    'What was your childhood nickname?',
]

# ── Middleware — security middleware goes FIRST ───────────────
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'apps.security.middleware.SuspiciousRequestMiddleware',   # ← add
    'apps.security.middleware.RateLimitMiddleware',           # ← add
    'apps.security.middleware.SecurityHeadersMiddleware',     # ← add
    'apps.security.middleware.AuditLogMiddleware',            # ← add
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'apps.security.middleware.SessionSecurityMiddleware',     # ← add (after auth)
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# ── Logging ───────────────────────────────────────────────────
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] [{levelname}] {name}: {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
        'simple': {
            'format': '[{levelname}] {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'security_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'security.log',
            'maxBytes': 10 * 1024 * 1024,   # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'audit_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'audit.log',
            'maxBytes': 10 * 1024 * 1024,
            'backupCount': 10,
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'mediqueue.security': {
            'handlers': ['console', 'security_file'],
            'level': 'WARNING',
            'propagate': False,
        },
        'mediqueue.audit': {
            'handlers': ['audit_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
        },
    },
}

# ── Django security settings ──────────────────────────────────
CSRF_COOKIE_SECURE      = not DEBUG
CSRF_COOKIE_HTTPONLY    = True
CSRF_COOKIE_SAMESITE    = 'Lax'
SESSION_COOKIE_SECURE   = not DEBUG
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SECURE_BROWSER_XSS_FILTER  = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# ── Production-only settings (set in env) ────────────────────
if not DEBUG:
    SECURE_SSL_REDIRECT         = True
    SECURE_HSTS_SECONDS         = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD         = True
    SECURE_PROXY_SSL_HEADER     = ('HTTP_X_FORWARDED_PROTO', 'https')

# ── File upload security ──────────────────────────────────────
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024   # 10MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
ALLOWED_UPLOAD_EXTENSIONS   = ['.pdf', '.jpg', '.jpeg', '.png', '.webp']

# ── Brute force protection ────────────────────────────────────
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'check-expiring-subscriptions': {
        'task':     'apps.finance.tasks.check_expiring_subscriptions',
        'schedule': crontab(hour=7, minute=0),  # every day at 7AM
    },
    'send-appointment-reminders': {
        'task':     'apps.finance.tasks.send_appointment_reminder',
        'schedule': crontab(hour=8, minute=0),  # every day at 8AM
    },
    'generate-monthly-summary': {
        'task':     'apps.finance.tasks.generate_monthly_summary',
        'schedule': crontab(hour=1, minute=0, day_of_month=1),  # 1st of month
    },
}

import sentry_sdk
from sentry_sdk.integrations.django  import DjangoIntegration
from sentry_sdk.integrations.celery  import CeleryIntegration
from sentry_sdk.integrations.redis   import RedisIntegration

SENTRY_DSN = config('SENTRY_DSN', default='')

if SENTRY_DSN and not DEBUG:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            DjangoIntegration(transaction_style='url'),
            CeleryIntegration(),
            RedisIntegration(),
        ],
        traces_sample_rate=0.1,       # 10% of transactions
        send_default_pii=False,       # NEVER send PII to Sentry
        environment='production',
    )

    PLATFORM_COMMISSION_RATE = config('PLATFORM_COMMISSION_RATE', default=5.0, cast=float)  # 5%

    APP_ENTITY_NAME = 'Hospital'
APP_ENTITY_NAME_PLURAL = 'Hospitals'

CSRF_TRUSTED_ORIGINS = config(
    'CSRF_TRUSTED_ORIGINS',
    default='http://localhost,http://127.0.0.1'
).split(',')

REDIS_URL = config('REDIS_URL', default='redis://localhost:6379')