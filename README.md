# Business Location RAG System

A real-time business registration and location-based search system powered by [Pathway](https://github.com/pathwaycom/pathway) RAG (Retrieval-Augmented Generation) with AI-powered vectorized search capabilities.

## 🌟 Overview

This system combines the power of Pathway's real-time document indexing with location-based business search, providing:

- **🏢 Business Registration**: Register businesses with location data and automatic indexing
- **🗺️ Location-Based Search**: Find businesses using GPS coordinates with distance filtering
- **🤖 AI-Powered Search**: Semantic search using OpenAI embeddings for intelligent matching
- **📱 Modern UI**: Streamlit-based interface with geolocation support
- **⚡ Real-Time Updates**: Automatic document reindexing when new businesses are added

## 🏗️ Architecture

### Core Components

1. **Pathway RAG Server** (Port 8000): Document indexing and vector search
2. **FastAPI Upload Server** (Port 8001): Business registration and location search
3. **Streamlit UI** (Port 8501): User interface for registration and search
4. **OpenAI Integration**: Embeddings and LLM for semantic understanding

### Data Flow

```
Business Registration → CSV Storage → Pathway Indexing → Vector Search → Location Filtering → Results
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
      "source_path": "data/data.csv"
    }
  ],
  "search_method": "vectorized",
  "total_found": 1
}
```

#### System Health

**GET /health**
Check system status and connectivity.

```bash
curl http://localhost:8001/health
```

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- OpenAI API key
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

### Running the System

**Option 1: Manual Start (Recommended for Development)**

```bash
# Terminal 1: Main application (Pathway + Upload API)
python app.py

# Terminal 2: Streamlit UI
cd ui
streamlit run main.py --server.port 8501
```

**Option 2: Docker**
```bash
docker compose build
docker compose up
```

### Access Points

- **Main UI**: http://localhost:8501
- **Business Registration**: http://localhost:8501/business_registration
- **Location Search**: http://localhost:8501/location_search
- **API Documentation**: http://localhost:8001/docs
- **Pathway API**: http://localhost:8000

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
OPENAI_API_KEY=your-openai-api-key
DATA_DIR=data                    # Data directory path
PATHWAY_HOST=localhost           # Pathway server host
PATHWAY_PORT=8000               # Pathway server port
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

### Search Intelligence

**Semantic Understanding:**
- "coffee shop" matches "cafe", "espresso bar"
- "italian food" finds "Italian restaurants", "pizza places"
- "car service" matches "auto repair", "gas stations"

**Ranking Algorithm:**
- **Limited Search** (<10,000km): 70% relevance, 30% distance
- **Unlimited Search** (≥10,000km): 40% relevance, 60% distance
- **Auto-detection**: Queries with "near me", "nearby" emphasize distance

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
  "limit": int                   # Result limit (1 to 200)
}
```

## 🔍 Search Methods

### 1. Vectorized Search (Primary)
- Uses OpenAI embeddings for semantic similarity
- Hybrid indexing (vector + BM25 keyword matching)
- Real-time document processing
- Intelligent ranking with distance weighting

### 2. Fallback Mechanisms
- Automatic fallback if Pathway is unavailable
- Graceful error handling with informative messages
- System health monitoring and status reporting

## 📊 System Monitoring

### Health Checks

The system provides comprehensive health monitoring:

```bash
# Check overall system health
curl http://localhost:8001/health

# Check Pathway statistics
curl -X POST http://localhost:8000/v1/statistics

# List indexed documents
curl -X POST http://localhost:8000/v2/list_documents
```

### Logging

- **Pathway Server**: Document indexing and search operations
- **Upload API**: Business registration and search requests
- **UI**: User interactions and system status

## 🐛 Troubleshooting

### Common Issues

**APIs not starting:**
```bash
# Check if ports are free
lsof -i :8000 :8001 :8501

# Verify Python environment
which python
pip list | grep -E "(pathway|fastapi|streamlit)"
```

**No search results:**
- Verify businesses exist in `data/data.csv`
- Check coordinate format: "latitude,longitude"
- Ensure businesses are within search radius
- Verify OpenAI API key in `.env`

**Indexing not working:**
- Check OpenAI API key configuration
- Monitor Pathway logs for embedding errors
- Verify document list via `/v2/list_documents`

**UI not loading:**
- Check Streamlit port (8501)
- Verify UI requirements installed
- Check browser console for errors

### Debug Commands

```bash
# Check system status
python -c "import requests; print(requests.get('http://localhost:8001/health').json())"

# Test business registration
curl -X POST http://localhost:8001/append-csv \
  -H "Content-Type: application/json" \
  -d '{"name": "Test", "business_name": "Test Business", "lat_long": "0,0", "business_category": "Test", "business_tags": "test"}'

# Test search
curl -X POST http://localhost:8001/search-businesses \
  -H "Content-Type: application/json" \
  -d '{"user_lat": 0, "user_lng": 0, "query": "test", "max_distance_km": 20000.0}'
```

## 🔧 Development

### Project Structure

```
ai-assistant-rag/
├── app.py                 # Main Pathway application
├── upload_api.py          # FastAPI business registration/search
├── utils.py              # Utility functions
├── app.yaml              # Pathway configuration
├── requirements.txt      # Python dependencies
├── .env                  # Environment variables
├── data/
│   ├── data.csv          # Business data storage
│   ├── businesses.txt    # Normalized business data
│   └── businesses/       # Individual business files
└── ui/
    ├── main.py           # Main Streamlit app
    ├── requirements.txt  # UI dependencies
    └── pages/
        ├── business_registration.py
        └── location_search.py
```

### Key Technologies

- **[Pathway](https://pathway.com/)**: Real-time data processing and RAG
- **[FastAPI](https://fastapi.tiangolo.com/)**: REST API framework
- **[Streamlit](https://streamlit.io/)**: Web UI framework
- **[OpenAI](https://openai.com/)**: Embeddings and LLM
- **[USearch](https://github.com/unum-cloud/usearch)**: Vector similarity search

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
  <strong>🗺️ Business Location RAG System | Powered by Pathway + OpenAI</strong>
</div>