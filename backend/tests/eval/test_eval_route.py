"""HTTP tests for POST /v1/evaluate/{flag_key}."""

import pytest
from fastapi import FastAPI, Header, HTTPException, status
from httpx import ASGITransport, AsyncClient

from app.services.auth.dependencies import get_current_client
from app.services.eval.eval_route import router


async def _fake_get_current_client(
    x_client_api_key: str = Header(default="", alias="X-Client-API-Key"),
) -> str:
    if not x_client_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing api key")
    return x_client_api_key


@pytest.fixture
def test_app(mock_flag_repo, fake_redis):  # noqa: ARG001 - fixtures ensure dependencies
    app = FastAPI()
    app.include_router(router, prefix="/v1")
    app.dependency_overrides[get_current_client] = _fake_get_current_client
    return app


@pytest.fixture
async def http_client(test_app):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.mark.asyncio
async def test_evaluate_returns_200_for_active_flag(http_client, mock_flag_repo, sample_flag):
    mock_flag_repo.return_value = sample_flag
    resp = await http_client.post(
        "/v1/evaluate/new_checkout",
        json={"user_id": "u1"},
        headers={"X-Client-API-Key": "client-1"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["reason"] == "computed"
    assert payload["cohort_id"] in {"c1", "c2"}


@pytest.mark.asyncio
async def test_evaluate_returns_401_without_api_key(http_client):
    resp = await http_client.post("/v1/evaluate/new_checkout", json={})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_evaluate_returns_404_when_flag_missing(http_client, mock_flag_repo):
    mock_flag_repo.return_value = None
    resp = await http_client.post(
        "/v1/evaluate/deleted_flag",
        json={},
        headers={"X-Client-API-Key": "client-1"},
    )
    assert resp.status_code == 404
    body = resp.json()
    assert body["detail"]["reason"] == "not_found"
    assert body["detail"]["value"] is None


@pytest.mark.asyncio
async def test_evaluate_cache_hit_second_call(http_client, mock_flag_repo, sample_flag):
    mock_flag_repo.return_value = sample_flag
    headers = {"X-Client-API-Key": "client-1"}
    body = {"user_id": "cache-me"}
    first = await http_client.post("/v1/evaluate/new_checkout", json=body, headers=headers)
    assert first.status_code == 200
    assert first.json()["reason"] == "computed"
    second = await http_client.post("/v1/evaluate/new_checkout", json=body, headers=headers)
    assert second.status_code == 200
    assert second.json()["reason"] == "cached"
