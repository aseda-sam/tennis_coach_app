import { useQueryClient } from '@tanstack/react-query';
import React, { createContext, useContext, useEffect, useState } from 'react';
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { AccountMenu } from '../AccountMenu';
import ErrorBoundary from '../ErrorBoundary';
import { Activity, X } from 'lucide-react';
import LoadingIndicator from '../LoadingIndicator';
import LoomVideoModal from '../LoomVideoModal';
import { QuickSetup } from '../QuickSetup';
import VideoUpload from '../VideoUpload';
import { useAuth } from '../../hooks/useAuth';
import { useAdmin } from '../../hooks/useAdmin';
import { videoApi } from '../../services/api';
import { VideoMetadata } from '../../types/video';
import '../../App.css';

// Context for upload modal so page components can trigger it
interface UploadModalContextValue {
  openUploadModal: () => void;
  openVideoModal: () => void;
}

const UploadModalContext = createContext<UploadModalContextValue>({
  openUploadModal: () => {},
  openVideoModal: () => {},
});

export function useUploadModal() {
  return useContext(UploadModalContext);
}

export function AppLayout() {
  const profile = process.env.REACT_APP_PROFILE || 'local';
  const { user, loading, signOut } = useAuth();
  const { isAdmin } = useAdmin();
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const location = useLocation();
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [showQuickSetup, setShowQuickSetup] = useState(false);
  const [isVideoModalOpen, setIsVideoModalOpen] = useState(false);

  // Check if user needs setup (invited user without display_name)
  useEffect(() => {
    if (profile !== 'local' && user && !loading) {
      const needsSetup = sessionStorage.getItem('needsSetup') === 'true';
      const hasDisplayName = user.user_metadata?.display_name;
      if (needsSetup && !hasDisplayName) {
        setShowQuickSetup(true);
      }
    }
  }, [user, loading, profile]);

  const handleVideoUploaded = (video: VideoMetadata) => {
    queryClient.invalidateQueries({ queryKey: ['videos'] });
    setIsUploadModalOpen(false);
    navigate('/library');
  };

  const openUploadModal = () => {
    if (profile === 'local' || user) {
      setIsUploadModalOpen(true);
    } else {
      navigate('/library');
    }
  };

  const handleLogout = async () => {
    try {
      await signOut();
      navigate('/');
    } catch (error) {
      console.error('Logout failed:', error);
    }
  };

  const handleGetStarted = () => {
    if (user) {
      openUploadModal();
    } else {
      navigate('/library');
    }
  };

  // Prefetch demo video metadata and URL when on home page
  useEffect(() => {
    if (location.pathname === '/') {
      queryClient
        .fetchQuery<VideoMetadata, Error>({
          queryKey: ['demo-video'],
          queryFn: async () => {
            return await videoApi.getDemoVideo();
          },
          staleTime: 5 * 60 * 1000,
        })
        .then((demoVideo) => {
          if (demoVideo?.id) {
            const expiresIn = 3600;
            queryClient
              .prefetchQuery<string>({
                queryKey: ['video-url', demoVideo.id, expiresIn],
                queryFn: async () => {
                  return await videoApi.getVideoUrl(demoVideo.id, expiresIn);
                },
                staleTime: expiresIn * 1000 * 0.9,
                gcTime: expiresIn * 1000,
              })
              .then(() => {
                const url = queryClient.getQueryData<string>([
                  'video-url',
                  demoVideo.id,
                  expiresIn,
                ]);
                if (url) {
                  try {
                    const urlObj = new URL(url);
                    const origin = urlObj.origin;
                    const existingLink = document.querySelector(
                      `link[rel="preconnect"][href="${origin}"]`
                    );
                    if (!existingLink) {
                      const link = document.createElement('link');
                      link.rel = 'preconnect';
                      link.href = origin;
                      link.crossOrigin = 'anonymous';
                      document.head.appendChild(link);
                    }
                  } catch (e) {
                    console.debug(
                      'Failed to parse demo video URL for preconnect:',
                      e
                    );
                  }
                }
              })
              .catch((error) => {
                console.debug('Failed to prefetch demo video URL:', error);
              });
          }
        })
        .catch((error) => {
          console.debug('Failed to fetch demo video metadata:', error);
        });
    }
  }, [location.pathname, queryClient]);

  const handleQuickSetupComplete = async () => {
    setShowQuickSetup(false);
    sessionStorage.removeItem('needsSetup');
    // Refresh auth state and queries instead of full page reload
    queryClient.invalidateQueries({ queryKey: ['admin-status'] });
    queryClient.invalidateQueries({ queryKey: ['playerProfile'] });
  };

  if (loading) {
    return (
      <div className="App">
        <div className="app-container">
          <div className="app-loading">
            <LoadingIndicator size="lg" label="Loading..." />
          </div>
        </div>
      </div>
    );
  }

  return (
    <UploadModalContext.Provider
      value={{
        openUploadModal,
        openVideoModal: () => setIsVideoModalOpen(true),
      }}
    >
      <div className="App">
        <ErrorBoundary>
          {/* Header */}
          <div className="app-header">
            <div className="app-header-wrapper">
              <div className="app-header-left">
                <NavLink to="/" className="app-brand" aria-label="Go to home">
                  <div className="app-logo">
                    <Activity size={18} color="white" strokeWidth={2.5} />
                  </div>
                  <h1 className="app-title">Serve Tennis Coach</h1>
                </NavLink>
              </div>

              <nav
                className="app-header-center"
                role="tablist"
                aria-label="Primary navigation"
              >
                <div className="view-toggle">
                  <NavLink
                    to="/"
                    end
                    role="tab"
                    className={({ isActive }) =>
                      `view-toggle-btn ${isActive ? 'active' : ''}`
                    }
                    aria-selected={location.pathname === '/'}
                  >
                    Home
                  </NavLink>
                  <NavLink
                    to="/library"
                    role="tab"
                    className={({ isActive }) =>
                      `view-toggle-btn ${isActive ? 'active' : ''}`
                    }
                    aria-selected={location.pathname === '/library'}
                  >
                    Library
                  </NavLink>
                  <NavLink
                    to="/demo"
                    role="tab"
                    className={({ isActive }) =>
                      `view-toggle-btn ${isActive ? 'active' : ''}`
                    }
                    aria-selected={location.pathname === '/demo'}
                  >
                    Demo
                  </NavLink>
                  {isAdmin && (
                    <NavLink
                      to="/admin/demos"
                      role="tab"
                      className={({ isActive }) =>
                        `view-toggle-btn ${isActive ? 'active' : ''}`
                      }
                      aria-selected={location.pathname === '/admin/demos'}
                    >
                      Admin
                    </NavLink>
                  )}
                </div>
              </nav>

              <div className="app-header-right">
                {user ? (
                  <AccountMenu onLogout={handleLogout} />
                ) : (
                  <button className="sign-in-btn" onClick={handleGetStarted}>
                    Sign In
                  </button>
                )}
              </div>
            </div>
          </div>

          {/* Page content */}
          <Outlet />

          {/* Quick Setup Modal */}
          {showQuickSetup && (
            <QuickSetup onComplete={handleQuickSetupComplete} />
          )}

          {/* Upload Modal */}
          {isUploadModalOpen && (
            <div
              className="upload-modal-overlay"
              onClick={() => setIsUploadModalOpen(false)}
            >
              <div
                className="upload-modal"
                onClick={(e) => e.stopPropagation()}
              >
                <div className="modal-header">
                  <h2 className="modal-title">Upload Video</h2>
                  <button
                    className="close-btn"
                    onClick={() => setIsUploadModalOpen(false)}
                    aria-label="Close"
                  >
                    <X size={18} />
                  </button>
                </div>
                <div className="modal-content">
                  <VideoUpload onUploadSuccess={handleVideoUploaded} />
                </div>
              </div>
            </div>
          )}

          {/* Loom Video Modal */}
          <LoomVideoModal
            isOpen={isVideoModalOpen}
            onClose={() => setIsVideoModalOpen(false)}
            videoId="4e50fe345c664fdca497c2ca884a52e3"
          />
        </ErrorBoundary>
      </div>
    </UploadModalContext.Provider>
  );
}
