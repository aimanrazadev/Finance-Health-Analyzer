import { useContext } from 'react';
import AuthStateContext from '../context/AuthStateContext';

export const useAuth = () => {
  const context = useContext(AuthStateContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};
