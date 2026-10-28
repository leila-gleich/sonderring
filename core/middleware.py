from django.conf import settings


class SecurityHeadersMiddleware:
    """
    Applies defense-in-depth HTTP security headers to all responses:
    - Content-Security-Policy (CSP) mitigating XSS and framing attacks
    - Referrer-Policy preventing sensitive URL leakage in Referer headers
    - Permissions-Policy restricting browser sensor/device APIs
    - X-Content-Type-Options preventing MIME-sniffing
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if 'Content-Security-Policy' not in response:
            csp_directives = [
                "default-src 'self'",
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
                "font-src 'self' https://fonts.gstatic.com data:",
                "img-src 'self' data: https: http:",
                "script-src 'self' 'unsafe-inline'",
                "connect-src 'self'",
                "frame-ancestors 'none'",
                "base-uri 'self'",
                "form-action 'self'",
            ]
            response['Content-Security-Policy'] = "; ".join(csp_directives)

        if 'Referrer-Policy' not in response:
            response['Referrer-Policy'] = getattr(
                settings, 'SECURE_REFERRER_POLICY', 'strict-origin-when-cross-origin'
            )

        if 'Permissions-Policy' not in response:
            response['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'

        if 'X-Content-Type-Options' not in response:
            response['X-Content-Type-Options'] = 'nosniff'

        return response
