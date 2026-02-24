import React from 'react';
import { AuthForm } from '../AuthForm';
import LoadingIndicator from '../LoadingIndicator';
import { useAuth } from '../../hooks/useAuth';
import { useAdmin } from '../../hooks/useAdmin';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requireAdmin?: boolean;
}

export function ProtectedRoute({
  children,
  requireAdmin,
}: ProtectedRouteProps) {
  const profile = process.env.REACT_APP_PROFILE || 'local';
  const { user, loading } = useAuth();
  const { isAdmin } = useAdmin();

  // Local profile bypasses auth
  if (profile === 'local') {
    return <>{children}</>;
  }

  if (loading) {
    return (
      <div className="app-container">
        <div className="app-loading">
          <LoadingIndicator size="lg" label="Loading..." />
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="app-container">
        <AuthForm />
      </div>
    );
  }

  if (requireAdmin && !isAdmin) {
    return (
      <div className="app-container">
        <div className="error-message">
          <p>Access denied. Admin privileges required.</p>
          <a href="/">Go Home</a>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
