async def test_hello_world(async_client):
    resp = await async_client.get("/")
    assert resp.status_code == 200
    assert "Loom" in resp.text
    assert "Hello, world!" in resp.text
