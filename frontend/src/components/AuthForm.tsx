import React, { useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import './AuthForm.css';

export function AuthForm() {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [showResendLink, setShowResendLink] = useState(false);
  const { signIn, signUp, resendConfirmationEmail } = useAuth();

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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    if (isLogin) {
      const { error: authError } = await signIn(email, password);
      setLoading(false);
      if (authError) {
        setError(authError.message);
      }
    } else {
      // Sign up
      const { data, error: authError } = await signUp(email, password);
      setLoading(false);
      
      if (authError) {
        setError(authError.message);
      } else if (data?.user) {
        // Signup successful
        // If email confirmation is disabled, user is automatically logged in
        // If email confirmation is enabled, show a message
        if (data.session) {
          // User is logged in (email confirmation disabled)
          setError(null);
          // The auth state change will automatically update the UI
        } else {
          // Email confirmation required
          setError('Please check your email to confirm your account before logging in.');
          setShowResendLink(true);
        }
      }
    }
  };

  const handleResendConfirmation = async () => {
    if (!email) {
      setError('Please enter your email address first.');
      return;
    }

    setError(null);
    setLoading(true);
    const { error: resendError } = await resendConfirmationEmail(email);
    setLoading(false);

    if (resendError) {
      setError(resendError.message);
    } else {
      setSuccess('Confirmation email sent! Please check your inbox.');
      setShowResendLink(false);
    }
  };

  return (
    <div className="auth-form">
      <h2>{isLogin ? 'Login' : 'Register'}</h2>
      <form onSubmit={handleSubmit}>
        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          disabled={loading}
        />
        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          disabled={loading}
        />
        {error && <div className="error">{error}</div>}
        {success && <div className="success">{success}</div>}
        <button type="submit" disabled={loading}>
          {loading ? 'Loading...' : isLogin ? 'Login' : 'Register'}
        </button>
      </form>
      {showResendLink && !isLogin && (
        <div style={{ marginTop: '10px', textAlign: 'center' }}>
          <button
            onClick={handleResendConfirmation}
            disabled={loading}
            type="button"
            style={{
              background: 'none',
              border: 'none',
              color: '#3b82f6',
              cursor: 'pointer',
              fontSize: '14px',
              textDecoration: 'underline',
            }}
          >
            Resend confirmation email
          </button>
        </div>
      )}
      <button
        onClick={() => {
          setIsLogin(!isLogin);
          setShowResendLink(false);
          setError(null);
          setSuccess(null);
        }}
        disabled={loading}
        type="button"
      >
        {isLogin ? 'Need an account? Register' : 'Have an account? Login'}
      </button>
    </div>
  );
}
