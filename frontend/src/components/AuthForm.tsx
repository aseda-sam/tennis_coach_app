import React, { useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import './AuthForm.css';

export function AuthForm() {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const { signIn, signUp } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    const { error: authError } = isLogin
      ? await signIn(email, password)
      : await signUp(email, password);

    setLoading(false);

    if (authError) {
      setError(authError.message);
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
        <button type="submit" disabled={loading}>
          {loading ? 'Loading...' : isLogin ? 'Login' : 'Register'}
        </button>
      </form>
      <button
        onClick={() => setIsLogin(!isLogin)}
        disabled={loading}
        type="button"
      >
        {isLogin ? 'Need an account? Register' : 'Have an account? Login'}
      </button>
    </div>
  );
}
