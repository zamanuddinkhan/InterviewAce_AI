"""Single-worker request hardening, bounded throttling and aggregate monitoring."""
from collections import Counter, OrderedDict
import logging
import os
import time
from uuid import uuid4

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.gzip import GZipMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .config import COOKIE_SECURE, PUBLIC_ORIGIN, SESSION_COOKIE, TRUSTED_HOSTS

log = logging.getLogger('interviewace.requests')
if not log.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(name)s %(message)s'))
    log.addHandler(handler)
log.setLevel(logging.INFO)
log.propagate = False
started = time.time()
counts = Counter()
buckets = OrderedDict()


def throttle(key, limit=20, window=600):
    now = time.monotonic()
    attempts, expires = buckets.get(key, (0, now + window))
    if expires <= now:
        attempts, expires = 0, now + window
    buckets[key] = (attempts + 1, expires)
    buckets.move_to_end(key)
    while len(buckets) > 5000:
        buckets.popitem(last=False)
    return attempts < limit, max(1, int(expires - now))


def install(app):
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=TRUSTED_HOSTS)

    @app.exception_handler(RequestValidationError)
    async def invalid(request, exc):
        # Never echo passwords, confirmation fields, contact numbers or raw bodies.
        return JSONResponse(status_code=422, content={'detail': [
            {'loc': list(e['loc']), 'msg': e['msg'], 'type': e['type']} for e in exc.errors()]})

    @app.exception_handler(SQLAlchemyError)
    async def database_failure(request, exc):
        log.error('database_request_failure type=%s request_id=%s', type(exc).__name__, getattr(request.state, 'request_id', 'unknown'))
        return JSONResponse(status_code=503, content={'detail':'Database temporarily unavailable. Please try again.'})

    @app.middleware('http')
    async def harden(request: Request, call_next):
        request.state.request_id = uuid4().hex
        start = time.perf_counter()
        response = None
        unsafe = request.method not in ('GET', 'HEAD', 'OPTIONS')
        origin = request.headers.get('origin')
        expected = PUBLIC_ORIGIN or str(request.base_url).rstrip('/')
        auth_paths = ('/api/login', '/api/register', '/api/password-reset')
        if unsafe and origin and origin != expected:
            response = JSONResponse(status_code=403, content={'detail':'Cross-origin requests are not allowed.'})
        elif unsafe and request.cookies.get(SESSION_COOKIE) and not request.headers.get('authorization') and request.url.path not in auth_paths and request.headers.get('x-requested-with') != 'InterviewAce':
            response = JSONResponse(status_code=403, content={'detail':'Missing request protection header. Refresh the page and try again.'})
        elif request.headers.get('content-length', '').isdigit() and int(request.headers['content-length']) > 20 * 1024 * 1024:
            response = JSONResponse(status_code=413, content={'detail':'Request exceeds the 20 MB limit.'})
        elif request.url.path in auth_paths and unsafe and os.getenv('INTERVIEWACE_TESTING') != '1':
            allowed, retry = throttle((request.client.host if request.client else 'unknown', request.url.path))
            if not allowed:
                response = JSONResponse(status_code=429, content={'detail':'Too many attempts. Please wait before trying again.'}, headers={'Retry-After': str(retry)})
        elif unsafe and request.url.path.rsplit('/', 1)[-1] in ('rag', 'execute', 'communication', 'transcribe', 'start', 'answer', 'documents', 'resumes') and os.getenv('INTERVIEWACE_TESTING') != '1':
            allowed, retry = throttle((request.client.host if request.client else 'unknown', 'processing'), limit=30, window=60)
            if not allowed:
                response = JSONResponse(status_code=429, content={'detail':'Processing limit reached. Please wait a moment.'}, headers={'Retry-After':str(retry)})
        if response is None:
            try:
                response = await call_next(request)
            except Exception as exc:
                log.error('request_failure type=%s request_id=%s', type(exc).__name__, request.state.request_id)
                response = JSONResponse(status_code=500, content={'detail':'Something went wrong. Please try again or share the request ID with support.'})
        counts[str(response.status_code)] += 1
        elapsed = round((time.perf_counter() - start) * 1000, 1)
        response.headers.update({
            'X-Request-ID': request.state.request_id,
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'Referrer-Policy': 'same-origin',
            'Permissions-Policy': 'camera=(self), microphone=(self), geolocation=()',
            'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self' ws: wss:; media-src 'self' blob:; object-src 'none'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'",
            'Cache-Control': 'no-store' if request.url.path.startswith('/api') else ('no-cache' if request.url.path == '/' else 'public, max-age=300, must-revalidate'),
            'Server-Timing': f'app;dur={elapsed}',
        })
        if COOKIE_SECURE:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000'
        route = getattr(request.scope.get('route'), 'path', 'unmatched')
        log.info('method=%s route=%s status=%s duration_ms=%s request_id=%s', request.method, route, response.status_code, elapsed, request.state.request_id)
        return response
