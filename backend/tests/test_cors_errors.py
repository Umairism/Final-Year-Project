import asyncio
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from api.app import app, UnhandledExceptionMiddleware


def test_unhandled_error_and_not_found_have_cors():
    path = "/__test_3d32_cors_unhandled_error"

    async def crash():
        raise RuntimeError("PRIVATE_ERROR_SENTINEL")

    app.add_api_route(path, crash, methods=["GET"])
    route = app.router.routes[-1]
    try:
        client = TestClient(app, raise_server_exceptions=False)
        headers = {"Origin": "http://localhost:8080"}
        response = client.get(path, headers=headers)
        assert response.status_code == 500
        body = response.json()
        assert body["detail"] == "Internal server error"
        assert body["error"] == "internal_error"
        assert datetime.fromisoformat(body["timestamp"]).utcoffset() == timedelta(0)
        assert "RuntimeError" not in response.text
        assert "PRIVATE_ERROR_SENTINEL" not in response.text
        assert response.headers["access-control-allow-origin"] in (headers["Origin"], "*")

        response = client.get(path + "/missing", headers=headers)
        assert response.status_code == 404
        assert response.headers["access-control-allow-origin"] in (headers["Origin"], "*")
    finally:
        app.router.routes.remove(route)


def test_started_response_is_not_replaced():
    messages = []

    async def downstream(scope, receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": []})
        raise RuntimeError("after start")

    async def receive():
        return {"type": "http.disconnect"}

    async def send(message):
        messages.append(message)

    with pytest.raises(RuntimeError, match="after start"):
        asyncio.run(UnhandledExceptionMiddleware(downstream)({"type": "http"}, receive, send))
    assert len(messages) == 1
    assert messages[0]["status"] == 200


@pytest.mark.parametrize("scope_type", ["websocket", "lifespan"])
def test_non_http_errors_pass_through(scope_type):
    async def downstream(scope, receive, send):
        assert scope["type"] == scope_type
        raise RuntimeError("non-http")

    async def receive():
        raise AssertionError("receive should not be called")

    async def send(message):
        raise AssertionError("send should not be called")

    with pytest.raises(RuntimeError, match="non-http"):
        asyncio.run(UnhandledExceptionMiddleware(downstream)({"type": scope_type}, receive, send))
