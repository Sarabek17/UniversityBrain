"""S2 tests: login for all 5 roles, wrong password, missing token, RBAC 403."""

import pytest

DEMO_PASSWORD = "demo123"

ROLE_LOGINS = [
    ("aliyev", "student"),
    ("tursunov", "teacher"),
    ("nazarova", "tutor"),
    ("rashidova", "staff"),
    ("admin", "admin"),
]


def login(client, username, password=DEMO_PASSWORD):
    return client.post(
        "/auth/login", json={"username": username, "password": password}
    )


def auth_headers(client, username):
    res = login(client, username)
    assert res.status_code == 200
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


@pytest.mark.parametrize("username,role", ROLE_LOGINS)
def test_login_and_me_all_roles(client, username, role):
    res = login(client, username)
    assert res.status_code == 200
    data = res.json()
    assert data["access_token"]
    assert data["token_type"] == "bearer"
    assert data["user"]["username"] == username
    assert data["user"]["role"] == role

    me = client.get(
        "/auth/me", headers={"Authorization": f"Bearer {data['access_token']}"}
    )
    assert me.status_code == 200
    assert me.json()["username"] == username
    assert me.json()["role"] == role


def test_login_wrong_password(client):
    res = login(client, "aliyev", "notogri-parol")
    assert res.status_code == 401


def test_login_unknown_user(client):
    res = login(client, "yoq-foydalanuvchi")
    assert res.status_code == 401


def test_protected_endpoint_without_token(client):
    assert client.get("/auth/me").status_code == 401
    assert client.get("/auth/test-staff-only").status_code == 401


def test_protected_endpoint_with_garbage_token(client):
    res = client.get("/auth/me", headers={"Authorization": "Bearer bunday-emas"})
    assert res.status_code == 401


def test_student_forbidden_on_staff_endpoint(client):
    headers = auth_headers(client, "aliyev")
    res = client.get("/auth/test-staff-only", headers=headers)
    assert res.status_code == 403


def test_staff_and_admin_allowed_on_staff_endpoint(client):
    for username in ("rashidova", "admin"):
        res = client.get("/auth/test-staff-only", headers=auth_headers(client, username))
        assert res.status_code == 200, username


def test_logout_returns_ok(client):
    res = client.post("/auth/logout", headers=auth_headers(client, "aliyev"))
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}
