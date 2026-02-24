# API Integration Documentation

This document describes how the frontend communicates with the backend API, including service layer architecture, error handling, and data flow patterns.

## Overview

The frontend uses a centralized API service layer to communicate with the FastAPI backend. This approach provides:

- **Centralized API configuration**
- **Consistent error handling**
- **Type safety with TypeScript**
- **Request/response interceptors**
- **Automatic retry logic**
- **Loading state management**

## Service Layer Architecture

### Base API Service

The `api.ts` service provides the foundation for all API communication:

```typescript
// services/api.ts
class ApiService {
  private baseURL: string;
  private defaultHeaders: Record<string, string>;

  constructor() {
    this.baseURL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    this.defaultHeaders = {
      'Content-Type': 'application/json',
    };
  }

  async request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
    const url = `${this.baseURL}${endpoint}`;
    const config: RequestInit = {
      ...options,
      headers: {
        ...this.defaultHeaders,
        ...options.headers,
      },
    };

    try {
      const response = await fetch(url, config);

      if (!response.ok) {
        throw new ApiError(response.status, await response.text());
      }

      return await response.json();
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      throw new NetworkError(error.message);
    }
  }
}
```

### API Error Handling

Custom error classes for different error types:

```typescript
// services/api.ts
export class ApiError extends Error {
  constructor(
    public status: number,
    public message: string,
    public details?: any
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export class NetworkError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'NetworkError';
  }
}

export class ValidationError extends Error {
  constructor(
    public field: string,
    message: string
  ) {
    super(message);
    this.name = 'ValidationError';
  }
}
```

## API Endpoints

### Video Management

#### Upload Video

```typescript
// services/videoService.ts
export const uploadVideo = async (file: File): Promise<VideoUploadResponse> => {
  const formData = new FormData();
  formData.append('file', file);

  return api.request<VideoUploadResponse>('/v0/videos/upload', {
    method: 'POST',
    headers: {
      // Don't set Content-Type for FormData
    },
    body: formData,
  });
};
```

#### Get Video List

```typescript
export const getVideos = async (): Promise<Video[]> => {
  return api.request<Video[]>('/v0/videos/');
};
```

#### Get Video Details

```typescript
export const getVideo = async (videoId: number): Promise<Video> => {
  return api.request<Video>(`/v0/videos/${videoId}`);
};
```

#### Delete Video

```typescript
export const deleteVideo = async (videoId: number): Promise<void> => {
  return api.request<void>(`/v0/videos/${videoId}`, {
    method: 'DELETE',
  });
};
```

### Analysis Management

#### Start Analysis

```typescript
// services/analysisService.ts
export const startAnalysis = async (
  videoId: number,
  analysisType: string,
  confidenceThreshold: number = 0.7
): Promise<AnalysisStartResponse> => {
  return api.request<AnalysisStartResponse>(`/v0/analysis/videos/${videoId}`, {
    method: 'POST',
    body: JSON.stringify({
      analysis_type: analysisType,
      confidence_threshold: confidenceThreshold,
    }),
  });
};
```

#### Get Analysis Results

```typescript
export const getAnalysis = async (analysisId: number): Promise<Analysis> => {
  return api.request<Analysis>(`/v0/analysis/${analysisId}`);
};
```

#### Get Video Jobs (DB-backed)

```typescript
export const getVideoJobs = async (
  status?: string
): Promise<VideoJob[]> => {
  return api.request<VideoJob[]>('/v0/videos/jobs', {
    params: status ? { status } : undefined,
  });
};
```

### Ball Contact Management

#### Create Ball Contact

```typescript
// services/ballContactService.ts
export const createBallContact = async (
  contact: CreateBallContactRequest
): Promise<BallContact> => {
  return api.request<BallContact>('/v0/ball-contacts/', {
    method: 'POST',
    body: JSON.stringify(contact),
  });
};
```

#### Get Ball Contacts

```typescript
export const getBallContacts = async (
  videoId: number
): Promise<BallContact[]> => {
  return api.request<BallContact[]>(`/v0/ball-contacts/video/${videoId}`);
};
```

#### Update Ball Contact

```typescript
export const updateBallContact = async (
  contactId: number,
  updates: Partial<BallContact>
): Promise<BallContact> => {
  return api.request<BallContact>(`/v0/ball-contacts/${contactId}`, {
    method: 'PUT',
    body: JSON.stringify(updates),
  });
};
```

#### Delete Ball Contact

```typescript
export const deleteBallContact = async (contactId: number): Promise<void> => {
  return api.request<void>(`/v0/ball-contacts/${contactId}`, {
    method: 'DELETE',
  });
};
```

## Data Types

### Core Types

```typescript
// types/video.ts
export interface Video {
  id: number;
  filename: string;
  file_path: string;
  file_size: number;
  content_type: string;
  duration: number;
  fps: number;
  width: number;
  height: number;
  frame_count: number;
  status: VideoStatus;
  error_message?: string;
  created_at: string;
  updated_at: string;
}

export interface Analysis {
  id: number;
  video_id: number;
  video_filename: string;
  analysis_type: string;
  status: AnalysisStatus;
  progress: number;
  total_frames: number;
  frames_with_balls: number;
  total_ball_detections: number;
  detection_rate: number;
  frames_with_pose: number;
  pose_detection_rate: number;
  processing_time: number;
  model_used: string;
  confidence_threshold: number;
  created_at: string;
  updated_at: string;
  completed_at?: string;
}

export interface BallContact {
  id: number;
  video_id: number;
  video_timestamp: number;
  contact_hand: 'left' | 'right';
  stroke_type: 'ground_stroke' | 'serve' | 'volley' | 'overhead';
  stroke_subtype?: string;
  detection_source: 'manual' | 'automated';
  created_at: string;
  updated_at: string;
}
```

### Request/Response Types

```typescript
export interface VideoUploadResponse {
  video_id: number;
  filename: string;
  file_size: number;
  status: string;
  message: string;
  metadata: {
    duration: number;
    fps: number;
    width: number;
    height: number;
    frame_count: number;
  };
}

export interface AnalysisStartResponse {
  analysis_id: number;
  video_filename: string;
  status: string;
  message: string;
  estimated_duration: number;
}

export interface AnalysisStatus {
  analysis_id: number;
  status: 'processing' | 'completed' | 'failed';
  progress: number;
  created_at: string;
  completed_at?: string;
}
```

## Error Handling Patterns

### Global Error Handler

```typescript
// services/errorHandler.ts
export const handleApiError = (error: Error): string => {
  if (error instanceof ApiError) {
    switch (error.status) {
      case 400:
        return 'Invalid request. Please check your input.';
      case 404:
        return 'Resource not found.';
      case 413:
        return 'File too large. Please choose a smaller file.';
      case 422:
        return 'Validation error. Please check your input.';
      case 500:
        return 'Server error. Please try again later.';
      default:
        return `Error ${error.status}: ${error.message}`;
    }
  }

  if (error instanceof NetworkError) {
    return 'Network error. Please check your connection.';
  }

  return 'An unexpected error occurred.';
};
```

### Component Error Handling

```typescript
// components/VideoUpload.tsx
const VideoUpload: React.FC<VideoUploadProps> = ({ onUploadSuccess, onUploadError }) => {
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);

  const handleUpload = async (file: File) => {
    try {
      setUploading(true);
      setError(null);

      const response = await uploadVideo(file);
      onUploadSuccess(response);
    } catch (err) {
      const errorMessage = handleApiError(err as Error);
      setError(errorMessage);
      onUploadError(errorMessage);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div>
      {error && <div className="error">{error}</div>}
      {uploading && <div className="uploading">Uploading...</div>}
      {/* Upload UI */}
    </div>
  );
};
```

## Loading State Management

### Custom Hook for API Calls

```typescript
// hooks/useApi.ts
export const useApi = <T>() => {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const execute = useCallback(async (apiCall: () => Promise<T>) => {
    try {
      setLoading(true);
      setError(null);
      const result = await apiCall();
      setData(result);
      return result;
    } catch (err) {
      const errorMessage = handleApiError(err as Error);
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  return { data, loading, error, execute };
};
```

### Usage in Components

```typescript
// components/VideoList.tsx
const VideoList: React.FC<VideoListProps> = () => {
  const { data: videos, loading, error, execute } = useApi<Video[]>();

  useEffect(() => {
    execute(() => getVideos());
  }, [execute]);

  if (loading) return <div>Loading videos...</div>;
  if (error) return <div>Error: {error}</div>;
  if (!videos) return <div>No videos found</div>;

  return (
    <div>
      {videos.map(video => (
        <VideoCard key={video.id} video={video} />
      ))}
    </div>
  );
};
```

## Real-time Updates

### Polling for Analysis Status

```typescript
// hooks/useAnalysisStatus.ts
export const useAnalysisStatus = (analysisId: number) => {
  const [status, setStatus] = useState<AnalysisStatus | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!analysisId) return;

    const pollStatus = async () => {
      try {
        setLoading(true);
        const currentStatus = await getAnalysisStatus(analysisId);
        setStatus(currentStatus);

        // Continue polling if still processing
        if (currentStatus.status === 'processing') {
          setTimeout(pollStatus, 2000); // Poll every 2 seconds
        }
      } catch (error) {
        console.error('Failed to get analysis status:', error);
      } finally {
        setLoading(false);
      }
    };

    pollStatus();
  }, [analysisId]);

  return { status, loading };
};
```

### WebSocket Integration (Future)

```typescript
// services/websocketService.ts
export class WebSocketService {
  private ws: WebSocket | null = null;
  private listeners: Map<string, Function[]> = new Map();

  connect() {
    this.ws = new WebSocket('ws://localhost:8000/ws');

    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      this.notifyListeners(data.type, data.payload);
    };
  }

  subscribe(eventType: string, callback: Function) {
    if (!this.listeners.has(eventType)) {
      this.listeners.set(eventType, []);
    }
    this.listeners.get(eventType)!.push(callback);
  }

  private notifyListeners(eventType: string, payload: any) {
    const callbacks = this.listeners.get(eventType) || [];
    callbacks.forEach((callback) => callback(payload));
  }
}
```

## Caching Strategy

### Simple In-Memory Cache

```typescript
// services/cache.ts
class ApiCache {
  private cache = new Map<string, { data: any; timestamp: number }>();
  private ttl = 5 * 60 * 1000; // 5 minutes

  set(key: string, data: any) {
    this.cache.set(key, {
      data,
      timestamp: Date.now(),
    });
  }

  get(key: string): any | null {
    const item = this.cache.get(key);
    if (!item) return null;

    if (Date.now() - item.timestamp > this.ttl) {
      this.cache.delete(key);
      return null;
    }

    return item.data;
  }

  clear() {
    this.cache.clear();
  }
}

export const apiCache = new ApiCache();
```

### Cached API Calls

```typescript
// services/cachedApi.ts
export const getCachedVideos = async (): Promise<Video[]> => {
  const cacheKey = 'videos';
  const cached = apiCache.get(cacheKey);

  if (cached) {
    return cached;
  }

  const videos = await getVideos();
  apiCache.set(cacheKey, videos);
  return videos;
};
```

## Testing

### Mock API Service

```typescript
// __mocks__/api.ts
export const mockApi = {
  getVideos: vi.fn(),
  uploadVideo: vi.fn(),
  startAnalysis: vi.fn(),
  getAnalysis: vi.fn(),
};

// Mock implementations
mockApi.getVideos.mockResolvedValue([
  { id: 1, filename: 'test.mp4', duration: 30 },
]);

mockApi.uploadVideo.mockResolvedValue({
  video_id: 1,
  filename: 'test.mp4',
  status: 'uploaded',
});
```

### Component Testing with Mocks

```typescript
// components/__tests__/VideoList.test.tsx
import { render, screen, waitFor } from '@testing-library/react';
import { VideoList } from '../VideoList';
import { mockApi } from '../../__mocks__/api';

vi.mock('../../services/api', () => mockApi);

describe('VideoList', () => {
  it('should display videos', async () => {
    render(<VideoList />);

    await waitFor(() => {
      expect(screen.getByText('test.mp4')).toBeInTheDocument();
    });
  });
});
```

## Performance Optimization

### Request Debouncing

```typescript
// hooks/useDebounce.ts
export const useDebounce = <T>(value: T, delay: number): T => {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
};
```

### Request Cancellation

```typescript
// services/api.ts
export class ApiService {
  private abortController: AbortController | null = null;

  async request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
    // Cancel previous request
    if (this.abortController) {
      this.abortController.abort();
    }

    this.abortController = new AbortController();

    const config: RequestInit = {
      ...options,
      signal: this.abortController.signal,
    };

    // ... rest of implementation
  }
}
```

## Security Considerations

### Input Validation

```typescript
// utils/validation.ts
export const validateVideoFile = (file: File): string | null => {
  const maxSize = 100 * 1024 * 1024; // 100MB
  const allowedTypes = ['video/mp4', 'video/mov', 'video/avi'];

  if (file.size > maxSize) {
    return 'File size exceeds 100MB limit';
  }

  if (!allowedTypes.includes(file.type)) {
    return 'Unsupported file type';
  }

  return null;
};
```

### XSS Prevention

```typescript
// utils/sanitization.ts
export const sanitizeInput = (input: string): string => {
  return input
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#x27;');
};
```

## Future Enhancements

### GraphQL Integration

Consider migrating to GraphQL for more efficient data fetching:

```typescript
// services/graphql.ts
import { request } from 'graphql-request';

const GRAPHQL_ENDPOINT = 'http://localhost:8000/graphql';

export const getVideosWithAnalysis = async () => {
  const query = `
    query GetVideosWithAnalysis {
      videos {
        id
        filename
        duration
        analyses {
          id
          status
          progress
        }
      }
    }
  `;

  return request(GRAPHQL_ENDPOINT, query);
};
```

### Offline Support

Implement offline capabilities with service workers:

```typescript
// sw.js
self.addEventListener('fetch', (event) => {
  if (event.request.url.includes('/api/')) {
    event.respondWith(
      caches.match(event.request).then((response) => {
        return response || fetch(event.request);
      })
    );
  }
});
```
