# Tennis Coach App - Frontend

Technical frontend guide for contributors working in `frontend/`.

For product context, screenshots, and a quick project intro, start at the root `README.md`.

This app covers authenticated upload flows, video review, and analysis UI rendering for serve data.

## Quick Start

### Prerequisites

- Node.js 16+ (18+ recommended)
- npm or yarn
- Backend server running (see [backend README](../backend/README.md))

### Installation

```bash
# Install dependencies
npm install

# Start development server
npm start
```

The app will open at http://localhost:3000

### Environment Configuration

Create a `.env` file in the `frontend/` directory:

```bash
# API Configuration
REACT_APP_API_URL=http://localhost:8000

# Authentication (Supabase)
# Required for user authentication
REACT_APP_SUPABASE_URL=https://your-project.supabase.co/
REACT_APP_SUPABASE_PUBLISHABLE_KEY=your-publishable-key

# File Upload
REACT_APP_MAX_FILE_SIZE=104857600  # 100MB

# Development
REACT_APP_DEBUG=true
```

## Available Scripts

### Development

```bash
# Start development server
npm start

# Run tests
npm test

# Run tests with coverage
npm run test:coverage

# Build for production
npm run build

# Eject from Create React App (not recommended)
npm run eject
```

### Code Quality

```bash
# Lint code
npm run lint

# Fix auto-fixable linting issues
npm run lint:fix

# Type check
npm run type-check

# Format code
npm run format
```

### Testing

```bash
# Run tests in watch mode
npm test

# Run tests once
npm run test:ci

# Run tests with coverage
npm run test:coverage

# Run specific test file
npm test -- VideoPlayer.test.tsx

# Run specific test
npm test -- --testNamePattern="should play video"
```

## Project Structure

```
frontend/
├── public/
│   ├── index.html          # Main HTML template
│   ├── favicon.ico         # App icon
│   └── manifest.json       # PWA manifest
├── src/
│   ├── components/         # React components
│   │   ├── AnalysisDashboard.tsx    # Main analysis view
│   │   ├── AnalysisModal.tsx        # Analysis results modal
│   │   ├── AnalysisResults.tsx      # Analysis metrics display
│   │   ├── Icons.tsx               # SVG icons
│   │   ├── VideoList.tsx           # Video library
│   │   ├── VideoPlayer.tsx         # Video playback
│   │   └── VideoUpload.tsx         # File upload
│   ├── services/
│   │   └── api.ts                  # API service layer
│   ├── types/
│   │   └── video.ts                # TypeScript type definitions
│   ├── App.tsx                     # Main app component
│   ├── App.css                     # App styles
│   ├── index.tsx                   # App entry point
│   └── index.css                   # Global styles
├── docs/                          # Detailed documentation
│   ├── components.md              # Component documentation
│   └── api-integration.md         # How frontend talks to backend
├── package.json                    # Dependencies and scripts
├── tsconfig.json                   # TypeScript configuration
└── README.md                      # This file
```

## Features

- **User Authentication**: Login and registration with Supabase Auth
- **User Sessions**: Secure session management and token handling
- **Player Profile**: Default player profile created during signup (name, dominant hand, backhand style)
- **Video Upload**: Drag-and-drop file upload with validation
- **Video Library**: Browse and manage your uploaded videos
- **Video Playback**: HTML5 video player with controls and fullscreen
- **Analysis Results**: Display ball detection and pose estimation metrics
- **Annotated Videos**: Automatic playback of videos with AI overlays
- **Responsive Design**: Works on desktop and mobile devices
- **TypeScript**: Full type safety and IntelliSense support

## Components Overview

### VideoUpload

- Drag-and-drop file upload interface
- File validation (size, format)
- Upload progress and error handling
- Supports MP4, MOV, AVI formats

### VideoList

- Displays uploaded videos in a grid
- Shows video metadata (size, duration, resolution)
- Delete functionality with confirmation
- Analysis status indicators
- Upload button opens floating modal (not full page navigation)

### VideoPlayer

- HTML5 video player with custom controls
- Play/pause, seek, volume, fullscreen
- Automatic annotated video selection
- Error handling for playback issues

### AnalysisDashboard

- Combined video player and analysis results
- Analysis trigger button
- Loading states during processing
- Collapsible video details

### AnalysisResults

- Displays ball detection metrics
- Shows pose estimation statistics
- Processing time and model information
- Collapsible sections for organization

### Tour

- Custom guided tour component for onboarding
- React 19 compatible (built due to react-joyride incompatibility)
- Supports multi-step tours with tooltips and highlights
- localStorage persistence for completion state
- **Future Migration**: Monitor react-joyride for React 19 support - consider migrating once available for better features and maintenance

## Navigation & Routing

The app uses view-based routing managed in `App.tsx`:

- **Home** (`demo-landing`): Default entry point with CTAs for Demo and Upload
- **Library** (`list`): Video library with grid of uploaded videos (requires auth)
- **Dashboard** (`dashboard`): Analysis dashboard for selected video (requires auth)
- **Demo** (`demo-dashboard`): Demo mode analysis dashboard (no auth required)

**Navigation Features**:

- Navigation tabs (Home, Library, Demo) visible on all pages
- Auth-aware header actions: "Get Started" when logged out, "Logout" when logged in
- Upload is gated behind login - opens modal when logged in, redirects to Library/auth when not
- **Performance**: Demo video metadata and URL are prefetched when landing page loads to optimize demo dashboard load time

## API Integration

### Base Configuration

The frontend communicates with the backend API through the `api.ts` service layer:

```typescript
// Default API configuration
const API_BASE_URL =
  process.env.REACT_APP_API_URL || 'http://localhost:8000/v0';
```

### Key Endpoints

- `POST /v0/videos/upload` - Upload video files
- `GET /v0/videos/` - List all videos
- `GET /v0/videos/{video_id}/stream` - Stream original video
- `GET /v0/videos/demo` - Get demo video (no auth required)
- `GET /v0/videos/{video_id}/analysis-status` - Get analysis status
- `POST /v0/analysis/videos/{video_id}` - Start analysis
- `GET /v0/analysis/{analysis_id}` - Get analysis results
- `GET /v0/players/me` - Get current user's default player profile
- `PUT /v0/players/me` - Create or update default player profile (used during signup)

### Error Handling

- Network errors with retry logic
- File upload validation
- Video playback error recovery
- User-friendly error messages

## Development Guidelines

### Code Style

- Use TypeScript for all new code
- Follow ESLint configuration
- Use Prettier for formatting
- Add JSDoc comments for complex functions

### Component Patterns

```typescript
// Functional components with hooks
const MyComponent: React.FC<MyComponentProps> = ({ prop1, prop2 }) => {
  const [state, setState] = useState<StateType>(initialState);

  useEffect(() => {
    // Side effects
  }, [dependencies]);

  return (
    <div className="my-component">
      {/* JSX content */}
    </div>
  );
};
```

### State Management

- Use React hooks (useState, useEffect, useCallback)
- Keep state as local as possible
- Lift state up when needed for sharing
- Consider Context API for global state

### Testing Patterns

```typescript
// Component test example
import { render, screen, fireEvent } from '@testing-library/react';
import { VideoPlayer } from './VideoPlayer';

describe('VideoPlayer', () => {
  it('should play video when play button is clicked', () => {
    render(<VideoPlayer src="test.mp4" />);

    const playButton = screen.getByRole('button', { name: /play/i });
    fireEvent.click(playButton);

    expect(screen.getByRole('video')).toHaveAttribute('src', 'test.mp4');
  });
});
```

## Testing

### Test Structure

- Unit tests for individual components
- Integration tests for component interactions
- API service tests with mocked responses
- User interaction tests with React Testing Library

### Running Tests

```bash
# Run all tests
npm test

# Run with coverage
npm run test:coverage

# Run specific test file
npm test -- VideoPlayer.test.tsx

# Run tests in CI mode
npm run test:ci
```

### Coverage Requirements

- Minimum 70% coverage for new code
- 100% coverage for critical components
- Focus on user interactions and business logic

## Build and Deployment

### Development Build

```bash
npm start
```

### Production Build

```bash
npm run build
```

The build output will be in the `build/` directory.

### Environment-Specific Builds

```bash
# Development
REACT_APP_API_URL=http://localhost:8000 npm run build

# Production
REACT_APP_API_URL=https://api.tennis-coach.com npm run build
```

### Deployment Options

#### GitHub Pages (Current)

- Automatic deployment via GitHub Actions
- Builds on main branch pushes
- Served from GitHub Pages CDN

#### Docker Deployment

```bash
# Build Docker image
docker build -t tennis-frontend .

# Run container
docker run -p 80:80 tennis-frontend
```

#### Static Hosting

- Upload `build/` contents to any static hosting service
- Configure environment variables for API URL
- Ensure CORS is properly configured on backend

## Troubleshooting

### Common Issues

#### API Connection Errors

- Verify backend server is running
- Check `REACT_APP_API_URL` environment variable
- Ensure CORS is configured on backend
- Check network connectivity

#### Video Playback Issues

- Verify video format is supported (MP4, MOV, AVI)
- Check video file integrity
- Ensure proper CORS headers for video streaming
- Test with different browsers

#### Build Errors

```bash
# Clear cache and reinstall dependencies
rm -rf node_modules package-lock.json
npm install

# Clear build cache
npm run build -- --reset-cache
```

#### Test Failures

```bash
# Clear test cache
npm test -- --clearCache

# Run tests with verbose output
npm test -- --verbose
```

### Debug Mode

```bash
# Enable debug logging
REACT_APP_DEBUG=true npm start

# Open browser dev tools
# Check Console and Network tabs for errors
```

## Performance Optimization

### Bundle Size

- Use dynamic imports for large components
- Implement code splitting with React.lazy
- Optimize images and assets
- Monitor bundle size with webpack-bundle-analyzer

### Runtime Performance

- Use React.memo for expensive components
- Implement proper dependency arrays in useEffect
- Avoid unnecessary re-renders
- Use React DevTools Profiler for analysis

### Video Performance

- Implement lazy loading for video thumbnails
- Use appropriate video quality settings
- Consider video compression for storage
- Implement video caching strategies
- **Demo video prefetching**: Demo video metadata and URL are prefetched when the landing page loads, reducing API round-trips and improving time-to-first-frame when users open the demo dashboard

## Documentation

- **[Component Guide](docs/components.md)** - Detailed component documentation
- **[API Integration](docs/api-integration.md)** - How frontend communicates with backend

## Contributing

1. Follow the established code patterns
2. Write tests for new features
3. Update documentation for API changes
4. Use conventional commit messages
5. Ensure all tests pass before submitting

## License

MIT License
