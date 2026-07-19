import { useUI } from '../../shared/context/UIContext';
import './UIPrimitives.css';

const ConfirmModal = () => {
  const { confirmState, closeConfirm } = useUI();

  if (!confirmState) return null;

  return (
    <div className="modal-backdrop" role="presentation">
      <section className="confirm-modal" role="dialog" aria-modal="true" aria-labelledby="confirm-title">
        <h2 id="confirm-title">{confirmState.title}</h2>
        <p>{confirmState.message}</p>
        <div className="confirm-actions">
          <button className="secondary-button" onClick={() => closeConfirm(false)}>
            {confirmState.cancelLabel}
          </button>
          <button className={confirmState.danger ? 'danger-button' : 'primary-button'} onClick={() => closeConfirm(true)}>
            {confirmState.confirmLabel}
          </button>
        </div>
      </section>
    </div>
  );
};

export default ConfirmModal;
