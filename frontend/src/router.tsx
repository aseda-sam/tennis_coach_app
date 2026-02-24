import React from 'react';
import { createBrowserRouter, Navigate } from 'react-router-dom';
import { AppLayout } from './components/layouts/AppLayout';
import { ProtectedRoute } from './components/layouts/ProtectedRoute';

const HomePage = React.lazy(() => import('./components/pages/HomePage'));
const DemoPage = React.lazy(() => import('./components/pages/DemoPage'));
const LibraryPage = React.lazy(() => import('./components/pages/LibraryPage'));
const VideoAnalysisPage = React.lazy(
  () => import('./components/pages/VideoAnalysisPage')
);
const AdminDemosPage = React.lazy(
  () => import('./components/pages/AdminDemosPage')
);

export const router = createBrowserRouter([
  {
    element: <AppLayout />,
    children: [
      {
        index: true,
        element: (
          <React.Suspense
            fallback={
              <div className="app-container">
                <div className="app-loading" />
              </div>
            }
          >
            <HomePage />
          </React.Suspense>
        ),
      },
      {
        path: 'demo',
        element: (
          <React.Suspense
            fallback={
              <div className="app-container">
                <div className="app-loading" />
              </div>
            }
          >
            <DemoPage />
          </React.Suspense>
        ),
      },
      {
        path: 'library',
        element: (
          <ProtectedRoute>
            <React.Suspense
              fallback={
                <div className="app-container">
                  <div className="app-loading" />
                </div>
              }
            >
              <LibraryPage />
            </React.Suspense>
          </ProtectedRoute>
        ),
      },
      {
        path: 'videos/:videoId',
        element: (
          <ProtectedRoute>
            <React.Suspense
              fallback={
                <div className="app-container">
                  <div className="app-loading" />
                </div>
              }
            >
              <VideoAnalysisPage />
            </React.Suspense>
          </ProtectedRoute>
        ),
      },
      {
        path: 'admin/demos',
        element: (
          <ProtectedRoute requireAdmin>
            <React.Suspense
              fallback={
                <div className="app-container">
                  <div className="app-loading" />
                </div>
              }
            >
              <AdminDemosPage />
            </React.Suspense>
          </ProtectedRoute>
        ),
      },
      {
        path: '*',
        element: <Navigate to="/" replace />,
      },
    ],
  },
]);
