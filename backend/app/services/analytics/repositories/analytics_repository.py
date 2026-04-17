"""MongoDB repository for the `analytics_events` collection."""

from datetime import datetime, timezone
from typing import Any, Dict, List

from pymongo import ASCENDING, DESCENDING

from app.database.base_repository import BaseRepository
from app.database.config import mongodb
from app.database.indexes import register_index_builder
from app.services.analytics.analytics_model import AnalyticsEvent

# TTL: do NOT add TTL for MVP — analytics retention is a product decision.
# Can be added later via `{expireAfterSeconds: N}` on `ts` index.

INTERVAL_MINUTE = "minute"
INTERVAL_HOUR = "hour"
INTERVAL_DAY = "day"
VALID_INTERVALS = frozenset({INTERVAL_MINUTE, INTERVAL_HOUR, INTERVAL_DAY})

_INTERVAL_FORMATS = {
    INTERVAL_MINUTE: "%Y-%m-%dT%H:%M:00Z",
    INTERVAL_HOUR: "%Y-%m-%dT%H:00:00Z",
    INTERVAL_DAY: "%Y-%m-%dT00:00:00Z",
}


class AnalyticsRepository(BaseRepository):
    COLLECTION_NAME = "analytics_events"

    async def insert(self, event: AnalyticsEvent) -> None:
        collection = await self._get_collection()
        document = event.model_dump(exclude={"id"})
        await collection.insert_one(document)

    async def get_latest_flag_key(self, client_id: str, flag_id: str) -> str:
        collection = await self._get_collection()
        document = await collection.find_one(
            {"client_id": client_id, "flag_id": flag_id},
            sort=[("ts", -1)],
        )
        if document is None:
            return ""
        return document.get("flag_key", "")

    async def aggregate_by_cohort(
        self,
        client_id: str,
        flag_id: str,
        from_ts: datetime,
        to_ts: datetime,
    ) -> List[Dict[str, Any]]:
        collection = await self._get_collection()
        pipeline = [
            {
                "$match": {
                    "client_id": client_id,
                    "flag_id": flag_id,
                    "ts": {"$gte": from_ts, "$lte": to_ts},
                }
            },
            {
                "$group": {
                    "_id": {
                        "cohort_id": "$cohort_id",
                        "cohort_name": "$cohort_name",
                    },
                    "count": {"$sum": 1},
                }
            },
            {"$sort": {"count": -1}},
        ]
        cursor = collection.aggregate(pipeline)
        results: List[Dict[str, Any]] = []
        async for document in cursor:
            results.append(
                {
                    "cohort_id": document["_id"].get("cohort_id"),
                    "cohort_name": document["_id"].get("cohort_name"),
                    "count": document["count"],
                }
            )
        return results

    async def time_series(
        self,
        client_id: str,
        flag_id: str,
        from_ts: datetime,
        to_ts: datetime,
        interval: str,
    ) -> List[Dict[str, Any]]:
        if interval not in VALID_INTERVALS:
            raise ValueError(f"invalid interval: {interval}")
        collection = await self._get_collection()
        date_format = _INTERVAL_FORMATS[interval]
        pipeline = [
            {
                "$match": {
                    "client_id": client_id,
                    "flag_id": flag_id,
                    "ts": {"$gte": from_ts, "$lte": to_ts},
                }
            },
            {
                "$group": {
                    "_id": {
                        "bucket": {
                            "$dateToString": {"date": "$ts", "format": date_format},
                        },
                        "cohort_name": "$cohort_name",
                        "cohort_id": "$cohort_id",
                    },
                    "count": {"$sum": 1},
                }
            },
            {"$sort": {"_id.bucket": 1}},
        ]
        cursor = collection.aggregate(pipeline)
        buckets: Dict[datetime, Dict[str, int]] = {}
        async for document in cursor:
            bucket_ts = datetime.strptime(document["_id"]["bucket"], "%Y-%m-%dT%H:%M:%SZ").replace(
                tzinfo=timezone.utc
            )
            cohort_key = self._resolve_cohort_key(
                document["_id"].get("cohort_id"),
                document["_id"].get("cohort_name"),
            )
            bucket = buckets.setdefault(bucket_ts, {})
            bucket[cohort_key] = bucket.get(cohort_key, 0) + document["count"]
        ordered = sorted(buckets.items(), key=lambda item: item[0])
        return [{"ts": ts, "counts_by_cohort": counts} for ts, counts in ordered]

    def _resolve_cohort_key(self, cohort_id: Any, cohort_name: Any) -> str:
        if cohort_name:
            return str(cohort_name)
        if cohort_id is None:
            return "__not_found__"
        return "__fallback__"


async def ensure_analytics_indexes() -> None:
    collection = mongodb.get_database()["analytics_events"]
    await collection.create_index(
        [("client_id", ASCENDING), ("flag_id", ASCENDING), ("ts", DESCENDING)],
        name="client_flag_ts",
    )
    await collection.create_index(
        [("client_id", ASCENDING), ("ts", DESCENDING)],
        name="client_ts",
    )


register_index_builder(ensure_analytics_indexes)

__all__ = ["AnalyticsRepository", "ensure_analytics_indexes", "VALID_INTERVALS"]
