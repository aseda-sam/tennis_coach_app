# Deployment Guide

This guide covers deploying the Tennis Coach App backend to production environments.

## Overview

The backend is designed to be deployed as a containerized application with support for multiple environments and database configurations.

## Prerequisites

- Docker and Docker Compose
- Database (SQLite for development, PostgreSQL for production)
- File storage (local filesystem or cloud storage)
- Environment variables configured

## Environment Configuration

### Required Environment Variables

Create a `.env.production` file:

```bash
# Database
DATABASE_URL=postgresql://user:password@host:5432/tennis_analysis
# OR for SQLite: sqlite:///./data/database/tennis_coach.db

# Profile Configuration
PROFILE=production

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=False

# File Storage
UPLOAD_DIR=./data/videos/raw
PROCESSED_DIR=./data/videos/processed
MAX_FILE_SIZE=104857600  # 100MB

# CORS (for frontend integration)
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# Security
SECRET_KEY=your-production-secret-key-here
```

### Optional Environment Variables

```bash
# Processing Configuration
MAX_WORKERS=4
BATCH_SIZE=10
CONFIDENCE_THRESHOLD=0.5

# Ball Contact Configuration
BALL_CONTACT_TIMESTAMP_TOLERANCE=0.1

# Logging
DEBUG=False
```

## Docker Deployment

### Build Production Image

```bash
# Build the Docker image
docker build -t tennis-backend:latest .

# Tag for registry
docker tag tennis-backend:latest your-registry/tennis-backend:latest
```

### Run with Docker Compose

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  backend:
    build: .
    ports:
      - "8000:8000"
    environment:
      - PROFILE=production
      - DATABASE_URL=postgresql://user:password@db:5432/tennis_analysis
      - DEBUG=False
    volumes:
      - ./data:/app/data
    depends_on:
      - db
    restart: unless-stopped

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=tennis_analysis
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

volumes:
  postgres_data:
```

```bash
# Deploy with Docker Compose
docker-compose -f docker-compose.prod.yml up -d
```

### Run Standalone Container

```bash
# Run with environment variables
docker run -p 8000:8000 \
  -e PROFILE=production \
  -e DATABASE_URL=postgresql://user:password@host:5432/tennis_analysis \
  -e MAX_FILE_SIZE=104857600 \
  -e DEBUG=False \
  -v $(pwd)/data:/app/data \
  tennis-backend:latest
```

## Cloud Deployment

### Render.com

1. **Connect Repository**: Link your GitHub repository to Render
2. **Create Web Service**: Choose "Web Service" and select your repository
3. **Configure Environment**:
   - **Build Command**: `pip install -e .`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Environment**: `Python 3.11`
4. **Set Environment Variables**:
   - `PROFILE`: `production`
   - `DATABASE_URL`: Your PostgreSQL connection string
   - `DEBUG`: `False`
   - `SECRET_KEY`: Generate a secure secret key
5. **Deploy**: Render will automatically build and deploy

### Railway

1. **Connect Repository**: Link your GitHub repository to Railway
2. **Create Project**: Create a new project from your repository
3. **Add Database**: Add a PostgreSQL database service
4. **Configure Environment Variables**:
   - `PROFILE`: `production`
   - `DATABASE_URL`: Use the generated PostgreSQL URL
   - `DEBUG`: `False`
5. **Deploy**: Railway will automatically deploy

### AWS/GCP/Azure

For cloud providers, use container orchestration:

```bash
# Example for AWS ECS
aws ecs create-service \
  --cluster your-cluster \
  --service-name tennis-backend \
  --task-definition tennis-backend:1 \
  --desired-count 1
```

## Database Setup

### PostgreSQL (Production)

```sql
-- Create database
CREATE DATABASE tennis_analysis;

-- Create user
CREATE USER tennis_user WITH PASSWORD 'secure_password';

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE tennis_analysis TO tennis_user;
```

### Run Migrations

```bash
# Apply database migrations
alembic upgrade head

# Or run in container
docker exec tennis-backend alembic upgrade head
```

## File Storage

### Local Filesystem

```bash
# Create data directories
mkdir -p data/videos/raw data/videos/processed data/database

# Set permissions
chmod 755 data/videos/raw data/videos/processed
```

### Cloud Storage (Future)

For production scale, consider cloud storage:

- **AWS S3**: Scalable object storage
- **Google Cloud Storage**: Integrated with GCP
- **Azure Blob Storage**: Integrated with Azure

## Health Checks

### Application Health

```bash
# Check if application is running
curl http://localhost:8000/health

# Expected response
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Database Health

```bash
# Check database connection
curl http://localhost:8000/v0

# Expected response includes database status
```

## Monitoring

### Logs

```bash
# View application logs
docker logs tennis-backend

# Follow logs
docker logs -f tennis-backend
```

### Metrics

The application provides basic metrics:

- Request processing time
- Error rates
- Database connection status

## Security Considerations

### Environment Variables

- Never commit `.env` files to version control
- Use secure secret keys for production
- Rotate secrets regularly

### CORS Configuration

```bash
# Restrict CORS to your domain only
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

### Database Security

- Use strong passwords
- Enable SSL connections
- Restrict database access by IP
- Regular security updates

## Performance Optimization

### Production Settings

```bash
# Optimize for production
PROFILE=production
DEBUG=False
DEBUG=False
MAX_WORKERS=4
```

### Resource Limits

```yaml
# Docker Compose resource limits
services:
  backend:
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '0.5'
```

## Backup Strategy

### Database Backup

```bash
# PostgreSQL backup
pg_dump tennis_analysis > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore
psql tennis_analysis < backup_20240115_103000.sql
```

### File Backup

```bash
# Backup video files
tar -czf videos_backup_$(date +%Y%m%d_%H%M%S).tar.gz data/videos/
```

## Troubleshooting

### Common Issues

#### Port Already in Use

```bash
# Check what's using the port
lsof -i :8000

# Kill process if needed
kill -9 <PID>
```

#### Database Connection Issues

```bash
# Test database connection
python -c "from app.core.database import engine; print(engine.execute('SELECT 1').fetchone())"
```

#### File Permission Issues

```bash
# Fix file permissions
chmod -R 755 data/
chown -R app:app data/
```

### Debug Mode

```bash
# Enable debug logging
export DEBUG=True
export DEBUG=True

# Start with debug
uvicorn app.main:app --reload --log-level debug
```

## Scaling

### Horizontal Scaling

For high traffic, consider:

- Load balancer (nginx, HAProxy)
- Multiple application instances
- Database connection pooling
- Redis for session storage

### Vertical Scaling

- Increase memory and CPU
- Optimize database queries
- Use faster storage (SSD)
- Enable database indexing

## Maintenance

### Regular Tasks

- Monitor disk space usage
- Check application logs for errors
- Update dependencies regularly
- Backup database and files
- Monitor performance metrics

### Updates

```bash
# Update application
git pull origin main
docker-compose down
docker-compose up --build -d

# Run migrations if needed
docker exec tennis-backend alembic upgrade head
```

## Support

- **Issues**: Check application logs and health endpoints
- **Development**: See [backend README](../README.md) for local setup
- **API**: See [API documentation](api.md) for endpoint details
