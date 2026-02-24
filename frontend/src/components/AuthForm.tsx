import React, { useState } from 'react';
import { AuthLoginForm } from './AuthLoginForm';
import { AuthSignupForm } from './AuthSignupForm';
import './AuthForm.css';

export function AuthForm() {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [showResendLink, setShowResendLink] = useState(false);

  // Check if we just confirmed email (from URL hash)
  React.useEffect(() => {
    const hashParams = new URLSearchParams(window.location.hash.substring(1));
    const type = hashParams.get('type');
    if (type === 'signup') {
      setSuccess('Email confirmed! You can now log in.');
      // Clean up URL
      window.history.replaceState(null, '', window.location.pathname);
    }
  }, []);

  const switchToLogin = () => {
    setIsLogin(true);
    setShowResendLink(false);
    setError(null);
    setSuccess(null);
  };

  const switchToSignup = () => {
    setIsLogin(false);
    setShowResendLink(false);
    setError(null);
    setSuccess(null);
  };

  return (
    <div className="auth-form">
      <div className="auth-form-header">
        <h2 className="auth-form-title">
          {isLogin ? 'Welcome back' : 'Create your account'}
        </h2>
        <p className="auth-form-subtitle">
          {isLogin
            ? 'Sign in to continue to Second Serve'
            : 'Join Second Serve to analyze your serve'}
        </p>
      </div>
      {isLogin ? (
        <AuthLoginForm
          email={email}
          setEmail={setEmail}
          error={error}
          setError={setError}
          success={success}
          setSuccess={setSuccess}
          loading={loading}
          setLoading={setLoading}
          onSwitchToSignup={switchToSignup}
        />
      ) : (
        <AuthSignupForm
          email={email}
          setEmail={setEmail}
          error={error}
          setError={setError}
          success={success}
          setSuccess={setSuccess}
          loading={loading}
          setLoading={setLoading}
          showResendLink={showResendLink}
          setShowResendLink={setShowResendLink}
          onSwitchToLogin={switchToLogin}
        />
      )}
    </div>
  );
}
