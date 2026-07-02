import { useEffect, useState } from 'react';
import AuthStateContext from './AuthStateContext';
import api, { getAuthHeaders } from '../utils/api';
import { clearPeriodSelection } from '../utils/periodSession';

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(() => localStorage.getItem('access_token'));
  const [loading, setLoading] = useState(() => Boolean(localStorage.getItem('access_token')));
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;

    const fetchCurrentUser = async () => {
      try {
        const response = await api.get('/auth/me', {
          headers: getAuthHeaders(token)
        });
        if (!cancelled) {
          setUser(response.data);
          setError(null);
        }
      } catch (err) {
        console.error('Failed to fetch current user:', err);
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        if (!cancelled) {
          setToken(null);
          setUser(null);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    if (!token) {
      return undefined;
    }

    fetchCurrentUser();

    return () => {
      cancelled = true;
    };
  }, [token]);

  const register = async (name, email, password) => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.post('/auth/register', {
        name,
        email,
        password
      });

      const { access_token, refresh_token, user: userData } = response.data;

      localStorage.setItem('access_token', access_token);
      if (refresh_token) {
        localStorage.setItem('refresh_token', refresh_token);
      }

      setToken(access_token);
      setUser(userData);
      setError(null);
      clearPeriodSelection();

      return { success: true, user: userData };
    } catch (err) {
      const errorMessage = err.response?.data?.detail || 'Registration failed';
      setError(errorMessage);
      return { success: false, error: errorMessage };
    } finally {
      setLoading(false);
    }
  };

  const login = async (email, password) => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.post('/auth/login', {
        email,
        password
      });

      const { access_token, refresh_token, user: userData } = response.data;

      localStorage.setItem('access_token', access_token);
      if (refresh_token) {
        localStorage.setItem('refresh_token', refresh_token);
      }

      setToken(access_token);
      setUser(userData);
      setError(null);

      return { success: true, user: userData };
    } catch (err) {
      const errorMessage = err.response?.data?.detail || 'Login failed';
      setError(errorMessage);
      return { success: false, error: errorMessage };
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    clearPeriodSelection();
    setToken(null);
    setUser(null);
    setError(null);
  };

  const value = {
    user,
    token,
    loading,
    error,
    register,
    login,
    logout,
    isAuthenticated: !!token
  };

  return (
    <AuthStateContext.Provider value={value}>
      {children}
    </AuthStateContext.Provider>
  );
};
