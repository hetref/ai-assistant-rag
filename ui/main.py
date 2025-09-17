import streamlit as st

st.set_page_config(
    page_title="Business Location System", 
    page_icon="🏢", 
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
.main-header {
    text-align: center;
    padding: 2rem 0;
    background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    color: white;
    border-radius: 10px;
    margin-bottom: 2rem;
}
.feature-card {
    background-color: #f8f9fa;
    padding: 1.5rem;
    border-radius: 10px;
    border: 1px solid #dee2e6;
    text-align: center;
    height: 200px;
    display: flex;
    flex-direction: column;
    justify-content: center;
}
.feature-card:hover {
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    transform: translateY(-2px);
    transition: all 0.3s ease;
}
.nav-button {
    width: 100%;
    height: 60px;
    font-size: 18px;
    font-weight: bold;
    margin: 10px 0;
}
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="main-header">
    <h1>🏢 Business Location System</h1>
    <p>Powered by Pathway RAG + Location Intelligence</p>
</div>
""", unsafe_allow_html=True)

# Main navigation
st.markdown("## 🚀 Choose Your Action")

col1, col2, col3 = st.columns([1, 1, 1])

with col1:
    st.markdown("""
    <div class="feature-card">
        <h3>🏪 Register Business</h3>
        <p>Add your business to our location-based search database</p>
        <ul style="text-align: left; padding-left: 20px;">
            <li>✅ Easy registration form</li>
            <li>📍 GPS coordinate validation</li>
            <li>🔄 Real-time indexing status</li>
            <li>📊 System health monitoring</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("🏪 Go to Business Registration", key="register", type="primary", use_container_width=True):
        st.switch_page("pages/business_registration.py")

with col2:
    st.markdown("""
    <div class="feature-card">
        <h3>🗺️ Location Search</h3>
        <p>Find businesses near any location with smart filtering</p>
        <ul style="text-align: left; padding-left: 20px;">
            <li>📍 GPS-based proximity search</li>
            <li>🔍 Category and tag filtering</li>
            <li>📏 Configurable search radius</li>
            <li>📱 Mobile geolocation support</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("🗺️ Go to Location Search", key="search", type="primary", use_container_width=True):
        st.switch_page("pages/location_search.py")

with col3:
    st.markdown("""
    <div class="feature-card">
        <h3>🤖 Original RAG Chat</h3>
        <p>Traditional document Q&A interface for general queries</p>
        <ul style="text-align: left; padding-left: 20px;">
            <li>💬 Natural language queries</li>
            <li>📄 Document context display</li>
            <li>🔄 Real-time document status</li>
            <li>📚 Multi-document search</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("🤖 Go to RAG Chat", key="chat", type="primary", use_container_width=True):
        st.switch_page("ui.py")

# System overview
st.markdown("---")
st.markdown("## 🏗️ System Architecture")

col1, col2 = st.columns([1, 1])

with col1:
    st.markdown("""
    ### 🔧 Backend Services
    - **Pathway RAG API** (Port 8000)
      - Document indexing and retrieval
      - AI-powered question answering
      - Real-time data processing
    
    - **Upload API** (Port 8001)
      - Business data management
      - Location-based search
      - CSV file operations
    """)

with col2:
    st.markdown("""
    ### 📊 Key Features
    - **Real-time Indexing**: Data is automatically re-indexed when new businesses are added
    - **Location Intelligence**: Haversine distance calculations for proximity search
    - **Smart Filtering**: Category detection and tag-based filtering
    - **Scalable Architecture**: Separate services for different functionalities
    """)

# Quick status check
st.markdown("---")
st.markdown("## 📊 System Status")

import requests

col1, col2, col3 = st.columns(3)

with col1:
    try:
        response = requests.get("http://localhost:8001/health", timeout=2)
        if response.status_code == 200:
            data = response.json()
            st.success("✅ Upload API: Online")
            st.info(f"📄 CSV exists: {data.get('csv_exists', False)}")
        else:
            st.error("❌ Upload API: Error")
    except:
        st.error("❌ Upload API: Offline")

with col2:
    try:
        response = requests.post("http://localhost:8000/v1/statistics", timeout=2)
        if response.status_code == 200:
            st.success("✅ Pathway API: Online")
        else:
            st.error("❌ Pathway API: Error")
    except:
        st.error("❌ Pathway API: Offline")

with col3:
    try:
        docs_response = requests.post("http://localhost:8000/v2/list_documents", timeout=3)
        if docs_response.status_code == 200:
            docs = docs_response.json()
            st.metric("📄 Documents", len(docs))
        else:
            st.warning("⚠️ Cannot fetch docs")
    except:
        st.warning("⚠️ Docs unavailable")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 2rem;'>
    <h4>🚀 Getting Started</h4>
    <p>
        1. <strong>Register businesses</strong> using the Business Registration page<br>
        2. <strong>Search for businesses</strong> using the Location Search page<br>
        3. <strong>Ask questions</strong> using the RAG Chat interface
    </p>
    <hr>
    <p><em>Business Location System | Built with Streamlit + FastAPI + Pathway</em></p>
</div>
""", unsafe_allow_html=True)
