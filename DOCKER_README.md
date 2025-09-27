# Docker Setup for AI RAG Assistant with Contextual Intelligence

This is a production-ready Docker setup for the AI RAG Assistant application with enhanced contextual features, Redis integration, collaborative filtering, and comprehensive health monitoring.

## Features

- **Virtual Environment**: All Python dependencies are installed in a virtual environment (`/app/venv`)
- **Security**: Runs as non-root user for enhanced security
- **Health Checks**: Built-in health monitoring for all services including contextual features
- **Service Dependencies**: Proper service startup ordering with Redis dependency
- **Persistent Data**: Docker volumes for data persistence and Redis cache
- **Optimized Builds**: Docker layer caching and .dockerignore for faster builds
- **🌤️ Contextual Intelligence**: Weather simulation and time-based recommendations
- **🔄 Collaborative Filtering**: Redis-powered user interaction tracking
- **📊 Analytics**: Performance monitoring and trending analysis

## Quick Start

### Option 1: Automated Setup (Recommended)
```bash
./setup.sh
```

### Option 2: Manual Setup
1. **Create environment file:**
   ```bash
   cp .env.example .env
   # Edit .env and add your OpenAI API key
   ```

2. **Build and run the services:**
   ```bash
   docker-compose up --build
   ```

3. **Access the applications:**
   - **Streamlit UI**: http://localhost:8501 (enhanced with contextual features)
   - **Location Search**: http://localhost:8501/location_search (weather cards & context)
   - **Analytics Dashboard**: http://localhost:8501/analytics_dashboard (CF performance)
   - **RAG API**: http://localhost:8000
   - **Upload/Search API**: http://localhost:8001 (contextual endpoints)
   - **Redis**: localhost:6379 (for debugging CF data)

## Services

### RAG Application (`rag-app`)
- **Container**: `business-rag-app`
- **Ports**: 8000 (Pathway RAG), 8001 (FastAPI with contextual features)
- **Command**: `python app.py`
- **Dependencies**: Installs from both `requirements.txt` and `ui/requirements.txt`
- **Features**: Vector search, contextual intelligence, collaborative filtering
- **Redis Connection**: Connects to Redis for CF data and contextual caching
- **Health Check**: Monitors Pathway, Redis, and contextual services

### Streamlit UI (`streamlit-ui`)
- **Container**: `business-rag-ui`
- **Port**: 8501
- **Command**: `streamlit run ui/main.py`
- **Dependencies**: Same virtual environment as RAG app
- **Features**: Enhanced UI with weather cards, contextual explanations, analytics dashboard
- **Redis Integration**: Displays CF performance and trending data

### Redis Cache (`redis`)
- **Container**: `business-rag-redis`
- **Port**: 6379
- **Image**: `redis:7-alpine` with optimized configuration
- **Purpose**: Collaborative filtering data, user interactions, contextual caching
- **Persistence**: Data stored in Docker volume for reliability
- **Performance**: Configured with memory limits and LRU eviction

## Environment Variables

Make sure you have a `.env` file with:
```
# Required
OPENAI_API_KEY=your_openai_api_key_here

# Optional - Redis Configuration
REDIS_URL=redis://redis:6379
REDIS_HOST=redis
REDIS_PORT=6379

# Optional - Feature Toggles
ENABLE_COLLABORATIVE_FILTERING=true
ENABLE_CONTEXTUAL_RECOMMENDATIONS=true
ENABLE_WEATHER_SIMULATION=true

# Optional - System Configuration
DATA_DIR=data
PATHWAY_HOST=localhost
PATHWAY_PORT=8000
```

### Docker Compose Environment

The `docker-compose.yml` automatically configures:
- **Redis Connection**: `REDIS_URL=redis://redis:6379`
- **Service Discovery**: All services can communicate via container names
- **Health Monitoring**: Built-in health checks for all components
- **Volume Mapping**: Data persistence for business data and Redis cache

## Docker Configuration

### Enhanced Dockerfile Features
- Uses Python 3.11 slim base image
- Creates virtual environment at `/app/venv`
- Installs system dependencies (build-essential, curl, git, redis-tools)
- Installs Python packages including Redis and contextual dependencies
- Runs as non-root user for security
- Optimized layer caching for faster builds
- Health check endpoint integration

### Enhanced Docker Compose Features
- **Three services**: `rag-app`, `streamlit-ui`, and `redis`
- **Shared network**: `business-rag-network` for inter-service communication
- **Docker volumes**: Data persistence for business data and Redis cache
- **Health checks**: Comprehensive monitoring including contextual services
- **Service dependencies**: Redis starts first, then RAG app, then UI
- **Automatic restart**: Services restart unless manually stopped
- **Redis optimization**: Memory limits, persistence, and performance tuning

### Redis Configuration in Docker

```yaml
redis:
  image: redis:7-alpine
  container_name: business-rag-redis
  command: |
    redis-server 
    --maxmemory 256mb 
    --maxmemory-policy allkeys-lru
    --save 300 10
    --appendonly yes
    --appendfsync everysec
  volumes:
    - redis_data:/data
  networks:
    - business-rag-network
  healthcheck:
    test: ["CMD", "redis-cli", "ping"]
    interval: 10s
    timeout: 5s
    retries: 3
```

## Commands

```bash
# Start all services (including Redis)
docker-compose up

# Start with rebuild
docker-compose up --build

# Run in background
docker-compose up -d

# Stop services
docker-compose down

# Stop and remove volumes (clears Redis data)
docker-compose down -v

# View logs
docker-compose logs

# View logs for specific service
docker-compose logs rag-app
docker-compose logs streamlit-ui
docker-compose logs redis

# Check service health
docker-compose ps

# Access Redis CLI for debugging
docker-compose exec redis redis-cli

# Monitor Redis memory usage
docker-compose exec redis redis-cli info memory

# Check contextual services
curl http://localhost:8001/health
```

## Troubleshooting

1. **Port conflicts**: Make sure ports 8000, 8001, 8501, and 6379 are available
2. **Environment variables**: Ensure `.env` file exists with required variables
3. **Build issues**: Try `docker-compose down` then `docker-compose up --build`
4. **Redis connection**: Check Redis health with `docker-compose exec redis redis-cli ping`
5. **Contextual features not working**: Verify Redis is running and health endpoint shows all services online
6. **Volume permissions**: On Linux, ensure Docker has permission to create volumes
7. **Memory issues**: Redis is configured with memory limits - monitor usage
8. **Logs**: Check logs with `docker-compose logs` for any errors

### Health Check Commands

```bash
# Check overall system health including contextual features
curl http://localhost:8001/health | jq '.'

# Test contextual search
curl -X POST http://localhost:8001/search-businesses/contextual \
  -H "Content-Type: application/json" \
  -d '{"user_lat": 37.7749, "user_lng": -122.4194, "query": "coffee"}'

# Test weather simulation
curl "http://localhost:8001/weather/current?lat=37.7749&lng=-122.4194" | jq '.'

# Check Redis connectivity
docker-compose exec redis redis-cli ping

# Monitor collaborative filtering data
curl http://localhost:8001/analytics/cf-performance | jq '.'
```

### Common Issues

**Redis Connection Failed:**
```bash
# Check if Redis container is running
docker-compose ps redis

# Restart Redis if needed
docker-compose restart redis

# Check Redis logs
docker-compose logs redis
```

**Contextual Features Disabled:**
```bash
# Verify environment variables
docker-compose exec rag-app env | grep -E "(REDIS|ENABLE_)"

# Check health endpoint
curl http://localhost:8001/health | jq '.contextual_recommendations'
```

**Performance Issues:**
```bash
# Monitor Redis memory
docker-compose exec redis redis-cli info memory

# Check container resource usage
docker stats
```

## File Structure

```
.
├── dockerfile                 # Enhanced Dockerfile with Redis tools and contextual deps
├── docker-compose.yml        # Three-service setup: rag-app, streamlit-ui, redis
├── requirements.txt          # Main dependencies including Redis and contextual libraries
├── ui/requirements.txt       # UI-specific dependencies with enhanced features
├── app.py                   # Main application entry point with contextual integration
├── upload_api.py            # Enhanced FastAPI with contextual endpoints
├── contextual_recommendations.py  # Contextual intelligence engine
├── weather_service.py       # Weather simulation service (no API keys)
├── collaborative_filtering.py     # Redis-powered CF system
├── ui/main.py              # Enhanced Streamlit UI entry point
├── ui/pages/
│   ├── location_search.py  # Enhanced with weather cards and contextual features
│   └── analytics_dashboard.py    # CF performance and trending analytics
├── data/                   # Business data (mounted as volume)
└── .env                    # Environment variables including Redis config
```

## Docker Compose Services Overview

```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    # Optimized Redis configuration for CF and contextual data
    
  rag-app:
    build: .
    ports:
      - "8000:8000"  # Pathway RAG API
      - "8001:8001"  # Enhanced FastAPI with contextual features
    depends_on:
      - redis
    environment:
      - REDIS_URL=redis://redis:6379
    # Health check includes contextual services
    
  streamlit-ui:
    build: .
    ports:
      - "8501:8501"
    depends_on:
      - rag-app
    # Enhanced UI with weather cards and analytics
```

## Production Deployment Considerations

### Resource Requirements
- **RAM**: Minimum 4GB (2GB for applications, 1GB for Redis, 1GB for system)
- **CPU**: 2+ cores recommended for concurrent contextual processing
- **Disk**: SSD recommended for Redis persistence and business data
- **Network**: Fast connection for OpenAI API calls

### Redis Optimization for Production
```yaml
# In docker-compose.yml
redis:
  command: |
    redis-server 
    --maxmemory 512mb              # Adjust based on available RAM
    --maxmemory-policy allkeys-lru # Evict least recently used keys
    --save 900 1                   # Save snapshots every 15 min if 1+ changes
    --save 300 10                  # Save every 5 min if 10+ changes
    --save 60 10000               # Save every min if 10000+ changes
    --appendonly yes              # Enable AOF persistence
    --appendfsync everysec        # Fsync every second (good balance)
    --tcp-keepalive 60           # TCP keepalive
```

### Security Considerations
- **Redis**: No authentication in development, add AUTH for production
- **Network**: Use custom networks instead of default bridge
- **Secrets**: Use Docker secrets for sensitive environment variables
- **User Permissions**: All containers run as non-root users
- **Volume Permissions**: Ensure proper file system permissions

### Monitoring and Logging
```yaml
# Add to docker-compose.yml for production monitoring
logging:
  driver: "json-file"
  options:
    max-size: "100m"
    max-file: "3"
```
