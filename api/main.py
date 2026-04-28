import os
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Query
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DB = os.getenv("MONGODB_DB", "urban_explorer")
MONGODB_COLLECTION = os.getenv("MONGODB_COLLECTION", "scores")

client = MongoClient(MONGODB_URI)
db = client[MONGODB_DB]
collection = db[MONGODB_COLLECTION]

app = FastAPI(
    title="API Mobilité",
    version="1.0.0",
    description="API pour récupérer les données géographiques, scores et indicateurs depuis MongoDB"
)


def serialize_doc(doc: dict) -> dict:
    """Convertit _id MongoDB en string."""
    if not doc:
        return doc
    doc["_id"] = str(doc["_id"])
    return doc


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/levels")
def get_levels() -> dict[str, list[str]]:
    levels = collection.distinct("level")
    return {"levels": sorted(levels)}


@app.get("/fields")
def get_fields(level: Optional[str] = None) -> dict[str, list[str]]:
    query = {}
    if level:
        query["level"] = level

    doc = collection.find_one(query)
    if not doc:
        return {"fields": []}

    properties = doc.get("properties", {})
    return {"fields": sorted(properties.keys())}


@app.get("/areas")
def get_areas(
    level: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=1000),
    skip: int = Query(default=0, ge=0),
    include_geometry: bool = Query(default=False)
) -> list[dict[str, Any]]:
    query: dict[str, Any] = {}
    if level:
        query["level"] = level

    projection = {
        "area_id": 1,
        "area_name": 1,
        "level": 1,
        "properties": 1
    }

    if include_geometry:
        projection["geometry"] = 1

    cursor = (
        collection.find(query, projection)
        .sort([("level", 1), ("area_id", 1)])
        .skip(skip)
        .limit(limit)
    )

    return [serialize_doc(doc) for doc in cursor]


@app.get("/areas/{level}/{area_id}")
def get_area(
    level: str,
    area_id: str,
    include_geometry: bool = Query(default=True)
) -> dict[str, Any]:
    projection = {
        "area_id": 1,
        "area_name": 1,
        "level": 1,
        "properties": 1
    }

    if include_geometry:
        projection["geometry"] = 1

    doc = collection.find_one(
        {"level": level, "area_id": area_id},
        projection
    )

    if not doc:
        # essai aussi en int si besoin
        try:
            area_id_int = int(area_id)
            doc = collection.find_one(
                {"level": level, "area_id": area_id_int},
                projection
            )
        except ValueError:
            pass

    if not doc:
        raise HTTPException(status_code=404, detail="Zone introuvable")

    return serialize_doc(doc)


@app.get("/areas/{level}/{area_id}/properties")
def get_area_properties(level: str, area_id: str) -> dict[str, Any]:
    doc = collection.find_one(
        {"level": level, "area_id": area_id},
        {"area_id": 1, "area_name": 1, "level": 1, "properties": 1}
    )

    if not doc:
        try:
            area_id_int = int(area_id)
            doc = collection.find_one(
                {"level": level, "area_id": area_id_int},
                {"area_id": 1, "area_name": 1, "level": 1, "properties": 1}
            )
        except ValueError:
            pass

    if not doc:
        raise HTTPException(status_code=404, detail="Zone introuvable")

    return serialize_doc(doc)


@app.get("/indicators/{field_name}")
def get_indicator(
    field_name: str,
    level: Optional[str] = None,
    min_value: Optional[float] = None,
    max_value: Optional[float] = None,
    limit: int = Query(default=100, ge=1, le=1000),
    skip: int = Query(default=0, ge=0),
    include_geometry: bool = Query(default=False)
) -> list[dict[str, Any]]:
    mongo_field = f"properties.{field_name}"

    query: dict[str, Any] = {
        mongo_field: {"$exists": True}
    }

    if level:
        query["level"] = level

    if min_value is not None or max_value is not None:
        query[mongo_field] = {}
        if min_value is not None:
            query[mongo_field]["$gte"] = min_value
        if max_value is not None:
            query[mongo_field]["$lte"] = max_value

    projection = {
        "area_id": 1,
        "area_name": 1,
        "level": 1,
        mongo_field: 1
    }

    if include_geometry:
        projection["geometry"] = 1

    cursor = (
        collection.find(query, projection)
        .sort(mongo_field, -1)
        .skip(skip)
        .limit(limit)
    )

    return [serialize_doc(doc) for doc in cursor]


@app.get("/indicators/{field_name}/ranking")
def get_indicator_ranking(
    field_name: str,
    level: Optional[str] = None,
    top: int = Query(default=10, ge=1, le=200)
) -> list[dict[str, Any]]:
    mongo_field = f"properties.{field_name}"

    query: dict[str, Any] = {
        mongo_field: {"$exists": True}
    }

    if level:
        query["level"] = level

    cursor = (
        collection.find(
            query,
            {
                "area_id": 1,
                "area_name": 1,
                "level": 1,
                mongo_field: 1
            }
        )
        .sort(mongo_field, -1)
        .limit(top)
    )

    return [serialize_doc(doc) for doc in cursor]


@app.get("/search/by-name")
def search_by_name(
    q: str,
    level: Optional[str] = None,
    limit: int = Query(default=20, ge=1, le=100)
) -> list[dict[str, Any]]:
    query: dict[str, Any] = {
        "area_name": {"$regex": q, "$options": "i"}
    }

    if level:
        query["level"] = level

    cursor = (
        collection.find(
            query,
            {
                "area_id": 1,
                "area_name": 1,
                "level": 1,
                "properties": 1
            }
        )
        .limit(limit)
    )

    return [serialize_doc(doc) for doc in cursor]