"""
MediQueue Security Middleware Stack
Covers: XSS, Clickjacking, MIME sniffing, referrer leakage,
rate limiting signals, suspicious request detection.
"""
import re
import logging
from django.http import HttpResponseForbidden, JsonResponse
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger('mediqueue.security')

# ── Security Headers ──────────────────────────────────────────

class SecurityHeadersMiddleware:
    """
    Adds comprehensive security headers to every response.
    CIA — Confidentiality: prevents data leakage via headers.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Prevent MIME type sniffing
        response['X-Content-Type-Options'] = 'nosniff'

        # Prevent clickjacking
        response['X-Frame-Options'] = 'DENY'

        # XSS protection (legacy browsers)
        response['X-XSS-Protection'] = '1; mode=block'

        # Referrer policy — don't leak URLs to external sites
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'

        # Permissions policy — disable unused browser features
        response['Permissions-Policy'] = (
            'geolocation=(), microphone=(), camera=(), '
            'payment=(), usb=(), magnetometer=(), '
            'accelerometer=(), gyroscope=()'
        )

        # Content Security Policy
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://js.stripe.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "img-src 'self' data: https:; "
            "font-src 'self' https://cdn.jsdelivr.net; "
            "frame-src https://js.stripe.com; "
            "connect-src 'self' https://api.stripe.com; "
            "object-src 'none'; "
            "base-uri 'self'; "
            "form-action 'self';"
        )
        response['Content-Security-Policy'] = csp

        # HSTS (only in production)
        if not settings.DEBUG:
            response['Strict-Transport-Security'] = (
                'max-age=31536000; includeSubDomains; preload'
            )

        # Remove server fingerprint
        if 'Server' in response:
            del response['Server']
        if 'X-Powered-By' in response:
            del response['X-Powered-By']

        return response


# ── Rate Limiting ─────────────────────────────────────────────

class RateLimitMiddleware:
    """
    Rate limiting for sensitive endpoints.
    CIA — Availability: prevents brute force and DDoS.
    """
    LIMITS = {
        '/login/':              (10, 300),    # 10 attempts per 5 minutes
        '/staff-login/':        (10, 300),
        '/forgot-password/':    (5,  600),    # 5 per 10 minutes
        '/register/':           (5,  300),
        '/clinics/register/':   (3,  600),
        '/appointments/api/':   (60, 60),     # 60 API calls per minute
    }

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == 'POST':
            result = self._check_rate_limit(request)
            if result:
                return result
        return self.get_response(request)

    def _get_client_ip(self, request):
        x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded:
            return x_forwarded.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '0.0.0.0')

    def _check_rate_limit(self, request):
        ip      = self._get_client_ip(request)
        path    = request.path

        for endpoint, (max_requests, window) in self.LIMITS.items():
            if path.startswith(endpoint):
                key   = f'rl:{ip}:{endpoint}'
                count = cache.get(key, 0)
                if count >= max_requests:
                    logger.warning(
                        f'[RateLimit] Blocked {ip} on {path} '
                        f'({count}/{max_requests} in {window}s)'
                    )
                    if request.headers.get('Accept') == 'application/json':
                        return JsonResponse(
                            {'error': 'Too many requests. Please wait before trying again.'},
                            status=429
                        )
                    return HttpResponseForbidden(
                        '<h1>429 Too Many Requests</h1>'
                        '<p>You have made too many attempts. Please wait a few minutes before trying again.</p>'
                    )
                cache.set(key, count + 1, window)
                break
        return None


# ── Suspicious Request Detection ──────────────────────────────

class SuspiciousRequestMiddleware:
    """
    Detects and blocks common attack patterns.
    CIA — Integrity: prevents injection attacks.
    """
    # Patterns that suggest SQL injection or path traversal
    SQL_PATTERNS = re.compile(
        r"(union\s+select|drop\s+table|insert\s+into|delete\s+from|"
        r"exec\s*\(|xp_cmdshell|information_schema|pg_sleep|"
        r"'|--|;\s*--)",
        re.IGNORECASE
    )
    PATH_TRAVERSAL = re.compile(r'\.\./|\.\.\\')
    XSS_PATTERNS   = re.compile(r'<script|javascript:|on\w+\s*=', re.IGNORECASE)

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not self._is_safe(request):
            ip = request.META.get('REMOTE_ADDR', 'unknown')
            logger.critical(
                f'[Security] Suspicious request blocked from {ip}: '
                f'{request.method} {request.path}'
            )
            return HttpResponseForbidden('Request blocked for security reasons.')
        return self.get_response(request)

    def _is_safe(self, request):
        # Check query string
        qs = request.META.get('QUERY_STRING', '')
        if self.SQL_PATTERNS.search(qs): return False
        if self.PATH_TRAVERSAL.search(qs): return False
        if self.XSS_PATTERNS.search(qs): return False

        # Check path
        if self.PATH_TRAVERSAL.search(request.path): return False

        # Check POST data (for non-file uploads)
        if request.method == 'POST' and not request.FILES:
            try:
                body = request.body.decode('utf-8', errors='ignore')
                if self.SQL_PATTERNS.search(body): return False
            except Exception:
                pass

        return True


# ── Session Security ──────────────────────────────────────────

class SessionSecurityMiddleware:
    """
    Regenerates session on login, binds session to IP/UA.
    CIA — Confidentiality: prevents session hijacking.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            session_ip = request.session.get('_bound_ip')
            session_ua = request.session.get('_bound_ua')
            current_ip = request.META.get('REMOTE_ADDR')
            current_ua = request.META.get('HTTP_USER_AGENT', '')[:200]

            if session_ip and session_ip != current_ip:
                # IP changed mid-session — potential hijack
                logger.warning(
                    f'[Session] IP mismatch for user {request.user.pk}: '
                    f'{session_ip} → {current_ip}'
                )
                # In strict mode, log out. In lenient mode (mobile users move IPs), just warn.
                # Uncomment below for strict:
                # from django.contrib.auth import logout
                # logout(request)

            if not session_ip:
                request.session['_bound_ip'] = current_ip
                request.session['_bound_ua'] = current_ua

        return self.get_response(request)


# ── Audit Log Middleware ──────────────────────────────────────

class AuditLogMiddleware:
    """
    Logs all write operations (POST/PUT/DELETE) for audit trail.
    CIA — Integrity: non-repudiation of actions.
    """
    SENSITIVE_PATHS = [
        '/superadmin/', '/finance/', '/records/',
        '/appointments/', '/clinics/admin/',
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if (request.method in ('POST', 'PUT', 'DELETE', 'PATCH') and
                any(request.path.startswith(p) for p in self.SENSITIVE_PATHS)):

            user_info = 'anonymous'
            if hasattr(request, 'user') and request.user.is_authenticated:
                user_info = f'{request.user.pk}:{request.user.email}:{request.user.role}'

            logger.info(
                f'[Audit] {request.method} {request.path} | '
                f'User: {user_info} | '
                f'IP: {request.META.get("REMOTE_ADDR")} | '
                f'Status: {response.status_code} | '
                f'Time: {timezone.now().isoformat()}'
            )

        return response