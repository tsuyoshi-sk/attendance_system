from datetime import datetime, timedelta

import pytest

from sqlalchemy.exc import IntegrityError

from backend.app.models import Employee, User, UserRole, WageType
from backend.app.schemas.auth import PasswordChange
from backend.app.services.auth_service import AuthService


@pytest.fixture
def auth_session(test_db):
    session = test_db.SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _add_user(session, username="svc_user", password="Secret1!"):
    service = AuthService(session)
    password_hash = service.get_password_hash(password)
    user = User(
        username=username,
        password_hash=password_hash,
        role=UserRole.ADMIN,
        is_active=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def test_authenticate_user_success(auth_session):
    service = AuthService(auth_session)
    user = _add_user(auth_session)

    assert service.authenticate_user("svc_user", "Secret1!").id == user.id


def test_authenticate_user_failure_wrong_password(auth_session):
    service = AuthService(auth_session)
    _add_user(auth_session)

    assert service.authenticate_user("svc_user", "wrong") is None


def test_create_user_duplicate_raises(auth_session):
    service = AuthService(auth_session)
    service.create_user("dup_user", "DupPass1!")
    with pytest.raises(ValueError):
        service.create_user("dup_user", "Another1!")


def test_change_password(auth_session):
    service = AuthService(auth_session)
    user = service.create_user("change_srv", "Oldpass1!")
    payload = PasswordChange(
        current_password="Oldpass1!",
        new_password="Newpass1!",
        confirm_password="Newpass1!",
    )

    assert service.change_password(user.id, payload)
    assert service.authenticate_user("change_srv", "Newpass1!")


def test_create_user_with_employee_association(auth_session):
    service = AuthService(auth_session)
    employee = Employee(
        employee_code="EMP200",
        name="Employee 200",
        wage_type=WageType.MONTHLY,
        monthly_salary=300000,
    )
    auth_session.add(employee)
    auth_session.commit()

    user = service.create_user(
        username="emp200",
        password="Password1!",
        role=UserRole.EMPLOYEE,
        employee_id=employee.id,
    )

    assert user.employee_id == employee.id


def test_create_user_validates_employee_presence(auth_session):
    service = AuthService(auth_session)
    with pytest.raises(ValueError):
        service.create_user(
            username="missing_emp",
            password="Password1!",
            employee_id=999,
        )


def test_create_user_rejects_duplicate_employee_account(auth_session):
    service = AuthService(auth_session)
    employee = Employee(
        employee_code="EMP300",
        name="Employee 300",
        wage_type=WageType.MONTHLY,
        monthly_salary=320000,
    )
    auth_session.add(employee)
    auth_session.commit()

    service.create_user("emp300", "Password1!", employee_id=employee.id)

    with pytest.raises(ValueError):
        service.create_user("emp300b", "Password1!", employee_id=employee.id)


def test_create_user_handles_integrity_error(auth_session, monkeypatch):
    service = AuthService(auth_session)

    def fail_commit():
        raise IntegrityError("stmt", {}, Exception("boom"))

    monkeypatch.setattr(auth_session, "commit", fail_commit)

    with pytest.raises(ValueError):
        service.create_user("integrity_user", "Password1!")


def test_change_password_user_not_found(auth_session):
    service = AuthService(auth_session)
    payload = PasswordChange(
        current_password="Password1!",
        new_password="Newpass1!",
        confirm_password="Newpass1!",
    )

    with pytest.raises(ValueError):
        service.change_password(user_id=12345, password_data=payload)


def test_change_password_rejects_wrong_current(auth_session):
    service = AuthService(auth_session)
    user = service.create_user("wrong_current", "Password1!")
    payload = PasswordChange(
        current_password="Wrongpass1!",
        new_password="Newpass1!",
        confirm_password="Newpass1!",
    )

    with pytest.raises(ValueError):
        service.change_password(user_id=user.id, password_data=payload)


def test_token_round_trip_and_current_user(auth_session):
    service = AuthService(auth_session)
    user = service.create_user("token_user", "Password1!", role=UserRole.ADMIN)

    token = service.create_access_token(user)
    payload = service.verify_token(token)
    assert payload is not None
    assert payload.username == "token_user"

    current = service.get_current_user(token)
    assert current.id == user.id


def test_verify_token_returns_none_on_invalid(auth_session):
    service = AuthService(auth_session)
    assert service.verify_token("invalid.token.value") is None


def test_create_initial_admin_skips_when_exists(auth_session):
    service = AuthService(auth_session)
    service.create_user("admin", "Password1!", role=UserRole.ADMIN)

    assert service.create_initial_admin() is None


def test_create_initial_admin_creates_admin(auth_session):
    service = AuthService(auth_session)

    admin = service.create_initial_admin()

    assert admin is not None
    assert admin.username == "admin"
