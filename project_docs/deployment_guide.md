# Deployment Guide

## Overview

This guide covers deployment options for the Tennis Analysis System, from local development to cloud deployment.

## Local Development Setup

### Prerequisites

#### System Requirements
- **OS**: macOS (M1 MacBook Pro recommended)
- **Python**: 3.8+ (3.11 recommended)
- **Node.js**: 16+ (18+ recommended)
- **Git**: Latest version
- **Docker**: Optional (for containerized deployment)

#### Hardware Requirements
- **RAM**: 8GB minimum, 16GB recommended
- **Storage**: 10GB free space
- **GPU**: M1 GPU acceleration available (optional)

### Environment Setup

#### 1. Python Environment
```bash
# Create virtual environment
python3 -m venv tennis_env
source tennis_env/bin/activate

# Install Python dependencies
cd backend
pip install -r requirements.txt
```

#### 2. Node.js Environment
```bash
# Install frontend dependencies
cd frontend
npm install
```

#### 3. Database Setup
```bash
# Create database directory
mkdir -p data/database

# Initialize database (will be done by Alembic)
cd backend
alembic upgrade head
```

### Development Server Startup

#### Backend (FastAPI)
```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend (React)
```bash
cd frontend
npm start
```

#### Access Points
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Frontend**: http://localhost:3000

## Production Deployment Options

### Option 1: Simple Cloud Deployment (Recommended for Portfolio)

#### Railway (Free Tier Available)
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login to Railway
railway login

# Deploy backend
cd backend
railway init
railway up

# Deploy frontend
cd ../frontend
railway init
railway up
```

#### Render (Free Tier Available)
```yaml
# render.yaml
services:
  - type: web
    name: tennis-analysis-backend
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: DATABASE_URL
        value: sqlite:///./data/database/tennis_analysis.db
```

#### Vercel (Frontend Only)
```bash
# Deploy frontend to Vercel
cd frontend
vercel --prod
```

### Option 2: Docker Deployment

#### Docker Compose Setup
```yaml
# docker-compose.yml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
    environment:
      - DATABASE_URL=sqlite:///./data/database/tennis_analysis.db
    depends_on:
      - redis

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    depends_on:
      - backend

  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
```

#### Backend Dockerfile
```dockerfile
# backend/Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### Frontend Dockerfile
```dockerfile
# frontend/Dockerfile
FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

EXPOSE 3000

CMD ["npm", "start"]
```

### Option 3: AWS Deployment (Advanced)

#### AWS Architecture
```
Internet Gateway → Application Load Balancer → ECS Fargate → RDS PostgreSQL
                                    ↓
                              S3 (Video Storage)
```

#### AWS Services Used
- **ECS Fargate**: Container orchestration
- **RDS**: PostgreSQL database
- **S3**: Video file storage
- **CloudFront**: CDN for static assets
- **Route 53**: DNS management

#### Deployment Steps
```bash
# Install AWS CLI
brew install awscli

# Configure AWS credentials
aws configure

# Deploy with AWS CDK
cd infrastructure
npm install
cdk deploy
```

## Environment Configuration

### Environment Variables

#### Backend (.env)
```bash
# Database
DATABASE_URL=sqlite:///./data/database/tennis_analysis.db

# File Storage
UPLOAD_DIR=./data/videos/raw
PROCESSED_DIR=./data/videos/processed
MAX_FILE_SIZE=104857600

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=True

# Security
SECRET_KEY=your-secret-key-here
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com

# Processing
MAX_WORKERS=4
BATCH_SIZE=10
```

#### Frontend (.env)
```bash
REACT_APP_API_URL=http://localhost:8000
REACT_APP_WS_URL=ws://localhost:8000
REACT_APP_MAX_FILE_SIZE=104857600
```

### Production Environment Variables
```bash
# Database (Production)
DATABASE_URL=postgresql://user:password@host:5432/tennis_analysis

# Storage (Production)
STORAGE_TYPE=s3
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_S3_BUCKET=tennis-analysis-videos

# Security (Production)
SECRET_KEY=your-production-secret-key
CORS_ORIGINS=https://yourdomain.com
```

## Monitoring and Logging

### Application Monitoring
```python
# backend/app/core/monitoring.py
import logging
from fastapi import Request
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def log_request(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    logger.info(f"{request.method} {request.url.path} - {response.status_code} - {process_time:.3f}s")
    return response
```

### Health Checks
```python
# backend/app/api/routes/health.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }
```

## Security Considerations

### Development Security
- Use environment variables for secrets
- Implement CORS properly
- Validate all inputs
- Use HTTPS in production

### Production Security
- Use managed databases
- Implement proper authentication
- Set up SSL certificates
- Configure firewall rules
- Regular security updates

## Performance Optimization

### Backend Optimization
```python
# Use async/await for I/O operations
# Implement caching with Redis
# Use connection pooling for database
# Optimize video processing with multiprocessing
```

### Frontend Optimization
```javascript
// Implement lazy loading
// Use React.memo for expensive components
// Optimize bundle size
// Implement proper error boundaries
```

## Backup and Recovery

### Database Backup
```bash
# SQLite backup
sqlite3 data/database/tennis_analysis.db ".backup backup.db"

# PostgreSQL backup (production)
pg_dump $DATABASE_URL > backup.sql
```

### File Backup
```bash
# Backup video files
rsync -av data/videos/ backup/videos/

# Backup configuration
cp .env backup/
```

## Troubleshooting

### Common Issues

#### Port Conflicts
```bash
# Check what's using port 8000
lsof -i :8000

# Kill process if needed
kill -9 <PID>
```

#### Database Issues
```bash
# Reset database
rm data/database/tennis_analysis.db
alembic upgrade head
```

#### Memory Issues
```bash
# Monitor memory usage
htop

# Increase swap if needed
sudo sysctl vm.swappiness=10
```

### Debug Mode
```bash
# Enable debug logging
export DEBUG=True
export LOG_LEVEL=DEBUG

# Start with debug
uvicorn app.main:app --reload --log-level debug
```

## Cost Optimization

### Free Tier Services
- **Railway**: $5/month free tier
- **Render**: Free tier available
- **Vercel**: Free tier for frontend
- **Supabase**: Free PostgreSQL database

### Cost Monitoring
```bash
# Monitor AWS costs
aws ce get-cost-and-usage --time-period Start=2024-01-01,End=2024-01-31 --granularity MONTHLY --metrics BlendedCost
```

## Future Scaling Considerations

### Horizontal Scaling
- Load balancers
- Multiple application instances
- Database read replicas
- CDN for static assets

### Vertical Scaling
- Larger instance types
- More memory allocation
- GPU acceleration for CV processing
- SSD storage for better I/O

### Microservices Architecture
- Separate video processing service
- Dedicated analysis service
- Independent storage service
- API gateway for routing 