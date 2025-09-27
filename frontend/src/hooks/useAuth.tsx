import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { toast } from '@/hooks/use-toast';
import { apiFetch } from '@/lib/api';

interface AuthContextType {
  isAuthenticated: boolean;
  username: string | null;
  token: string | null;
  login: (token: string, username: string) => void;
  logout: () => void;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider = ({ children }: AuthProviderProps) => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [username, setUsername] = useState<string | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Check for existing token on mount
  useEffect(() => {
    const checkAuth = async () => {
      const storedToken = localStorage.getItem('digiclinic_token');
      const storedUsername = localStorage.getItem('digiclinic_username');

      if (storedToken && storedUsername) {
        try {
          // Verify token with backend
          const response = await apiFetch('/api/auth/verify', {
            auth: true,
            token: storedToken,
          });

          if (response.ok) {
            setToken(storedToken);
            setUsername(storedUsername);
            setIsAuthenticated(true);
          } else {
            // Token invalid, clear storage
            localStorage.removeItem('digiclinic_token');
            localStorage.removeItem('digiclinic_username');
          }
        } catch (error) {
          console.error('Auth verification failed:', error);
          localStorage.removeItem('digiclinic_token');
          localStorage.removeItem('digiclinic_username');
        }
      }
      setIsLoading(false);
    };

    checkAuth();

    // Listen for global unauthorized events to auto-logout
    const onUnauthorized = () => {
      toast({ title: 'Session expired', description: 'Please log in again.', variant: 'destructive' });
      logout();
    };
    window.addEventListener('auth:unauthorized' as any, onUnauthorized);
    return () => window.removeEventListener('auth:unauthorized' as any, onUnauthorized);
  }, []);

  const login = (newToken: string, newUsername: string) => {
    setToken(newToken);
    setUsername(newUsername);
    setIsAuthenticated(true);
    localStorage.setItem('digiclinic_token', newToken);
    localStorage.setItem('digiclinic_username', newUsername);
  };

  const logout = () => {
    setToken(null);
    setUsername(null);
    setIsAuthenticated(false);
    localStorage.removeItem('digiclinic_token');
    localStorage.removeItem('digiclinic_username');
  };

  const value = {
    isAuthenticated,
    username,
    token,
    login,
    logout,
    isLoading,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};