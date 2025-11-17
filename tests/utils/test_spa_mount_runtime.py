from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app import spa_mount_runtime


def test_apply_spa_mount_skips_when_static_missing(monkeypatch):
    fake_root = Path("/tmp/nonexistent_spa_dir")
    monkeypatch.setattr(spa_mount_runtime, "__file__", str(fake_root / "spa_mount_runtime.py"))
    app = FastAPI()

    spa_mount_runtime.apply_spa_mount(app)

    asset_routes = [route.path for route in app.routes if getattr(route, "path", "").startswith("/assets")]
    assert asset_routes == []


def test_apply_spa_mount_serves_assets_and_index(tmp_path, monkeypatch):
    fake_root = tmp_path / "spa_runtime"
    static_dir = fake_root / "static"
    assets_dir = static_dir / "assets"
    assets_dir.mkdir(parents=True)
    (static_dir / "index.html").write_text("<html>SPA</html>", encoding="utf-8")
    (assets_dir / "app.js").write_text("console.log('hi');", encoding="utf-8")
    (static_dir / "robots.txt").write_text("robots", encoding="utf-8")
    monkeypatch.setattr(spa_mount_runtime, "__file__", str(fake_root / "spa_mount_runtime.py"))

    app = FastAPI()
    @app.get("/api/data")
    async def api_data():
        return {"ok": True}

    spa_mount_runtime.apply_spa_mount(app)
    client = TestClient(app)

    asset_resp = client.get("/assets/app.js")
    assert asset_resp.status_code == 200
    assert "console.log" in asset_resp.text

    fallback_resp = client.get("/dashboard")
    assert fallback_resp.status_code == 200
    assert "SPA" in fallback_resp.text

    static_resp = client.get("/robots.txt")
    assert static_resp.status_code == 200
    assert static_resp.text == "robots"

    api_resp = client.get("/api/data")
    assert api_resp.json() == {"ok": True}


def test_spa_fallback_skips_health_paths(tmp_path, monkeypatch):
    fake_root = tmp_path / "spa_runtime"
    static_dir = fake_root / "static"
    assets_dir = static_dir / "assets"
    assets_dir.mkdir(parents=True)
    (static_dir / "index.html").write_text("index", encoding="utf-8")
    monkeypatch.setattr(spa_mount_runtime, "__file__", str(fake_root / "spa_mount_runtime.py"))

    app = FastAPI()
    spa_mount_runtime.apply_spa_mount(app)
    client = TestClient(app)

    response = client.get("/health/status")
    assert response.status_code == 200
    assert response.text == "null"


def test_spa_mount_returns_error_when_index_missing(tmp_path, monkeypatch):
    fake_root = tmp_path / "spa_runtime"
    static_dir = fake_root / "static"
    assets_dir = static_dir / "assets"
    assets_dir.mkdir(parents=True)
    monkeypatch.setattr(spa_mount_runtime, "__file__", str(fake_root / "spa_mount_runtime.py"))

    app = FastAPI()
    spa_mount_runtime.apply_spa_mount(app)
    client = TestClient(app)

    response = client.get("/any")
    assert response.status_code == 200
    assert response.json() == {"error": "SPA not found"}
