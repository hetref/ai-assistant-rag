# 🚀 Digital Ocean Deployment Guide

Complete guide to deploy the AI Assistant RAG system with Collaborative Filtering on Digital Ocean.

## 📋 Prerequisites

### Digital Ocean Requirements
- **Droplet Size**: Minimum 4GB RAM, 2 CPU cores (recommended: 8GB RAM, 4 CPU cores)
- **Operating System**: Ubuntu 22.04 LTS
- **Storage**: At least 25GB SSD
- **Ports**: 8000, 8001, 8501, 6379 (Redis)

### Local Requirements
- Git configured with your GitHub credentials
- OpenAI API key

## 🔧 Step 1: Create and Setup Digital Ocean Droplet

### 1.1 Create Droplet
```bash
# Via DigitalOcean CLI (optional)
doctl compute droplet create ai-rag-server \
  --image ubuntu-22-04-x64 \
  --size s-2vcpu-4gb \
  --region nyc3 \
  --ssh-keys YOUR_SSH_KEY_ID

# Or use the web interface:
# - Go to DigitalOcean dashboard
# - Click "Create" → "Droplet"  
# - Choose Ubuntu 22.04 LTS
# - Select at least 4GB RAM / 2 CPU
# - Add your SSH key
# - Name it "ai-rag-server"
```

### 1.2 Connect to Your Droplet
```bash
# Replace YOUR_DROPLET_IP with actual IP
ssh root@YOUR_DROPLET_IP
```

## 🛠️ Step 2: Server Setup

### 2.1 System Updates and Dependencies
```bash
# Update system packages
apt update && apt upgrade -y

# Install essential packages
apt install -y curl wget git unzip software-properties-common apt-transport-https ca-certificates gnupg lsb-release

# Install Docker
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

apt update
apt install -y docker-ce docker-ce-cli containerd.io

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Start and enable Docker
systemctl start docker
systemctl enable docker

# Verify installation
docker --version
docker-compose --version
```

### 2.2 Configure Firewall (UFW)
```bash
# Enable UFW
ufw enable

# Allow SSH
ufw allow 22

# Allow application ports
ufw allow 8000  # Pathway RAG API
ufw allow 8001  # FastAPI Upload/Search API  
ufw allow 8501  # Streamlit UI
ufw allow 6379  # Redis (optional, for external access)

# Allow HTTP/HTTPS for potential reverse proxy
ufw allow 80
ufw allow 443

# Check firewall status
ufw status
```

## 📦 Step 3: Deploy Your Application

### 3.1 Clone Your Repository
```bash
# Create application directory
mkdir -p /opt/ai-rag
cd /opt/ai-rag

# Clone your specific branch
git clone -b shoto-the-rag-model https://github.com/hetref/ai-assistant-rag.git .

# Verify files are present
ls -la
```

### 3.2 Set Environment Variables
```bash
# Create production environment file
cat > .env << EOF
# OpenAI Configuration
OPENAI_API_KEY=your_actual_openai_api_key_here

# Application Configuration
DATA_DIR=/app/data
PATHWAY_HOST=0.0.0.0
PATHWAY_PORT=8000
REDIS_URL=redis://redis:6379

# Production Settings
ENVIRONMENT=production
EOF

# Secure the environment file
chmod 600 .env
```

### 3.3 Configure Docker Compose for Production
```bash
# Create production docker-compose override
cat > docker-compose.prod.yml << EOF
version: '3.8'

services:
  rag-app:
    restart: always
    environment:
      - ENVIRONMENT=production
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  redis:
    restart: always
    # Uncomment for Redis persistence
    # command: redis-server --appendonly yes --save 900 1 --save 300 10
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  streamlit-ui:
    restart: always
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
EOF
```

## 🚀 Step 4: Build and Deploy

### 4.1 Build Docker Images
```bash
# Build the application
docker-compose -f docker-compose.yml -f docker-compose.prod.yml build

# This will take 5-10 minutes depending on your droplet size
```

### 4.2 Start Services
```bash
# Start all services in detached mode
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Check service status
docker-compose ps

# Monitor logs (optional)
docker-compose logs -f
```

### 4.3 Verify Deployment
```bash
# Check if all containers are running
docker ps

# Test health endpoints
curl http://localhost:8001/health
curl http://localhost:8000/v1/statistics

# Test Streamlit UI (from another terminal)
curl http://localhost:8501
```

## 🔍 Step 5: Access Your Application

### 5.1 Web Access
- **Main UI**: `http://YOUR_DROPLET_IP:8501`
- **API Documentation**: `http://YOUR_DROPLET_IP:8001/docs`
- **Health Check**: `http://YOUR_DROPLET_IP:8001/health`
- **Analytics Dashboard**: `http://YOUR_DROPLET_IP:8501/analytics_dashboard`

### 5.2 Test Collaborative Filtering
```bash
# Test CF endpoints
curl -X POST http://YOUR_DROPLET_IP:8001/search-businesses \
  -H "Content-Type: application/json" \
  -d '{
    "user_lat": 37.7749,
    "user_lng": -122.4194, 
    "query": "coffee shops",
    "include_recommendations": true
  }'

# Test Redis
docker exec business-rag-redis redis-cli ping
```

## 🔧 Step 6: Production Optimizations

### 6.1 Setup Nginx Reverse Proxy (Recommended)
```bash
# Install Nginx
apt install -y nginx

# Create configuration
cat > /etc/nginx/sites-available/ai-rag << EOF
server {
    listen 80;
    server_name YOUR_DOMAIN_OR_IP;

    # Main Streamlit UI
    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$http_host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 86400;
    }

    # API endpoints
    location /api/ {
        proxy_pass http://localhost:8001/;
        proxy_set_header Host \$http_host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # Pathway RAG API
    location /pathway/ {
        proxy_pass http://localhost:8000/;
        proxy_set_header Host \$http_host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# Enable site
ln -s /etc/nginx/sites-available/ai-rag /etc/nginx/sites-enabled/
rm /etc/nginx/sites-enabled/default

# Test and restart Nginx
nginx -t
systemctl restart nginx
systemctl enable nginx
```

### 6.2 Setup SSL with Let's Encrypt (Optional)
```bash
# Install Certbot
snap install --classic certbot

# Get SSL certificate (replace YOUR_DOMAIN with actual domain)
certbot --nginx -d YOUR_DOMAIN

# Auto-renewal is set up automatically
certbot renew --dry-run
```

### 6.3 Setup Monitoring and Logging
```bash
# Create log monitoring script
cat > /opt/ai-rag/monitor.sh << 'EOF'
#!/bin/bash
echo "=== AI RAG System Status ==="
echo "Date: $(date)"
echo ""

echo "=== Docker Containers ==="
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""

echo "=== System Resources ==="
free -h
df -h /
echo ""

echo "=== Service Logs (Last 10 lines) ==="
echo "--- RAG App ---"
docker logs --tail 10 business-rag-app 2>/dev/null || echo "Container not running"
echo "--- Redis ---"  
docker logs --tail 10 business-rag-redis 2>/dev/null || echo "Container not running"
echo "--- Streamlit UI ---"
docker logs --tail 10 business-rag-ui 2>/dev/null || echo "Container not running"
EOF

chmod +x /opt/ai-rag/monitor.sh

# Add to crontab for regular monitoring
crontab -e
# Add this line: */15 * * * * /opt/ai-rag/monitor.sh >> /var/log/ai-rag-monitor.log 2>&1
```

## 🔄 Step 7: Maintenance and Updates

### 7.1 Update Application
```bash
cd /opt/ai-rag

# Pull latest changes
git pull origin shoto-the-rag-model

# Rebuild and restart
docker-compose -f docker-compose.yml -f docker-compose.prod.yml build
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### 7.2 Backup Data
```bash
# Create backup script
cat > /opt/ai-rag/backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/backups/ai-rag"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup Redis data
docker exec business-rag-redis redis-cli BGSAVE
sleep 5
docker cp business-rag-redis:/data/dump.rdb $BACKUP_DIR/redis_$DATE.rdb

# Backup application data
docker run --rm -v ai-assistant-rag_rag-data:/data -v $BACKUP_DIR:/backup alpine tar czf /backup/app_data_$DATE.tar.gz -C /data .

# Keep only last 7 days of backups
find $BACKUP_DIR -type f -mtime +7 -delete

echo "Backup completed: $DATE"
EOF

chmod +x /opt/ai-rag/backup.sh

# Add to daily crontab
# 0 2 * * * /opt/ai-rag/backup.sh >> /var/log/ai-rag-backup.log 2>&1
```

### 7.3 Common Commands
```bash
# View logs
docker-compose logs -f [service_name]

# Restart specific service
docker-compose restart rag-app

# Scale services (if needed)
docker-compose up -d --scale streamlit-ui=2

# Clean up old images
docker system prune -a

# Check Redis data
docker exec -it business-rag-redis redis-cli
# In Redis CLI: KEYS *, INFO memory
```

## 🚨 Troubleshooting

### Common Issues and Solutions

**1. Out of Memory**
```bash
# Check memory usage
free -h
docker stats

# Add swap space
fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' | tee -a /etc/fstab
```

**2. Port Conflicts**
```bash
# Check what's using ports
netstat -tulpn | grep -E ':(8000|8001|8501|6379)'

# Kill conflicting processes
sudo fuser -k 8000/tcp
```

**3. Docker Build Fails**
```bash
# Clean Docker cache
docker system prune -a

# Build with no cache
docker-compose build --no-cache

# Check disk space
df -h
```

**4. Collaborative Filtering Not Working**
```bash
# Check Redis connection
docker exec business-rag-redis redis-cli ping

# Check CF status
curl http://localhost:8001/health | jq .collaborative_filtering

# View CF logs
docker logs business-rag-app | grep -i collaborative
```

## 📊 Performance Monitoring

### Key Metrics to Monitor
- **Memory Usage**: Should stay under 80% of available RAM
- **Redis Memory**: Monitor with `docker exec business-rag-redis redis-cli info memory`
- **Response Times**: API endpoints should respond < 2 seconds
- **Error Rates**: Check application logs for errors

### Monitoring Commands
```bash
# System overview
htop

# Docker resources
docker stats

# Application health
curl http://localhost:8001/health
curl http://localhost:8001/analytics/cf-performance

# Redis monitoring
docker exec business-rag-redis redis-cli --latency
```

## 🎯 Next Steps

1. **Domain Setup**: Point your domain to the droplet IP
2. **SSL Certificate**: Set up HTTPS with Let's Encrypt
3. **Monitoring**: Install Grafana/Prometheus for advanced monitoring
4. **Scaling**: Consider load balancing for high traffic
5. **Backup Strategy**: Implement automated backups to DigitalOcean Spaces

## 📞 Support

If you encounter issues:

1. Check the logs: `docker-compose logs -f`
2. Verify system resources: `free -h` and `df -h`
3. Test individual services: `curl http://localhost:8001/health`
4. Check the troubleshooting section above

---

**Your AI Assistant RAG system with Collaborative Filtering is now running on Digital Ocean! 🚀**

Access your application at: `http://YOUR_DROPLET_IP:8501`
