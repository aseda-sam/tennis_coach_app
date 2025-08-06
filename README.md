# Tennis Computer Vision Analysis System

A computer vision-based tennis analysis system that demonstrates data engineering and AI evaluation skills. Process tennis videos to extract meaningful insights about player performance, ball trajectory, and court positioning.

## 🎾 Features

- **Video Upload & Processing**: Batch analysis of tennis video clips (30-60 seconds)
- **Ball Tracking**: YOLO-based ball detection with trajectory analysis
- **Player Positioning**: MediaPipe pose estimation for court position analysis
- **Stroke Detection**: Basic forehand identification and analysis
- **Metrics Dashboard**: Visualization of key tennis performance metrics
- **Historical Analysis**: Store and compare analysis results over time

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Node.js 16+
- M1 MacBook Pro (GPU acceleration available)

### Local Development

1. **Clone and Setup**
```bash
git clone <repository-url>
cd tennis_coach_app_2

# Create Python virtual environment
python3 -m venv tennis_env
source tennis_env/bin/activate
```

2. **Backend Setup**
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

3. **Frontend Setup**
```bash
cd frontend
npm install
npm start
```

4. **Access the Application**
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Frontend**: http://localhost:3000

## 📁 Project Structure

```
tennis_coach_app_2/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── api/            # API routes and models
│   │   ├── core/           # Configuration and database
│   │   ├── services/       # Business logic
│   │   └── utils/          # Helper functions
│   └── requirements.txt
├── frontend/               # React frontend
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── pages/          # Page components
│   │   └── utils/          # Frontend utilities
│   └── package.json
├── data/                   # Data storage
│   ├── videos/             # Video files
│   ├── database/           # SQLite database
│   └── analysis_cache/     # Processing cache
├── project_docs/           # Project documentation
└── tests/                  # Test files
```

## 🛠 Tech Stack

- **Backend**: FastAPI (Python)
- **Frontend**: React
- **Computer Vision**: YOLO + MediaPipe
- **Database**: SQLite (MVP) → PostgreSQL (later)
- **Storage**: Local file system → S3/MinIO (later)
- **Processing**: Batch processing with background tasks

## 📊 Key Metrics Tracked

- Ball trajectory and speed
- Player court positioning (baseline vs service line)
- Stroke count and types
- Rally duration and patterns
- Court coverage heatmaps

## 🎯 Portfolio Highlights

This project demonstrates:
- **Computer Vision Pipeline Development**: YOLO ball detection, MediaPipe pose estimation
- **Data Engineering**: FastAPI backend, SQLite database, batch processing
- **Full-Stack Development**: React frontend with real-time updates
- **Scalable Architecture**: Modular design for future enhancements
- **Real-World Application**: Tennis performance analysis

## 📚 Documentation

- [Project Overview](project_docs/README.md)
- [API Documentation](project_docs/api_documentation.md)
- [Database Schema](project_docs/database_schema.md)
- [Deployment Guide](project_docs/deployment_guide.md)

## 🔧 Development

### Backend Development
```bash
cd backend
# Install dependencies
pip install -r requirements.txt

# Run development server
uvicorn app.main:app --reload

# Run tests
pytest

# Database migrations
alembic upgrade head
```

### Frontend Development
```bash
cd frontend
# Install dependencies
npm install

# Start development server
npm start

# Run tests
npm test

# Build for production
npm run build
```

## 🚀 Deployment

### Local Development
- Backend: http://localhost:8000
- Frontend: http://localhost:3000

### Cloud Deployment Options
- **Railway**: Free tier available
- **Render**: Free tier available
- **Vercel**: Frontend deployment
- **AWS**: Full production setup

See [Deployment Guide](project_docs/deployment_guide.md) for detailed instructions.

## 🎾 Tennis Analysis Features

### Current MVP Features
- ✅ Video upload and processing
- ✅ Ball tracking with YOLO
- ✅ Player pose estimation
- ✅ Basic forehand detection
- ✅ Court position analysis
- ✅ Metrics dashboard

### Future Enhancements
- 🔄 Backhand and serve detection
- 🔄 Real-time processing
- 🔄 Advanced stroke analysis
- 🔄 Player comparison features
- 🔄 Cloud deployment

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is for portfolio demonstration purposes.

## 🎯 Success Metrics

### Technical Goals
- [ ] Process 30-60 second tennis videos successfully
- [ ] Detect and track tennis ball with 80%+ accuracy
- [ ] Identify player position on court correctly
- [ ] Detect forehand strokes with reasonable accuracy
- [ ] Generate meaningful tennis performance metrics

### Portfolio Goals
- [ ] Clean, well-documented codebase
- [ ] Demonstrates data engineering best practices
- [ ] Shows computer vision pipeline development
- [ ] Scalable architecture design
- [ ] Professional project presentation

---

**Built with ❤️ for tennis and data engineering** 