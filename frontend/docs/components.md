# Frontend Components Documentation

This document provides detailed information about the React components in the Tennis Coach App frontend.

## Component Architecture

The frontend is built with React and TypeScript, using functional components with hooks for state management. Components are organized by functionality and follow a consistent pattern.

## Core Components

### App.tsx

**Purpose**: Main application component that orchestrates the entire frontend experience.

**Key Features**:
- Application routing and navigation
- Global state management
- Error boundary implementation
- Theme and styling setup

**Props**: None (root component)

**State**:
- `videos`: Array of video objects
- `selectedVideo`: Currently selected video for analysis
- `loading`: Global loading state
- `error`: Global error state

### VideoUpload.tsx

**Purpose**: Handles video file uploads with drag-and-drop functionality.

**Key Features**:
- Drag-and-drop file upload interface
- File validation (size, format, type)
- Upload progress tracking
- Error handling and user feedback
- Support for multiple video formats (MP4, MOV, AVI)

**Props**:
```typescript
interface VideoUploadProps {
  onUploadSuccess: (video: Video) => void;
  onUploadError: (error: string) => void;
  maxFileSize?: number;
  acceptedFormats?: string[];
}
```

**State**:
- `isDragOver`: Boolean for drag state
- `uploading`: Boolean for upload progress
- `uploadProgress`: Number for progress percentage

**Usage**:
```typescript
<VideoUpload
  onUploadSuccess={(video) => setVideos([...videos, video])}
  onUploadError={(error) => setError(error)}
  maxFileSize={104857600} // 100MB
  acceptedFormats={['.mp4', '.mov', '.avi']}
/>
```

### VideoList.tsx

**Purpose**: Displays a grid of uploaded videos with metadata and management options.

**Key Features**:
- Grid layout with responsive design
- Video metadata display (size, duration, resolution)
- Analysis status indicators
- Delete functionality with confirmation
- Video selection for analysis

**Props**:
```typescript
interface VideoListProps {
  videos: Video[];
  onVideoSelect: (video: Video) => void;
  onVideoDelete: (videoId: number) => void;
  selectedVideoId?: number;
}
```

**State**:
- `deleteConfirmId`: ID of video pending deletion
- `sortBy`: Sort criteria for video list
- `filterBy`: Filter criteria for video list

**Usage**:
```typescript
<VideoList
  videos={videos}
  onVideoSelect={setSelectedVideo}
  onVideoDelete={handleVideoDelete}
  selectedVideoId={selectedVideo?.id}
/>
```

### VideoPlayer.tsx

**Purpose**: HTML5 video player with custom controls and tennis-specific features.

**Key Features**:
- Custom video controls (play, pause, seek, volume, fullscreen)
- Automatic annotated video selection when available
- Ball contact timeline markers
- Keyboard shortcuts for playback control
- Error handling for playback issues
- Responsive design for mobile and desktop

**Props**:
```typescript
interface VideoPlayerProps {
  video: Video;
  ballContacts?: BallContact[];
  onTimeUpdate?: (currentTime: number) => void;
  onContactClick?: (contact: BallContact) => void;
  autoPlay?: boolean;
  showControls?: boolean;
}
```

**State**:
- `currentTime`: Current playback time
- `duration`: Total video duration
- `isPlaying`: Playback state
- `volume`: Audio volume level
- `isFullscreen`: Fullscreen state
- `error`: Playback error state

**Usage**:
```typescript
<VideoPlayer
  video={selectedVideo}
  ballContacts={ballContacts}
  onTimeUpdate={setCurrentTime}
  onContactClick={handleContactClick}
  autoPlay={false}
  showControls={true}
/>
```

### AnalysisDashboard.tsx

**Purpose**: Main analysis interface combining video player and results display.

**Key Features**:
- Integrated video player and analysis results
- Analysis trigger button with loading states
- Progress tracking for ongoing analyses
- Collapsible video details section
- Real-time status updates

**Props**:
```typescript
interface AnalysisDashboardProps {
  video: Video;
  analysis?: Analysis;
  onStartAnalysis: (videoId: number, analysisType: string) => void;
  onCancelAnalysis?: (analysisId: number) => void;
}
```

**State**:
- `showDetails`: Boolean for details panel visibility
- `analysisProgress`: Number for analysis progress
- `isAnalyzing`: Boolean for analysis state

**Usage**:
```typescript
<AnalysisDashboard
  video={selectedVideo}
  analysis={analysis}
  onStartAnalysis={handleStartAnalysis}
  onCancelAnalysis={handleCancelAnalysis}
/>
```

### AnalysisResults.tsx

**Purpose**: Displays analysis results with detailed metrics and visualizations.

**Key Features**:
- Ball detection metrics and statistics
- Pose estimation results and keypoints
- Processing time and model information
- Collapsible sections for organization
- Visual indicators for analysis quality
- Export functionality for results

**Props**:
```typescript
interface AnalysisResultsProps {
  analysis: Analysis;
  video: Video;
  onExportResults?: (analysis: Analysis) => void;
  showDetails?: boolean;
}
```

**State**:
- `expandedSections`: Set of expanded section IDs
- `exporting`: Boolean for export state

**Usage**:
```typescript
<AnalysisResults
  analysis={analysis}
  video={selectedVideo}
  onExportResults={handleExportResults}
  showDetails={true}
/>
```

### AnalysisModal.tsx

**Purpose**: Modal dialog for displaying analysis results in a focused view.

**Key Features**:
- Full-screen analysis results display
- Close and minimize functionality
- Responsive design for different screen sizes
- Keyboard navigation support
- Print-friendly layout

**Props**:
```typescript
interface AnalysisModalProps {
  isOpen: boolean;
  onClose: () => void;
  analysis: Analysis;
  video: Video;
}
```

**State**:
- `isMinimized`: Boolean for minimized state
- `currentSection`: String for active section

**Usage**:
```typescript
<AnalysisModal
  isOpen={showAnalysisModal}
  onClose={() => setShowAnalysisModal(false)}
  analysis={analysis}
  video={selectedVideo}
/>
```

## Utility Components

### Icons.tsx

**Purpose**: Centralized SVG icon components for consistent iconography.

**Key Features**:
- Custom SVG icons for tennis-specific actions
- Consistent sizing and styling
- Accessibility support with ARIA labels
- Easy to extend with new icons

**Available Icons**:
- `PlayIcon`: Video playback
- `PauseIcon`: Video pause
- `UploadIcon`: File upload
- `DeleteIcon`: Delete actions
- `AnalysisIcon`: Analysis actions
- `BallIcon`: Ball detection
- `PoseIcon`: Pose estimation
- `ContactIcon`: Ball contact markers

**Usage**:
```typescript
import { PlayIcon, UploadIcon } from './Icons';

<PlayIcon size={24} color="#007bff" />
<UploadIcon size={32} color="#28a745" />
```

## Component Patterns

### State Management

Components use React hooks for state management:

```typescript
const [state, setState] = useState<StateType>(initialState);
const [loading, setLoading] = useState(false);
const [error, setError] = useState<string | null>(null);
```

### Effect Hooks

Use useEffect for side effects:

```typescript
useEffect(() => {
  // Side effect logic
  const fetchData = async () => {
    try {
      setLoading(true);
      const data = await api.getData();
      setState(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  fetchData();
}, [dependencies]);
```

### Event Handlers

Use useCallback for optimized event handlers:

```typescript
const handleClick = useCallback((event: React.MouseEvent) => {
  // Handle click
  onItemClick(item);
}, [item, onItemClick]);
```

### Custom Hooks

Create custom hooks for reusable logic:

```typescript
const useVideoAnalysis = (videoId: number) => {
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [loading, setLoading] = useState(false);

  const startAnalysis = useCallback(async (analysisType: string) => {
    setLoading(true);
    try {
      const result = await api.startAnalysis(videoId, analysisType);
      setAnalysis(result);
    } catch (error) {
      console.error('Analysis failed:', error);
    } finally {
      setLoading(false);
    }
  }, [videoId]);

  return { analysis, loading, startAnalysis };
};
```

## Styling

### CSS Modules

Components use CSS modules for scoped styling:

```typescript
import styles from './VideoPlayer.module.css';

<div className={styles.videoPlayer}>
  <video className={styles.video} />
  <div className={styles.controls} />
</div>
```

### Responsive Design

Components are designed to be responsive:

```css
.videoPlayer {
  width: 100%;
  max-width: 800px;
  margin: 0 auto;
}

@media (max-width: 768px) {
  .videoPlayer {
    max-width: 100%;
    padding: 0 1rem;
  }
}
```

### Theme Support

Components support theming through CSS custom properties:

```css
.videoPlayer {
  background-color: var(--bg-color, #ffffff);
  color: var(--text-color, #000000);
  border: 1px solid var(--border-color, #e0e0e0);
}
```

## Testing

### Component Testing

Components are tested using React Testing Library:

```typescript
import { render, screen, fireEvent } from '@testing-library/react';
import { VideoPlayer } from './VideoPlayer';

describe('VideoPlayer', () => {
  it('should render video element', () => {
    const video = { id: 1, filename: 'test.mp4' };
    render(<VideoPlayer video={video} />);
    
    expect(screen.getByRole('video')).toBeInTheDocument();
  });

  it('should handle play button click', () => {
    const video = { id: 1, filename: 'test.mp4' };
    render(<VideoPlayer video={video} />);
    
    const playButton = screen.getByRole('button', { name: /play/i });
    fireEvent.click(playButton);
    
    // Assert expected behavior
  });
});
```

### Integration Testing

Test component interactions:

```typescript
describe('VideoUpload Integration', () => {
  it('should upload video and update video list', async () => {
    const onUploadSuccess = jest.fn();
    render(<VideoUpload onUploadSuccess={onUploadSuccess} />);
    
    const file = new File(['video content'], 'test.mp4', { type: 'video/mp4' });
    const input = screen.getByLabelText(/upload/i);
    
    fireEvent.change(input, { target: { files: [file] } });
    
    await waitFor(() => {
      expect(onUploadSuccess).toHaveBeenCalledWith(
        expect.objectContaining({ filename: 'test.mp4' })
      );
    });
  });
});
```

## Performance Optimization

### Memoization

Use React.memo for expensive components:

```typescript
const VideoPlayer = React.memo<VideoPlayerProps>(({ video, ballContacts }) => {
  // Component implementation
});
```

### Lazy Loading

Use React.lazy for code splitting:

```typescript
const AnalysisModal = React.lazy(() => import('./AnalysisModal'));

// In component
<Suspense fallback={<div>Loading...</div>}>
  <AnalysisModal />
</Suspense>
```

### Virtual Scrolling

For large video lists, implement virtual scrolling:

```typescript
import { FixedSizeList as List } from 'react-window';

const VirtualizedVideoList = ({ videos }) => (
  <List
    height={600}
    itemCount={videos.length}
    itemSize={120}
    itemData={videos}
  >
    {VideoItem}
  </List>
);
```

## Accessibility

### ARIA Labels

Add proper ARIA labels for screen readers:

```typescript
<button
  aria-label="Play video"
  aria-pressed={isPlaying}
  onClick={handlePlay}
>
  <PlayIcon />
</button>
```

### Keyboard Navigation

Support keyboard navigation:

```typescript
const handleKeyDown = (event: React.KeyboardEvent) => {
  switch (event.key) {
    case ' ':
      event.preventDefault();
      togglePlay();
      break;
    case 'ArrowLeft':
      seek(-10);
      break;
    case 'ArrowRight':
      seek(10);
      break;
  }
};
```

### Focus Management

Manage focus for better accessibility:

```typescript
const focusRef = useRef<HTMLButtonElement>(null);

useEffect(() => {
  if (isVisible && focusRef.current) {
    focusRef.current.focus();
  }
}, [isVisible]);
```

## Error Handling

### Error Boundaries

Implement error boundaries for graceful error handling:

```typescript
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    console.error('Error caught by boundary:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return <ErrorFallback />;
    }

    return this.props.children;
  }
}
```

### Error States

Handle error states in components:

```typescript
const [error, setError] = useState<string | null>(null);

if (error) {
  return (
    <div className="error-state">
      <p>Error: {error}</p>
      <button onClick={() => setError(null)}>Retry</button>
    </div>
  );
}
```

## Future Enhancements

### Planned Features

- **Real-time Collaboration**: Multiple users analyzing the same video
- **Advanced Filtering**: Filter videos by analysis results
- **Batch Operations**: Bulk analysis and management
- **Custom Themes**: User-selectable themes and layouts
- **Offline Support**: PWA capabilities for offline usage
- **Advanced Analytics**: Detailed performance metrics and trends

### Performance Improvements

- **Service Worker**: Caching and offline functionality
- **Web Workers**: Background processing for heavy computations
- **Streaming**: Progressive video loading and analysis
- **Compression**: Optimized video compression and storage
