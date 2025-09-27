# Business Location RAG System

A real-time business registration and location-based search system powered by [Pathway](https://github.com/pathwaycom/pathway) RAG (Retrieval-Augmented Generation) with AI-powered vectorized search and intelligent contextual recommendations.

## 🌟 Overview

This system combines the power of Pathway's real-time document indexing with location-based business search and advanced contextual intelligence, providing:

- **🏢 Business Registration**: Register businesses with location data and automatic indexing
- **🗺️ Location-Based Search**: Find businesses using GPS coordinates with distance filtering
- **🤖 AI-Powered Search**: Semantic search using OpenAI embeddings for intelligent matching
- **🌤️ Contextual Recommendations**: Smart suggestions based on time of day, weather, and user history
- **⏰ Time Intelligence**: Time-aware recommendations (breakfast spots in morning, bars in evening)
- **🌡️ Weather Simulation**: Realistic weather patterns without requiring API keys
- **👤 User History Context**: Personalized recommendations based on interaction patterns
- **🔄 Collaborative Filtering**: Find businesses similar users enjoyed
- **📱 Modern UI**: Enhanced Streamlit interface with contextual features and weather cards
- **⚡ Real-Time Updates**: Automatic document reindexing when new businesses are added

## 🏗️ Architecture

### Core Components

1. **Pathway RAG Server** (Port 8000): Document indexing and vector search
2. **FastAPI Upload Server** (Port 8001): Business registration, location search, and contextual recommendations
3. **Streamlit UI** (Port 8501): Enhanced user interface with contextual features and weather display
4. **Redis Cache** (Port 6379): Collaborative filtering data and user interaction tracking
5. **OpenAI Integration**: Embeddings and LLM for semantic understanding
6. **Weather Simulation Engine**: No-API-key weather system using realistic patterns
7. **Contextual Intelligence**: Time-based and weather-aware recommendation engine

### Data Flow

```
Business Registration → CSV Storage → Pathway Indexing → Vector Search → 
Location Filtering → Contextual Enhancement → Weather & Time Intelligence → 
Collaborative Filtering → Personalized Results
```

### Contextual Intelligence Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Time Service   │    │ Weather Service │    │ User History    │
│                 │    │                 │    │                 │
│ - Morning/Night │    │ - Climate Zones │    │ - Interactions  │
│ - Business Hours│    │ - Seasonal Data │    │ - Preferences   │
│ - Day/Weekend   │    │ - Temperature   │    │ - Categories    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │ Contextual      │
                    │ Recommendation  │
                    │ Engine          │
                    │                 │
                    │ - Factors Calc  │
                    │ - Score Boosts  │
                    │ - Smart Ranking │
                    └─────────────────┘
```

## 📡 API Endpoints

### 🔵 Pathway RAG API (Port 8000)

#### Document Indexing Endpoints

**GET /v1/statistics**
Get indexing statistics and system health.

```bash
curl -X POST http://localhost:8000/v1/statistics \
  -H "Content-Type: application/json"
```

**POST /v2/list_documents**
Retrieve metadata of all indexed documents.

```bash
curl -X POST http://localhost:8000/v2/list_documents \
  -H "Content-Type: application/json" \
  -d '{}'
```

**POST /v1/retrieve**
Perform vector similarity search on indexed documents.

```bash
curl -X POST http://localhost:8000/v1/retrieve \
  -H "Content-Type: application/json" \
  -d '{
    "query": "coffee shops with wifi",
    "k": 10
  }'
```

#### LLM and RAG Capabilities

**POST /v2/answer**
Ask questions about your documents or chat with the LLM.

**POST /v2/summarize**
Summarize a list of texts.

### 🟢 Business API (Port 8001)

#### Business Registration Endpoints

**POST /append-csv**
Register a single business.

```bash
curl -X POST http://localhost:8001/append-csv \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Smith",
    "business_name": "Smith Coffee House",
    "lat_long": "37.7749,-122.4194",
    "business_category": "Cafe",
    "business_tags": "coffee,wifi,outdoor-seating"
  }'
```

**POST /append-csv/batch**
Register multiple businesses at once.

```bash
curl -X POST http://localhost:8001/append-csv/batch \
  -H "Content-Type: application/json" \
  -d '{
    "records": [
      {
        "name": "John Smith",
        "business_name": "Smith Coffee House",
        "lat_long": "37.7749,-122.4194",
        "business_category": "Cafe",
        "business_tags": "coffee,wifi"
      }
    ]
  }'
```

#### Search Endpoints

**POST /search-businesses**
Primary search endpoint with AI-powered vectorized search and location filtering.

```bash
curl -X POST http://localhost:8001/search-businesses \
  -H "Content-Type: application/json" \
  -d '{
    "user_lat": 37.7749,
    "user_lng": -122.4194,
    "query": "coffee shops with wifi",
    "max_distance_km": 20.0,
    "category_filter": "Cafe",
    "tag_filters": ["wifi", "coffee"],
    "limit": 10
  }'
```

**POST /search-businesses/contextual**
Enhanced contextual search with weather, time, and user history intelligence.

```bash
curl -X POST http://localhost:8001/search-businesses/contextual \
  -H "Content-Type: application/json" \
  -d '{
    "user_lat": 37.7749,
    "user_lng": -122.4194,
    "query": "coffee shops",
    "max_distance_km": 10.0,
    "limit": 10
  }'
```

**Response Format:**
```json
{
  "ok": true,
  "results": [
    {
      "name": "John Smith",
      "business_name": "Smith Coffee House",
      "latitude": 37.7749,
      "longitude": -122.4194,
      "business_category": "Cafe",
      "business_tags": "coffee,wifi,outdoor-seating",
      "distance_km": 0.0,
      "vector_score": 0.12,
      "contextual_score": 0.85,
      "context_boosts": {
        "time_boost": 1.2,
        "weather_boost": 1.1,
        "history_boost": 0.9
      },
      "source_path": "data/data.csv"
    }
  ],
  "search_method": "contextual_vectorized",
  "total_found": 1,
  "contextual_factors": {
    "time_of_day": "morning",
    "weather_condition": "sunny",
    "temperature": 72,
    "user_preferences": ["coffee", "breakfast"]
  }
}
```

#### Contextual Intelligence Endpoints

**GET /weather/current**
Get current weather simulation for a location.

```bash
curl "http://localhost:8001/weather/current?lat=37.7749&lng=-122.4194"
```

**Response:**
```json
{
  "ok": true,
  "weather": {
    "temperature": 72.5,
    "condition": "sunny",
    "description": "Clear skies with comfortable temperature",
    "humidity": 65,
    "climate_zone": "mediterranean",
    "time_of_day": "morning"
  },
  "business_suggestions": {
    "recommended_categories": ["Cafe", "Outdoor Dining", "Parks"],
    "weather_factor": 1.1
  }
}
```

**POST /recommendations/contextual**
Get personalized contextual recommendations.

```bash
curl -X POST http://localhost:8001/recommendations/contextual \
  -H "Content-Type: application/json" \
  -d '{
    "user_lat": 37.7749,
    "user_lng": -122.4194,
    "limit": 10
  }'
```

#### Collaborative Filtering Endpoints

**POST /interactions/track**
Track user interactions for personalized recommendations.

```bash
curl -X POST http://localhost:8001/interactions/track \
  -H "Content-Type: application/json" \
  -d '{
    "business_id": "smith_coffee_001",
    "business_name": "Smith Coffee House",
    "interaction_type": "click",
    "query": "coffee shops",
    "category": "Cafe"
  }'
```

**GET /recommendations/trending-searches**
Get popular search queries.

```bash
curl "http://localhost:8001/recommendations/trending-searches?limit=5"
```

#### System Health

**GET /health**
Check system status including Redis, collaborative filtering, and contextual services.

```bash
curl http://localhost:8001/health
```

**Response:**
```json
{
  "status": "healthy",
  "pathway_status": "online",
  "redis_status": "online",
  "collaborative_filtering": true,
  "contextual_recommendations": true,
  "weather_service": "active",
  "services": {
    "pathway_api": "http://localhost:8000",
    "redis": "redis://redis:6379",
    "contextual_engine": "initialized"
  }
}
```

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- OpenAI API key
- Redis server (Docker recommended)
- Virtual environment (recommended)

### Installation

1. **Clone and setup environment:**
```bash
git clone <repository-url>
cd ai-assistant-rag
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# or venv\Scripts\activate  # Windows
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
cd ui && pip install -r requirements.txt && cd ..
```

3. **Configure environment:**
```bash
echo "OPENAI_API_KEY=your-key-here" > .env
```

4. **Start Redis (required for contextual features):**
```bash
# Using Docker (recommended)
docker run -d -p 6379:6379 --name redis-server redis:7-alpine

# Or install Redis locally
# brew install redis  # macOS
# sudo apt-get install redis-server  # Ubuntu
```

### Running the System

**Option 1: Manual Start (Recommended for Development)**

```bash
# Terminal 1: Main application (Pathway + Upload API)
python app.py

# Terminal 2: Streamlit UI
cd ui
streamlit run main.py --server.port 8501
```

**Option 2: Docker (Recommended for Production)**
```bash
# Includes Redis and all services
docker compose build
docker compose up
```

### Access Points

- **Main UI**: http://localhost:8501
- **Business Registration**: http://localhost:8501/business_registration  
- **Location Search**: http://localhost:8501/location_search (enhanced with contextual features)
- **Analytics Dashboard**: http://localhost:8501/analytics_dashboard
- **API Documentation**: http://localhost:8001/docs
- **Pathway API**: http://localhost:8000
- **Redis**: localhost:6379 (for debugging)

## 🔧 Configuration

### app.yaml Configuration

The system is configured through `app.yaml`:

```yaml
# Data sources - reads from individual business files
$sources:
  - !pw.io.fs.read
    path: data/businesses
    format: binary
    with_metadata: true

# LLM configuration
$llm: !pw.xpacks.llm.llms.OpenAIChat
  model: "gpt-4o"
  temperature: 0

# Embedder for vector search
$embedder: !pw.xpacks.llm.embedders.OpenAIEmbedder
  model: "text-embedding-3-small"

# Document processing
$splitter: !pw.xpacks.llm.splitters.TokenCountSplitter
  max_tokens: 60

# Hybrid search (vector + keyword)
$retriever_factory: !pw.stdlib.indexing.HybridIndexFactory
  retriever_factories:
    - $knn_index    # Vector similarity
    - $bm25_index   # Keyword matching
```

### Environment Variables

```bash
# Required
OPENAI_API_KEY=your-openai-api-key

# Optional - System Configuration  
DATA_DIR=data                    # Data directory path
PATHWAY_HOST=localhost           # Pathway server host
PATHWAY_PORT=8000               # Pathway server port

# Optional - Redis Configuration (for contextual features)
REDIS_URL=redis://localhost:6379  # Redis connection URL
REDIS_HOST=localhost             # Redis host
REDIS_PORT=6379                  # Redis port

# Optional - Feature Toggles
ENABLE_COLLABORATIVE_FILTERING=true    # Enable CF recommendations
ENABLE_CONTEXTUAL_RECOMMENDATIONS=true # Enable contextual intelligence
ENABLE_WEATHER_SIMULATION=true         # Enable weather-based suggestions
```

## 🎯 Features

### Business Registration

- **Validation**: GPS coordinate validation and format checking
- **Storage**: CSV and individual text file storage for optimal indexing
- **Real-time Indexing**: Automatic Pathway reindexing after registration
- **Batch Support**: Register multiple businesses simultaneously

### Location-Based Search

- **AI-Powered**: Uses OpenAI embeddings for semantic understanding
- **Distance Filtering**: Configurable search radius (up to 25,000km)
- **Smart Ranking**: Combines relevance score with distance proximity
- **Category/Tag Filtering**: Filter by business type and tags
- **Geolocation Support**: Browser-based location detection

### 🌟 Contextual Recommendations

**Time Intelligence:**
- **Morning Boost**: Coffee shops, breakfast places, gyms (6AM-11AM)
- **Lunch Enhancement**: Restaurants, fast-casual dining (11AM-2PM)  
- **Evening Preferences**: Bars, fine dining, entertainment (6PM-11PM)
- **Late Night**: 24/7 establishments, convenience stores (11PM-6AM)
- **Weekend Patterns**: Different preferences for leisure activities

**Weather Intelligence:**
- **Sunny Days**: Outdoor dining, parks, ice cream shops boosted
- **Rainy Weather**: Indoor activities, cafes, shopping malls preferred
- **Hot Weather**: Air-conditioned venues, cold beverages prioritized
- **Cold Weather**: Warm restaurants, indoor entertainment enhanced
- **Climate Zones**: Mediterranean, tropical, continental patterns

**User History Context:**
- **Interaction Tracking**: Clicks, views, searches without personal data
- **Preference Learning**: Categories and tags from user behavior
- **Collaborative Filtering**: "Users like you also visited..."
- **Trending Discovery**: Popular searches and emerging businesses
- **Session Continuity**: Consistent experience across searches

### 🌤️ Weather Simulation (No API Keys Required)

- **Realistic Patterns**: Location-based climate simulation
- **Seasonal Variation**: Temperature and weather changes throughout the year
- **Daily Cycles**: Morning coolness, afternoon warmth, evening temperatures
- **Climate Zones**: Different patterns for different geographical regions
- **Business Suggestions**: Weather-appropriate business recommendations

### Search Intelligence

**Semantic Understanding:**
- "coffee shop" matches "cafe", "espresso bar"
- "italian food" finds "Italian restaurants", "pizza places"
- "car service" matches "auto repair", "gas stations"

**Contextual Ranking Algorithm:**
- **Base Score**: Vector similarity (semantic relevance)
- **Distance Factor**: Proximity weighting based on search radius
- **Time Boost**: 1.1-1.3x for time-appropriate businesses
- **Weather Boost**: 1.1-1.2x for weather-suitable venues  
- **History Boost**: 0.9-1.4x based on user interaction patterns
- **Collaborative Boost**: Similar user preferences influence ranking

## 🗂️ Data Models

### Business Record Schema

```python
{
  "name": str,                    # Business owner name
  "business_name": str,           # Business name
  "lat_long": str,               # "latitude,longitude"
  "business_category": str,       # Business category
  "business_tags": str           # Comma-separated tags
}
```

### Search Request Schema

```python
{
  "user_lat": float,             # User latitude (-90 to 90)
  "user_lng": float,             # User longitude (-180 to 180)
  "query": str,                  # Search query (optional)
  "max_distance_km": float,      # Search radius (0.1 to 25000)
  "category_filter": str,        # Category filter (optional)
  "tag_filters": List[str],      # Tag filters (optional)
  "limit": int,                  # Result limit (1 to 200)
  "include_contextual": bool,    # Enable contextual features (optional)
  "user_session_id": str         # Session tracking (optional)
}
```

### Contextual Response Schema

```python
{
  "ok": bool,
  "results": List[BusinessResult],
  "contextual_factors": {
    "time_of_day": str,          # "morning", "afternoon", "evening", "night"
    "weather_condition": str,     # "sunny", "rainy", "cloudy", etc.
    "temperature": float,         # Simulated temperature
    "user_preferences": List[str] # Learned preferences
  },
  "context_boosts": {
    "time_boost": float,         # Time-based boost factor
    "weather_boost": float,      # Weather-based boost factor  
    "history_boost": float       # User history boost factor
  },
  "search_method": str,          # "contextual_vectorized"
  "total_found": int
}
```

## 🔍 Search Methods

### 1. Contextual Vectorized Search (Primary)
- Uses OpenAI embeddings for semantic similarity
- Hybrid indexing (vector + BM25 keyword matching)
- Real-time contextual intelligence integration
- Weather and time-based business suggestions
- User history and collaborative filtering
- Intelligent ranking with multiple boost factors

### 2. Standard Vectorized Search (Fallback)
- Traditional vector similarity search
- Distance-based ranking
- Category and tag filtering
- Used when contextual features unavailable

### 3. Graceful Degradation
- Automatic fallback if advanced features unavailable
- System health monitoring and status reporting
- Informative error messages for users

## 📊 System Monitoring

### Health Checks

The system provides comprehensive health monitoring including contextual services:

```bash
# Check overall system health including contextual features
curl http://localhost:8001/health

# Check current weather simulation
curl "http://localhost:8001/weather/current?lat=37.7749&lng=-122.4194"

# Check collaborative filtering analytics  
curl http://localhost:8001/analytics/cf-performance

# Check Pathway statistics
curl -X POST http://localhost:8000/v1/statistics

# List indexed documents
curl -X POST http://localhost:8000/v2/list_documents
```

### Logging

- **Pathway Server**: Document indexing and search operations
- **Upload API**: Business registration, search requests, and contextual processing
- **UI**: User interactions, weather display, and contextual features
- **Redis**: Collaborative filtering data and user interaction tracking
- **Contextual Engine**: Weather simulation and time intelligence processing

## 🐛 Troubleshooting

### Common Issues

**APIs not starting:**
```bash
# Check if ports are free (including Redis)
lsof -i :8000 :8001 :8501 :6379

# Verify Python environment
which python
pip list | grep -E "(pathway|fastapi|streamlit|redis)"

# Check Redis connectivity
redis-cli ping
```

**No search results:**
- Verify businesses exist in `data/data.csv`
- Check coordinate format: "latitude,longitude"
- Ensure businesses are within search radius
- Verify OpenAI API key in `.env`
- Check Redis connection for contextual features

**Contextual features not working:**
- Verify Redis server is running: `redis-cli ping`
- Check Redis connection in health endpoint
- Ensure collaborative filtering is enabled in health response
- Monitor logs for contextual service errors

**Weather simulation issues:**
- No external API needed - weather is simulated
- Check location coordinates are valid
- Verify weather service in health endpoint
- Check console logs for weather processing errors

**Indexing not working:**
- Check OpenAI API key configuration
- Monitor Pathway logs for embedding errors
- Verify document list via `/v2/list_documents`

**UI not loading:**
- Check Streamlit port (8501)
- Verify UI requirements installed
- Check browser console for errors
- Ensure all backend services are running

### Debug Commands

```bash
# Check system status including contextual features
python -c "import requests; print(requests.get('http://localhost:8001/health').json())"

# Test contextual search
curl -X POST http://localhost:8001/search-businesses/contextual \
  -H "Content-Type: application/json" \
  -d '{"user_lat": 37.7749, "user_lng": -122.4194, "query": "coffee", "max_distance_km": 10}'

# Test weather simulation
curl "http://localhost:8001/weather/current?lat=37.7749&lng=-122.4194"

# Test collaborative filtering
curl -X POST http://localhost:8001/interactions/track \
  -H "Content-Type: application/json" \
  -d '{"business_id": "test_001", "business_name": "Test Coffee", "interaction_type": "click", "query": "coffee"}'

# Test business registration
curl -X POST http://localhost:8001/append-csv \
  -H "Content-Type: application/json" \
  -d '{"name": "Test", "business_name": "Test Business", "lat_long": "0,0", "business_category": "Test", "business_tags": "test"}'

# Check Redis connectivity
redis-cli ping

# Test standard search
curl -X POST http://localhost:8001/search-businesses \
  -H "Content-Type: application/json" \
  -d '{"user_lat": 0, "user_lng": 0, "query": "test", "max_distance_km": 20000.0}'
```

## 🔧 Development

### Project Structure

```
ai-assistant-rag/
├── app.py                 # Main Pathway application
├── upload_api.py          # Enhanced FastAPI with contextual features
├── utils.py              # Utility functions
├── app.yaml              # Pathway configuration
├── requirements.txt      # Python dependencies
├── .env                  # Environment variables
├── contextual_recommendations.py  # Contextual intelligence engine
├── weather_service.py    # Weather simulation (no API keys)
├── collaborative_filtering.py     # User interaction tracking & CF
├── data/
│   ├── data.csv          # Business data storage
│   ├── businesses.txt    # Normalized business data
│   └── businesses/       # Individual business files
└── ui/
    ├── main.py           # Main Streamlit app
    ├── requirements.txt  # UI dependencies
    └── pages/
        ├── business_registration.py
        ├── location_search.py      # Enhanced with contextual UI
        └── analytics_dashboard.py  # CF performance analytics
```

### Key Technologies

- **[Pathway](https://pathway.com/)**: Real-time data processing and RAG
- **[FastAPI](https://fastapi.tiangolo.com/)**: REST API framework
- **[Streamlit](https://streamlit.io/)**: Web UI framework
- **[OpenAI](https://openai.com/)**: Embeddings and LLM
- **[Redis](https://redis.io/)**: In-memory data store for collaborative filtering
- **[USearch](https://github.com/unum-cloud/usearch)**: Vector similarity search
- **Contextual Intelligence**: Time-based and weather-aware recommendations
- **Weather Simulation**: Realistic weather patterns without external APIs

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- [Pathway](https://pathway.com/) for the real-time RAG framework
- [OpenAI](https://openai.com/) for embeddings and language models
- [FastAPI](https://fastapi.tiangolo.com/) and [Streamlit](https://streamlit.io/) communities

---

<div align="center">
  <strong>🗺️ Business Location RAG System | Enhanced with Contextual Intelligence</strong><br>
  <strong>Powered by Pathway + OpenAI + Redis | Weather-Aware & Time-Smart Recommendations</strong>
</div>
