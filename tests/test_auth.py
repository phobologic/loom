"""Tests for dev auth routes and get_current_user dependency."""

from httpx import AsyncClient

from loom.main import _DEV_USERS


class TestDevLoginPage:
    async def test_returns_200(self, client: AsyncClient) -> None:
        response = await client.get("/dev/login")
        assert response.status_code == 200

    async def test_lists_seeded_users(self, client: AsyncClient) -> None:
        response = await client.get("/dev/login")
        for name in _DEV_USERS:
            assert name in response.text


class TestDevLogin:
    async def test_redirects_to_games(self, client: AsyncClient) -> None:
        # First get the login page to find a user id
        response = await client.get("/dev/login")
        assert response.status_code == 200

        # Parse out the first user_id from the form (simplest: just try id=1)
        post = await client.post("/dev/login", data={"user_id": "1"}, follow_redirects=False)
        assert post.status_code == 303
        assert post.headers["location"] == "/games"

    async def test_sets_session_cookie(self, client: AsyncClient) -> None:
        await client.post("/dev/login", data={"user_id": "1"}, follow_redirects=False)
        # Session cookie should now be set
        assert "session" in client.cookies


class TestDevLogout:
    async def test_clears_session_and_redirects(self, client: AsyncClient) -> None:
        await client.post("/dev/login", data={"user_id": "1"}, follow_redirects=False)
        logout = await client.post("/dev/logout", follow_redirects=False)
        assert logout.status_code == 303
        assert logout.headers["location"] == "/dev/login"


class TestGamesPage:
    async def test_requires_auth(self, client: AsyncClient) -> None:
        response = await client.get("/games", follow_redirects=False)
        assert response.status_code == 302
        assert "/login" in response.headers["location"]

    async def test_shows_username_when_authenticated(self, client: AsyncClient) -> None:
        await client.post("/dev/login", data={"user_id": "1"}, follow_redirects=False)
        response = await client.get("/games")
        assert response.status_code == 200
        # One of the dev user names should appear
        assert any(name in response.text for name in _DEV_USERS)
