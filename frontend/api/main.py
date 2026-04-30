import os
import re
import unicodedata
from typing import Any, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DB = os.getenv("MONGODB_DB", "urban_explorer")
MONGODB_COLLECTION = os.getenv("MONGODB_COLLECTION", "scores")

if not MONGODB_URI:
    raise RuntimeError("MONGODB_URI est manquant dans le fichier .env")

client = MongoClient(MONGODB_URI)
db = client[MONGODB_DB]
collection = db[MONGODB_COLLECTION]

app = FastAPI(
    title="Urban Data Explorer API",
    version="1.0.0",
    description="API pour récupérer les données géographiques, scores et indicateurs depuis MongoDB Atlas",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://[::1]:5500",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PROFILE_FIELDS = {
    "profil_ideal": 1,
    "score_senior": 1,
    "score_actifs": 1,
    "score_jeune_adulte": 1,
    "score_junior": 1,
}


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
    extra_fields = [field for field in PROFILE_FIELDS if field in doc]
    return {"fields": sorted(set(properties.keys()) | set(extra_fields))}


@app.get("/areas")
def get_areas(
    level: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=1000),
    skip: int = Query(default=0, ge=0),
    include_geometry: bool = Query(default=False),
) -> list[dict[str, Any]]:
    query: dict[str, Any] = {}
    if level:
        query["level"] = level

    projection = {
        "area_id": 1,
        "area_name": 1,
        "level": 1,
        "year": 1,
        "properties": 1,
        **PROFILE_FIELDS,
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
    include_geometry: bool = Query(default=True),
) -> dict[str, Any]:
    projection = {
        "area_id": 1,
        "area_name": 1,
        "level": 1,
        "year": 1,
        "properties": 1,
        **PROFILE_FIELDS,
    }

    if include_geometry:
        projection["geometry"] = 1

    doc = collection.find_one(
        {"level": level, "area_id": area_id},
        projection,
    )

    if not doc:
        try:
            area_id_int = int(area_id)
            doc = collection.find_one(
                {"level": level, "area_id": area_id_int},
                projection,
            )
        except ValueError:
            pass

    if not doc:
        raise HTTPException(status_code=404, detail="Zone introuvable")

    return serialize_doc(doc)


@app.get("/areas/{level}/{area_id}/properties")
def get_area_properties(level: str, area_id: str) -> dict[str, Any]:
    projection = {
        "area_id": 1,
        "area_name": 1,
        "level": 1,
        "year": 1,
        "properties": 1,
        **PROFILE_FIELDS,
    }

    doc = collection.find_one(
        {"level": level, "area_id": area_id},
        projection,
    )

    if not doc:
        try:
            area_id_int = int(area_id)
            doc = collection.find_one(
                {"level": level, "area_id": area_id_int},
                projection,
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
    include_geometry: bool = Query(default=False),
) -> list[dict[str, Any]]:
    mongo_field = f"properties.{field_name}"

    query: dict[str, Any] = (
        {"$or": [{mongo_field: {"$exists": True}}, {field_name: {"$exists": True}}]}
        if field_name in PROFILE_FIELDS
        else {mongo_field: {"$exists": True}}
    )

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
        "year": 1,
        mongo_field: 1,
        field_name: 1,
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
    top: int = Query(default=10, ge=1, le=200),
) -> list[dict[str, Any]]:
    mongo_field = f"properties.{field_name}"
    sort_field = field_name if field_name in PROFILE_FIELDS else mongo_field

    query: dict[str, Any] = (
        {"$or": [{mongo_field: {"$exists": True}}, {field_name: {"$exists": True}}]}
        if field_name in PROFILE_FIELDS
        else {mongo_field: {"$exists": True}}
    )

    if level:
        query["level"] = level

    cursor = (
        collection.find(
            query,
            {
                "area_id": 1,
                "area_name": 1,
                "level": 1,
                "year": 1,
                mongo_field: 1,
                field_name: 1,
            },
        )
        .sort(sort_field, -1)
        .limit(top)
    )

    return [serialize_doc(doc) for doc in cursor]


@app.get("/search/by-name")
def search_by_name(
    q: str,
    level: Optional[str] = None,
    limit: int = Query(default=20, ge=1, le=100),
) -> list[dict[str, Any]]:
    normalized_q = normalize_search(q)
    arrondissement = parse_arrondissement(q)
    postal_code = f"750{arrondissement:02d}" if arrondissement else None
    commune_code = f"751{arrondissement:02d}" if arrondissement else None
    numeric_q = int(q) if str(q).strip().isdigit() else None

    query: dict[str, Any] = {
        "$or": [
            {"area_name": {"$regex": q, "$options": "i"}},
            {"area_id": {"$regex": q, "$options": "i"}},
            {"properties.code_commune": {"$regex": q, "$options": "i"}},
            {"properties.code_iris": {"$regex": q, "$options": "i"}},
            {"properties.nom_quartier": {"$regex": q, "$options": "i"}},
            {"properties.nom_iris": {"$regex": q, "$options": "i"}},
            {"properties.nom_commune": {"$regex": q, "$options": "i"}},
        ],
    }

    if level:
        query["level"] = level

    if arrondissement:
        query["$or"].extend(
            [
                {"properties.arrondissement": arrondissement},
                {"properties.arrondissement": str(arrondissement)},
                {"area_id": arrondissement},
                {"area_id": commune_code},
                {"properties.code_commune": commune_code},
                {"properties.code_postal": postal_code},
            ]
        )
    elif numeric_q is not None:
        query["$or"].append({"area_id": numeric_q})

    cursor = (
        collection.find(
            query,
            {
                "area_id": 1,
                "area_name": 1,
                "level": 1,
                "year": 1,
                "properties": 1,
                **PROFILE_FIELDS,
            },
        )
        .limit(limit)
    )

    docs = [serialize_doc(doc) for doc in cursor]
    if len(docs) >= limit:
        return docs

    seen = {(doc.get("level"), str(doc.get("area_id"))) for doc in docs}
    fallback_query = {"level": level} if level else {}
    fallback_cursor = collection.find(
        fallback_query,
        {
            "area_id": 1,
            "area_name": 1,
            "level": 1,
            "year": 1,
            "properties": 1,
            **PROFILE_FIELDS,
        },
    )

    for doc in fallback_cursor:
        key = (doc.get("level"), str(doc.get("area_id")))
        if key in seen:
            continue
        if document_matches_search(doc, normalized_q, arrondissement, postal_code, commune_code):
            docs.append(serialize_doc(doc))
            seen.add(key)
        if len(docs) >= limit:
            break

    return docs


def normalize_search(value: Any) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    text = re.sub(r"[^a-zA-Z0-9]+", " ", text)
    return text.lower().strip()


def parse_arrondissement(query: str) -> Optional[int]:
    normalized = normalize_search(query)
    postal = re.search(r"\b750([0-2][0-9])\b", normalized)
    if postal:
        value = int(postal.group(1))
        return value if 1 <= value <= 20 else None
    number = re.search(r"\b([1-9]|1[0-9]|20)\b", normalized)
    return int(number.group(1)) if number else None


def document_matches_search(
    doc: dict,
    normalized_q: str,
    arrondissement: Optional[int],
    postal_code: Optional[str],
    commune_code: Optional[str],
) -> bool:
    props = doc.get("properties", {})
    searchable_values = [
        doc.get("area_id"),
        doc.get("area_name"),
        props.get("code_commune"),
        props.get("code_iris"),
        props.get("code_postal"),
        props.get("nom_quartier"),
        props.get("nom_iris"),
        props.get("nom_commune"),
        props.get("arrondissement"),
        postal_code,
        commune_code,
    ]
    haystack = normalize_search(" ".join(str(value) for value in searchable_values if value is not None))
    if normalized_q and normalized_q in haystack:
        return True
    return arrondissement is not None and str(props.get("arrondissement")) == str(arrondissement)
