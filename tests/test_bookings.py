from tests.conftest import create_service, create_user, get_booking_by_contact, get_service_by_id


def _login(client, email: str, password: str):
    response = client.post(
        "/login",
        data={"email": email, "password": password},
        follow_redirects=False,
    )
    assert response.status_code == 303
    return response.cookies


def test_booking_requires_auth(client):
    response = client.get("/bookings", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_create_booking_uses_service_price(client):
    create_user("booker@example.com", "pass1234")
    cookies = _login(client, "booker@example.com", "pass1234")

    service_id = create_service("خدمة اختبار", 150.5)
    service = get_service_by_id(service_id)
    assert service is not None

    response = client.post(
        "/bookings",
        data={
            "service_id": service_id,
            "contact_name": "Test Booker",
            "contact_phone": "0501111111",
            "description": "Test booking",
            "address_text": "Test address",
        },
        cookies=cookies,
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/dashboard"

    booking = get_booking_by_contact("Test Booker")
    assert booking is not None
    assert booking.price == service.price
