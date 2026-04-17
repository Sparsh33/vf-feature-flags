"""Tests for creating flags."""

import pytest

from app.common.errors import FlagAlreadyExists, InvalidCohortSum, ValidationError
from app.services.flag.flag_model import Cohort, FlagCreateRequest


async def test_create_flag_returns_model(service, create_request):
    flag = await service.create_flag(create_request)
    assert flag.id is not None
    assert flag.client_id == "client-a"
    assert flag.flag_key == "new_feature"
    assert flag.status == "active"
    assert flag.is_deleted is False
    assert len(flag.cohorts) == 2
    for cohort in flag.cohorts:
        assert cohort.id and cohort.id != ""


async def test_create_flag_cohort_sum_mismatch_raises(service):
    request = FlagCreateRequest(
        flag_key="bad_sum",
        name="Bad Sum",
        default_value=False,
        cohorts=[
            Cohort(id="", name="a", percentage=30.0, value=False),
            Cohort(id="", name="b", percentage=60.0, value=True),
        ],
    )
    with pytest.raises(InvalidCohortSum):
        await service.create_flag(request)


async def test_create_flag_empty_cohorts_raises(service):
    request = FlagCreateRequest(
        flag_key="no_cohorts",
        name="No Cohorts",
        default_value=False,
        cohorts=[],
    )
    with pytest.raises(InvalidCohortSum):
        await service.create_flag(request)


async def test_create_flag_duplicate_flag_key_raises(service, create_request):
    await service.create_flag(create_request)
    with pytest.raises(FlagAlreadyExists):
        await service.create_flag(create_request)


async def test_create_flag_invalid_flag_key_regex_raises(service, cohorts_50_50):
    request = FlagCreateRequest(
        flag_key="BadKey!",
        name="Bad Key",
        default_value=False,
        cohorts=cohorts_50_50,
    )
    with pytest.raises(ValidationError):
        await service.create_flag(request)


async def test_create_flag_duplicate_cohort_name_raises(service):
    request = FlagCreateRequest(
        flag_key="dup_cohort",
        name="Dup Cohort",
        default_value=False,
        cohorts=[
            Cohort(id="", name="control", percentage=50.0, value=False),
            Cohort(id="", name="control", percentage=50.0, value=True),
        ],
    )
    with pytest.raises(ValidationError):
        await service.create_flag(request)


async def test_create_flag_invalid_status_raises(service, cohorts_50_50):
    request = FlagCreateRequest(
        flag_key="bad_status",
        name="Bad Status",
        default_value=False,
        cohorts=cohorts_50_50,
        status="unknown",
    )
    with pytest.raises(ValidationError):
        await service.create_flag(request)


async def test_create_flag_via_http_returns_201(http_client, create_request):
    response = await http_client.post(
        "/api/flags",
        json=create_request.model_dump(),
        headers={"X-User-Id": "user-1", "X-Client-Id": "client-a"},
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["flag_key"] == "new_feature"
    assert payload["id"]


async def test_create_flag_via_http_duplicate_returns_409(http_client, create_request):
    headers = {"X-User-Id": "user-1", "X-Client-Id": "client-a"}
    body = create_request.model_dump()
    first = await http_client.post("/api/flags", json=body, headers=headers)
    assert first.status_code == 201
    second = await http_client.post("/api/flags", json=body, headers=headers)
    assert second.status_code == 409


async def test_create_flag_assigns_uuids_when_cohorts_have_none_id(service):
    """Cohort.id is Optional[str] = None. When the NL path (or any caller)
    omits ids, FlagService.create_flag must assign server-side UUIDs so the
    eval bucketing hash ring stays stable.
    """
    request = FlagCreateRequest(
        flag_key="id_less_create",
        name="ID-less create",
        default_value=False,
        cohorts=[
            Cohort(name="control", percentage=50.0, value=False),  # id=None
            Cohort(name="treatment", percentage=50.0, value=True),  # id=None
        ],
        status="active",
    )
    assert all(cohort.id is None for cohort in request.cohorts)
    flag = await service.create_flag(request)
    assert len(flag.cohorts) == 2
    ids = {cohort.id for cohort in flag.cohorts}
    assert None not in ids
    assert all(isinstance(cid, str) and cid for cid in ids)
    assert len(ids) == 2  # unique ids per cohort


async def test_create_flag_via_http_bad_sum_returns_422(http_client):
    body = {
        "flag_key": "bad_http",
        "name": "Bad HTTP",
        "default_value": False,
        "cohorts": [
            {"id": "", "name": "a", "percentage": 25.0, "value": False},
            {"id": "", "name": "b", "percentage": 50.0, "value": True},
        ],
        "status": "active",
    }
    response = await http_client.post(
        "/api/flags",
        json=body,
        headers={"X-User-Id": "user-1", "X-Client-Id": "client-a"},
    )
    assert response.status_code == 422
