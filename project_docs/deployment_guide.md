# Deployment Guide

## Overview

This guide covers deployment options for the Tennis Analysis System, from local development to cloud deployment, including CI/CD pipeline setup.

## CI/CD Pipeline

### GitHub Actions Setup

The project includes a comprehensive CI/CD pipeline using GitHub Actions with the following workflows:

#### 1. Continuous Integration (CI)
**File**: `.github/workflows/ci.yml`

Runs on every push and pull request to ensure code quality:

- **Backend Testing**:
  - Python 3.11 environment setup
  - Dependency installation with caching
  - Ruff linting and formatting checks
  - Pytest execution
  - Code quality enforcement

- **Frontend Testing**:
  - Node.js 20 environment setup
  - npm dependency installation with caching
  - Build verification
  - Test execution with coverage
  - TypeScript compilation check

#### 2. Frontend Deployment
**File**: `.github/workflows/deploy-frontend.yml`

Automatically deploys the React frontend to GitHub Pages on main branch pushes:

- Triggers on frontend changes
- Builds production bundle
- Deploys to GitHub Pages
- Provides deployment URL

#### 3. Docker Containerization
**File**: `.github/workflows/docker-publish.yml`

Builds and publishes Docker images to GitHub Container Registry:

- Multi-platform Docker builds
- Automatic versioning
- GitHub Container Registry integration
- Health check validation

### Docker Setup

#### Recent Docker Improvements ✅
- **Fixed casing issues** - All `FROM ... AS` statements use consistent uppercase
- **Improved layer caching** - Better organization for faster builds
- **Added `.dockerignore` files** - Reduced build context size
- **Updated health checks** - Now uses existing `/api/videos/` endpoint
- **Enhanced error handling** - Better build process reliability

#### Backend Container
**File**: `Dockerfile`

```dockerfile
# Base stage
FROM python:3.11-slim as base

WORKDIR /app

# Install system dependencies including OpenCV requirements
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY backend/pyproject.toml ./

# Development stage
FROM base as development
COPY backend/ ./backend/
RUN pip install --no-cache-dir -e . && \
    pip install --no-cache-dir pytest ruff
RUN mkdir -p data/videos/raw data/videos/processed data/analysis_cache data/database
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Production stage
FROM base as production
RUN pip install --no-cache-dir -e .
COPY backend/ ./backend/
RUN mkdir -p data/videos/raw data/videos/processed data/analysis_cache data/database
RUN adduser --disabled-password --gecos '' appuser && \
    chown -R appuser:appuser /app
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### Docker Optimization
**File**: `.dockerignore`

Excludes unnecessary files from Docker build context:
- Git files and documentation
- Node.js dependencies
- IDE files and OS artifacts
- Large video files
- Test files and coverage reports

### CI/CD Benefits

1. **Automated Quality Checks**:
   - Code formatting with Ruff
   - Linting for Python and TypeScript
   - Test execution on every change
   - Build verification

2. **Deployment Automation**:
   - Automatic frontend deployment to GitHub Pages
   - Docker image publishing
   - Zero-downtime deployments

3. **Developer Experience**:
   - Fast feedback on code changes
   - Consistent development environment
   - Automated dependency management

4. **Production Readiness**:
   - Containerized deployment
   - Health checks and monitoring
   - Scalable architecture

### Setting Up CI/CD

#### 1. Enable GitHub Actions
- Go to your repository Settings
- Navigate to Actions > General
- Enable "Allow all actions and reusable workflows"

#### 2. Configure Branch Protection
- Go to Settings > Branches
- Add rule for `main` branch
- Enable "Require status checks to pass before merging"
- Select the CI workflow as required

#### 3. Set Up GitHub Pages
- Go to Settings > Pages
- Select "GitHub Actions" as source
- The deployment workflow will automatically configure Pages

#### 4. Configure Container Registry
- Go to Settings > Actions > General
- Enable "Read and write permissions" for Actions
- This allows publishing to GitHub Container Registry

### CI/CD Workflow Triggers

```yaml
# Main CI - runs on all pushes and PRs
on:
  push:
    branches: [ main, develop, feature/** ]
  pull_request:
    branches: [ main ]

# Frontend deployment - only on main branch
on:
  push:
    branches: [ main ]
    paths:
      - 'frontend/**'

# Docker publishing - only on main branch
on:
  push:
    branches: [ main ]
    paths:
      - 'backend/**'
      - 'Dockerfile'
```

### Monitoring CI/CD

#### GitHub Actions Dashboard
- View workflow runs at `https://github.com/{owner}/{repo}/actions`
- Monitor build times and success rates
- Debug failed builds with detailed logs

#### Deployment Status
- Frontend: Check GitHub Pages settings for deployment URL
- Docker: View published images in GitHub Container Registry
- Backend: Monitor container health checks

### Troubleshooting CI/CD

#### Common Issues

1. **Build Failures**:
   ```bash
   # Check local environment matches CI
   cd backend
   ruff check .
   pytest
   
   cd ../frontend
   npm run build
   npm test
   ```

2. **Docker Build Issues**:
   ```bash
   # Test Docker build locally
   docker build -t tennis-backend .
   docker run -p 8000:8000 tennis-backend
   ```

3. **Deployment Failures**:
   - Check GitHub Pages settings
   - Verify repository permissions
   - Review workflow logs for specific errors

#### Performance Optimization

1. **Cache Dependencies**:
   - Python: Uses pip cache with pyproject.toml
   - Node.js: Uses npm cache with package-lock.json
   - Docker: Multi-stage builds for efficiency

2. **Parallel Execution**:
   - Backend and frontend jobs run in parallel
   - Concurrency controls prevent resource conflicts
   - Cancels in-progress builds on new commits

3. **Selective Triggers**:
   - Path-based triggers reduce unnecessary builds
   - Branch-specific deployments
   - Conditional job execution

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

#### Development Docker Compose
```yaml
# docker-compose.yml (Development)
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data  # Bind mount for easy development access
      - ./backend:/app/backend  # Hot reload
    environment:
      - DATABASE_URL=sqlite:///./data/database/tennis_analysis.db
    depends_on:
      - redis

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    volumes:
      - ./frontend:/app
      - /app/node_modules
    depends_on:
      - backend

  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  redis_data:
```

#### Production Docker Compose
```yaml
# docker-compose.prod.yml (Production)
version: '3.8'

services:
  backend:
    image: ghcr.io/your-repo/backend:latest
    ports:
      - "8000:8000"
    volumes:
      - app_data:/app/data  # Named volume for production
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/tennis_analysis
      - UPLOAD_DIR=/app/data/videos/raw
      - PROCESSED_DIR=/app/data/videos/processed
    depends_on:
      - db
      - redis
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'

  frontend:
    image: ghcr.io/your-repo/frontend:latest
    ports:
      - "80:80"
    depends_on:
      - backend
    restart: unless-stopped

  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=tennis_analysis
      - POSTGRES_USER=tennisuser
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:alpine
    volumes:
      - redis_data:/data
    restart: unless-stopped

volumes:
  app_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /opt/tennis-app/data  # Dedicated server path
  postgres_data:
  redis_data:
```

#### Volume Management Strategy

**Development (Bind Mounts)**:
- Easy file access for debugging
- Direct host filesystem access
- Perfect for development workflow

**Production (Named Volumes)**:
- Docker-managed storage optimization
- Better performance and reliability
- Proper backup and recovery support

#### Volume Operations
```bash
# Backup production data
docker run --rm -v tennis_app_data:/data -v $(pwd):/backup alpine tar czf /backup/app-data-backup.tar.gz /data

# Restore production data
docker run --rm -v tennis_app_data:/data -v $(pwd):/backup alpine tar xzf /backup/app-data-backup.tar.gz -C /

# Migrate from development to production
docker run --rm -v ./data:/source -v tennis_app_data:/dest alpine cp -r /source/* /dest/
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