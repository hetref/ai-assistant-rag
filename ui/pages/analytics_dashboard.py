import streamlit as st
import requests
import json
from datetime import datetime
import pandas as pd

# Configuration
UPLOAD_API_URL = "http://rag-app:8001"

st.set_page_config(
    page_title="Analytics Dashboard", 
    page_icon="📊", 
    layout="wide"
)

st.markdown("""
<style>
.metric-card {
    background-color: #f8f9fa;
    padding: 1rem;
    border-radius: 0.5rem;
    border-left: 4px solid #007bff;
    margin: 0.5rem 0;
}
.analytics-header {
    text-align: center;
    padding: 1rem 0;
    background: linear-gradient(90deg, #28a745 0%, #20c997 100%);
    color: white;
    border-radius: 10px;
    margin-bottom: 2rem;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="analytics-header">
    <h1>📊 Collaborative Filtering Analytics</h1>
    <p>Monitor recommendation performance and user engagement</p>
</div>
""", unsafe_allow_html=True)

def get_cf_analytics():
    """Get collaborative filtering analytics data."""
    try:
        response = requests.get(f"{UPLOAD_API_URL}/analytics/cf-performance", timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            return None
    except Exception as e:
        st.error(f"Failed to fetch analytics: {e}")
        return None

def get_trending_searches():
    """Get trending searches."""
    try:
        response = requests.get(f"{UPLOAD_API_URL}/recommendations/trending-searches?limit=20", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get("ok"):
                return data.get("trending_searches", [])
        return []
    except Exception as e:
        return []

# Main analytics display
col1, col2 = st.columns([2, 1])

with col1:
    st.header("📈 System Performance")
    
    # Get analytics data
    analytics_data = get_cf_analytics()
    
    if analytics_data and analytics_data.get("ok"):
        analytics = analytics_data.get("analytics", {})
        
        # Display key metrics
        metric_col1, metric_col2, metric_col3 = st.columns(3)
        
        with metric_col1:
            st.metric(
                "Total Search Queries", 
                analytics.get("total_search_queries", 0),
                delta=None
            )
        
        with metric_col2:
            st.metric(
                "Unique Search Terms", 
                analytics.get("unique_search_terms", 0),
                delta=None
            )
        
        with metric_col3:
            st.metric(
                "Cache Status", 
                analytics.get("cache_status", "unknown").title(),
                delta=None
            )
        
        # Display trending searches in a chart
        trending = analytics.get("trending_searches", [])
        if trending:
            st.subheader("🔥 Top Trending Searches")
            
            # Convert to DataFrame for better visualization
            trending_df = pd.DataFrame(trending, columns=["Query", "Count"])
            
            # Create bar chart
            st.bar_chart(trending_df.set_index("Query")["Count"])
            
            # Also show as table
            st.subheader("📋 Trending Searches Details")
            st.dataframe(trending_df, use_container_width=True)
        
    elif analytics_data and not analytics_data.get("ok"):
        st.error(f"Analytics API error: {analytics_data.get('error', 'Unknown error')}")
    else:
        st.warning("⚠️ Analytics data unavailable - Collaborative filtering may not be running")
        st.info("Make sure Redis is running and collaborative filtering is enabled")

with col2:
    st.header("🔧 System Status")
    
    # Check system health
    try:
        health_response = requests.get(f"{UPLOAD_API_URL}/health", timeout=5)
        if health_response.status_code == 200:
            health_data = health_response.json()
            
            # Redis status
            redis_status = health_data.get("redis_status", "unknown")
            if redis_status == "online":
                st.success("✅ Redis: Online")
            else:
                st.error(f"❌ Redis: {redis_status}")
            
            # Collaborative filtering status
            cf_available = health_data.get("collaborative_filtering", False)
            if cf_available:
                st.success("✅ Collaborative Filtering: Available")
            else:
                st.error("❌ Collaborative Filtering: Not Available")
            
            # Pathway status
            pathway_status = health_data.get("pathway_status", "unknown")
            if pathway_status == "online":
                st.success("✅ Pathway RAG: Online")
            else:
                st.warning(f"⚠️ Pathway RAG: {pathway_status}")
                
        else:
            st.error("❌ Cannot connect to API")
    except Exception as e:
        st.error(f"❌ Health check failed: {e}")
    
    st.markdown("---")
    
    # Manual trending searches section
    st.subheader("🔍 Live Trending Searches")
    
    trending_searches = get_trending_searches()
    if trending_searches:
        for trend in trending_searches[:10]:
            st.markdown(f"""
            <div class="metric-card">
                <strong>{trend['query']}</strong><br>
                <small>🔍 {trend['search_count']} searches</small>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No trending searches available")

# Footer with refresh button
st.markdown("---")
col1, col2, col3 = st.columns([1, 1, 1])

with col2:
    if st.button("🔄 Refresh Analytics", type="primary", use_container_width=True):
        st.rerun()

st.markdown(f"""
<div style='text-align: center; color: #666; padding: 1rem;'>
    📊 Analytics Dashboard | Last updated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
</div>
""", unsafe_allow_html=True)

# Technical Details Section
with st.expander("🔧 Technical Details"):
    st.markdown("""
    ### Collaborative Filtering Implementation
    
    **🧠 User-Based Collaborative Filtering:**
    - Finds users with similar search/interaction patterns
    - Uses cosine similarity to compare user preferences
    - Recommends businesses liked by similar users
    
    **📊 Implicit Rating System:**
    - Search queries: 1.0 points
    - Business views: 2.0 points  
    - Business clicks: 3.0 points
    - Bookmarks: 5.0 points
    - Bonus for dwell time (view duration)
    
    **💾 Data Storage:**
    - Redis for fast in-memory operations
    - User interactions stored as sorted sets
    - Business interactions tracked separately
    - 30-day data retention policy
    
    **🔍 Search Enhancement:**
    - Vectorized AI search (primary)
    - Collaborative recommendations (secondary)
    - Popular/trending suggestions
    - "People also searched for" feature
    
    **📈 Analytics Tracking:**
    - Real-time interaction monitoring
    - Search query popularity
    - User engagement metrics
    - Recommendation effectiveness
    """)

# Debugging section for developers
if st.checkbox("🐛 Show Debug Info"):
    st.subheader("Debug Information")
    
    if analytics_data:
        st.json(analytics_data)
    
    st.code(f"""
API Endpoints Used:
- Health: GET {UPLOAD_API_URL}/health
- Analytics: GET {UPLOAD_API_URL}/analytics/cf-performance  
- Trending: GET {UPLOAD_API_URL}/recommendations/trending-searches
- Track Interaction: POST {UPLOAD_API_URL}/interactions/track
- Get Recommendations: POST {UPLOAD_API_URL}/recommendations
    """)
