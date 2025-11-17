import pytest
from fastapi import HTTPException

from backend.app.utils import auth_utils


def test_get_current_user_or_bypass_returns_bypass_user(monkeypatch):
    monkeypatch.setenv("BYPASS_AUTH", "true")

    user = auth_utils.get_current_user_or_bypass()

    assert user["username"] == "test_admin"
    assert user["role"].name == "ADMIN"


def test_get_current_user_or_bypass_calls_real_get_current_user(monkeypatch):
    monkeypatch.setenv("BYPASS_AUTH", "false")
    sentinel_user = {"username": "real_user"}
    monkeypatch.setattr(auth_utils, "get_current_user", lambda: sentinel_user)

    user = auth_utils.get_current_user_or_bypass()

    assert user is sentinel_user


@pytest.mark.asyncio
async def test_require_permission_or_bypass_allows_with_permission(monkeypatch):
    monkeypatch.setenv("BYPASS_AUTH", "false")
    checker = auth_utils.require_permission_or_bypass("employee:read")

    result = await checker(current_user={"permissions": ["employee:read"]})

    assert result["permissions"] == ["employee:read"]


@pytest.mark.asyncio
async def test_require_permission_or_bypass_raises_on_missing_permission(monkeypatch):
    monkeypatch.setenv("BYPASS_AUTH", "false")
    checker = auth_utils.require_permission_or_bypass("employee:delete")

    with pytest.raises(HTTPException) as exc:
        await checker(current_user={"permissions": ["employee:read"]})

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_require_permission_or_bypass_bypasses_when_env_true(monkeypatch):
    monkeypatch.setenv("BYPASS_AUTH", "true")
    checker = auth_utils.require_permission_or_bypass("any:permission")
    sentinel = {"permissions": []}

    result = await checker(current_user=sentinel)

    assert result is sentinel


def test_get_current_user_or_bypass_returns_bypass_after_exception(monkeypatch):
    monkeypatch.setenv("BYPASS_AUTH", "false")

    def boom():
        monkeypatch.setenv("BYPASS_AUTH", "true")
        raise RuntimeError("auth failure")

    monkeypatch.setattr(auth_utils, "get_current_user", boom)

    user = auth_utils.get_current_user_or_bypass()

    assert user["username"] == "test_admin"


def test_get_current_user_or_bypass_raises_when_not_bypassed(monkeypatch):
    monkeypatch.setenv("BYPASS_AUTH", "false")

    def boom():
        raise RuntimeError("auth failure")

    monkeypatch.setattr(auth_utils, "get_current_user", boom)

    with pytest.raises(RuntimeError):
        auth_utils.get_current_user_or_bypass()


@pytest.mark.asyncio
async def test_require_permission_handles_async_user(monkeypatch):
    monkeypatch.setenv("BYPASS_AUTH", "false")
    checker = auth_utils.require_permission_or_bypass("system:admin")

    class AsyncUser:
        async def get_permissions(self):
            return ["system:admin"]

    async def async_user():
        return AsyncUser()

    result = await checker(current_user=async_user())

    assert isinstance(result, AsyncUser)


@pytest.mark.asyncio
async def test_require_permission_reads_attribute_permissions(monkeypatch):
    monkeypatch.setenv("BYPASS_AUTH", "false")
    checker = auth_utils.require_permission_or_bypass("employee:read")

    class UserObject:
        def __init__(self):
            self.permissions = ["employee:read"]

    result = await checker(current_user=UserObject())

    assert isinstance(result, UserObject)
