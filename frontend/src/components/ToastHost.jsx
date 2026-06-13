import { useUI } from '../hooks/useUI';
import '../styles/UIPrimitives.css';

const ToastHost = () => {
  const { toasts } = useUI();

  return (
    <div className="toast-host" aria-live="polite">
      {toasts.map((toast) => (
        <div className={`toast toast-${toast.type}`} key={toast.id}>
          {toast.message}
        </div>
      ))}
    </div>
  );
};

export default ToastHost;
