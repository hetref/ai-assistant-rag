import os
import uuid
import csv
import math
from pathlib import Path
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from utils import (
    search_businesses_advanced, 
    validate_coordinates, 
    parse_lat_lng,
    calculate_distance,
    format_distance
)
import requests
import re


app = FastAPI(title="Upload API", version="1.0.0")


DATA_DIR = Path(os.getenv("DATA_DIR", "data")).resolve()
CSV_PATH = DATA_DIR / "data.csv"

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
    return len(rows)


def parse_business_from_text(text: str) -> List[Dict[str, Any]]:
    """Parse business data from vectorized document text."""
    businesses = []
    
    # Handle CSV-like text
    lines = text.strip().split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Skip header line
        if 'name,business_name,lat_long' in line.lower():
            continue
            
        # Try to parse CSV format
        parts = [p.strip().strip('"') for p in line.split(',')]
        if len(parts) >= 6:  # name, business_name, lat, lng, category, tags
            name = parts[0]
            business_name = parts[1]
            latitude = parts[2]
            longitude = parts[3]
            category = parts[4]
            tags = parts[5] if len(parts) > 5 else ""
            
            # Skip if any essential field is empty
            if not name or not business_name or not latitude or not longitude or not category:
                continue
            
            try:
                lat = float(latitude)
                lng = float(longitude)
                
                # Validate coordinates
                if not validate_coordinates(lat, lng):
                    continue
                    
                lat_long = f"{lat},{lng}"
                
                businesses.append({
                    "name": name,
                    "business_name": business_name,
                    "latitude": lat,
                    "longitude": lng,
                    "lat_long": lat_long,
                    "business_category": category,
                    "business_tags": tags
                })
            except (ValueError, TypeError):
                continue
    
    return businesses


def search_businesses_vectorized(
    query: str,
    user_lat: float,
    user_lng: float,
    max_distance_km: float = 10.0,
    category_filter: Optional[str] = None,
    tag_filters: Optional[List[str]] = None,
    limit: int = 20
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
        
        if retrieve_response.status_code != 200:
            print(f"Pathway retrieve failed: {retrieve_response.status_code}")
            csv_results = search_businesses_advanced(
                csv_path=CSV_PATH,
                user_lat=user_lat,
                user_lng=user_lng,
                max_distance_km=max_distance_km,
                category_filter=category_filter,
                tag_filters=tag_filters,
                limit=limit
            )
            return csv_results, "csv_retrieve_error"
        
        retrieve_data = retrieve_response.json()
        
        # If Pathway returns empty data, fall back to CSV immediately
        if not retrieve_data:
            print(f"Pathway retrieve returned empty data, falling back to CSV search")
            csv_results = search_businesses_advanced(
                csv_path=CSV_PATH,
                user_lat=user_lat,
                user_lng=user_lng,
                max_distance_km=max_distance_km,
                category_filter=category_filter,
                tag_filters=tag_filters,
                limit=limit
            )
            return csv_results, "csv_empty_retrieve"
        
        # Step 2: Parse businesses from vectorized results
        all_businesses = []
        for item in retrieve_data:
            text = item.get("text", "")
            metadata = item.get("metadata", {})
            
            # Parse businesses from the text
            businesses = parse_business_from_text(text)
            
            # Add vector similarity score to each business
            for business in businesses:
                business["vector_score"] = item.get("dist", 0.0)
                business["source_path"] = metadata.get("path", "")
            
            all_businesses.extend(businesses)
        
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
        
        # Step 6: Sort by combination of vector relevance and distance
        def sort_key(business):
            # Combine vector similarity and distance (both lower is better)
            vector_score = business.get("vector_score", 1.0)
            distance = business.get("distance_km", 0)
            
            # For unlimited search (large max_distance), prioritize distance more
            if max_distance_km >= 10000:
                # For unlimited search: 40% relevance, 60% distance (normalized by max actual distance)
                max_distance_in_results = max(b.get("distance_km", 0) for b in filtered_businesses) if filtered_businesses else 1
                normalized_distance = distance / max(max_distance_in_results, 1)
                return 0.4 * vector_score + 0.6 * normalized_distance
            else:
                # For limited search: 70% relevance, 30% distance  
                normalized_distance = distance / max_distance_km
                return 0.7 * vector_score + 0.3 * normalized_distance
        
        filtered_businesses.sort(key=sort_key)
        
        # Step 7: Limit results
        limited_results = filtered_businesses[:limit]
        
        # If vectorized search returns empty results, fall back to CSV search
        if not limited_results:
            print(f"Vectorized search returned no results, falling back to CSV search")
            csv_results = search_businesses_advanced(
                csv_path=CSV_PATH,
                user_lat=user_lat,
                user_lng=user_lng,
                max_distance_km=max_distance_km,
                category_filter=category_filter,
                tag_filters=tag_filters,
                limit=limit
            )
            return csv_results, "csv_fallback"
        
        return limited_results, "vectorized"
        
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to Pathway: {e}")
        # Fallback to CSV-based search
        csv_results = search_businesses_advanced(
            csv_path=CSV_PATH,
            user_lat=user_lat,
            user_lng=user_lng,
            max_distance_km=max_distance_km,
            category_filter=category_filter,
            tag_filters=tag_filters,
            limit=limit
        )
        return csv_results, "csv_error_fallback"
    except Exception as e:
        print(f"Vectorized search error: {e}")
        return [], "error"


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
            limit=request.limit
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


@app.post("/search-businesses-csv")
def search_businesses_csv(request: LocationSearchRequest):
    """Search for businesses using CSV data only (fallback method)."""
    try:
        # Validate user coordinates
        if not validate_coordinates(request.user_lat, request.user_lng):
            raise HTTPException(status_code=400, detail="Invalid user coordinates")
        
        # Use CSV-based search
        results = search_businesses_advanced(
            csv_path=CSV_PATH,
            user_lat=request.user_lat,
            user_lng=request.user_lng,
            max_distance_km=request.max_distance_km,
            category_filter=request.category_filter,
            tag_filters=request.tag_filters,
            limit=request.limit
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
            "search_method": "csv_only"
        }
        
    except Exception as e:
        return JSONResponse(status_code=400, content={"ok": False, "error": str(e)})


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


