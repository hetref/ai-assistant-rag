# Docker Setup for AI RAG Assistant

This is a simplified Docker setup for the AI RAG Assistant application that uses a virtual environment for dependency management.

## Features

- **Virtual Environment**: All Python dependencies are installed in a virtual environment (`/app/venv`)
- **Simplified Configuration**: No health checks or complex user management
- **Root User**: Uses the default root user for simplicity
- **Dual Requirements**: Installs both main requirements and UI requirements

## Quick Start

1. **Build and run the services:**
   ```bash
   docker-compose up --build
   ```

2. **Access the applications:**
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
- Runs as root user (no user creation)
- No health checks for simplicity

### Docker Compose Features
- Two services: `rag-app` and `streamlit-ui`
- Shared network: `business-rag-network`
- Volume mounts for data persistence
- No health checks or service dependencies
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