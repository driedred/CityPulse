from httpx import AsyncClient


async def test_register_login_and_get_current_user(client: AsyncClient) -> None:
    register_response = await client.post(
        "/api/auth/register",
        json={
            "email": "citizen@example.com",
            "password": "SecurePass123!",
            "full_name": "Casey Citizen",
            "preferred_locale": "en",
        },
    )

    assert register_response.status_code == 201
    assert register_response.json()["role"] == "citizen"

    login_response = await client.post(
        "/api/auth/login",
        json={
            "email": "citizen@example.com",
            "password": "SecurePass123!",
        },
    )

    assert login_response.status_code == 200
    login_body = login_response.json()
    assert login_body["token_type"] == "bearer"
    assert login_body["user"]["email"] == "citizen@example.com"

    me_response = await client.get(
        "/api/users/me",
        headers={"Authorization": f"Bearer {login_body['access_token']}"},
    )

    assert me_response.status_code == 200
    assert me_response.json()["full_name"] == "Casey Citizen"
