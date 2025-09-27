import streamlit as st
import requests
import json
import time
from typing import Dict, Any

# Configuration
UPLOAD_API_URL = "http://rag-app:8001"
PATHWAY_API_URL = "http://rag-app:8000"

st.set_page_config(
    page_title="Business Registration", 
    page_icon="🏢", 
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
.success-box {
    padding: 1rem;
    border-radius: 0.5rem;
    background-color: #d4edda;
    border: 1px solid #c3e6cb;
    color: #155724;
    margin: 1rem 0;
}
.error-box {
    padding: 1rem;
    border-radius: 0.5rem;
    background-color: #f8d7da;
    border: 1px solid #f5c6cb;
    color: #721c24;
    margin: 1rem 0;
}
.info-box {
    padding: 1rem;
    border-radius: 0.5rem;
    background-color: #d1ecf1;
    border: 1px solid #bee5eb;
    color: #0c5460;
    margin: 1rem 0;
}
.metric-card {
    background-color: #f8f9fa;
    padding: 1rem;
    border-radius: 0.5rem;
    border: 1px solid #dee2e6;
    text-align: center;
}
</style>
""", unsafe_allow_html=True)

st.title("🏢 Business Registration System")
st.markdown("Register your business and add it to our location-based search index")

# Sidebar with system status
with st.sidebar:
    st.header("📊 System Status")
    
    # Check API status
    try:
        upload_status = requests.get(f"{UPLOAD_API_URL}/docs", timeout=2)
        st.success("✅ Upload API: Online")
    except:
        st.error("❌ Upload API: Offline")
    
    try:
        pathway_status = requests.post(f"{PATHWAY_API_URL}/v1/statistics", timeout=2)
        st.success("✅ Pathway API: Online")
        
        # Show document count
        try:
            docs_response = requests.post(f"{PATHWAY_API_URL}/v2/list_documents", timeout=5)
            if docs_response.status_code == 200:
                docs_data = docs_response.json()
                total_docs = len(docs_data)
                st.metric("📄 Total Documents", total_docs)
        except:
            pass
            
    except:
        st.error("❌ Pathway API: Offline")
    
    st.markdown("---")
    st.info("💡 **Tip:** Fill out all fields accurately for better search results")

# Main content
col1, col2 = st.columns([2, 1])

with col1:
    st.header("Register New Business")
    
    with st.form("business_form", clear_on_submit=True):
        # Business details
        name = st.text_input(
            "👤 Business Owner Name *", 
            placeholder="e.g., John Smith",
            help="Full name of the business owner"
        )
        
        business_name = st.text_input(
            "🏪 Business Name *", 
            placeholder="e.g., Smith's Coffee House",
            help="Official name of your business"
        )
        
        # Location
        st.subheader("📍 Location Details")
        col_lat, col_lng = st.columns(2)
        
        with col_lat:
            latitude = st.number_input(
                "Latitude *", 
                min_value=-90.0, 
                max_value=90.0, 
                value=None,
                format="%.6f",
                help="GPS latitude coordinate"
            )
        
        with col_lng:
            longitude = st.number_input(
                "Longitude *", 
                min_value=-180.0, 
                max_value=180.0, 
                value=None,
                format="%.6f",
                help="GPS longitude coordinate"
            )
        
        # Business category
        business_category = st.selectbox(
            "🏷️ Business Category *",
            options=[
                "Cafe", "Restaurant", "Bakery", "Bar", "Fast Food",
                "Grocery Store", "Pharmacy", "Gas Station", "Bank", "ATM",
                "Hospital", "Clinic", "Gym", "Spa", "Hotel",
                "Shopping Mall", "Clothing Store", "Electronics", "Bookstore",
                "Car Repair", "Beauty Salon", "Barbershop", "Laundry",
                "Real Estate", "Insurance", "Legal Services", "Accounting",
                "Education", "Daycare", "Veterinary", "Pet Store",
                "Hardware Store", "Garden Center", "Sports Store",
                "Other"
            ],
            help="Select the category that best describes your business"
        )
        
        # Business tags
        business_tags = st.text_input(
            "🏷️ Business Tags", 
            placeholder="e.g., coffee,wifi,outdoor-seating,takeout",
            help="Comma-separated tags that describe your business features and services"
        )
        
        # Submit button
        submitted = st.form_submit_button(
            "📝 Register Business", 
            type="primary",
            use_container_width=True
        )
        
        if submitted:
            # Validation
            errors = []
            if not name.strip():
                errors.append("Business Owner Name is required")
            if not business_name.strip():
                errors.append("Business Name is required")
            if latitude is None:
                errors.append("Latitude is required")
            if longitude is None:
                errors.append("Longitude is required")
            if not business_category:
                errors.append("Business Category is required")
            
            if errors:
                st.error("❌ Please fix the following errors:")
                for error in errors:
                    st.error(f"• {error}")
            else:
                # Prepare data
                lat_long = f"{latitude},{longitude}"
                
                business_data = {
                    "name": name.strip(),
                    "business_name": business_name.strip(),
                    "lat_long": lat_long,
                    "business_category": business_category,
                    "business_tags": business_tags.strip() if business_tags else ""
                }
                
                # Submit to API
                try:
                    with st.spinner("🔄 Registering business..."):
                        response = requests.post(
                            f"{UPLOAD_API_URL}/append-csv",
                            json=business_data,
                            timeout=10
                        )
                    
                    if response.status_code == 200:
                        result = response.json()
                        st.success("✅ Business registered successfully!")
                        
                        # Show success details
                        st.markdown(
                            f"""
                            <div class="success-box">
                                <strong>Registration Complete!</strong><br>
                                📍 <strong>{business_name}</strong> has been added to the database.<br>
                                📄 Data saved to: {result.get('csv_path', 'data.csv')}<br>
                                🔄 The system will automatically reindex this data for search.
                            </div>
                            """, 
                            unsafe_allow_html=True
                        )
                        
                        # Show indexing status
                        st.info("⏳ **Indexing Status:** Your business data is being processed and will be available for search within 1-2 minutes.")
                        
                    else:
                        st.error(f"❌ Registration failed: {response.status_code}")
                        if response.text:
                            st.error(response.text)
                            
                except requests.exceptions.Timeout:
                    st.error("❌ Request timed out. Please try again.")
                except requests.exceptions.ConnectionError:
                    st.error("❌ Cannot connect to the server. Please check if the upload API is running.")
                except Exception as e:
                    st.error(f"❌ An error occurred: {str(e)}")

with col2:
    st.header("📋 Recent Registrations")
    
    # Show recent CSV data
    try:
        # Try to get document list to show recent additions
        docs_response = requests.post(f"{PATHWAY_API_URL}/v2/list_documents", timeout=5)
        if docs_response.status_code == 200:
            docs_data = docs_response.json()
            csv_docs = [doc for doc in docs_data if 'data.csv' in doc.get('path', '')]
            
            if csv_docs:
                st.success(f"📄 Found {len(csv_docs)} CSV document(s) in the index")
                
                # Show indexing status
                for doc in csv_docs[:3]:  # Show first 3
                    status = doc.get('_indexing_status', 'UNKNOWN')
                    path = doc.get('path', 'Unknown path')
                    
                    if status == 'INDEXED':
                        st.success(f"✅ {path} - Indexed")
                    elif status == 'INGESTED':
                        st.warning(f"⏳ {path} - Processing...")
                    else:
                        st.info(f"📄 {path} - {status}")
            else:
                st.info("📄 No CSV documents found yet")
        else:
            st.warning("⚠️ Cannot fetch document status")
            
    except Exception as e:
        st.warning("⚠️ Cannot check document status")
    
    st.markdown("---")
    
    # Quick stats
    st.subheader("📊 Quick Actions")
    
    if st.button("🔄 Refresh Status", use_container_width=True):
        st.rerun()
    
    if st.button("📍 Test Location Search", use_container_width=True):
        st.switch_page("location_search.py")
    
    # Sample coordinates helper
    st.markdown("---")
    st.subheader("📍 Sample Coordinates")
    st.markdown("""
    **Popular Cities:**
    - New York: `40.7128, -74.0060`
    - Los Angeles: `34.0522, -118.2437`
    - Chicago: `41.8781, -87.6298`
    - San Francisco: `37.7749, -122.4194`
    - Miami: `25.7617, -80.1918`
    """)

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666; padding: 1rem;'>
        🏢 Business Registration System | Powered by Pathway RAG
    </div>
    """, 
    unsafe_allow_html=True
)
