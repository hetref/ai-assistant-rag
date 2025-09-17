import streamlit as st
import requests
import json
import math
from typing import List, Dict, Any, Optional

# Configuration
UPLOAD_API_URL = "http://localhost:8001"
PATHWAY_API_URL = "http://localhost:8000"

st.set_page_config(
    page_title="Location Search", 
    page_icon="🗺️", 
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
.search-result {
    background-color: #f8f9fa;
    padding: 1rem;
    border-radius: 0.5rem;
    border-left: 4px solid #007bff;
    margin: 0.5rem 0;
}
.distance-badge {
    background-color: #28a745;
    color: white;
    padding: 0.2rem 0.5rem;
    border-radius: 1rem;
    font-size: 0.8rem;
    font-weight: bold;
}
.category-badge {
    background-color: #17a2b8;
    color: white;
    padding: 0.2rem 0.5rem;
    border-radius: 0.3rem;
    font-size: 0.8rem;
    margin-right: 0.5rem;
}
.location-input {
    background-color: #e9ecef;
    padding: 1rem;
    border-radius: 0.5rem;
    margin: 1rem 0;
}
.map-placeholder {
    background-color: #e9ecef;
    border: 2px dashed #6c757d;
    border-radius: 0.5rem;
    padding: 2rem;
    text-align: center;
    color: #6c757d;
    margin: 1rem 0;
}
</style>
""", unsafe_allow_html=True)

def calculate_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate distance between two points using Haversine formula."""
    R = 6371  # Earth's radius in kilometers
    
    lat1, lng1, lat2, lng2 = map(math.radians, [lat1, lng1, lat2, lng2])
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng/2)**2
    c = 2 * math.asin(math.sqrt(a))
    distance = R * c
    
    return distance

def parse_lat_lng(lat_lng_str: str) -> Optional[tuple]:
    """Parse lat,lng string into tuple of floats."""
    try:
        parts = lat_lng_str.split(',')
        if len(parts) == 2:
            lat = float(parts[0].strip())
            lng = float(parts[1].strip())
            return (lat, lng)
    except:
        pass
    return None

def search_businesses(query: str, user_lat: float, user_lng: float, max_distance: Optional[float] = 10.0) -> tuple[List[Dict], str]:
    """Search for businesses using vectorized data from Pathway with location filtering."""
    try:
        # Use the vectorized search endpoint
        payload = {
            "user_lat": user_lat,
            "user_lng": user_lng,
            "query": query,
            "limit": 100  # Increased limit for unlimited search
        }
        
        # Only add distance constraint if specified
        if max_distance is not None:
            payload["max_distance_km"] = max_distance
        else:
            # Use a very large radius for "unlimited" search
            payload["max_distance_km"] = 20000.0  # 20,000 km (essentially unlimited on Earth)
        
        response = requests.post(
            f"{UPLOAD_API_URL}/search-businesses",
            json=payload,
            timeout=15
        )
        
        if response.status_code != 200:
            st.error(f"API Error: {response.status_code}")
            return [], "error"
        
        data = response.json()
        
        if not data.get("ok", False):
            st.error(f"Search failed: {data.get('error', 'Unknown error')}")
            return [], "error"
        
        results = data.get("results", [])
        search_method = data.get("search_method", "unknown")
        
        # Convert to expected format
        formatted_results = []
        for business in results:
            result = {
                "name": business.get("name", ""),
                "business_name": business.get("business_name", ""),
                "latitude": business.get("latitude", 0),
                "longitude": business.get("longitude", 0),
                "category": business.get("business_category", ""),
                "tags": business.get("business_tags", ""),
                "distance": business.get("distance_km", 0)
            }
            
            # Add vectorized search specific fields
            if "vector_score" in business:
                result["vector_score"] = business["vector_score"]
                result["relevance"] = 1.0 / (1.0 + business["vector_score"])  # Convert to 0-1 scale
            
            formatted_results.append(result)
        
        return formatted_results, search_method
        
    except requests.exceptions.Timeout:
        st.error("❌ Search timed out. Please try again.")
        return [], "timeout"
    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot connect to search API. Please check if the service is running.")
        return [], "connection_error"
    except Exception as e:
        st.error(f"❌ Search error: {str(e)}")
        return [], "error"

# Main UI
st.title("🗺️ Location-Based Business Search")
st.markdown("Find businesses near your location using AI-powered search")

# Sidebar
with st.sidebar:
    st.header("🔧 Search Settings")
    
    # Distance constraint option
    unlimited_search = st.checkbox(
        "🌍 Search All Businesses (No Distance Limit)", 
        value=True,
        help="When enabled, searches all businesses regardless of distance and sorts by proximity"
    )
    
    if not unlimited_search:
        max_distance = st.slider(
            "📏 Search Radius (km)", 
            min_value=1.0, 
            max_value=100.0, 
            value=25.0, 
            step=5.0
        )
    else:
        max_distance = None
        st.info("🌍 **Unlimited search enabled** - All businesses will be returned, sorted by distance")
    
    show_map = st.checkbox("🗺️ Show Map View", value=False)
    
    st.markdown("---")
    st.header("📊 System Status")
    
    # Enhanced API status checks
    upload_api_online = False
    pathway_online = False
    
    # Check Upload API
    try:
        health_response = requests.get(f"{UPLOAD_API_URL}/health", timeout=3)
        if health_response.status_code == 200:
            upload_api_online = True
            st.success("✅ Upload API: Online")
        else:
            st.error(f"❌ Upload API: HTTP {health_response.status_code}")
    except requests.exceptions.ConnectionError:
        st.error("❌ Upload API: Connection refused")
    except requests.exceptions.Timeout:
        st.warning("⏰ Upload API: Timeout")
    except Exception as e:
        st.error(f"❌ Upload API: {str(e)}")
    
    # Check Pathway directly (more reliable than health endpoint)
    try:
        pathway_response = requests.post(f"{PATHWAY_API_URL}/v1/statistics", timeout=3)
        if pathway_response.status_code == 200:
            pathway_online = True
            st.success("✅ Pathway RAG: Online")
            st.info("🧠 **Vectorized search enabled**")
        else:
            st.error(f"❌ Pathway RAG: HTTP {pathway_response.status_code}")
            st.warning("⚠️ Using CSV fallback only")
    except requests.exceptions.ConnectionError:
        st.error("❌ Pathway RAG: Connection refused")
        st.warning("⚠️ Using CSV fallback only")
    except requests.exceptions.Timeout:
        st.warning("⏰ Pathway RAG: Timeout")
        st.info("🔄 Service may be starting up or overloaded")
    except Exception as e:
        st.error(f"❌ Pathway RAG: {str(e)}")
        st.warning("⚠️ Using CSV fallback only")
    
    # Overall status summary
    if upload_api_online and pathway_online:
        st.success("🚀 All systems operational")
    elif upload_api_online and not pathway_online:
        st.warning("⚠️ Partial functionality - CSV search only")
    elif not upload_api_online and pathway_online:
        st.info("ℹ️ Direct Pathway access available")
    else:
        st.error("❌ System offline")

# Main content
col1, col2 = st.columns([2, 1])

with col1:
    st.header("🔍 Search for Businesses")
    
    # Location input
    st.subheader("📍 Your Location")
    
    location_method = st.radio(
        "How would you like to provide your location?",
        ["🧭 Manual Coordinates", "🌐 Browser Geolocation (JS)", "📍 City/Address Lookup"],
        horizontal=True
    )
    
    user_lat = user_lng = None
    
    if location_method == "🧭 Manual Coordinates":
        col_lat, col_lng = st.columns(2)
        with col_lat:
            user_lat = st.number_input(
                "Your Latitude", 
                min_value=-90.0, 
                max_value=90.0, 
                value=37.7749,  # Default to San Francisco
                format="%.6f"
            )
        with col_lng:
            user_lng = st.number_input(
                "Your Longitude", 
                min_value=-180.0, 
                max_value=180.0, 
                value=-122.4194,  # Default to San Francisco
                format="%.6f"
            )
    
    elif location_method == "🌐 Browser Geolocation (JS)":
        st.markdown("""
        <div class="location-input">
            <strong>📱 Browser Geolocation</strong><br>
            Click the button below to get your current location using your browser's geolocation API.
        </div>
        """, unsafe_allow_html=True)
        
        # JavaScript geolocation (simplified version)
        geolocation_js = """
        <script>
        function getLocation() {
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(function(position) {
                    document.getElementById("lat_result").innerHTML = position.coords.latitude;
                    document.getElementById("lng_result").innerHTML = position.coords.longitude;
                    window.parent.postMessage({
                        type: 'location', 
                        lat: position.coords.latitude, 
                        lng: position.coords.longitude
                    }, '*');
                });
            } else {
                alert("Geolocation is not supported by this browser.");
            }
        }
        </script>
        <button onclick="getLocation()" style="padding: 10px 20px; background: #007bff; color: white; border: none; border-radius: 5px;">
            🧭 Get My Location
        </button>
        <div style="margin-top: 10px;">
            <strong>Latitude:</strong> <span id="lat_result">Not detected</span><br>
            <strong>Longitude:</strong> <span id="lng_result">Not detected</span>
        </div>
        """
        
        st.components.v1.html(geolocation_js, height=150)
        
        # Manual fallback
        st.markdown("**Or enter manually:**")
        col_lat, col_lng = st.columns(2)
        with col_lat:
            user_lat = st.number_input("Latitude", value=None, format="%.6f", key="geo_lat")
        with col_lng:
            user_lng = st.number_input("Longitude", value=None, format="%.6f", key="geo_lng")
    
    elif location_method == "📍 City/Address Lookup":
        address = st.text_input(
            "Enter city or address", 
            placeholder="e.g., San Francisco, CA or Times Square, New York"
        )
        
        if address:
            st.info("🔄 Address geocoding would be implemented here using a service like Google Maps API")
            # For demo, provide some common city coordinates
            city_coords = {
                "san francisco": (37.7749, -122.4194),
                "new york": (40.7128, -74.0060),
                "los angeles": (34.0522, -118.2437),
                "chicago": (41.8781, -87.6298),
                "miami": (25.7617, -80.1918)
            }
            
            for city, coords in city_coords.items():
                if city in address.lower():
                    user_lat, user_lng = coords
                    st.success(f"📍 Found coordinates for {city.title()}: {user_lat}, {user_lng}")
                    break
    
    # Search query
    st.subheader("🔍 What are you looking for?")
    search_query = st.text_input(
        "",
        placeholder="e.g., coffee shops, restaurants, gas stations, pharmacies",
        help="Describe what type of business you're looking for"
    )
    
    # Search button
    search_button = st.button("🔍 Search Nearby Businesses", type="primary", use_container_width=True)
    
    # Search results
    if search_button and search_query and user_lat is not None and user_lng is not None:
        with st.spinner("🔄 Searching vectorized business data..."):
            results, search_method = search_businesses(search_query, user_lat, user_lng, max_distance)
        
        if results:
            # Show search method and success
            distance_text = f"within {max_distance}km" if max_distance else "sorted by distance"
            
            if search_method == "vectorized":
                st.success(f"✅ Found {len(results)} businesses using **vectorized AI search** {distance_text}")
                if max_distance is None:
                    st.info("🌍 **Unlimited search** - All businesses returned, ranked by AI similarity + distance")
                else:
                    st.info("🧠 Results are ranked by AI similarity to your query + distance proximity")
            elif search_method == "csv_only":
                st.success(f"✅ Found {len(results)} businesses using **CSV fallback** {distance_text}")
                if max_distance is None:
                    st.warning("⚠️ Vectorized search unavailable, using basic text matching for all businesses")
                else:
                    st.warning("⚠️ Vectorized search unavailable, using basic text matching")
            else:
                st.success(f"✅ Found {len(results)} businesses {distance_text}")
            
            for i, business in enumerate(results):
                # Prepare relevance display
                relevance_info = ""
                if "relevance" in business:
                    relevance_score = business["relevance"]
                    relevance_pct = int(relevance_score * 100)
                    relevance_info = f'<span class="category-badge">🧠 {relevance_pct}% relevant</span>'
                
                st.markdown(f"""
                <div class="search-result">
                    <h4>🏪 {business['business_name']}</h4>
                    <p><strong>👤 Owner:</strong> {business['name']}</p>
                    <p>
                        <span class="category-badge">{business['category']}</span>
                        <span class="distance-badge">📏 {business['distance']:.1f} km away</span>
                        {relevance_info}
                    </p>
                    <p><strong>📍 Location:</strong> {business['latitude']:.4f}, {business['longitude']:.4f}</p>
                    <p><strong>🏷️ Tags:</strong> {business['tags']}</p>
                </div>
                """, unsafe_allow_html=True)
        
        else:
            if search_method == "vectorized":
                if max_distance is None:
                    st.warning(f"😔 No businesses found for '{search_query}' in the entire vectorized database")
                    st.info("💡 The AI search found no relevant matches. Try different keywords or check if businesses are registered")
                else:
                    st.warning(f"😔 No businesses found for '{search_query}' in vectorized data within {max_distance}km")
                    st.info("💡 The AI search found no relevant matches. Try different keywords or expand your search radius")
            else:
                if max_distance is None:
                    st.warning(f"😔 No businesses found for '{search_query}' in the entire database")
                    st.info("💡 Try using different keywords or check if businesses are registered")
                else:
                    st.warning(f"😔 No businesses found for '{search_query}' within {max_distance}km of your location")
                    st.info("💡 Try expanding your search radius or using different keywords")
    
    elif search_button:
        if not search_query:
            st.error("❌ Please enter a search query")
        if user_lat is None or user_lng is None:
            st.error("❌ Please provide your location coordinates")

with col2:
    st.header("📋 Search Tips")
    
    st.markdown("""
    **🧠 Vectorized AI Search:**
    - Uses OpenAI embeddings for semantic understanding
    - Matches meaning, not just keywords
    - "coffee shop" also finds "cafe", "espresso bar"
    - Results ranked by AI relevance + distance
    
    **🎯 Search Examples:**
    - "coffee near me" → finds cafes, coffee shops
    - "italian food" → finds Italian restaurants
    - "car service" → finds auto repair, gas stations
    - "healthcare" → finds hospitals, clinics
    - "wifi workspace" → finds cafes with wifi
    
    **📍 Search Options:**
    - **🌍 Unlimited Search**: Returns ALL businesses, sorted by distance
    - **📏 Limited Radius**: Only businesses within specified distance
    - Use precise coordinates for best distance calculations
    - Browser geolocation works best on mobile
    
    **🔧 Search Methods:**
    - **Vectorized**: AI-powered semantic search (preferred)
    - **CSV Fallback**: Basic text matching (backup)
    - System automatically chooses best available method
    
    **💡 Pro Tip:**
    - Enable unlimited search to see all businesses ranked by proximity
    - Use limited radius when you only want nearby options
    """)
    
    if show_map:
        st.subheader("🗺️ Map View")
        st.markdown("""
        <div class="map-placeholder">
            <h3>🗺️ Interactive Map</h3>
            <p>Map integration would be implemented here using services like:</p>
            <ul style="list-style: none; padding: 0;">
                <li>📍 Google Maps API</li>
                <li>🗺️ Mapbox</li>
                <li>🌍 OpenStreetMap</li>
                <li>📱 Leaflet.js</li>
            </ul>
            <small>This would show your location and nearby businesses with markers</small>
        </div>
        """, unsafe_allow_html=True)
    
    # Quick location buttons
    st.subheader("⚡ Quick Locations")
    
    if st.button("🌉 San Francisco", use_container_width=True):
        st.session_state.quick_lat = 37.7749
        st.session_state.quick_lng = -122.4194
        st.rerun()
    
    if st.button("🗽 New York", use_container_width=True):
        st.session_state.quick_lat = 40.7128
        st.session_state.quick_lng = -74.0060
        st.rerun()
    
    if st.button("🏖️ Los Angeles", use_container_width=True):
        st.session_state.quick_lat = 34.0522
        st.session_state.quick_lng = -118.2437
        st.rerun()

# Handle quick location selection
if hasattr(st.session_state, 'quick_lat') and hasattr(st.session_state, 'quick_lng'):
    user_lat = st.session_state.quick_lat
    user_lng = st.session_state.quick_lng
    st.success(f"📍 Location set to: {user_lat}, {user_lng}")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 1rem;'>
    🗺️ Location-Based Search | Powered by Pathway RAG + Distance Calculation
</div>
""", unsafe_allow_html=True)
