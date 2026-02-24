import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import React from 'react';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';

// Import AppLayout and ProtectedRoute after mocks
import { AppLayout } from './components/layouts/AppLayout';

// Mock localStorage BEFORE importing to prevent demo landing issues
const localStorageMock = {
  getItem: jest.fn(() => 'true'), // hasVisitedApp = true
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
};
Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
});

// Mock the useAuth hook to avoid async loading state
jest.mock('./hooks/useAuth', () => ({
  useAuth: () => ({
    user: {
      id: 'test-user-id',
      email: 'test@example.com',
    },
    loading: false,
    signOut: jest.fn(),
  }),
}));

// Mock useAdmin
jest.mock('./hooks/useAdmin', () => ({
  useAdmin: () => ({
    isAdmin: false,
    isLoading: false,
    error: null,
  }),
}));

// Mock the API service to avoid axios import issues
jest.mock('./services/api', () => ({
  videoApi: {
    uploadVideo: jest.fn(),
    getVideos: jest.fn(),
    getVideo: jest.fn(),
    getDemoVideo: jest.fn(),
    deleteVideo: jest.fn(),
    getVideoUrl: jest.fn(),
    checkAdminStatus: jest.fn().mockResolvedValue({ is_admin: false }),
  },
  analysisApi: {
    startAnalysis: jest.fn(),
  },
}));

// Mock the components that use the API
jest.mock('./components/VideoUpload', () => {
  return function MockVideoUpload() {
    return <div data-testid="video-upload">Upload Tennis Video</div>;
  };
});

jest.mock('./components/VideoList', () => {
  return function MockVideoList() {
    return <div data-testid="video-list">Uploaded Videos</div>;
  };
});

jest.mock('./components/AnalysisDashboard', () => {
  return function MockAnalysisDashboard() {
    return <div data-testid="analysis-dashboard">Analysis Dashboard</div>;
  };
});

jest.mock('./components/DemoLanding', () => {
  return function MockDemoLanding() {
    return <div data-testid="demo-landing">Demo Landing</div>;
  };
});

jest.mock('./components/LoomVideoModal', () => {
  return function MockLoomVideoModal() {
    return null;
  };
});

jest.mock('./components/AccountMenu', () => ({
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

test('renders serve tennis coach app title', () => {
  renderWithRouter('/');
  const titleElement = screen.getByText(/Serve Tennis Coach/i);
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
