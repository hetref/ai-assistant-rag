import os
import uuid
import csv
import math
import logging
import hashlib
from datetime import datetime
from pathlib import Path
import json
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, HTTPException, Request
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

# Import collaborative filtering
try:
    from collaborative_filtering_simple import (
        cf_engine, 
        UserInteraction, 
        CollaborativeFilteringEngine
    )
    CF_AVAILABLE = True
    print("Collaborative filtering loaded successfully (simple version)")
except ImportError as e:
    print(f"Collaborative filtering not available - Redis dependencies missing: {e}")
    CF_AVAILABLE = False
except Exception as e:
    print(f"Collaborative filtering failed to load: {e}")
    CF_AVAILABLE = False

# Import contextual recommendations
try:
    from contextual_recommendations import contextual_engine
    from weather_service import weather_service
    CONTEXTUAL_AVAILABLE = True
    print("Contextual recommendations loaded successfully")
except ImportError as e:
    print(f"Contextual recommendations not available: {e}")
    CONTEXTUAL_AVAILABLE = False
except Exception as e:
    print(f"Contextual recommendations failed to load: {e}")
    CONTEXTUAL_AVAILABLE = False


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
    # Collaborative filtering fields
    user_session_id: Optional[str] = Field(None, description="User session ID for tracking")
    include_recommendations: bool = Field(True, description="Include collaborative filtering recommendations")


# Collaborative Filtering Models
class InteractionRequest(BaseModel):
    business_id: str = Field(..., description="Business ID that was interacted with")
    business_name: str = Field(..., description="Business name")
    interaction_type: str = Field(..., description="Type: 'search', 'view', 'click', 'bookmark'")
    query: Optional[str] = Field(None, description="Search query if applicable")
    category: Optional[str] = Field(None, description="Business category")
    tags: Optional[List[str]] = Field(None, description="Business tags")
    dwell_time_seconds: Optional[int] = Field(None, description="Time spent viewing (for rating calculation)")
    user_lat: Optional[float] = Field(None, description="User location when interacting")
    user_lng: Optional[float] = Field(None, description="User location when interacting")


class RecommendationsRequest(BaseModel):
    user_lat: Optional[float] = Field(None, description="User's latitude")
    user_lng: Optional[float] = Field(None, description="User's longitude") 
    limit: int = Field(10, description="Maximum recommendations to return", gt=0, le=50)
    exclude_business_ids: Optional[List[str]] = Field(None, description="Business IDs to exclude")
    recommendation_types: List[str] = Field(
        default=["collaborative", "popular", "trending"], 
        description="Types of recommendations to include"
    )


class ContextualRecommendationsRequest(BaseModel):
    """Request model for contextual recommendations."""
    user_lat: float = Field(..., description="User's latitude", ge=-90, le=90)
    user_lng: float = Field(..., description="User's longitude", ge=-180, le=180)
    search_query: Optional[str] = Field(None, description="Current search query for context")
    limit: int = Field(15, description="Maximum recommendations to return", gt=0, le=50)
    include_weather: bool = Field(True, description="Include weather-based recommendations")
    include_time_context: bool = Field(True, description="Include time-of-day context")
    include_user_history: bool = Field(True, description="Include user history context")
    user_session_id: Optional[str] = Field(None, description="User session ID for tracking")


class WeatherRequest(BaseModel):
    """Request model for weather data."""
    user_lat: float = Field(..., description="Latitude", ge=-90, le=90)
    user_lng: float = Field(..., description="Longitude", ge=-180, le=180)


def generate_user_id(request: Request) -> str:
    """Generate user ID from request headers."""
    user_agent = request.headers.get("user-agent", "unknown")
    # In production, you might want to use more sophisticated user identification
    x_forwarded_for = request.headers.get("x-forwarded-for")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0].strip()
    else:
        ip = request.client.host if request.client else "unknown"
    
    identifier = f"{user_agent}:{ip}"
    return hashlib.sha256(identifier.encode()).hexdigest()[:16]


def generate_session_id() -> str:
    """Generate a new session ID."""
    return str(uuid.uuid4())


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
    """Create a single per-business .json file with normalized keys."""
    coords = parse_lat_lng(record.lat_long)
    lat, lon = (None, None)
    if coords:
        lat, lon = coords
    safe_name = "_".join(
        [
            str(record.business_name).strip().replace("/", "-").replace(" ", "_")[:40],
            uuid.uuid4().hex[:8],
        ]
    )

    payload = {
        "name": record.name,
        "owner_name": record.name,
        "business_name": record.business_name,
        "business_category": record.business_category,
        "business_tags": record.business_tags,
        "latitude": lat,
        "longitude": lon,
        "lat_long": record.lat_long,
    }

    out_path = BUSINESSES_DIR / f"{safe_name}.json"
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path


def parse_business_from_text(text: str) -> List[Dict[str, Any]]:
    """Parse business data from vectorized document text.

    Supports both per-business key:value files and CSV-like rows.
    """
    businesses: List[Dict[str, Any]] = []

    raw = (text or "").strip()
    if not raw:
        return businesses

    # 0) Try JSON first (supports either a dict or a list of dicts)
    try:
        parsed = json.loads(raw)
        candidate_items: List[Dict[str, Any]] = []
        if isinstance(parsed, dict):
            candidate_items = [parsed]
        elif isinstance(parsed, list):
            candidate_items = [p for p in parsed if isinstance(p, dict)]

        for item in candidate_items:
            business_name = (item.get("business_name") or item.get("business") or "").strip()
            name = (item.get("name") or item.get("owner_name") or "").strip()
            category = (item.get("business_category") or item.get("category") or "").strip()
            tags = item.get("business_tags") or item.get("tags") or ""
            lat = item.get("latitude")
            lon = item.get("longitude")
            lat_long = item.get("lat_long") or (f"{lat},{lon}" if lat is not None and lon is not None else "")

            if (lat is None or lon is None) and lat_long:
                coords = parse_lat_lng(str(lat_long))
                if coords:
                    lat, lon = coords
            try:
                if lat is not None:
                    lat = float(lat)
                if lon is not None:
                    lon = float(lon)
            except (TypeError, ValueError):
                lat, lon = None, None

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

        if businesses:
            return businesses
    except json.JSONDecodeError:
        pass

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
async def search_businesses(request: LocationSearchRequest, http_request: Request):
    """Search for businesses using vectorized data from Pathway with location filtering and collaborative filtering."""
    try:
        # Validate user coordinates
        if not validate_coordinates(request.user_lat, request.user_lng):
            raise HTTPException(status_code=400, detail="Invalid user coordinates")
        
        # Generate user ID and session ID
        user_id = generate_user_id(http_request)
        session_id = request.user_session_id or generate_session_id()
        
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
        
        # Track search interaction for collaborative filtering
        if CF_AVAILABLE and request.query:
            try:
                interaction = UserInteraction(
                    user_id=user_id,
                    business_id="search_query",  # Special ID for search queries
                    business_name=request.query,
                    interaction_type="search",
                    timestamp=datetime.now(),
                    query=request.query,
                    category=request.category_filter,
                    tags=request.tag_filters,
                    location=(request.user_lat, request.user_lng),
                    session_id=session_id,
                    implicit_rating=1.0
                )
                await cf_engine.record_interaction(interaction)
            except Exception as e:
                logger.warning(f"Failed to record search interaction: {e}")
        
        # Get collaborative filtering recommendations if enabled
        recommendations = []
        if CF_AVAILABLE and request.include_recommendations and results:
            try:
                # Get business IDs from current results to exclude from recommendations
                current_business_ids = {r.get("business_id", r.get("business_name", "")) for r in results}
                
                cf_recommendations = await cf_engine.get_collaborative_recommendations(
                    user_id=user_id,
                    exclude_businesses=current_business_ids,
                    limit=5
                )
                recommendations = cf_recommendations
            except Exception as e:
                logger.warning(f"Failed to get collaborative recommendations: {e}")
        
        return {
            "ok": True,
            "results": results,
            "recommendations": recommendations,
            "user_id": user_id,
            "session_id": session_id,
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
async def health_check():
    """Health check endpoint."""
    pathway_status = "offline"
    redis_status = "offline"
    
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
        
        print("PATHWAY STATUS", pathway_status)
    
    # Check Redis status
    if CF_AVAILABLE:
        try:
            await cf_engine.connect()
            redis_status = "online"
        except Exception as e:
            redis_status = f"error: {str(e)[:50]}"
    
    return {
        "status": "healthy",
        "csv_exists": CSV_PATH.exists(),
        "csv_path": str(CSV_PATH),
        "data_dir": str(DATA_DIR),
        "pathway_status": pathway_status,
        "pathway_url": PATHWAY_URL,
        "redis_status": redis_status,
        "collaborative_filtering": CF_AVAILABLE
    }


# Collaborative Filtering Endpoints

@app.post("/interactions/track")
async def track_interaction(interaction_req: InteractionRequest, request: Request):
    """Track user interaction with a business for collaborative filtering."""
    if not CF_AVAILABLE:
        raise HTTPException(status_code=503, detail="Collaborative filtering not available")
    
    try:
        user_id = generate_user_id(request)
        session_id = generate_session_id()
        
        # Calculate implicit rating based on interaction type and dwell time
        if CF_AVAILABLE:
            rating = cf_engine.calculate_implicit_rating(
                interaction_req.interaction_type, 
                interaction_req.dwell_time_seconds
            )
        else:
            rating = 1.0
        
        # Create interaction
        interaction = UserInteraction(
            user_id=user_id,
            business_id=interaction_req.business_id,
            business_name=interaction_req.business_name,
            interaction_type=interaction_req.interaction_type,
            timestamp=datetime.now(),
            query=interaction_req.query,
            category=interaction_req.category,
            tags=interaction_req.tags,
            location=(interaction_req.user_lat, interaction_req.user_lng) if interaction_req.user_lat and interaction_req.user_lng else None,
            session_id=session_id,
            implicit_rating=rating
        )
        
        await cf_engine.record_interaction(interaction)
        
        return {
            "ok": True,
            "user_id": user_id,
            "session_id": session_id,
            "implicit_rating": rating,
            "message": "Interaction tracked successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to track interaction: {e}")
        return JSONResponse(
            status_code=500, 
            content={"ok": False, "error": f"Failed to track interaction: {str(e)}"}
        )


@app.post("/recommendations")
async def get_recommendations(req: RecommendationsRequest, request: Request):
    """Get collaborative filtering recommendations for a user."""
    if not CF_AVAILABLE:
        raise HTTPException(status_code=503, detail="Collaborative filtering not available")
    
    try:
        user_id = generate_user_id(request)
        
        recommendations = []
        
        # Get collaborative recommendations if requested
        if "collaborative" in req.recommendation_types:
            cf_recs = await cf_engine.get_collaborative_recommendations(
                user_id=user_id,
                exclude_businesses=set(req.exclude_business_ids or []),
                limit=req.limit
            )
            recommendations.extend(cf_recs)
        
        # Get trending searches if requested
        trending_searches = []
        if "trending" in req.recommendation_types:
            trending = await cf_engine.get_trending_searches(limit=10)
            trending_searches = [{"query": query, "count": count} for query, count in trending]
        
        return {
            "ok": True,
            "user_id": user_id,
            "recommendations": recommendations[:req.limit],
            "trending_searches": trending_searches,
            "total_found": len(recommendations)
        }
        
    except Exception as e:
        logger.error(f"Failed to get recommendations: {e}")
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": f"Failed to get recommendations: {str(e)}"}
        )


@app.get("/recommendations/trending-searches")
async def get_trending_searches(limit: int = 10):
    """Get trending search queries."""
    if not CF_AVAILABLE:
        raise HTTPException(status_code=503, detail="Collaborative filtering not available")
    
    try:
        trending = await cf_engine.get_trending_searches(limit=limit)
        return {
            "ok": True,
            "trending_searches": [{"query": query, "search_count": count} for query, count in trending]
        }
    except Exception as e:
        logger.error(f"Failed to get trending searches: {e}")
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": f"Failed to get trending searches: {str(e)}"}
        )


@app.get("/recommendations/people-also-searched")
async def get_people_also_searched(query: str, limit: int = 5):
    """Get 'People also searched for' suggestions."""
    if not CF_AVAILABLE:
        raise HTTPException(status_code=503, detail="Collaborative filtering not available")
    
    try:
        suggestions = await cf_engine.get_people_also_searched(query, limit=limit)
        return {
            "ok": True,
            "query": query,
            "suggestions": suggestions
        }
    except Exception as e:
        logger.error(f"Failed to get people also searched: {e}")
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": f"Failed to get suggestions: {str(e)}"}
        )


@app.get("/analytics/cf-performance")
async def get_cf_analytics():
    """Get collaborative filtering analytics and performance metrics."""
    if not CF_AVAILABLE:
        raise HTTPException(status_code=503, detail="Collaborative filtering not available")
    
    try:
        analytics = await cf_engine.get_analytics_data()
        return {
            "ok": True,
            "analytics": analytics,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get CF analytics: {e}")
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": f"Failed to get analytics: {str(e)}"}
        )


# Contextual Recommendations Endpoints

@app.post("/recommendations/contextual")
async def get_contextual_recommendations(req: ContextualRecommendationsRequest, request: Request):
    """Get contextual recommendations based on time, weather, and user history."""
    if not CONTEXTUAL_AVAILABLE:
        raise HTTPException(status_code=503, detail="Contextual recommendations not available")
    
    try:
        # Validate user coordinates
        if not validate_coordinates(req.user_lat, req.user_lng):
            raise HTTPException(status_code=400, detail="Invalid user coordinates")
        
        # Generate user ID
        user_id = generate_user_id(request)
        session_id = req.user_session_id or generate_session_id()
        
        # Get contextual recommendations
        result = await contextual_engine.get_contextual_recommendations(
            user_id=user_id,
            user_lat=req.user_lat,
            user_lng=req.user_lng,
            search_query=req.search_query,
            limit=req.limit,
            session_id=session_id
        )
        
        return {
            "ok": True,
            "recommendations": result["recommendations"],
            "context": result["context"],
            "user_id": user_id,
            "session_id": session_id,
            "generated_at": result["generated_at"],
            "total_found": len(result["recommendations"])
        }
        
    except Exception as e:
        logger.error(f"Failed to get contextual recommendations: {e}")
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": f"Failed to get contextual recommendations: {str(e)}"}
        )


@app.get("/weather/current")
async def get_current_weather(user_lat: float, user_lng: float):
    """Get current weather data for a location."""
    try:
        # Validate coordinates
        if not validate_coordinates(user_lat, user_lng):
            raise HTTPException(status_code=400, detail="Invalid coordinates")
        
        weather_data = await weather_service.get_current_weather(user_lat, user_lng)
        
        if not weather_data:
            return JSONResponse(
                status_code=503,
                content={"ok": False, "error": "Weather data not available"}
            )
        
        return {
            "ok": True,
            "weather": {
                "temperature_celsius": weather_data.temperature_celsius,
                "temperature_fahrenheit": weather_data.temperature_fahrenheit,
                "condition": weather_data.condition.value,
                "description": weather_data.description,
                "humidity": weather_data.humidity,
                "wind_speed_kmh": weather_data.wind_speed_kmh,
                "feels_like_celsius": weather_data.feels_like_celsius,
                "is_hot": weather_data.is_hot,
                "is_cold": weather_data.is_cold,
                "is_rainy": weather_data.is_rainy,
                "is_pleasant": weather_data.is_pleasant,
                "timestamp": weather_data.timestamp.isoformat(),
                "location": {"lat": weather_data.location[0], "lng": weather_data.location[1]}
            },
            "business_suggestions": weather_service.get_weather_business_suggestions(weather_data)
        }
        
    except Exception as e:
        logger.error(f"Failed to get weather data: {e}")
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": f"Failed to get weather data: {str(e)}"}
        )


@app.post("/search-businesses/contextual")
async def search_businesses_contextual(request: LocationSearchRequest, http_request: Request):
    """Enhanced business search with contextual recommendations."""
    try:
        # Validate user coordinates
        if not validate_coordinates(request.user_lat, request.user_lng):
            raise HTTPException(status_code=400, detail="Invalid user coordinates")
        
        # Generate user ID and session ID
        user_id = generate_user_id(http_request)
        session_id = request.user_session_id or generate_session_id()
        
        # Get regular search results
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
        
        # Track search interaction
        if CF_AVAILABLE and request.query:
            try:
                interaction = UserInteraction(
                    user_id=user_id,
                    business_id="search_query",
                    business_name=request.query,
                    interaction_type="search",
                    timestamp=datetime.now(),
                    query=request.query,
                    category=request.category_filter,
                    tags=request.tag_filters,
                    location=(request.user_lat, request.user_lng),
                    session_id=session_id,
                    implicit_rating=1.0
                )
                await cf_engine.record_interaction(interaction)
            except Exception as e:
                logger.warning(f"Failed to record search interaction: {e}")
        
        # Get contextual recommendations if available
        contextual_recommendations = []
        context_info = {}
        
        if CONTEXTUAL_AVAILABLE:
            try:
                # Initialize contextual engine with CF engine
                contextual_engine.cf_engine = cf_engine
                
                # Apply contextual factors to search results
                contextual_result = await contextual_engine.get_contextual_recommendations(
                    user_id=user_id,
                    user_lat=request.user_lat,
                    user_lng=request.user_lng,
                    search_query=request.query,
                    base_results=results,
                    limit=request.limit,
                    session_id=session_id
                )
                
                # Use contextually enhanced results
                results = contextual_result["recommendations"]
                context_info = contextual_result["context"]
                
                # Also get separate contextual recommendations
                contextual_recommendations = await contextual_engine.get_contextual_recommendations(
                    user_id=user_id,
                    user_lat=request.user_lat,
                    user_lng=request.user_lng,
                    search_query=request.query,
                    limit=5,
                    session_id=session_id
                )
                contextual_recommendations = contextual_recommendations["recommendations"]
                
            except Exception as e:
                logger.warning(f"Failed to get contextual recommendations: {e}")
        
        return {
            "ok": True,
            "results": results,
            "contextual_recommendations": contextual_recommendations,
            "context": context_info,
            "user_id": user_id,
            "session_id": session_id,
            "search_params": {
                "user_location": {"lat": request.user_lat, "lng": request.user_lng},
                "max_distance_km": request.max_distance_km,
                "category_filter": request.category_filter,
                "tag_filters": request.tag_filters,
                "query": request.query
            },
            "total_found": len(results),
            "search_method": search_method,
            "contextual_features_available": CONTEXTUAL_AVAILABLE
        }
        
    except Exception as e:
        logger.error(f"Contextual search failed: {e}")
        return JSONResponse(status_code=400, content={"ok": False, "error": str(e)})


