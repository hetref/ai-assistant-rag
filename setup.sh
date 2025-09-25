#!/bin/bash

# AI RAG Assistant Docker Setup Script
# This script helps you set up and run the AI RAG Assistant using Docker

set -e

echo "🚀 AI RAG Assistant Docker Setup"
echo "================================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    echo "   Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    echo "   Visit: https://docs.docker.com/compose/install/"
    exit 1
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    cat > .env << EOF
# OpenAI API Key - Required for LLM functionality
OPENAI_API_KEY=your_openai_api_key_here

# Data directory configuration
DATA_DIR=/app/data

# Pathway configuration
PATHWAY_HOST=0.0.0.0
PATHWAY_PORT=8000

# Streamlit configuration
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_ADDRESS=0.0.0.0
EOF
    echo "✅ Created .env file. Please edit it and add your OpenAI API key."
    echo "   Edit: nano .env"
    echo ""
    read -p "Press Enter after you've updated the .env file with your OpenAI API key..."
fi

# Create necessary directories
echo "📁 Creating necessary directories..."
mkdir -p data/businesses
mkdir -p Cache

# Build and start the services
echo "🔨 Building and starting Docker services..."
docker-compose up --build -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Check service health
echo "🔍 Checking service health..."
if curl -f http://localhost:8001/health > /dev/null 2>&1; then
    echo "✅ Upload API is running on http://localhost:8001"
else
    echo "⚠️  Upload API might still be starting up..."
fi

if curl -f http://localhost:8000/v1/statistics > /dev/null 2>&1; then
    echo "✅ Pathway RAG API is running on http://localhost:8000"
else
    echo "⚠️  Pathway RAG API might still be starting up..."
fi

if curl -f http://localhost:8501 > /dev/null 2>&1; then
    echo "✅ Streamlit UI is running on http://localhost:8501"
else
    echo "⚠️  Streamlit UI might still be starting up..."
fi

echo ""
echo "🎉 Setup complete!"
echo ""
echo "📊 Access your applications:"
echo "   • Streamlit UI: http://localhost:8501"
echo "   • RAG API: http://localhost:8000"
echo "   • Upload/Search API: http://localhost:8001"
echo ""
echo "🔧 Useful commands:"
echo "   • View logs: docker-compose logs"
echo "   • Stop services: docker-compose down"
echo "   • Restart services: docker-compose restart"
echo "   • Rebuild and start: docker-compose up --build"
echo ""
echo "📚 For more information, see DOCKER_README.md"
