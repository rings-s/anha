from tests.conftest import create_user, get_user_by_email


def test_register_forces_client_role(client):
    response = client.post(
        "/register",
        data={
            "email": "client1@example.com",
            "password": "pass1234",
            "full_name": "Client One",
            "phone": "0500000000",
            "role": "admin",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/dashboard"

    user = get_user_by_email("client1@example.com")
    assert user is not None
    assert user.role.value == "client"


def test_login_invalid_password(client):
    create_user("client2@example.com", "pass1234")
    response = client.post(
        "/login",
        data={"email": "client2@example.com", "password": "wrongpass"},
        follow_redirects=False,
    )
    assert response.status_code == 401


def test_admin_login_redirects_to_admin(client):
    create_user("admin1@example.com", "pass1234", role="admin")
    response = client.post(
        "/login",
        data={"email": "admin1@example.com", "password": "pass1234"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/admin"
