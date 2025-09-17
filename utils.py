import math
import csv
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

def calculate_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Calculate the distance between two geographic points using the Haversine formula.
    
    Args:
        lat1, lng1: Latitude and longitude of the first point
        lat2, lng2: Latitude and longitude of the second point
    
    Returns:
        Distance in kilometers
    """
    # Convert latitude and longitude from degrees to radians
    lat1, lng1, lat2, lng2 = map(math.radians, [lat1, lng1, lat2, lng2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    # Radius of Earth in kilometers
    R = 6371
    distance = R * c
    
    return distance

def parse_lat_lng(lat_lng_str: str) -> Optional[Tuple[float, float]]:
    """
    Parse a lat,lng string into a tuple of floats.
    
    Args:
        lat_lng_str: String in format "latitude,longitude"
    
    Returns:
        Tuple of (latitude, longitude) or None if parsing fails
    """
    try:
        parts = lat_lng_str.strip().split(',')
        if len(parts) == 2:
            lat = float(parts[0].strip())
            lng = float(parts[1].strip())
            return (lat, lng)
    except (ValueError, AttributeError):
        pass
    return None

def read_csv_businesses(csv_path: Path) -> List[Dict[str, Any]]:
    """
    Read business data from CSV file.
    
    Args:
        csv_path: Path to the CSV file
    
    Returns:
        List of business dictionaries
    """
    businesses = []
    
    if not csv_path.exists():
        return businesses
    
    try:
        with csv_path.open('r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Parse coordinates
                coords = parse_lat_lng(row.get('lat_long', ''))
                if coords:
                    lat, lng = coords
                    business = {
                        'name': row.get('name', '').strip(),
                        'business_name': row.get('business_name', '').strip(),
                        'latitude': lat,
                        'longitude': lng,
                        'lat_long': row.get('lat_long', '').strip(),
                        'business_category': row.get('business_category', '').strip(),
                        'business_tags': row.get('business_tags', '').strip()
                    }
                    businesses.append(business)
    except Exception as e:
        print(f"Error reading CSV: {e}")
    
    return businesses

def filter_businesses_by_location(
    businesses: List[Dict[str, Any]], 
    user_lat: float, 
    user_lng: float, 
    max_distance_km: float = 10.0
) -> List[Dict[str, Any]]:
    """
    Filter businesses by distance from user location.
    
    Args:
        businesses: List of business dictionaries
        user_lat: User's latitude
        user_lng: User's longitude
        max_distance_km: Maximum distance in kilometers
    
    Returns:
        List of businesses within distance, sorted by proximity
    """
    filtered = []
    
    for business in businesses:
        distance = calculate_distance(
            user_lat, user_lng,
            business['latitude'], business['longitude']
        )
        
        business_copy = business.copy()
        business_copy['distance_km'] = round(distance, 2)
        
        # Apply distance filter only if max_distance_km is reasonable (not unlimited)
        if max_distance_km >= 10000:  # 10,000km+ is considered "unlimited"
            filtered.append(business_copy)
        elif distance <= max_distance_km:
            filtered.append(business_copy)
    
    # Sort by distance
    filtered.sort(key=lambda x: x['distance_km'])
    return filtered

def filter_businesses_by_category(
    businesses: List[Dict[str, Any]], 
    category_filter: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Filter businesses by category.
    
    Args:
        businesses: List of business dictionaries
        category_filter: Category to filter by (case-insensitive)
    
    Returns:
        Filtered list of businesses
    """
    if not category_filter:
        return businesses
    
    category_lower = category_filter.lower()
    return [
        business for business in businesses
        if category_lower in business.get('business_category', '').lower()
    ]

def filter_businesses_by_tags(
    businesses: List[Dict[str, Any]], 
    tag_filters: List[str]
) -> List[Dict[str, Any]]:
    """
    Filter businesses by tags.
    
    Args:
        businesses: List of business dictionaries
        tag_filters: List of tags to filter by (case-insensitive)
    
    Returns:
        Filtered list of businesses
    """
    if not tag_filters:
        return businesses
    
    filtered = []
    for business in businesses:
        business_tags = business.get('business_tags', '').lower()
        if any(tag.lower() in business_tags for tag in tag_filters):
            filtered.append(business)
    
    return filtered

def search_businesses_advanced(
    csv_path: Path,
    user_lat: float,
    user_lng: float,
    max_distance_km: float = 10.0,
    category_filter: Optional[str] = None,
    tag_filters: Optional[List[str]] = None,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """
    Advanced business search with multiple filters.
    
    Args:
        csv_path: Path to CSV file containing business data
        user_lat: User's latitude
        user_lng: User's longitude
        max_distance_km: Maximum distance in kilometers
        category_filter: Category to filter by
        tag_filters: List of tags to filter by
        limit: Maximum number of results to return
    
    Returns:
        Filtered and sorted list of businesses
    """
    # Read all businesses
    businesses = read_csv_businesses(csv_path)
    
    # Apply filters
    businesses = filter_businesses_by_location(businesses, user_lat, user_lng, max_distance_km)
    businesses = filter_businesses_by_category(businesses, category_filter)
    
    if tag_filters:
        businesses = filter_businesses_by_tags(businesses, tag_filters)
    
    # Limit results
    return businesses[:limit]

def validate_coordinates(lat: float, lng: float) -> bool:
    """
    Validate latitude and longitude coordinates.
    
    Args:
        lat: Latitude
        lng: Longitude
    
    Returns:
        True if coordinates are valid, False otherwise
    """
    return -90 <= lat <= 90 and -180 <= lng <= 180

def format_distance(distance_km: float) -> str:
    """
    Format distance for display.
    
    Args:
        distance_km: Distance in kilometers
    
    Returns:
        Formatted distance string
    """
    if distance_km < 1:
        return f"{int(distance_km * 1000)}m"
    else:
        return f"{distance_km:.1f}km"

def get_business_summary(business: Dict[str, Any]) -> str:
    """
    Generate a summary string for a business.
    
    Args:
        business: Business dictionary
    
    Returns:
        Formatted summary string
    """
    name = business.get('business_name', 'Unknown Business')
    category = business.get('business_category', 'Unknown')
    distance = business.get('distance_km', 0)
    tags = business.get('business_tags', '')
    
    summary = f"{name} ({category})"
    if distance > 0:
        summary += f" - {format_distance(distance)} away"
    if tags:
        summary += f" | Tags: {tags}"
    
    return summary
