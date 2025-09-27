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

def search_businesses(query: str, user_lat: float, user_lng: float, max_distance: Optional[float] = 10.0, user_session_id: Optional[str] = None) -> tuple[List[Dict], List[Dict], Dict, str]:
    """Search for businesses using vectorized data from Pathway with contextual recommendations."""
    try:
        # Use the enhanced contextual search endpoint
        payload = {
            "user_lat": user_lat,
            "user_lng": user_lng,
            "query": query,
            "limit": 100,  # Increased limit for unlimited search
            "include_recommendations": True
        }
        
        if user_session_id:
            payload["user_session_id"] = user_session_id
        
        # Only add distance constraint if specified
        if max_distance is not None:
            payload["max_distance_km"] = max_distance
        else:
            # Use a very large radius for "unlimited" search
            payload["max_distance_km"] = 20000.0  # 20,000 km (essentially unlimited on Earth)
        
        # Try contextual search first
        contextual_available = False
        try:
            response = requests.post(
                f"{UPLOAD_API_URL}/search-businesses/contextual",
                json=payload,
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("ok", False):
                    contextual_available = True
        except Exception:
            contextual_available = False
        
        # Fallback to regular search if contextual not available
        if not contextual_available:
            response = requests.post(
                f"{UPLOAD_API_URL}/search-businesses",
                json=payload,
                timeout=15
            )
        
        if response.status_code != 200:
            st.error(f"API Error: {response.status_code}")
            return [], [], {}, "error"
        
        data = response.json()
        
        if not data.get("ok", False):
            st.error(f"Search failed: {data.get('error', 'Unknown error')}")
            return [], [], {}, "error"
        
        results = data.get("results", [])
        recommendations = data.get("contextual_recommendations", data.get("recommendations", []))
        context_info = data.get("context", {})
        search_method = data.get("search_method", "unknown")
        
        # Store user session info for tracking
        if "user_id" in data and "session_id" in data:
            st.session_state.cf_user_id = data["user_id"]
            st.session_state.cf_session_id = data["session_id"]
        
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
                "distance": business.get("distance_km", 0),
                "business_id": business.get("business_id", business.get("business_name", ""))
            }
            
            # Add contextual search specific fields
            if "contextual_score" in business:
                result["contextual_score"] = business["contextual_score"]
                result["applied_factors"] = business.get("applied_factors", [])
            
            if "vector_score" in business:
                result["vector_score"] = business["vector_score"]
                result["relevance"] = 1.0 / (1.0 + business["vector_score"])  # Convert to 0-1 scale
            
            formatted_results.append(result)
        
        return formatted_results, recommendations, context_info, search_method
        
    except requests.exceptions.Timeout:
        st.error("❌ Search timed out. Please try again.")
        return [], [], {}, "timeout"
    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot connect to search API. Please check if the service is running.")
        return [], [], {}, "connection_error"
    except Exception as e:
        st.error(f"❌ Search error: {str(e)}")
        return [], [], {}, "error"


def track_business_interaction(business_id: str, business_name: str, interaction_type: str, query: Optional[str] = None, category: Optional[str] = None, tags: Optional[List[str]] = None, user_lat: Optional[float] = None, user_lng: Optional[float] = None):
    """Track user interaction with a business for collaborative filtering."""
    try:
        payload = {
            "business_id": business_id,
            "business_name": business_name,
            "interaction_type": interaction_type,  # 'view', 'click', 'bookmark'
            "query": query,
            "category": category,
            "tags": tags,
            "user_lat": user_lat,
            "user_lng": user_lng
        }
        
        response = requests.post(
            f"{UPLOAD_API_URL}/interactions/track",
            json=payload,
            timeout=5
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            st.warning(f"Failed to track interaction: {response.status_code}")
            return None
            
    except Exception as e:
        # Silently fail for tracking - don't disrupt user experience
        return None


def get_trending_searches(limit: int = 10) -> List[Dict]:
    """Get trending search queries."""
    try:
        response = requests.get(
            f"{UPLOAD_API_URL}/recommendations/trending-searches?limit={limit}",
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("ok"):
                return data.get("trending_searches", [])
        
        return []
        
    except Exception as e:
        return []


def get_people_also_searched(query: str, limit: int = 5) -> List[str]:
    """Get 'People also searched for' suggestions."""
    try:
        response = requests.get(
            f"{UPLOAD_API_URL}/recommendations/people-also-searched",
            params={"query": query, "limit": limit},
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("ok"):
                return data.get("suggestions", [])
        
        return []
        
    except Exception as e:
        return []


def get_weather_info(user_lat: float, user_lng: float) -> Optional[Dict]:
    """Get current weather information for location."""
    try:
        response = requests.get(
            f"{UPLOAD_API_URL}/weather/current",
            params={"user_lat": user_lat, "user_lng": user_lng},
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("ok"):
                return data
        
        return None
        
    except Exception as e:
        return None


def display_weather_card(weather_data: Dict):
    """Display weather information in a nice card format."""
    if not weather_data or not weather_data.get("ok"):
        return
    
    weather = weather_data.get("weather", {})
    suggestions = weather_data.get("business_suggestions", {})
    
    # Weather emoji mapping
    condition_emojis = {
        "clear": "☀️",
        "sunny": "🌞", 
        "partly_cloudy": "⛅",
        "cloudy": "☁️",
        "overcast": "☁️",
        "light_rain": "🌦️",
        "rain": "🌧️",
        "heavy_rain": "🌨️",
        "thunderstorm": "⛈️",
        "snow": "❄️",
        "fog": "🌫️",
        "windy": "💨",
        "unknown": "🌤️"
    }
    
    condition = weather.get("condition", "unknown")
    emoji = condition_emojis.get(condition, "🌤️")
    temp = weather.get("temperature_celsius", 0)
    description = weather.get("description", "Unknown")
    
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #74b9ff, #0984e3); color: white; padding: 1rem; border-radius: 10px; margin: 1rem 0;">
        <div style="display: flex; align-items: center; justify-content: space-between;">
            <div>
                <h3 style="margin: 0; color: white;">{emoji} {description.title()}</h3>
                <p style="margin: 5px 0; font-size: 1.2em;"><strong>{temp:.0f}°C</strong> (feels like {weather.get('feels_like_celsius', temp):.0f}°C)</p>
                <p style="margin: 0; font-size: 0.9em;">Humidity: {weather.get('humidity', 0):.0f}% | Wind: {weather.get('wind_speed_kmh', 0):.0f} km/h</p>
                <p style="margin: 5px 0 0 0; font-size: 0.7em; opacity: 0.8;">🤖 Simulated weather data based on location & time</p>
            </div>
            <div style="font-size: 3em;">{emoji}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Weather-based business suggestions
    preferred = suggestions.get("preferred", [])
    avoid = suggestions.get("avoid", [])
    
    if preferred or avoid:
        st.markdown("**🌤️ Weather-Based Suggestions:**")
        
        if preferred:
            preferred_text = ", ".join(preferred[:5])  # Show first 5
            st.success(f"✅ **Recommended:** {preferred_text}")
        
        if avoid:
            avoid_text = ", ".join(avoid[:3])  # Show first 3
            st.warning(f"❌ **Consider avoiding:** {avoid_text}")


def display_context_info(context_info: Dict):
    """Display contextual information about the recommendations."""
    if not context_info:
        return
    
    time_of_day = context_info.get("time_of_day", "").replace("_", " ").title()
    factors_applied = context_info.get("factors_applied", [])
    summary = context_info.get("summary", "")
    
    if time_of_day or factors_applied or summary:
        st.markdown("### 🧠 Smart Context")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            if summary:
                st.info(f"📍 **Current Context:** {summary}")
        
        with col2:
            if factors_applied:
                st.markdown("**🎯 Applied Factors:**")
                for factor in factors_applied[:3]:  # Show first 3
                    st.write(f"• {factor}")
                    
                if len(factors_applied) > 3:
                    st.write(f"• ... and {len(factors_applied) - 3} more")


def display_contextual_business_card(business: Dict, search_query: str, user_lat: float, user_lng: float):
    """Display a business card with contextual information."""
    # Prepare contextual information
    contextual_score = business.get("contextual_score", 1.0)
    applied_factors = business.get("applied_factors", [])
    relevance_info = ""
    
    # Show contextual boost if significant
    if contextual_score > 1.1:
        boost_pct = int((contextual_score - 1.0) * 100)
        relevance_info = f'<span class="category-badge" style="background: #28a745;">🚀 {boost_pct}% boosted</span>'
    elif contextual_score < 0.9:
        penalty_pct = int((1.0 - contextual_score) * 100)
        relevance_info = f'<span class="category-badge" style="background: #dc3545;">⬇️ {penalty_pct}% reduced</span>'
    
    # Regular relevance info
    if "relevance" in business:
        relevance_score = business["relevance"]
        relevance_pct = int(relevance_score * 100)
        if not relevance_info:  # Only show if no contextual info
            relevance_info = f'<span class="category-badge">🧠 {relevance_pct}% relevant</span>'
    
    business_id = business.get('business_id', business['business_name'])
    view_key = f"view_{business_id}_{hash(search_query) % 1000}"
    bookmark_key = f"bookmark_{business_id}_{hash(search_query) % 1000}"
    
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
    
    # Show contextual factors if available
    if applied_factors:
        with st.expander(f"🎯 Why this business is recommended", expanded=False):
            st.markdown("**Contextual factors applied:**")
            for factor in applied_factors:
                st.write(f"• {factor}")
    
    # Add interaction buttons
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        if st.button("👁️ View Details", key=view_key):
            track_business_interaction(
                business_id=business_id,
                business_name=business['business_name'],
                interaction_type='click',
                query=search_query,
                category=business.get('category'),
                tags=business.get('tags', '').split(',') if business.get('tags') else None,
                user_lat=user_lat,
                user_lng=user_lng
            )
            st.success(f"📍 Viewing {business['business_name']}")
    
    with col2:
        if st.button("🔖 Bookmark", key=bookmark_key):
            track_business_interaction(
                business_id=business_id,
                business_name=business['business_name'],
                interaction_type='bookmark',
                query=search_query,
                category=business.get('category'),
                tags=business.get('tags', '').split(',') if business.get('tags') else None,
                user_lat=user_lat,
                user_lng=user_lng
            )
            st.success(f"🔖 Bookmarked {business['business_name']}")

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
    
    # Handle clicked suggestions or trending searches
    default_query = ""
    if 'suggestion_clicked' in st.session_state:
        default_query = st.session_state.suggestion_clicked
        del st.session_state.suggestion_clicked
    elif 'trending_clicked' in st.session_state:
        default_query = st.session_state.trending_clicked
        del st.session_state.trending_clicked
    
    search_query = st.text_input(
        "",
        value=default_query,
        placeholder="e.g., coffee shops, restaurants, gas stations, pharmacies",
        help="Describe what type of business you're looking for"
    )
    
    # Search button
    search_button = st.button("🔍 Search Nearby Businesses", type="primary", use_container_width=True)
    
    # Search results
    if search_button and search_query and user_lat is not None and user_lng is not None:
        # Get weather information first
        weather_info = get_weather_info(user_lat, user_lng)
        if weather_info:
            display_weather_card(weather_info)
        
        # Get session ID for tracking
        session_id = st.session_state.get('cf_session_id')
        
        with st.spinner("🔄 Searching with smart contextual recommendations..."):
            results, recommendations, context_info, search_method = search_businesses(search_query, user_lat, user_lng, max_distance, session_id)
        
        # Display context information
        if context_info:
            display_context_info(context_info)
        
        if results:
            # Show search method and success
            distance_text = f"within {max_distance}km" if max_distance else "sorted by distance"
            
            if search_method == "vectorized":
                st.success(f"✅ Found {len(results)} businesses using **smart contextual search** {distance_text}")
                if max_distance is None:
                    st.info("🌍 **Unlimited search** - All businesses returned, ranked by AI similarity + context + distance")
                else:
                    st.info("🧠 Results ranked by AI similarity + contextual factors + distance proximity")
            elif search_method == "csv_only":
                st.success(f"✅ Found {len(results)} businesses using **CSV fallback** {distance_text}")
                if max_distance is None:
                    st.warning("⚠️ Contextual search unavailable, using basic text matching for all businesses")
                else:
                    st.warning("⚠️ Contextual search unavailable, using basic text matching")
            else:
                st.success(f"✅ Found {len(results)} businesses {distance_text}")
            
            # Show recommendations if available
            if recommendations:
                st.markdown("### 🤖 Contextual Recommendations")
                st.info("Based on time, weather, and your search patterns:")
                
                rec_cols = st.columns(min(len(recommendations), 3))
                for idx, rec in enumerate(recommendations[:3]):
                    with rec_cols[idx % 3]:
                        # Get contextual score info
                        contextual_score = rec.get('contextual_score', 1.0)
                        score_text = ""
                        if contextual_score > 1.1:
                            score_text = f"🚀 {int((contextual_score-1)*100)}% boost"
                        
                        st.markdown(f"""
                        <div style="background: #f0f8ff; padding: 10px; border-radius: 5px; margin: 5px 0; border-left: 4px solid #007bff;">
                            <strong>🏪 {rec.get('business_name', 'Unknown')}</strong><br>
                            <small>📂 {rec.get('category', '')}</small><br>
                            <small>⭐ Score: {rec.get('recommendation_score', rec.get('contextual_score', 0)):.2f}</small><br>
                            {f"<small style='color: #28a745;'>{score_text}</small>" if score_text else ""}
                        </div>
                        """, unsafe_allow_html=True)
            
            # Display main search results with contextual information
            for i, business in enumerate(results):
                # Track business view interaction
                if 'cf_session_id' in st.session_state:
                    track_business_interaction(
                        business_id=business.get('business_id', business['business_name']),
                        business_name=business['business_name'],
                        interaction_type='view',
                        query=search_query,
                        category=business.get('category'),
                        tags=business.get('tags', '').split(',') if business.get('tags') else None,
                        user_lat=user_lat,
                        user_lng=user_lng
                    )
                
                # Use contextual business card display
                display_contextual_business_card(business, search_query, user_lat, user_lng)
            
            # Show "People also searched for" suggestions
            if search_query:
                people_also_searched = get_people_also_searched(search_query, limit=5)
                if people_also_searched:
                    st.markdown("### 👥 People Also Searched For")
                    cols = st.columns(len(people_also_searched))
                    for idx, suggestion in enumerate(people_also_searched):
                        with cols[idx]:
                            if st.button(f"🔍 {suggestion}", key=f"suggestion_{idx}"):
                                # Track click and update search query
                                st.session_state.suggestion_clicked = suggestion
                                st.rerun()
        
        else:
            if search_method == "vectorized":
                if max_distance is None:
                    st.warning(f"😔 No businesses found for '{search_query}' in the entire contextual database")
                    st.info("💡 The smart search found no relevant matches. Try different keywords or check if businesses are registered")
                else:
                    st.warning(f"😔 No businesses found for '{search_query}' in contextual data within {max_distance}km")
                    st.info("💡 The smart search found no relevant matches. Try different keywords or expand your search radius")
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
    
    # Add trending searches section
    st.subheader("🔥 Trending Searches")
    trending_searches = get_trending_searches(limit=8)
    if trending_searches:
        for trend in trending_searches:
            if st.button(f"🔍 {trend['query']} ({trend['search_count']})", key=f"trending_{trend['query']}", use_container_width=True):
                st.session_state.trending_clicked = trend['query']
                st.rerun()
    else:
        st.info("No trending searches available yet")
    
    st.markdown("---")
    
    st.markdown("""
    **🧠 Smart Contextual Search:**
    - Uses OpenAI embeddings + time/weather context
    - Adapts suggestions to current conditions
    - "coffee shop" → boosted in morning/cold weather  
    - "restaurant" → boosted during meal times
    - Results ranked by AI relevance + context + distance
    
    **🌤️ Weather-Aware Recommendations:**
    - ☀️ Sunny: Outdoor dining, parks, ice cream
    - 🌧️ Rainy: Indoor venues, shopping malls  
    - ❄️ Cold: Coffee shops, warm food, heated places
    - 🌡️ Hot: Air-conditioned venues, cold drinks
    
    **🕒 Time-Based Intelligence:**
    - **Morning (6-11)**: Coffee shops, breakfast, gyms
    - **Lunch (12-14)**: Restaurants, fast food, cafes
    - **Afternoon (14-17)**: Shopping, services, coffee
    - **Evening (17-21)**: Dinner, entertainment, bars
    - **Night (21+)**: Late-night food, 24hr services
    
    **🤖 Collaborative Filtering:**
    - Learns from user interactions
    - Shows "Recommended for you" businesses
    - "People also searched for" suggestions
    - Tracks views, clicks, and bookmarks
    
    **🎯 Smart Examples:**
    - "lunch" at 12pm → restaurants boosted
    - "coffee" on rainy day → indoor cafes prioritized
    - "dinner" + cold weather → warm food highlighted
    - Friday evening → bars and entertainment boosted
    
    **📍 Search Options:**
    - **🌍 Unlimited Search**: ALL businesses, context-ranked
    - **📏 Limited Radius**: Nearby + contextually relevant
    - Use precise coordinates for best results
    - Weather and time automatically detected
    
    **🔧 Search Methods:**
    - **Contextual**: AI + time + weather + history (best)
    - **Vectorized**: AI-powered semantic search 
    - **CSV Fallback**: Basic text matching (backup)
    
    **💡 Pro Tips:**
    - Search is automatically optimized for current time/weather
    - Context factors shown in expandable sections
    - Bookmarking improves future recommendations
    - Weather data refreshed every 15 minutes
    """)
    
    if show_map:
        st.subheader("🗺️ Map View")
        st.markdown("""
        <div class="map-placeholder">
            <h3>🗺️ Interactive Map</h3>
            <p>Map integration would show:</p>
            <ul style="list-style: none; padding: 0;">
                <li>📍 Your current location</li>
                <li>🏪 Contextually ranked businesses</li>
                <li>�️ Weather-aware markers</li>
                <li>⏰ Time-based highlights</li>
                <li>🎯 Smart routing suggestions</li>
            </ul>
            <small>Integrated with contextual recommendation engine</small>
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
