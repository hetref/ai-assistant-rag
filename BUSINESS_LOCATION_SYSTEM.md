# 🏢 Business Location System

A comprehensive location-based business search system powered by Pathway RAG, FastAPI, and Streamlit.

## 🌟 Features

### 🏪 Business Registration
- Easy-to-use registration form
- GPS coordinate validation
- Real-time indexing status
- Automatic CSV file management
- System health monitoring

### 🗺️ Location-Based Search
- **Vectorized AI Search**: Uses OpenAI embeddings for semantic understanding
- **Hybrid Ranking**: Combines AI relevance with GPS proximity
- **Smart Query Processing**: "coffee shop" finds "cafe", "espresso bar", etc.
- **Location Filtering**: Haversine distance calculations within configurable radius
- **Fallback System**: Automatic CSV-based search if vectorization unavailable

### 🤖 AI-Powered RAG
- Real-time document indexing
- Natural language querying
- Context-aware responses
- Multi-document search

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Streamlit UI  │    │   Upload API    │    │  Pathway RAG    │
│   (Port 8501)   │◄──►│   (Port 8001)   │◄──►│   (Port 8000)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Business Forms  │    │  CSV Management │    │ Vector Database │
│ Location Search │    │ Distance Calc   │    │ LLM Integration │
│ RAG Chat        │    │ Smart Filtering │    │ Auto Indexing   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- OpenAI API key
- Git

### Installation

1. **Clone and setup**
```bash
cd /root/ai-rag/mk1/ai-assistant-rag
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. **Configure environment**
```bash
echo "OPENAI_API_KEY=your_openai_api_key_here" > .env
```

3. **Install UI dependencies**
```bash
cd ui
pip install -r requirements.txt
cd ..
```

### Running the System

#### Option 1: Manual Start (Recommended for Development)

**Terminal 1: Start Pathway + Upload API**
```bash
cd /root/ai-rag/mk1/ai-assistant-rag
source venv/bin/activate
python app.py
```

**Terminal 2: Start Streamlit UI**
```bash
cd /root/ai-rag/mk1/ai-assistant-rag/ui
source ../venv/bin/activate
streamlit run main.py --server.port 8501
```

#### Option 2: Docker (Production)
```bash
cd /root/ai-rag/mk1/ai-assistant-rag
docker compose build
docker compose up
```

### Accessing the System

- **Main Dashboard**: http://localhost:8501
- **Business Registration**: http://localhost:8501/business_registration
- **Location Search**: http://localhost:8501/pages/location_search
- **RAG Chat**: http://localhost:8501/ui
- **Upload API Docs**: http://localhost:8001/docs
- **Pathway API**: http://localhost:8000

## 📖 Usage Guide

### 1. Register a Business

1. Go to **Business Registration** page
2. Fill out the form:
   - **Owner Name**: Full name of business owner
   - **Business Name**: Official business name
   - **Coordinates**: GPS latitude, longitude
   - **Category**: Select from predefined categories
   - **Tags**: Comma-separated features (optional)
3. Click **Register Business**
4. Monitor indexing status in sidebar

### 2. Search for Businesses

1. Go to **Location Search** page
2. Set your location:
   - **Manual Coordinates**: Enter lat/lng directly
   - **Browser Geolocation**: Use GPS (if available)
   - **City Lookup**: Enter city name (basic geocoding)
3. Enter search query (e.g., "coffee shops", "restaurants near me")
4. Adjust search radius (1-50km)
5. Click **Search Nearby Businesses**
6. View distance-sorted results

### 3. Chat with RAG System

1. Go to **RAG Chat** page
2. Ask natural language questions about indexed documents
3. View response with context sources
4. Monitor document indexing status

## 🔧 API Endpoints

### Upload API (Port 8001)

- `POST /append-csv` - Add single business record
- `POST /append-csv/batch` - Add multiple business records
- `POST /search-businesses` - **Vectorized location-based search** (primary)
- `POST /search-businesses-csv` - CSV-only search (fallback)
- `GET /health` - Health check with Pathway status
- `GET /docs` - API documentation

### Pathway API (Port 8000)

- `POST /v2/answer` - AI question answering
- `POST /v2/summarize` - Text summarization
- `POST /v1/retrieve` - Similarity search
- `POST /v1/statistics` - System statistics
- `POST /v2/list_documents` - Document metadata

## 📊 Example API Calls

### Register a Business
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

### Search Nearby Businesses
```bash
curl -X POST http://localhost:8001/search-businesses \
  -H "Content-Type: application/json" \
  -d '{
    "user_lat": 37.7749,
    "user_lng": -122.4194,
    "query": "coffee shops",
    "max_distance_km": 5.0,
    "limit": 10
  }'
```

### Ask RAG Question
```bash
curl -X POST http://localhost:8000/v2/answer \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "What cafes are available in the data?",
    "return_context_docs": true
  }'
```

## 🔧 Configuration

### Environment Variables
- `OPENAI_API_KEY` - Your OpenAI API key
- `DATA_DIR` - Directory for CSV files (default: "data")
- `PATHWAY_HOST` - Pathway API host (default: "localhost")
- `PATHWAY_PORT` - Pathway API port (default: 8000)

### Pathway Configuration (`app.yaml`)
```yaml
# Embedder model
$embedder: !pw.xpacks.llm.embedders.OpenAIEmbedder
  model: "text-embedding-3-small"  # Recommended upgrade

# Chunking
$splitter: !pw.xpacks.llm.splitters.TokenCountSplitter
  max_tokens: 400

# Search results
question_answerer: !pw.xpacks.llm.question_answering.SummaryQuestionAnswerer
  search_topk: 8  # Increase for more context
```

## 📈 Performance Optimization

### For Better Embeddings
1. **Upgrade embedding model**:
   ```yaml
   model: "text-embedding-3-small"  # Better than ada-002
   ```

2. **Optimize chunk size**:
   ```yaml
   max_tokens: 300-500  # Test different values
   ```

### For Better Retrieval
1. **Increase search results**:
   ```yaml
   search_topk: 8-12
   ```

2. **Use hybrid indexing**:
   ```yaml
   $hybrid_index_factory: !pw.stdlib.indexing.HybridIndexFactory
     retriever_factories:
       - $knn_index      # Vector similarity
       - $bm25_index     # Keyword matching
   ```

### For Better Location Search
1. **Optimize search radius** based on area density
2. **Use tag-based filtering** for precise results
3. **Implement result caching** for frequent searches

## 🐛 Troubleshooting

### Common Issues

**APIs not starting**
```bash
# Check if ports are free
lsof -i :8000 :8001 :8501

# Check Python environment
which python
pip list | grep -E "(pathway|fastapi|streamlit)"
```

**No search results**
- Verify CSV file exists: `data/data.csv`
- Check coordinate format: `"latitude,longitude"`
- Ensure businesses within search radius
- Verify API connectivity in UI sidebar

**Indexing not working**
- Check OpenAI API key in `.env`
- Monitor Pathway logs for embedding errors
- Verify document list via `/v2/list_documents`

**UI not loading**
- Check Streamlit port (8501)
- Verify UI requirements installed
- Check browser console for JavaScript errors

### Debug Commands
```bash
# Test Upload API
curl http://localhost:8001/health

# Test Pathway API
curl -X POST http://localhost:8000/v1/statistics

# Check CSV content
cat data/data.csv

# Monitor logs
tail -f pathway.log  # If logging enabled
```

## 🔮 Future Enhancements

### Planned Features
- **Real-time map visualization** with Leaflet.js or Google Maps
- **Advanced geocoding** with Google Maps API
- **Business reviews and ratings** system
- **Operating hours** and availability
- **Route optimization** for multiple locations
- **Mobile app** with native GPS integration

### System Improvements
- **Caching layer** for frequent searches
- **Database backend** (PostgreSQL + PostGIS)
- **Horizontal scaling** with load balancers
- **Advanced analytics** and usage metrics
- **Multi-language support**

## 📄 License

This project uses the same license as the base Pathway RAG template.

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Make changes
4. Test thoroughly
5. Submit pull request

## 📞 Support

- Check API documentation: http://localhost:8001/docs
- Review Pathway documentation: https://pathway.com/developers
- Monitor system status via UI dashboard
