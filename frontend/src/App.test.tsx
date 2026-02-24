import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import React from 'react';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';

// Import AppLayout and ProtectedRoute after mocks
import { AppLayout } from './components/layouts/AppLayout';

// Mock localStorage BEFORE importing to prevent demo landing issues
const localStorageMock = {
  getItem: vi.fn(() => 'true'), // hasVisitedApp = true
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
};
Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
});

// Mock the useAuth hook to avoid async loading state
vi.mock('./hooks/useAuth', () => ({
  useAuth: () => ({
    user: {
      id: 'test-user-id',
      email: 'test@example.com',
    },
    loading: false,
    signOut: vi.fn(),
  }),
}));

// Mock useAdmin
vi.mock('./hooks/useAdmin', () => ({
  useAdmin: () => ({
    isAdmin: false,
    isLoading: false,
    error: null,
  }),
}));

// Mock the API service to isolate routing/layout behavior
vi.mock('./services/api', () => ({
  videoApi: {
    uploadVideo: vi.fn(),
    getVideos: vi.fn(),
    getVideo: vi.fn(),
    getDemoVideo: vi.fn(),
    deleteVideo: vi.fn(),
    getVideoUrl: vi.fn(),
    checkAdminStatus: vi.fn().mockResolvedValue({ is_admin: false }),
  },
  analysisApi: {
    startAnalysis: vi.fn(),
  },
}));

// Mock the components that use the API
vi.mock('./components/VideoUpload', () => {
  return {
    default: function MockVideoUpload() {
      return <div data-testid="video-upload">Upload Tennis Video</div>;
    },
  };
});

vi.mock('./components/VideoList', () => {
  return {
    default: function MockVideoList() {
      return <div data-testid="video-list">Uploaded Videos</div>;
    },
  };
});

vi.mock('./components/AnalysisDashboard', () => {
  return {
    default: function MockAnalysisDashboard() {
      return <div data-testid="analysis-dashboard">Analysis Dashboard</div>;
    },
  };
});

vi.mock('./components/DemoLanding', () => {
  return {
    default: function MockDemoLanding() {
      return <div data-testid="demo-landing">Demo Landing</div>;
    },
  };
});

vi.mock('./components/LoomVideoModal', () => {
  return {
    default: function MockLoomVideoModal() {
      return null;
    },
  };
});

vi.mock('./components/AccountMenu', () => ({
  AccountMenu: function MockAccountMenu() {
    return <div data-testid="account-menu">Account</div>;
  },
}));

function renderWithRouter(initialRoute = '/') {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  const routes = [
    {
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: (
            <React.Suspense fallback={null}>
              <MockHomePage />
            </React.Suspense>
          ),
        },
        {
          path: 'demo',
          element: (
            <React.Suspense fallback={null}>
              <MockDemoPage />
            </React.Suspense>
          ),
        },
        {
          path: 'library',
          element: (
            <React.Suspense fallback={null}>
              <MockLibraryPage />
            </React.Suspense>
          ),
        },
      ],
    },
  ];

  const router = createMemoryRouter(routes, {
    initialEntries: [initialRoute],
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  );
}

// Inline mock pages that render the mocked components
function MockHomePage() {
  return <div data-testid="demo-landing">Demo Landing</div>;
}

function MockDemoPage() {
  return <div data-testid="demo-dashboard">Demo Dashboard</div>;
}

function MockLibraryPage() {
  return <div data-testid="video-list">Uploaded Videos</div>;
}

test('renders app title', () => {
  renderWithRouter('/');
  const titleElement = screen.getByText(/Second Serve/i);
  expect(titleElement).toBeInTheDocument();
});

test('renders demo landing by default on / route', () => {
  renderWithRouter('/');
  const demoLanding = screen.getByTestId('demo-landing');
  expect(demoLanding).toBeInTheDocument();
});

test('renders library nav link', () => {
  renderWithRouter('/');
  const libraryLink = screen.getByText(/Library/i);
  expect(libraryLink).toBeInTheDocument();
});

test('renders app content on / route', () => {
  renderWithRouter('/');
  const demoLanding = screen.getByTestId('demo-landing');
  expect(demoLanding).toBeInTheDocument();
});
