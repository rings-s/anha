def test_home_page(client):
    response = client.get("/")
    assert response.status_code == 200


def test_login_register_pages(client):
    assert client.get("/login").status_code == 200
    assert client.get("/register").status_code == 200


def test_booking_requires_login(client):
    response = client.get("/book", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"
