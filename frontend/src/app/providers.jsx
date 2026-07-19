import { AuthProvider } from '../features/auth/authContext.jsx';
import { UIProvider } from '../shared/context/UIContext.jsx';
import ConfirmModal from '../components/ui/ConfirmModal';
import ToastHost from '../components/ui/ToastHost';

export default function Providers({ children }) {
  return (
    <AuthProvider>
      <UIProvider>
        {children}
        <ToastHost />
        <ConfirmModal />
      </UIProvider>
    </AuthProvider>
  );
}
