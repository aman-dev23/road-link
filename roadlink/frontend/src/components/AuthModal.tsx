import React, { useState } from 'react';
import { api } from '../api/client';
import { useAuthStore } from '../store/useAuthStore';

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const AuthModal: React.FC<AuthModalProps> = ({ isOpen, onClose }) => {
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const { login } = useAuthStore();

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      if (isRegister) {
        const resp = await api.post('/api/auth/register', {
          email: email.trim(),
          password,
          display_name: displayName.trim(),
        });
        await login(resp.data.access_token, resp.data.refresh_token, resp.data.user);
      } else {
        const resp = await api.post('/api/auth/login', {
          email: email.trim(),
          password,
        });
        await login(resp.data.access_token, resp.data.refresh_token, resp.data.user);
      }
      onClose();
    } catch (err: any) {
      const msg = err.response?.data?.detail?.message || 'Authentication failed. Please check credentials.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-card auth-card" onClick={(e) => e.stopPropagation()}>
        <div className="auth-header">
          <div className="auth-logo">🛣️ RoadLink</div>
          <h3>{isRegister ? 'Join the Traveller Network' : 'Welcome back, Traveller'}</h3>
          <p className="subtext">
            {isRegister
              ? 'Get help and help other motorists on highways and roads.'
              : 'Sign in to access radar, live emergency alerts, and assistance.'}
          </p>
        </div>

        {error && <div className="alert-banner error">{error}</div>}

        <form onSubmit={handleSubmit} className="auth-form">
          {isRegister && (
            <div className="form-group">
              <label>Your Name / Handle</label>
              <input
                type="text"
                required
                minLength={2}
                maxLength={40}
                className="text-input"
                placeholder="e.g. Rahul Sharma"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
              />
            </div>
          )}

          <div className="form-group">
            <label>Email Address</label>
            <input
              type="email"
              required
              className="text-input"
              placeholder="e.g. rahul@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>

          <div className="form-group">
            <label>Password</label>
            <input
              type="password"
              required
              minLength={8}
              className="text-input"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>

          <button type="submit" className="btn-primary full-width" disabled={loading}>
            {loading ? 'Please wait...' : isRegister ? 'Create Account' : 'Sign In'}
          </button>
        </form>

        <div className="auth-footer">
          {isRegister ? (
            <p>
              Already registered?{' '}
              <button className="link-btn" onClick={() => { setIsRegister(false); setError(null); }}>
                Sign In
              </button>
            </p>
          ) : (
            <p>
              New to RoadLink?{' '}
              <button className="link-btn" onClick={() => { setIsRegister(true); setError(null); }}>
                Create Account
              </button>
            </p>
          )}
        </div>
      </div>
    </div>
  );
};

