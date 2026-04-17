"""Tests for listing flags — isolation, filtering, pagination."""

from app.middleware.request_context import RequestContextManager
from app.services.flag.flag_model import Cohort, FlagCreateRequest


def _simple_cohorts() -> list[Cohort]:
    return [
        Cohort(id="", name="control", percentage=50.0, value=False),
        Cohort(id="", name="treatment", percentage=50.0, value=True),
    ]


def _request(key: str, status: str = "active") -> FlagCreateRequest:
    return FlagCreateRequest(
        flag_key=key,
        name=key,
        default_value=False,
        cohorts=_simple_cohorts(),
        status=status,
    )


async def test_list_empty_returns_zero(service):
    response = await service.list_flags()
    assert response.total == 0
    assert response.flags == []


async def test_list_returns_only_current_client(service):
    RequestContextManager.set_client_id("client-a")
    await service.create_flag(_request("flag_a1"))
    await service.create_flag(_request("flag_a2"))
    RequestContextManager.set_client_id("client-b")
    await service.create_flag(_request("flag_b1"))
    RequestContextManager.set_client_id("client-a")
    response = await service.list_flags()
    keys = {flag.flag_key for flag in response.flags}
    assert keys == {"flag_a1", "flag_a2"}
    assert response.total == 2


async def test_list_filter_by_status(service):
    await service.create_flag(_request("f1", status="active"))
    await service.create_flag(_request("f2", status="draft"))
    await service.create_flag(_request("f3", status="draft"))
    active = await service.list_flags(status="active")
    draft = await service.list_flags(status="draft")
    assert active.total == 1
    assert draft.total == 2
    assert {flag.flag_key for flag in draft.flags} == {"f2", "f3"}


async def test_list_pagination(service):
    for i in range(5):
        await service.create_flag(_request(f"flag_{i}"))
    page1 = await service.list_flags(limit=2, skip=0)
    page2 = await service.list_flags(limit=2, skip=2)
    page3 = await service.list_flags(limit=2, skip=4)
    assert len(page1.flags) == 2
    assert len(page2.flags) == 2
    assert len(page3.flags) == 1
    assert page1.total == page2.total == page3.total == 5
    seen = [flag.flag_key for flag in (*page1.flags, *page2.flags, *page3.flags)]
    assert len(set(seen)) == 5


async def test_get_flag_cross_client_isolation(service):
    RequestContextManager.set_client_id("client-a")
    flag_a = await service.create_flag(_request("only_a"))
    RequestContextManager.set_client_id("client-b")
    import pytest

    from app.common.errors import FlagNotFound

    with pytest.raises(FlagNotFound):
        await service.get_flag(flag_a.id)


async def test_list_via_http_isolation(http_client):
    headers_a = {"X-User-Id": "user-1", "X-Client-Id": "client-a"}
    headers_b = {"X-User-Id": "user-2", "X-Client-Id": "client-b"}
    body = _request("http_flag").model_dump()
    await http_client.post("/api/flags", json=body, headers=headers_a)
    response_b = await http_client.get("/api/flags", headers=headers_b)
    assert response_b.status_code == 200
    assert response_b.json()["total"] == 0
    response_a = await http_client.get("/api/flags", headers=headers_a)
    assert response_a.status_code == 200
    assert response_a.json()["total"] == 1
