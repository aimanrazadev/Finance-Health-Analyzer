import { useContext } from 'react';
import UIContext from './UIContextCore';

export default function useUI() {
  const context = useContext(UIContext);
  if (!context) {
    throw new Error('useUI must be used inside UIProvider');
  }
  return context;
}
