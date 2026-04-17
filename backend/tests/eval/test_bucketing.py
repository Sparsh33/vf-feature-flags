"""Unit tests for bucketing primitives."""

import random
from typing import List

from app.services.eval.bucketing import (
    BUCKET_RESOLUTION,
    Cohort,
    canonical_json,
    compute_bucket,
    pick_cohort,
)


def _make_cohorts(entries: List[tuple]) -> List[Cohort]:
    return [Cohort(id=cid, name=cid, percentage=pct, value=val) for cid, pct, val in entries]


def test_canonical_json_is_sorted_and_compact():
    data = {"b": 2, "a": 1, "nested": {"z": 9, "y": 8}}
    result = canonical_json(data)
    assert result == '{"a":1,"b":2,"nested":{"y":8,"z":9}}'


def test_canonical_json_key_order_does_not_matter():
    assert canonical_json({"a": 1, "b": 2}) == canonical_json({"b": 2, "a": 1})


def test_compute_bucket_is_deterministic():
    params = {"user_id": "42", "region": "us"}
    b1 = compute_bucket("client-1", "flag-x", params)
    b2 = compute_bucket("client-1", "flag-x", params)
    assert b1 == b2
    assert 0 <= b1 < BUCKET_RESOLUTION


def test_compute_bucket_differs_across_clients():
    params = {"user_id": "42"}
    assert compute_bucket("client-1", "flag-x", params) != compute_bucket(
        "client-2", "flag-x", params
    )


def test_pick_cohort_empty_returns_none():
    assert pick_cohort(0, []) is None
    assert pick_cohort(5000, []) is None


def test_pick_cohort_single_100pct_always_wins():
    cohorts = _make_cohorts([("only", 100.0, "v")])
    for bucket in (0, 1234, 9999):
        picked = pick_cohort(bucket, cohorts)
        assert picked is not None
        assert picked.id == "only"


def test_pick_cohort_50_50_split():
    cohorts = _make_cohorts([("a", 50.0, "va"), ("b", 50.0, "vb")])
    assert pick_cohort(0, cohorts).id == "a"
    assert pick_cohort(4999, cohorts).id == "a"
    assert pick_cohort(5000, cohorts).id == "b"
    assert pick_cohort(9999, cohorts).id == "b"


def test_pick_cohort_33_33_34_split():
    cohorts = _make_cohorts([("a", 33.0, 1), ("b", 33.0, 2), ("c", 34.0, 3)])
    assert pick_cohort(0, cohorts).id == "a"
    assert pick_cohort(3299, cohorts).id == "a"
    assert pick_cohort(3300, cohorts).id == "b"
    assert pick_cohort(6599, cohorts).id == "b"
    assert pick_cohort(6600, cohorts).id == "c"
    assert pick_cohort(9999, cohorts).id == "c"


def test_pick_cohort_sum_below_100_last_catches_all():
    cohorts = _make_cohorts([("a", 40.0, 1), ("b", 40.0, 2)])
    # bucket beyond 8000 should fall into last cohort defensively
    assert pick_cohort(9500, cohorts).id == "b"


def test_distribution_smoke_50_50():
    cohorts = _make_cohorts([("a", 50.0, 1), ("b", 50.0, 2)])
    rng = random.Random(1234)
    counts = {"a": 0, "b": 0}
    for _ in range(1000):
        params = {"user": rng.randint(0, 10**9)}
        bucket = compute_bucket("client-1", "flag-x", params)
        winner = pick_cohort(bucket, cohorts)
        counts[winner.id] += 1
    assert 400 <= counts["a"] <= 600
    assert 400 <= counts["b"] <= 600
