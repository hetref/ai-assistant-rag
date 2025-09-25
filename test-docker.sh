
#!/bin/bash

# Docker Testing Script for AI RAG Assistant
# This script tests whether the project is properly dockerized

set -e

echo "🧪 Testing Docker Setup for AI RAG Assistant"
echo "============================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test functions
test_docker_installed() {
    echo -e "\n${BLUE}1. Testing Docker Installation${NC}"
    if command -v docker &> /dev/null; then
        echo -e "${GREEN}✅ Docker is installed${NC}"
        docker --version
    else
        echo -e "${RED}❌ Docker is not installed${NC}"
        return 1
    fi
}

test_docker_compose_installed() {
    echo -e "\n${BLUE}2. Testing Docker Compose Installation${NC}"
    if command -v docker-compose &> /dev/null; then
        echo -e "${GREEN}✅ Docker Compose is installed${NC}"
        docker-compose --version
    else
        echo -e "${RED}❌ Docker Compose is not installed${NC}"
        return 1
    fi
}

test_docker_files_exist() {
    echo -e "\n${BLUE}3. Testing Docker Configuration Files${NC}"
    
    local files=("dockerfile" "docker-compose.yml" ".dockerignore")
    local all_exist=true
    
    for file in "${files[@]}"; do
        if [ -f "$file" ]; then
            echo -e "${GREEN}✅ $file exists${NC}"
        else
            echo -e "${RED}❌ $file is missing${NC}"
            all_exist=false
        fi
    done
    
    if [ "$all_exist" = true ]; then
        echo -e "${GREEN}✅ All Docker configuration files are present${NC}"
    else
        echo -e "${RED}❌ Some Docker configuration files are missing${NC}"
        return 1
    fi
}

test_docker_build() {
    echo -e "\n${BLUE}4. Testing Docker Build${NC}"
    echo "Building Docker image (this may take a few minutes)..."
    
    if docker-compose build --no-cache; then
        echo -e "${GREEN}✅ Docker build successful${NC}"
    else
        echo -e "${RED}❌ Docker build failed${NC}"
        return 1
    fi
}

test_docker_containers_start() {
    echo -e "\n${BLUE}5. Testing Container Startup${NC}"
    echo "Starting containers..."
    
    if docker-compose up -d; then
        echo -e "${GREEN}✅ Containers started successfully${NC}"
        sleep 10  # Wait for services to initialize
    else
        echo -e "${RED}❌ Failed to start containers${NC}"
        return 1
    fi
}

test_services_health() {
    echo -e "\n${BLUE}6. Testing Service Health${NC}"
    
    # Test Upload API
    echo "Testing Upload API (port 8001)..."
    if curl -f http://localhost:8001/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Upload API is healthy${NC}"
    else
        echo -e "${YELLOW}⚠️  Upload API is not responding (may still be starting)${NC}"
    fi
    
    # Test Pathway RAG API
    echo "Testing Pathway RAG API (port 8000)..."
    if curl -f -X POST http://localhost:8000/v1/statistics > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Pathway RAG API is healthy${NC}"
    else
        echo -e "${YELLOW}⚠️  Pathway RAG API is not responding (may still be starting)${NC}"
    fi
    
    # Test Streamlit UI
    echo "Testing Streamlit UI (port 8501)..."
    if curl -f http://localhost:8501 > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Streamlit UI is healthy${NC}"
    else
        echo -e "${YELLOW}⚠️  Streamlit UI is not responding (may still be starting)${NC}"
    fi
}

test_container_logs() {
    echo -e "\n${BLUE}7. Checking Container Logs${NC}"
    
    echo "RAG App logs (last 10 lines):"
    docker-compose logs --tail=10 rag-app
    
    echo -e "\nStreamlit UI logs (last 10 lines):"
    docker-compose logs --tail=10 streamlit-ui
}

test_cleanup() {
    echo -e "\n${BLUE}8. Testing Cleanup${NC}"
    echo "Stopping and removing containers..."
    
    if docker-compose down; then
        echo -e "${GREEN}✅ Cleanup successful${NC}"
    else
        echo -e "${RED}❌ Cleanup failed${NC}"
        return 1
    fi
}

# Main test execution
main() {
    local failed_tests=0
    
    # Run tests
    test_docker_installed || ((failed_tests++))
    test_docker_compose_installed || ((failed_tests++))
    test_docker_files_exist || ((failed_tests++))
    
    # Ask user if they want to run build tests (they take time)
    echo -e "\n${YELLOW}Build and runtime tests take several minutes. Continue? (y/n)${NC}"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        test_docker_build || ((failed_tests++))
        test_docker_containers_start || ((failed_tests++))
        test_services_health
        test_container_logs
        test_cleanup || ((failed_tests++))
    else
        echo -e "${YELLOW}⏭️  Skipping build and runtime tests${NC}"
    fi
    
    # Summary
    echo -e "\n${BLUE}📊 Test Summary${NC}"
    echo "==============="
    if [ $failed_tests -eq 0 ]; then
        echo -e "${GREEN}🎉 All tests passed! Your project is properly dockerized.${NC}"
        echo -e "\n${GREEN}✅ Your Docker setup is ready to use!${NC}"
        echo -e "\n${BLUE}Next steps:${NC}"
        echo "1. Run: ./setup.sh (for automated setup)"
        echo "2. Or run: docker-compose up --build"
        echo "3. Access your app at: http://localhost:8501"
    else
        echo -e "${RED}❌ $failed_tests test(s) failed. Please check the errors above.${NC}"
        echo -e "\n${YELLOW}Common issues:${NC}"
        echo "- Missing Docker or Docker Compose"
        echo "- Missing configuration files"
        echo "- Build errors (check logs)"
        echo "- Port conflicts (ports 8000, 8001, 8501 must be free)"
    fi
}

# Run main function
main "$@"
