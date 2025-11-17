import pytest
from sqlalchemy.exc import IntegrityError

from backend.app.schemas.employee import EmployeeCreate, EmployeeUpdate
from backend.app.schemas.employee_card import CardCreate
from backend.app.services.employee_service import EmployeeService
from backend.app.models import EmployeeCard, User, UserRole, WageType


@pytest.fixture
def employee_db_session(test_db):
    session = test_db.SessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_create_employee_success(employee_db_session):
    service = EmployeeService(employee_db_session)
    payload = EmployeeCreate(
        employee_code="EMP01",
        name="Employee One",
        wage_type="monthly",
        monthly_salary=300000,
        hourly_rate=None,
        email="emp01@example.com",
    )

    employee = service.create_employee(payload)

    assert employee.employee_code == "EMP01"
    assert employee.monthly_salary == 300000


def test_create_employee_duplicate_code(employee_db_session):
    service = EmployeeService(employee_db_session)
    payload = EmployeeCreate(
        employee_code="EMP02",
        name="Employee Two",
        wage_type="monthly",
        monthly_salary=300000,
        hourly_rate=None,
        email="emp02@example.com",
    )
    service.create_employee(payload)

    with pytest.raises(ValueError):
        service.create_employee(payload)


def test_update_employee_success(employee_db_session):
    service = EmployeeService(employee_db_session)
    created = service.create_employee(
        EmployeeCreate(
            employee_code="EMP03",
            name="Employee Three",
            wage_type="monthly",
            monthly_salary=300000,
            hourly_rate=None,
            email="emp03@example.com",
        )
    )

    updated = service.update_employee(
        created.id,
        EmployeeUpdate(name="Employee 3 Updated", email="new_emp03@example.com"),
    )

    assert updated.name == "Employee 3 Updated"
    assert updated.email == "new_emp03@example.com"


def test_update_employee_not_found(employee_db_session):
    service = EmployeeService(employee_db_session)
    with pytest.raises(ValueError):
        service.update_employee(999, EmployeeUpdate(name="No One"))


def test_delete_employee_marks_inactive(employee_db_session):
    service = EmployeeService(employee_db_session)
    created = service.create_employee(
        EmployeeCreate(
            employee_code="EMP04",
            name="Employee Four",
            wage_type="monthly",
            monthly_salary=300000,
            hourly_rate=None,
            email="emp04@example.com",
        )
    )

    assert service.delete_employee(created.id) is True
    employee = service.get_employee(created.id)
    assert employee.is_active is False


def test_create_employee_duplicate_email(employee_db_session):
    service = EmployeeService(employee_db_session)
    service.create_employee(
        EmployeeCreate(
            employee_code="EMP05",
            name="Employee Five",
            wage_type="monthly",
            monthly_salary=310000,
            hourly_rate=None,
            email="dup@example.com",
        )
    )

    with pytest.raises(ValueError):
        service.create_employee(
            EmployeeCreate(
                employee_code="EMP05B",
                name="Employee Five B",
                wage_type="monthly",
                monthly_salary=320000,
                hourly_rate=None,
                email="dup@example.com",
            )
        )


def test_get_employees_filters_by_search(employee_db_session):
    service = EmployeeService(employee_db_session)
    service.create_employee(
        EmployeeCreate(
            employee_code="EMP06",
            name="Gamma Tester",
            wage_type="monthly",
            monthly_salary=330000,
            hourly_rate=None,
            email="gamma@example.com",
        )
    )
    service.create_employee(
        EmployeeCreate(
            employee_code="EMP07",
            name="Delta User",
            wage_type="monthly",
            monthly_salary=340000,
            hourly_rate=None,
            email="delta@example.com",
            is_active=False,
        )
    )

    filtered = service.get_employees(is_active=True, search="Gamma")

    assert len(filtered) == 1
    assert filtered[0].employee_code == "EMP06"


def test_delete_employee_not_found(employee_db_session):
    service = EmployeeService(employee_db_session)
    with pytest.raises(ValueError):
        service.delete_employee(9999)


def test_delete_employee_disables_cards_and_user(employee_db_session):
    service = EmployeeService(employee_db_session)
    employee = service.create_employee(
        EmployeeCreate(
            employee_code="EMP08",
            name="Employee Eight",
            wage_type="monthly",
            monthly_salary=350000,
            hourly_rate=None,
            email="emp08@example.com",
        )
    )
    card = service.add_employee_card(
        employee.id,
        CardCreate(card_idm_hash="a" * 64, card_nickname="primary"),
    )
    user = User(
        username="emp08user",
        password_hash="hash",
        role=UserRole.EMPLOYEE,
        employee_id=employee.id,
    )
    employee_db_session.add(user)
    employee_db_session.commit()

    service.delete_employee(employee.id)

    refreshed_employee = service.get_employee(employee.id)
    refreshed_card = employee_db_session.query(EmployeeCard).get(card.id)
    refreshed_user = employee_db_session.query(User).get(user.id)
    assert refreshed_employee.is_active is False
    assert refreshed_card.is_active is False
    assert refreshed_user.is_active is False


def test_add_employee_card_sets_primary_hash(employee_db_session):
    service = EmployeeService(employee_db_session)
    employee = service.create_employee(
        EmployeeCreate(
            employee_code="EMP09",
            name="Employee Nine",
            wage_type="monthly",
            monthly_salary=360000,
            hourly_rate=None,
            email="emp09@example.com",
        )
    )

    card = service.add_employee_card(
        employee.id,
        CardCreate(card_idm_hash="b" * 64, card_nickname="main"),
    )

    refreshed_employee = service.get_employee(employee.id)
    assert refreshed_employee.card_idm_hash == "b" * 64
    assert service.get_employee_cards(employee.id)[0].id == card.id


def test_add_employee_card_requires_employee(employee_db_session):
    service = EmployeeService(employee_db_session)
    with pytest.raises(ValueError):
        service.add_employee_card(
            9999,
            CardCreate(card_idm_hash="c" * 64, card_nickname="missing"),
        )


def test_delete_card_updates_primary_hash(employee_db_session):
    service = EmployeeService(employee_db_session)
    employee = service.create_employee(
        EmployeeCreate(
            employee_code="EMP10",
            name="Employee Ten",
            wage_type="monthly",
            monthly_salary=370000,
            hourly_rate=None,
            email="emp10@example.com",
        )
    )
    first = service.add_employee_card(
        employee.id, CardCreate(card_idm_hash="d" * 64, card_nickname="first")
    )
    second = service.add_employee_card(
        employee.id, CardCreate(card_idm_hash="e" * 64, card_nickname="second")
    )

    service.delete_card(first.id)

    refreshed_employee = service.get_employee(employee.id)
    assert refreshed_employee.card_idm_hash == "e" * 64
    cards = service.get_employee_cards(employee.id)
    assert len(cards) == 1
    assert cards[0].id == second.id


def test_delete_card_missing(employee_db_session):
    service = EmployeeService(employee_db_session)
    with pytest.raises(ValueError):
        service.delete_card(12345)


def test_create_employee_handles_integrity_error(employee_db_session, monkeypatch):
    service = EmployeeService(employee_db_session)

    def fail_commit():
        raise IntegrityError("stmt", {}, Exception("fail"))

    monkeypatch.setattr(employee_db_session, "commit", fail_commit)

    with pytest.raises(ValueError):
        service.create_employee(
            EmployeeCreate(
                employee_code="EMP11",
                name="Employee Eleven",
                wage_type="monthly",
                monthly_salary=380000,
                hourly_rate=None,
                email="emp11@example.com",
            )
        )


def test_get_employee_by_code(employee_db_session):
    service = EmployeeService(employee_db_session)
    service.create_employee(
        EmployeeCreate(
            employee_code="EMP12",
            name="Employee Twelve",
            wage_type="monthly",
            monthly_salary=390000,
            hourly_rate=None,
            email="emp12@example.com",
        )
    )

    found = service.get_employee_by_code("EMP12")
    assert found is not None
    assert found.email == "emp12@example.com"


def test_add_employee_card_rejects_duplicate_hash(employee_db_session):
    service = EmployeeService(employee_db_session)
    emp_a = service.create_employee(
        EmployeeCreate(
            employee_code="EMP13",
            name="Employee Thirteen",
            wage_type="monthly",
            monthly_salary=400000,
            hourly_rate=None,
            email="emp13@example.com",
        )
    )
    emp_b = service.create_employee(
        EmployeeCreate(
            employee_code="EMP14",
            name="Employee Fourteen",
            wage_type="monthly",
            monthly_salary=410000,
            hourly_rate=None,
            email="emp14@example.com",
        )
    )
    service.add_employee_card(emp_a.id, CardCreate(card_idm_hash="f" * 64))

    with pytest.raises(ValueError):
        service.add_employee_card(emp_b.id, CardCreate(card_idm_hash="f" * 64))


def test_delete_card_clears_hash_when_no_other_cards(employee_db_session):
    service = EmployeeService(employee_db_session)
    employee = service.create_employee(
        EmployeeCreate(
            employee_code="EMP15",
            name="Employee Fifteen",
            wage_type="monthly",
            monthly_salary=420000,
            hourly_rate=None,
            email="emp15@example.com",
        )
    )
    card = service.add_employee_card(employee.id, CardCreate(card_idm_hash="1" * 64))

    service.delete_card(card.id)

    refreshed_employee = service.get_employee(employee.id)
    assert refreshed_employee.card_idm_hash is None


def test_normalize_wage_type_variants(employee_db_session):
    service = EmployeeService(employee_db_session)

    assert service._normalize_wage_type(WageType.MONTHLY) == WageType.MONTHLY
    assert service._normalize_wage_type("") == WageType.MONTHLY
    with pytest.raises(ValueError):
        service._normalize_wage_type("invalid")


def test_validate_wage_data_errors(employee_db_session):
    service = EmployeeService(employee_db_session)

    with pytest.raises(ValueError):
        service._validate_wage_data(WageType.HOURLY, hourly_rate=None, monthly_salary=None)

    with pytest.raises(ValueError):
        service._validate_wage_data(WageType.MONTHLY, hourly_rate=None, monthly_salary=None)
