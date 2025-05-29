"""
メインアプリケーションのユニットテスト
"""

import pytest
from fastapi.testclient import TestClient

from attendance_system.app.main import app


@pytest.mark.unit
def test_root_endpoint():
    """ルートエンドポイントのテスト"""
    client = TestClient(app)
    response = client.get("/")

    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "version" in data
    assert "status" in data
    assert data["status"] == "running"


@pytest.mark.unit
def test_health_endpoint():
    """ヘルスチェックエンドポイントのテスト"""
    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "name" in data
    assert "version" in data
    assert data["status"] == "healthy"


@pytest.mark.unit
def test_info_endpoint():
    """システム情報エンドポイントのテスト"""
    client = TestClient(app)
    response = client.get("/info")

    assert response.status_code == 200
    data = response.json()
    assert "app" in data
    assert "features" in data
    assert "name" in data["app"]
    assert "version" in data["app"]
