from httpx import AsyncClient


async def test_submit_issue_and_list_own_issues(
    client: AsyncClient,
    seeded_category_id: str,
) -> None:
    await client.post(
        "/api/auth/register",
        json={
            "email": "reporter@example.com",
            "password": "SecurePass123!",
            "full_name": "Riley Reporter",
            "preferred_locale": "en",
        },
    )

    login_response = await client.post(
        "/api/auth/login",
        json={
            "email": "reporter@example.com",
            "password": "SecurePass123!",
        },
    )
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    create_response = await client.post(
        "/api/issues",
        headers=headers,
        json={
            "title": "Broken streetlight on Main",
            "short_description": "The streetlight near 5th and Main has been out for two nights.",
            "category_id": seeded_category_id,
            "latitude": 43.2389,
            "longitude": 76.8897,
            "source_locale": "en",
        },
    )

    assert create_response.status_code == 201
    issue_body = create_response.json()
    assert issue_body["status"] == "pending_moderation"
    assert issue_body["moderation_state"] == "queued"
    assert issue_body["category"]["slug"] == "roads"

    list_response = await client.get("/api/issues/me", headers=headers)

    assert list_response.status_code == 200
    issues = list_response.json()
    assert len(issues) == 1
    assert issues[0]["title"] == "Broken streetlight on Main"
