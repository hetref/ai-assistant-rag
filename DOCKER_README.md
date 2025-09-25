# Docker Setup for AI RAG Assistant

This is a production-ready Docker setup for the AI RAG Assistant application with enhanced security, health checks, and proper service orchestration.

## Features

- **Virtual Environment**: All Python dependencies are installed in a virtual environment (`/app/venv`)
- **Security**: Runs as non-root user for enhanced security
- **Health Checks**: Built-in health monitoring for all services
- **Service Dependencies**: Proper service startup ordering
- **Persistent Data**: Docker volumes for data persistence
- **Optimized Builds**: Docker layer caching and .dockerignore for faster builds

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
   - **Streamlit UI**: http://localhost:8501
   - **RAG API**: http://localhost:8000
   - **Upload/Search API**: http://localhost:8001

## Services

### RAG Application (`rag-app`)
- **Container**: `business-rag-app`
- **Ports**: 8000 (Pathway RAG), 8001 (FastAPI)
- **Command**: `python app.py`
- **Dependencies**: Installs from both `requirements.txt` and `ui/requirements.txt`

### Streamlit UI (`streamlit-ui`)
- **Container**: `business-rag-ui`
- **Port**: 8501
- **Command**: `streamlit run ui/main.py`
- **Dependencies**: Same virtual environment as RAG app

## Environment Variables

Make sure you have a `.env` file with:
```
OPENAI_API_KEY=your_openai_api_key_here
```

## Docker Configuration

### Dockerfile Features
- Uses Python 3.11 slim base image
- Creates virtual environment at `/app/venv`
- Installs system dependencies (build-essential, curl, git)
- Installs Python packages in virtual environment
- Runs as non-root user for security
- Optimized layer caching for faster builds

### Docker Compose Features
- Two services: `rag-app` and `streamlit-ui`
- Shared network: `business-rag-network`
- Docker volumes for data persistence
- Health checks for service monitoring
- Service dependencies for proper startup ordering
- Automatic restart unless stopped

## Commands

```bash
# Start services
docker-compose up

# Start with rebuild
docker-compose up --build

# Run in background
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs

# View logs for specific service
docker-compose logs rag-app
docker-compose logs streamlit-ui
```

## Troubleshooting

1. **Port conflicts**: Make sure ports 8000, 8001, and 8501 are available
2. **Environment variables**: Ensure `.env` file exists with required variables
3. **Build issues**: Try `docker-compose down` then `docker-compose up --build`
4. **Logs**: Check logs with `docker-compose logs` for any errors

## File Structure

```
.
├── dockerfile                 # Simplified Dockerfile with venv
├── docker-compose.yml        # Simplified compose configuration
├── requirements.txt          # Main application dependencies
├── ui/requirements.txt       # UI-specific dependencies
├── app.py                   # Main application entry point
├── ui/main.py              # Streamlit UI entry point
└── .env                    # Environment variables
```