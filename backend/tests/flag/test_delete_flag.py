"""Tests for soft-deleting flags."""

import pytest

from app.common.errors import FlagNotFound


async def test_soft_delete_hides_from_get(service, create_request):
    created = await service.create_flag(create_request)
    await service.delete_flag(created.id)
    with pytest.raises(FlagNotFound):
        await service.get_flag(created.id)


async def test_soft_delete_hides_from_list(service, create_request):
    created = await service.create_flag(create_request)
    before = await service.list_flags()
    assert before.total == 1
    await service.delete_flag(created.id)
    after = await service.list_flags()
    assert after.total == 0
    assert after.flags == []


async def test_soft_delete_hides_from_get_by_key(service, create_request):
    created = await service.create_flag(create_request)
    await service.delete_flag(created.id)
    with pytest.raises(FlagNotFound):
        await service.get_flag_by_key(created.flag_key)


async def test_soft_delete_sets_is_deleted_true_on_document(service, create_request):
    from bson import ObjectId

    from app.services.flag.repositories.flag_repository import FlagRepository

    created = await service.create_flag(create_request)
    await service.delete_flag(created.id)
    repo = FlagRepository()
    collection = await repo._get_collection()
    raw = await collection.find_one({"_id": ObjectId(created.id)})
    assert raw is not None
    assert raw["is_deleted"] is True


async def test_delete_unknown_flag_raises(service):
    with pytest.raises(FlagNotFound):
        await service.delete_flag("507f1f77bcf86cd799439011")


async def test_delete_allows_reuse_of_flag_key(service, create_request):
    created = await service.create_flag(create_request)
    await service.delete_flag(created.id)
    recreated = await service.create_flag(create_request)
    assert recreated.id != created.id
    assert recreated.flag_key == created.flag_key


async def test_delete_via_http_returns_204(http_client, create_request):
    headers = {"X-User-Id": "user-1", "X-Client-Id": "client-a"}
    create_response = await http_client.post(
        "/api/flags", json=create_request.model_dump(), headers=headers
    )
    flag_id = create_response.json()["id"]
    delete_response = await http_client.delete(f"/api/flags/{flag_id}", headers=headers)
    assert delete_response.status_code == 204
    get_response = await http_client.get(f"/api/flags/{flag_id}", headers=headers)
    assert get_response.status_code == 404
