import { useContext } from 'react';
import { UIContext } from '../context/uiContextCore';

export const useUI = () => {
  const context = useContext(UIContext);
  if (!context) {
    throw new Error('useUI must be used inside UIProvider');
  }
  return context;
};
