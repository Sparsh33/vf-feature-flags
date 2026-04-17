"""Tests for updating flags."""

import pytest

from app.common.errors import FlagNotFound, InvalidCohortSum
from app.services.flag.flag_model import Cohort, FlagUpdateRequest


async def test_update_partial_name_and_description(service, create_request):
    created = await service.create_flag(create_request)
    update = FlagUpdateRequest(name="Renamed", description="New description")
    updated = await service.update_flag(created.id, update)
    assert updated.name == "Renamed"
    assert updated.description == "New description"
    assert updated.flag_key == created.flag_key
    assert len(updated.cohorts) == len(created.cohorts)


async def test_update_cohorts_preserves_ids_for_matching_names(service, create_request):
    created = await service.create_flag(create_request)
    original_ids = {cohort.name: cohort.id for cohort in created.cohorts}
    new_cohorts = [
        Cohort(id="", name="control", percentage=40.0, value=False),
        Cohort(id="", name="treatment", percentage=60.0, value=True),
    ]
    updated = await service.update_flag(created.id, FlagUpdateRequest(cohorts=new_cohorts))
    updated_ids = {cohort.name: cohort.id for cohort in updated.cohorts}
    assert updated_ids["control"] == original_ids["control"]
    assert updated_ids["treatment"] == original_ids["treatment"]
    percentages = {cohort.name: cohort.percentage for cohort in updated.cohorts}
    assert percentages == {"control": 40.0, "treatment": 60.0}


async def test_update_cohorts_new_name_gets_fresh_uuid(service, create_request):
    created = await service.create_flag(create_request)
    control_id = next(c.id for c in created.cohorts if c.name == "control")
    new_cohorts = [
        Cohort(id="", name="control", percentage=30.0, value=False),
        Cohort(id="", name="variant_a", percentage=35.0, value="a"),
        Cohort(id="", name="variant_b", percentage=35.0, value="b"),
    ]
    updated = await service.update_flag(created.id, FlagUpdateRequest(cohorts=new_cohorts))
    ids_by_name = {cohort.name: cohort.id for cohort in updated.cohorts}
    assert ids_by_name["control"] == control_id
    assert ids_by_name["variant_a"] != control_id
    assert ids_by_name["variant_b"] != ids_by_name["variant_a"]
    for name, new_id in ids_by_name.items():
        assert new_id and new_id != ""


async def test_update_cohort_sum_mismatch_raises(service, create_request):
    created = await service.create_flag(create_request)
    bad_cohorts = [
        Cohort(id="", name="control", percentage=10.0, value=False),
        Cohort(id="", name="treatment", percentage=10.0, value=True),
    ]
    with pytest.raises(InvalidCohortSum):
        await service.update_flag(created.id, FlagUpdateRequest(cohorts=bad_cohorts))


async def test_update_unknown_flag_id_raises(service):
    with pytest.raises(FlagNotFound):
        await service.update_flag("507f1f77bcf86cd799439011", FlagUpdateRequest(name="X"))


async def test_update_invalid_flag_id_format_raises(service):
    with pytest.raises(FlagNotFound):
        await service.update_flag("not-an-objectid", FlagUpdateRequest(name="X"))


async def test_update_status_only(service, create_request):
    created = await service.create_flag(create_request)
    updated = await service.update_flag(created.id, FlagUpdateRequest(status="draft"))
    assert updated.status == "draft"


async def test_update_no_changes_returns_existing(service, create_request):
    created = await service.create_flag(create_request)
    updated = await service.update_flag(created.id, FlagUpdateRequest())
    assert updated.id == created.id
    assert updated.name == created.name


async def test_update_with_idless_cohorts_gets_server_assigned_ids(service, create_request):
    """An update that sends cohorts without ids must have fresh UUIDs assigned
    for any new-name cohort — no cohort may ever be persisted with id=None,
    since the evaluator depends on stable cohort ids for bucketing.
    """
    created = await service.create_flag(create_request)
    control_id = next(c.id for c in created.cohorts if c.name == "control")
    new_cohorts = [
        Cohort(name="control", percentage=40.0, value=False),  # id=None, existing name
        Cohort(name="fresh_cohort", percentage=60.0, value=True),  # id=None, new name
    ]
    assert all(cohort.id is None for cohort in new_cohorts)
    updated = await service.update_flag(created.id, FlagUpdateRequest(cohorts=new_cohorts))
    ids_by_name = {cohort.name: cohort.id for cohort in updated.cohorts}
    assert ids_by_name["control"] == control_id  # existing name preserves id
    fresh_id = ids_by_name["fresh_cohort"]
    assert fresh_id and isinstance(fresh_id, str) and fresh_id != ""
    assert fresh_id != control_id


async def test_repo_refuses_insert_with_idless_cohort(monkeypatch, service):
    """Repo-layer defense: even if the service somehow skips _assign_new_cohort_ids,
    the repository must reject persistence of cohorts with null ids.
    """
    from app.services.flag.flag_model import Cohort as _Cohort, FlagConfig

    # Bypass the service's id-assign + validation so we can prove the repo guard
    # catches the raw case.
    repository = service._repository

    idless_flag = FlagConfig(
        client_id="client-a",
        flag_key="repo_guard_insert",
        name="Repo Guard",
        default_value=False,
        cohorts=[
            _Cohort(name="a", percentage=50.0, value=False),  # id=None
            _Cohort(name="b", percentage=50.0, value=True),
        ],
    )
    with pytest.raises(ValueError, match="missing an id"):
        await repository.insert(idless_flag)


async def test_repo_refuses_update_with_idless_cohort(service, create_request):
    """Same repo-layer guard applies to the update path when cohorts are
    replaced via raw repo.update (bypassing FlagService._reconcile_cohorts).
    """
    created = await service.create_flag(create_request)
    repository = service._repository
    with pytest.raises(ValueError, match="missing an id"):
        await repository.update(
            "client-a",
            created.id,
            {"cohorts": [{"name": "a", "percentage": 50.0, "value": False}]},  # no id
        )
