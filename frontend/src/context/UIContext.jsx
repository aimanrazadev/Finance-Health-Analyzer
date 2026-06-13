import { useCallback, useMemo, useState } from 'react';
import { UIContext } from './uiContextCore';

export const UIProvider = ({ children }) => {
  const [toasts, setToasts] = useState([]);
  const [confirmState, setConfirmState] = useState(null);

  const showToast = useCallback((message, type = 'success') => {
    const id = Date.now();
    setToasts((current) => [...current, { id, message, type }]);
    window.setTimeout(() => {
      setToasts((current) => current.filter((toast) => toast.id !== id));
    }, 3500);
  }, []);

  const confirm = useCallback((options) => (
    new Promise((resolve) => {
      setConfirmState({
        title: options.title || 'Confirm action',
        message: options.message || 'Are you sure?',
        confirmLabel: options.confirmLabel || 'Confirm',
        cancelLabel: options.cancelLabel || 'Cancel',
        danger: Boolean(options.danger),
        resolve,
      });
    })
  ), []);

  const closeConfirm = useCallback((value) => {
    setConfirmState((current) => {
      if (current?.resolve) {
        current.resolve(value);
      }
      return null;
    });
  }, []);

  const value = useMemo(() => ({
    toasts,
    showToast,
    confirm,
    confirmState,
    closeConfirm,
  }), [closeConfirm, confirm, confirmState, showToast, toasts]);

  return (
    <UIContext.Provider value={value}>
      <div>
        {children}
      </div>
    </UIContext.Provider>
  );
};
