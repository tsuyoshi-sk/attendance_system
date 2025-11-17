from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from starlette.testclient import TestClient

from backend.app.middleware.security import add_security_middleware


def _create_app(settings):
    app = FastAPI()
    add_security_middleware(app, settings)

    @app.get("/ping")
    async def ping():
        return JSONResponse({"status": "ok"})

    return app


def test_security_headers_added_in_development():
    settings = SimpleNamespace(
        CORS_ORIGINS=["https://example.com"],
        CORS_CREDENTIALS=True,
        ENVIRONMENT="development",
        SECURITY_HEADERS_ENABLED=True,
    )
    app = _create_app(settings)

    response = TestClient(app).get("/ping")

    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["X-XSS-Protection"] == "1; mode=block"
    assert "Strict-Transport-Security" not in response.headers
    assert "X-Request-ID" in response.headers


def test_security_headers_include_hsts_in_production():
    settings = SimpleNamespace(
        CORS_ORIGINS=["https://example.com"],
        CORS_CREDENTIALS=True,
        ENVIRONMENT="production",
        SECURITY_HEADERS_ENABLED=True,
    )
    app = _create_app(settings)

    response = TestClient(app).get("/ping", headers={"host": "localhost"})

    assert response.status_code == 200
    assert response.headers["Strict-Transport-Security"].startswith("max-age=")
    assert response.headers["Content-Security-Policy"].startswith("default-src 'self'")
