from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.api import admin
from backend.app.database import get_db
from backend.app.api.auth import get_current_active_user
from backend.app.models import Employee, WageType


@pytest.fixture
def admin_app(test_db):
    app = FastAPI()
    app.include_router(admin.router, prefix="/api/v1/admin")

    def override_get_db():
        db = test_db.SessionLocal()
        try:
            yield db
        finally:
            db.close()

    def fake_user():
        return SimpleNamespace(id=1, role="admin")

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_active_user] = fake_user
    return app


@pytest.fixture
def admin_client(admin_app, test_db):
    db = test_db.SessionLocal()
    employee = Employee(
        employee_code="ADMIN01",
        name="Admin Tester",
        wage_type=WageType.MONTHLY,
        monthly_salary=300000,
        is_active=True,
    )
    db.add(employee)
    db.commit()
    db.close()
    return TestClient(admin_app)


def test_admin_health_endpoint(admin_client):
    response = admin_client.get("/api/v1/admin/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_admin_get_employees_returns_list(admin_client):
    response = admin_client.get("/api/v1/admin/employees?limit=10")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] >= 1
    assert payload["data"][0]["employee_code"] == "ADMIN01"
