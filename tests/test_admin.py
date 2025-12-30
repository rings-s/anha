from tests.conftest import create_user, get_service_by_name


def _login(client, email: str, password: str):
    response = client.post(
        "/login",
        data={"email": email, "password": password},
        follow_redirects=False,
    )
    assert response.status_code == 303
    return response.cookies


def test_admin_requires_role(client):
    create_user("client3@example.com", "pass1234")
    cookies = _login(client, "client3@example.com", "pass1234")

    response = client.get("/admin", cookies=cookies, follow_redirects=False)
    assert response.status_code == 403


def test_admin_can_create_service_with_price(client):
    create_user("admin2@example.com", "pass1234", role="admin")
    cookies = _login(client, "admin2@example.com", "pass1234")

    response = client.post(
        "/admin/services/create",
        data={
            "name_ar": "خدمة جديدة",
            "name_en": "New Service",
            "description": "Service description",
            "price": "200.25",
        },
        cookies=cookies,
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/admin"

    service = get_service_by_name("خدمة جديدة")
    assert service is not None
    assert service.price == 200.25
