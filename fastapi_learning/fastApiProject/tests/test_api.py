"""FastAPI 项目核心接口自动化测试。"""

import os
from datetime import datetime

os.environ["DATABASE_URL"] = "sqlite:///./tests/test_fastapi.db"
os.environ["SECRET_KEY"] = "test-secret-key-with-at-least-32-bytes"
os.environ["JWT_ALGORITHM"] = "HS256"

import pytest
from fastapi.testclient import TestClient

from app.database import Base, engine
from app.dependencies import get_current_user
from app.models import User
from main import app


@pytest.fixture()
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as test_client:
        yield test_client


def register_user(client, username: str, password: str = "secret123"):
    return client.post(
        "/users/register",
        json={
            "username": username,
            "password": password,
            "age": 20,
            "email": f"{username}@example.com",
        },
    )


def login(client, username: str, password: str = "secret123"):
    return client.post(
        "/auth/login",
        data={"username": username, "password": password},
    )


def auth_header(response):
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello World"}


def test_register_login_me(client):
    register = register_user(client, "alice")
    assert register.status_code == 201
    assert "password" not in register.json()

    login_response = login(client, "alice")
    assert login_response.status_code == 200
    assert login_response.json()["token_type"] == "bearer"

    me_response = client.get(
        "/users/me",
        headers=auth_header(login_response),
    )
    assert me_response.status_code == 200
    assert me_response.json()["username"] == "alice"


def test_login_wrong_password(client):
    register_user(client, "bob")
    response = login(client, "bob", password="wrong-password")
    assert response.status_code == 401


def test_me_without_token(client):
    assert client.get("/users/me").status_code == 401


def test_create_item_requires_auth(client):
    response = client.post("/items", json={"name": "book", "price": 9.9})
    assert response.status_code == 401


def test_create_item_uses_current_user(client):
    register_user(client, "carol")
    login_response = login(client, "carol")
    headers = auth_header(login_response)

    response = client.post(
        "/items",
        json={"name": "Python Book", "price": 59.9},
        headers=headers,
    )
    assert response.status_code == 201
    me_response = client.get("/users/me", headers=headers)
    assert response.json()["user_id"] == me_response.json()["id"]


def test_update_and_delete_item_owner_only(client):
    register_user(client, "owner")
    register_user(client, "intruder")
    owner_headers = auth_header(login(client, "owner"))
    intruder_headers = auth_header(login(client, "intruder"))

    create_response = client.post(
        "/items",
        json={"name": "Secret Item", "price": 19.9},
        headers=owner_headers,
    )
    assert create_response.status_code == 201
    item_id = create_response.json()["id"]

    intruder_update = client.put(
        f"/items/{item_id}",
        json={"price": 1.0},
        headers=intruder_headers,
    )
    assert intruder_update.status_code == 403

    owner_update = client.put(
        f"/items/{item_id}",
        json={"price": 29.9},
        headers=owner_headers,
    )
    assert owner_update.status_code == 200
    assert owner_update.json()["price"] == 29.9

    intruder_delete = client.delete(f"/items/{item_id}", headers=intruder_headers)
    assert intruder_delete.status_code == 403

    owner_delete = client.delete(f"/items/{item_id}", headers=owner_headers)
    assert owner_delete.status_code == 204
    assert client.get(f"/items/{item_id}").status_code == 404


def test_http_error_format(client):
    response = client.get("/users/99999")
    assert response.status_code == 404
    assert response.json()["code"] == "HTTP_ERROR"
    assert "message" in response.json()


def test_validation_error_format(client):
    response = client.get("/users/not-an-int")
    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert body["message"] == "参数校验失败"
    assert isinstance(body["detail"], list)


def test_request_id_header(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID")


def test_dependency_override(client):
    def fake_current_user():
        return User(
            id=999,
            username="fake_user",
            password="hashed",
            age=1,
            email=None,
            created_at=datetime.now(),
        )

    app.dependency_overrides[get_current_user] = fake_current_user
    try:
        response = client.get("/users/me")
        assert response.status_code == 200
        assert response.json()["username"] == "fake_user"
    finally:
        app.dependency_overrides.clear()
