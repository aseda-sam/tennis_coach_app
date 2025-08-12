# React Frontend Development Guide - Tennis Analysis System

## Overview

This guide breaks down React frontend development into simple, digestible steps. We'll build a minimal but functional frontend that connects to our FastAPI backend.

**Goal**: Simple React app that can upload videos, display the list, and play videos.

## ✅ **Recent Updates**
- **Video Playback** - Added comprehensive VideoPlayer component with controls
- **Enhanced Testing** - Jest configuration with coverage thresholds
- **Development Tools** - ESLint, Prettier, and type checking scripts  
- **Best Practices** - Comprehensive React development rules in `.cursor/rules/react-frontend.mdc`

## Phase 5: Frontend Development - Step-by-Step

### Step 12A: React Project Setup

#### Task 1: Create React App
```bash
# Create React app in frontend directory
npx create-react-app frontend --template typescript
cd frontend
npm install
```

#### Task 2: Install Dependencies
```bash
# Install required packages
npm install axios react-dropzone
npm install @types/react-dropzone --save-dev
```

#### Task 3: Clean Up Default Files
- Remove default content from `src/App.tsx`
- Remove unused files (logo, test files)
- Update `public/index.html` title

### Step 12B: Basic Component Structure

#### Task 4: Create Component Files
```
frontend/src/
├── components/
│   ├── VideoUpload.tsx
│   ├── VideoList.tsx
│   └── VideoItem.tsx
├── services/
│   └── api.ts
└── types/
    └── video.ts
```

#### Task 5: Define TypeScript Types
**File**: `frontend/src/types/video.ts`
```typescript
export interface VideoInfo {
  filename: string;
  file_size: number;
  content_type?: string;
  duration?: number;
  fps?: number;
  width?: number;
  height?: number;
  frame_count?: number;
  message: string;
}

export interface VideoListItem {
  filename: string;
  file_size: number;
  duration?: number;
  width?: number;
  height?: number;
}
```

#### Task 6: Create API Service
**File**: `frontend/src/services/api.ts`
```typescript
import axios from 'axios';
import { VideoInfo, VideoListItem } from '../types/video';

const API_BASE_URL = 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
});

export const videoApi = {
  // Upload video
  uploadVideo: async (file: File): Promise<VideoInfo> => {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await api.post('/videos/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  // Get all videos
  getVideos: async (): Promise<VideoListItem[]> => {
    const response = await api.get('/videos/');
    return response.data;
  },

  // Get video details
  getVideoDetails: async (filename: string): Promise<VideoInfo> => {
    const response = await api.get(`/videos/${filename}`);
    return response.data;
  },

  // Delete video
  deleteVideo: async (filename: string): Promise<void> => {
    await api.delete(`/videos/${filename}`);
  },
};
```

### Step 12C: Video Upload Component

#### Task 7: Create VideoUpload Component
**File**: `frontend/src/components/VideoUpload.tsx`
```typescript
import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { videoApi } from '../services/api';
import { VideoInfo } from '../types/video';

interface VideoUploadProps {
  onUploadSuccess: (video: VideoInfo) => void;
}

export const VideoUpload: React.FC<VideoUploadProps> = ({ onUploadSuccess }) => {
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    if (acceptedFiles.length === 0) return;

    const file = acceptedFiles[0];
    setUploading(true);
    setError(null);

    try {
      const video = await videoApi.uploadVideo(file);
      onUploadSuccess(video);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setUploading(false);
    }
  }, [onUploadSuccess]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'video/*': ['.mp4', '.mov', '.avi']
    },
    multiple: false
  });

  return (
    <div className="video-upload">
      <h2>Upload Tennis Video</h2>
      
      <div
        {...getRootProps()}
        className={`dropzone ${isDragActive ? 'active' : ''}`}
      >
        <input {...getInputProps()} />
        {uploading ? (
          <p>Uploading...</p>
        ) : (
          <p>
            {isDragActive
              ? 'Drop the video here'
              : 'Drag & drop a video file, or click to select'}
          </p>
        )}
      </div>

      {error && (
        <div className="error">
          Error: {error}
        </div>
      )}
    </div>
  );
};
```

#### Task 8: Add Basic Styling
**File**: `frontend/src/components/VideoUpload.css`
```css
.video-upload {
  margin: 20px;
  padding: 20px;
  border: 1px solid #ccc;
  border-radius: 8px;
}

.dropzone {
  border: 2px dashed #ccc;
  border-radius: 4px;
  padding: 40px;
  text-align: center;
  cursor: pointer;
  transition: border-color 0.3s ease;
}

.dropzone:hover,
.dropzone.active {
  border-color: #007bff;
}

.error {
  color: #dc3545;
  margin-top: 10px;
  padding: 10px;
  background-color: #f8d7da;
  border-radius: 4px;
}
```

### Step 12D: Video List Component

#### Task 9: Create VideoItem Component
**File**: `frontend/src/components/VideoItem.tsx`
```typescript
import React from 'react';
import { VideoListItem } from '../types/video';
import { videoApi } from '../services/api';

interface VideoItemProps {
  video: VideoListItem;
  onDelete: (filename: string) => void;
}

export const VideoItem: React.FC<VideoItemProps> = ({ video, onDelete }) => {
  const handleDelete = async () => {
    if (window.confirm(`Delete ${video.filename}?`)) {
      try {
        await videoApi.deleteVideo(video.filename);
        onDelete(video.filename);
      } catch (error) {
        alert('Failed to delete video');
      }
    }
  };

  const formatFileSize = (bytes: number): string => {
    const mb = bytes / (1024 * 1024);
    return `${mb.toFixed(1)} MB`;
  };

  const formatDuration = (seconds?: number): string => {
    if (!seconds) return 'Unknown';
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  };

  return (
    <div className="video-item">
      <div className="video-info">
        <h3>{video.filename}</h3>
        <p>Size: {formatFileSize(video.file_size)}</p>
        {video.duration && <p>Duration: {formatDuration(video.duration)}</p>}
        {video.width && video.height && (
          <p>Resolution: {video.width}x{video.height}</p>
        )}
      </div>
      
      <div className="video-actions">
        <button onClick={handleDelete} className="delete-btn">
          Delete
        </button>
      </div>
    </div>
  );
};
```

#### Task 10: Create VideoList Component
**File**: `frontend/src/components/VideoList.tsx`
```typescript
import React, { useEffect, useState } from 'react';
import { VideoListItem } from '../types/video';
import { VideoItem } from './VideoItem';
import { videoApi } from '../services/api';

export const VideoList: React.FC = () => {
  const [videos, setVideos] = useState<VideoListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadVideos = async () => {
    try {
      setLoading(true);
      const videoList = await videoApi.getVideos();
      setVideos(videoList);
    } catch (err) {
      setError('Failed to load videos');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadVideos();
  }, []);

  const handleDelete = (filename: string) => {
    setVideos(videos.filter(video => video.filename !== filename));
  };

  const handleUploadSuccess = () => {
    loadVideos(); // Reload the list
  };

  if (loading) {
    return <div>Loading videos...</div>;
  }

  if (error) {
    return <div className="error">Error: {error}</div>;
  }

  return (
    <div className="video-list">
      <h2>Uploaded Videos ({videos.length})</h2>
      
      {videos.length === 0 ? (
        <p>No videos uploaded yet.</p>
      ) : (
        <div className="videos-grid">
          {videos.map(video => (
            <VideoItem
              key={video.filename}
              video={video}
              onDelete={handleDelete}
            />
          ))}
        </div>
      )}
    </div>
  );
};
```

### Step 12E: Main App Component

#### Task 11: Update App Component
**File**: `frontend/src/App.tsx`
```typescript
import React from 'react';
import { VideoUpload } from './components/VideoUpload';
import { VideoList } from './components/VideoList';
import { VideoInfo } from './types/video';
import './App.css';

function App() {
  const handleUploadSuccess = (video: VideoInfo) => {
    console.log('Upload successful:', video);
    // The VideoList component will reload automatically
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>Tennis Analysis System</h1>
      </header>
      
      <main>
        <VideoUpload onUploadSuccess={handleUploadSuccess} />
        <VideoList />
      </main>
    </div>
  );
}

export default App;
```

#### Task 12: Add App Styling
**File**: `frontend/src/App.css`
```css
.App {
  text-align: center;
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.App-header {
  background-color: #282c34;
  padding: 20px;
  color: white;
  margin-bottom: 20px;
  border-radius: 8px;
}

.App-header h1 {
  margin: 0;
  font-size: 2rem;
}

main {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.video-list {
  margin-top: 20px;
}

.videos-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
  margin-top: 20px;
}

.video-item {
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 15px;
  background-color: #f9f9f9;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.video-info h3 {
  margin: 0 0 10px 0;
  font-size: 1.1rem;
}

.video-info p {
  margin: 5px 0;
  color: #666;
  font-size: 0.9rem;
}

.video-actions {
  display: flex;
  gap: 10px;
}

.delete-btn {
  background-color: #dc3545;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
}

.delete-btn:hover {
  background-color: #c82333;
}

.error {
  color: #dc3545;
  background-color: #f8d7da;
  padding: 10px;
  border-radius: 4px;
  margin: 10px 0;
}
```

### Step 12F: Testing and Integration

#### Task 13: Test Backend Connection
```bash
# Start backend server
cd backend
python -m uvicorn app.main:app --reload --port 8000

# In another terminal, start frontend
cd frontend
npm start
```

#### Task 14: Test Upload Functionality
- Upload a video file
- Verify it appears in the list
- Test delete functionality
- Check error handling

#### Task 15: Add Loading States
- Show loading spinner during upload
- Disable upload button while processing
- Add progress indicators

## Development Commands

### Setup
```bash
# Create React app
npx create-react-app frontend --template typescript
cd frontend

# Install dependencies
npm install axios react-dropzone
npm install @types/react-dropzone --save-dev
```

### Development
```bash
# Start development server
npm start

# Build for production
npm run build

# Run tests
npm test
```

### Backend Integration
```bash
# Start backend (in backend directory)
python -m uvicorn app.main:app --reload --port 8000

# Start frontend (in frontend directory)
npm start
```

## Success Criteria

### Functional Requirements
- ✅ Upload video files via drag-and-drop
- ✅ Display list of uploaded videos
- ✅ Show video metadata (size, duration, resolution)
- ✅ Delete videos from list
- ✅ Handle upload errors gracefully
- ✅ Real-time feedback during upload

### Technical Requirements
- ✅ TypeScript for type safety
- ✅ Axios for API communication
- ✅ React Dropzone for file uploads
- ✅ Responsive design
- ✅ Error handling and loading states

### User Experience
- ✅ Simple, intuitive interface
- ✅ Clear feedback for all actions
- ✅ Responsive design for different screen sizes
- ✅ Fast loading and smooth interactions

## Next Steps After Frontend

Once the basic frontend is working:

1. **Test the complete system** - Upload, list, delete videos
2. **Add video playback** - Show uploaded videos
3. **Add analysis results display** - When we add CV features
4. **Enhance UI/UX** - Better styling and animations
5. **Add more features** - Video details, processing status

## Notes

- **Keep it simple** - Focus on functionality over fancy UI
- **Test frequently** - Upload different file types and sizes
- **Handle errors** - Network issues, file validation errors
- **Mobile friendly** - Test on different screen sizes
- **Performance** - Large files should show progress

This frontend will give us a complete working system to test our backend and prepare for computer vision features! 