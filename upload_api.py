import os
import uuid
import csv
import math
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from utils import (
    validate_coordinates,
    parse_lat_lng,
    calculate_distance,
)
import requests
import re


app = FastAPI(title="Upload API", version="1.0.0")

# Add CORS middleware to fix cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

logger = logging.getLogger("upload_api")
logging.basicConfig(level=logging.INFO)


DATA_DIR = Path(os.getenv("DATA_DIR", "data")).resolve()
CSV_PATH = DATA_DIR / "data.csv"
TXT_MIRROR_PATH = DATA_DIR / "businesses.txt"
BUSINESSES_DIR = DATA_DIR / "businesses"

# Pathway API configuration
PATHWAY_HOST = os.getenv("PATHWAY_HOST", "localhost")
PATHWAY_PORT = os.getenv("PATHWAY_PORT", "8000")
PATHWAY_URL = f"http://{PATHWAY_HOST}:{PATHWAY_PORT}"


class DataRecord(BaseModel):
    name: str = Field(..., description="Business owner name")
    business_name: str = Field(..., description="Business name")
    lat_long: str = Field(..., description="Latitude,longitude coordinates")
    business_category: str = Field(..., description="Business category")
    business_tags: str = Field(default="", description="Comma-separated business tags")


class BatchPayload(BaseModel):
    records: List[DataRecord]


class LocationSearchRequest(BaseModel):
    user_lat: float = Field(..., description="User's latitude", ge=-90, le=90)
    user_lng: float = Field(..., description="User's longitude", ge=-180, le=180)
    query: Optional[str] = Field(None, description="Search query (category, tags, or keywords)")
    max_distance_km: float = Field(10.0, description="Maximum search radius in kilometers", gt=0, le=25000)
    category_filter: Optional[str] = Field(None, description="Filter by business category")
    tag_filters: Optional[List[str]] = Field(None, description="Filter by business tags")
    limit: int = Field(20, description="Maximum number of results", gt=0, le=200)
    distance_weight: Optional[float] = Field(None, description="Weight of distance in final ranking (0..1). If None, auto-detected from query.")
    sort_mode: Optional[str] = Field(None, description="Optional sort override: 'hybrid' (default), 'distance', or 'relevance'")


def ensure_dirs_and_csv() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not CSV_PATH.exists():
        with CSV_PATH.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "name",
                    "business_name",
                    "lat_long",
                    "business_category",
                    "business_tags",
                ]
            )
    # Ensure mirror txt exists
    if not TXT_MIRROR_PATH.exists():
        with TXT_MIRROR_PATH.open("w", encoding="utf-8") as tf:
            tf.write(
                "name,business_name,lat,lon,business_category,business_tags\n"
            )
    BUSINESSES_DIR.mkdir(parents=True, exist_ok=True)


def append_rows(rows: List[DataRecord]) -> int:
    ensure_dirs_and_csv()
    with CSV_PATH.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for r in rows:
            writer.writerow(
                [
                    r.name,
                    r.business_name,
                    r.lat_long,
                    r.business_category,
                    r.business_tags,
                ]
            )
    # Also append to normalized TXT mirror to aid parsing during retrieval
    with TXT_MIRROR_PATH.open("a", encoding="utf-8") as tf:
        for r in rows:
            coords = parse_lat_lng(r.lat_long)
            if coords:
                lat, lon = coords
                tf.write(
                    f"{r.name},{r.business_name},{lat},{lon},{r.business_category},{r.business_tags}\n"
                )
    # Write per-business text files to guarantee one-vector-per-business chunks
    for r in rows:
        write_business_file(r)
    return len(rows)


def write_business_file(record: DataRecord) -> Path:
    """Create a single per-business .txt file (same logic as append-csv)."""
    coords = parse_lat_lng(record.lat_long)
    lat_str, lon_str = ("", "")
    if coords:
        lat_str, lon_str = coords
    safe_name = "_".join(
        [
            str(record.business_name).strip().replace("/", "-").replace(" ", "_")[:40],
            uuid.uuid4().hex[:8],
        ]
    )
    content_lines = [
        f"business_name: {record.business_name}",
        f"owner_name: {record.name}",
        f"business_category: {record.business_category}",
        f"business_tags: {record.business_tags}",
        f"latitude: {lat_str}",
        f"longitude: {lon_str}",
        f"lat_long: {record.lat_long}",
    ]
    out_path = BUSINESSES_DIR / f"{safe_name}.txt"
    out_path.write_text("\n".join(content_lines), encoding="utf-8")
    return out_path


def parse_business_from_text(text: str) -> List[Dict[str, Any]]:
    """Parse business data from vectorized document text.

    Supports both per-business key:value files and CSV-like rows.
    """
    businesses: List[Dict[str, Any]] = []

    raw = (text or "").strip()
    if not raw:
        return businesses

    # 1) Try key:value per-business format first
    if "business_name:" in raw and "business_category:" in raw:
        kv: Dict[str, str] = {}
        for line in raw.split("\n"):
            line = line.strip()
            if not line or ":" not in line:
                continue
            k, v = line.split(":", 1)
            kv[k.strip().lower().replace(" ", "_")] = v.strip()

        business_name = kv.get("business_name")
        name = kv.get("owner_name", "")
        category = kv.get("business_category")
        tags = kv.get("business_tags", "")
        lat_str = kv.get("latitude", "")
        lon_str = kv.get("longitude", "")
        lat_long = kv.get("lat_long", "")

        lat, lon = None, None
        if lat_str and lon_str:
            try:
                lat = float(lat_str)
                lon = float(lon_str)
            except ValueError:
                lat, lon = None, None
        if (lat is None or lon is None) and lat_long:
            coords = parse_lat_lng(lat_long)
            if coords:
                lat, lon = coords

        if business_name and category and lat is not None and lon is not None and validate_coordinates(lat, lon):
            businesses.append({
                "name": name,
                "business_name": business_name,
                "latitude": lat,
                "longitude": lon,
                "lat_long": f"{lat},{lon}",
                "business_category": category,
                "business_tags": tags,
            })
            return businesses

    # 2) Fallback: CSV-like rows
    for line in raw.split("\n"):
        line = line.strip()
        if not line:
            continue
        if "name,business_name,lat_long" in line.lower():
            continue
        parts = [p.strip().strip('"') for p in line.split(',')]
        if len(parts) >= 6:
            name = parts[0]
            business_name = parts[1]
            latitude = parts[2]
            longitude = parts[3]
            category = parts[4]
            tags = parts[5] if len(parts) > 5 else ""
            if not name or not business_name or not latitude or not longitude or not category:
                continue
            try:
                lat = float(latitude)
                lon = float(longitude)
                if not validate_coordinates(lat, lon):
                    continue
                businesses.append({
                    "name": name,
                    "business_name": business_name,
                    "latitude": lat,
                    "longitude": lon,
                    "lat_long": f"{lat},{lon}",
                    "business_category": category,
                    "business_tags": tags,
                })
            except (ValueError, TypeError):
                continue
        elif len(parts) >= 5:
            name = parts[0]
            business_name = parts[1]
            lat_long = parts[2]
            category = parts[3]
            tags = parts[4] if len(parts) > 4 else ""
            coords = parse_lat_lng(lat_long)
            if not (name and business_name and category and coords):
                continue
            lat, lon = coords
            if not validate_coordinates(lat, lon):
                continue
            businesses.append({
                "name": name,
                "business_name": business_name,
                "latitude": lat,
                "longitude": lon,
                "lat_long": f"{lat},{lon}",
                "business_category": category,
                "business_tags": tags,
            })
    return businesses


def search_businesses_vectorized(
    query: str,
    user_lat: float,
    user_lng: float,
    max_distance_km: float = 10.0,
    category_filter: Optional[str] = None,
    tag_filters: Optional[List[str]] = None,
    limit: int = 20,
    distance_weight: Optional[float] = None,
    sort_mode: Optional[str] = None
) -> tuple[List[Dict[str, Any]], str]:
    """Search businesses using Pathway's vectorized data with location filtering."""
    try:
        # Step 1: Get vectorized results from Pathway
        search_query = query
        
        # Enhance query with filters for better vector search
        if category_filter:
            search_query += f" {category_filter}"
        if tag_filters:
            search_query += f" {' '.join(tag_filters)}"
        
        # Use Pathway's retrieve endpoint for vector similarity search
        # Adjust k based on whether this is unlimited search or not
        k_value = 200 if max_distance_km >= 10000 else 50
        
        retrieve_response = requests.post(
            f"{PATHWAY_URL}/v1/retrieve",
            json={
                "query": search_query,
                "k": k_value  # Get more results for unlimited search
            },
            timeout=10
        )
        
        # print("RETRIEVED DATA for RESULTS", retrieve_response.json())
        
        if retrieve_response.status_code != 200:
            logger.error(f"Pathway retrieve failed: {retrieve_response.status_code}")
            return [], "vectorized_error"
        
        retrieve_data = retrieve_response.json()
        # print("RETRIEVED DATA", retrieve_data)
        
        # If Pathway returns empty data, just return empty vectorized result
        if not retrieve_data:
            logger.info("Pathway retrieve returned empty data")
            return [], "vectorized_empty"
        
        # Step 2: Parse businesses from vectorized results
        all_businesses = []
        for item in retrieve_data:
            text = item.get("text", "")
            metadata = item.get("metadata", {})
            
            # Parse businesses from the text
            businesses = parse_business_from_text(text)
            # print("BUSINESSES", businesses)
            
            # Add vector similarity score to each business
            for business in businesses:
                business["vector_score"] = item.get("dist", 0.0)
                business["source_path"] = metadata.get("path", "")
            
            all_businesses.extend(businesses)
            # print("ALL BUSINESSES", all_businesses)
        # Step 3: Remove duplicates (same business appearing multiple times)
        unique_businesses = {}
        for business in all_businesses:
            key = f"{business['business_name']}_{business['lat_long']}"
            if key not in unique_businesses:
                unique_businesses[key] = business
            else:
                # Keep the one with better vector score (lower distance = better)
                if business["vector_score"] < unique_businesses[key]["vector_score"]:
                    unique_businesses[key] = business
        
        businesses_list = list(unique_businesses.values())
        
        # Step 4: Calculate distances and apply location filtering
        filtered_businesses = []
        for business in businesses_list:
            distance = calculate_distance(
                user_lat, user_lng,
                business["latitude"], business["longitude"]
            )
            business["distance_km"] = round(distance, 2)
            
            # Apply distance filter only if max_distance_km is reasonable (not unlimited)
            if max_distance_km >= 10000:  # 10,000km+ is considered "unlimited"
                filtered_businesses.append(business)
            elif distance <= max_distance_km:
                filtered_businesses.append(business)
        
        # Step 5: Apply category and tag filters
        if category_filter:
            filtered_businesses = [
                b for b in filtered_businesses
                if category_filter.lower() in b.get("business_category", "").lower()
            ]
        
        if tag_filters:
            filtered_businesses = [
                b for b in filtered_businesses
                if any(tag.lower() in b.get("business_tags", "").lower() for tag in tag_filters)
            ]
        
        # Step 6: Sort by semantic relevance + distance proximity
        # Auto-detect distance emphasis if query contains locality cues
        query_lower = (query or "").lower()
        near_cues = ["near me", "nearby", "closest", "around me", "near "]
        auto_distance_bias = any(cue in query_lower for cue in near_cues)

        # Determine weights
        if sort_mode == "distance":
            rel_w, dist_w = 0.0, 1.0
        elif sort_mode == "relevance":
            rel_w, dist_w = 1.0, 0.0
        else:
            if distance_weight is not None:
                rel_w = max(0.0, min(1.0 - distance_weight, 1.0))
                dist_w = max(0.0, min(distance_weight, 1.0))
            else:
                # Heuristic: if query implies locality, lean more on distance
                if auto_distance_bias:
                    rel_w, dist_w = 0.5, 0.5
                else:
                    rel_w, dist_w = 0.7, 0.3

        max_distance_in_results = max(b.get("distance_km", 0) for b in filtered_businesses) if filtered_businesses else 1

        def sort_key(business):
            # Lower vector_score is better; lower normalized_distance is better
            vector_score = business.get("vector_score", 1.0)
            distance = business.get("distance_km", 0)
            if max_distance_km >= 10000:
                # If essentially unlimited radius, normalize by max observed distance
                normalized_distance = distance / max(max_distance_in_results, 1)
            else:
                normalized_distance = distance / max(max_distance_km, 1)
            return rel_w * vector_score + dist_w * normalized_distance
        
        filtered_businesses.sort(key=sort_key)
        
        # Step 7: Limit results
        limited_results = filtered_businesses[:limit]
        
        # Return vectorized results only
        if not limited_results:
            return [], "vectorized_empty"

        return limited_results, "vectorized"
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error connecting to Pathway: {e}")
        return [], "vectorized_error"
    except Exception as e:
        print(f"Vectorized search error: {e}")
        return [], "error"


def _monitor_indexing_for_csv(pathway_url: str, csv_rel_path: str) -> None:
    """Poll Pathway until the CSV is indexed; log start/finish."""
    try:
        logger.info(f"[indexing] Monitoring indexing for {csv_rel_path}...")
        # naive polling loop
        import time
        started_logged = False
        for _ in range(120):  # up to ~2 minutes
            try:
                resp = requests.post(f"{pathway_url}/v2/list_documents", timeout=5)
                if resp.status_code == 200:
                    docs = resp.json()
                    for doc in docs:
                        path = doc.get("path", "") or doc.get("metadata", {}).get("path", "")
                        status = doc.get("_indexing_status") or doc.get("indexing_status")
                        if isinstance(path, str) and csv_rel_path in path:
                            if not started_logged and status:
                                logger.info(f"[indexing] {csv_rel_path} status: {status}")
                                started_logged = True
                            if str(status).upper() == "INDEXED":
                                logger.info(f"[indexing] {csv_rel_path} is indexed and ready to query.")
                                return
                else:
                    logger.warning(f"[indexing] list_documents returned {resp.status_code}")
            except Exception as e:  # noqa: BLE001
                logger.warning(f"[indexing] polling error: {e}")
            time.sleep(1)
        logger.warning(f"[indexing] Timed out waiting for {csv_rel_path} to index.")
    except Exception as e:  # noqa: BLE001
        logger.error(f"[indexing] monitor error: {e}")


@app.post("/append-csv")
def append_csv(record: DataRecord):
    """Add a single business record to the CSV file."""
    try:
        # Validate coordinates
        coords = parse_lat_lng(record.lat_long)
        if not coords:
            raise ValueError("Invalid lat_long format. Use 'latitude,longitude'")
        
        lat, lng = coords
        if not validate_coordinates(lat, lng):
            raise ValueError("Invalid coordinates. Latitude must be -90 to 90, longitude must be -180 to 180")
        
        count = append_rows([record])
        # Kick off indexing monitor in background
        import threading as _t
        _t.Thread(
            target=_monitor_indexing_for_csv,
            args=(PATHWAY_URL, "businesses"),
            daemon=True,
        ).start()

        return {
            "ok": True, 
            "appended": count, 
            "csv_path": str(CSV_PATH),
            "coordinates": {"latitude": lat, "longitude": lng}
        }
    except Exception as e:
        return JSONResponse(status_code=400, content={"ok": False, "error": str(e)})


@app.post("/append-csv/batch")
def append_csv_batch(payload: BatchPayload):
    """Add multiple business records to the CSV file."""
    try:
        # Validate all records first
        for i, record in enumerate(payload.records):
            coords = parse_lat_lng(record.lat_long)
            if not coords:
                raise ValueError(f"Record {i+1}: Invalid lat_long format. Use 'latitude,longitude'")
            
            lat, lng = coords
            if not validate_coordinates(lat, lng):
                raise ValueError(f"Record {i+1}: Invalid coordinates")
        
        count = append_rows(payload.records)
        # Kick off indexing monitor in background
        import threading as _t
        _t.Thread(
            target=_monitor_indexing_for_csv,
            args=(PATHWAY_URL, "businesses"),
            daemon=True,
        ).start()
        return {"ok": True, "appended": count, "csv_path": str(CSV_PATH)}
    except Exception as e:
        return JSONResponse(status_code=400, content={"ok": False, "error": str(e)})


@app.post("/search-businesses")
def search_businesses(request: LocationSearchRequest):
    """Search for businesses using vectorized data from Pathway with location filtering."""
    try:
        # Validate user coordinates
        if not validate_coordinates(request.user_lat, request.user_lng):
            raise HTTPException(status_code=400, detail="Invalid user coordinates")
        
        # Use vectorized search from Pathway
        results, search_method = search_businesses_vectorized(
            query=request.query or "business",
            user_lat=request.user_lat,
            user_lng=request.user_lng,
            max_distance_km=request.max_distance_km,
            category_filter=request.category_filter,
            tag_filters=request.tag_filters,
            limit=request.limit,
            distance_weight=request.distance_weight,
            sort_mode=request.sort_mode
        )
        
        return {
            "ok": True,
            "results": results,
            "search_params": {
                "user_location": {"lat": request.user_lat, "lng": request.user_lng},
                "max_distance_km": request.max_distance_km,
                "category_filter": request.category_filter,
                "tag_filters": request.tag_filters,
                "query": request.query
            },
            "total_found": len(results),
            "search_method": search_method
        }
        
    except Exception as e:
        return JSONResponse(status_code=400, content={"ok": False, "error": str(e)})


# Removed CSV-only search endpoint to ensure all queries use vectorized data


@app.get("/health")
def health_check():
    """Health check endpoint."""
    pathway_status = "offline"
    
    # Try statistics endpoint (this is the main Pathway endpoint that works)
    try:
        pathway_response = requests.post(f"{PATHWAY_URL}/v1/statistics", timeout=3)
        if pathway_response.status_code == 200:
            pathway_status = "online"
        else:
            pathway_status = "error"
    except requests.exceptions.ConnectionError:
        pathway_status = "offline"
    except requests.exceptions.Timeout:
        pathway_status = "timeout"
    except Exception as e:
        pathway_status = f"error: {str(e)[:50]}"
    
    return {
        "status": "healthy",
        "csv_exists": CSV_PATH.exists(),
        "csv_path": str(CSV_PATH),
        "data_dir": str(DATA_DIR),
        "pathway_status": pathway_status,
        "pathway_url": PATHWAY_URL
    }


