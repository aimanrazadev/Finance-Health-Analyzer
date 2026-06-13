import { useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import api, { getAuthHeaders } from '../utils/api';
import '../styles/Assistant.css';

const defaultSuggestions = [
  'How much did I spend this month?',
  'Show my top merchants this month',
  'Which categories are over budget?',
  'Search transactions for Zomato',
  'Change all Zomato transactions to Food',
];

const initialMessages = [
  {
    role: 'assistant',
    text: 'Ask me about spending, budgets, goals, friends, uploads, or transaction updates. I will ask before changing anything.',
  },
];

const FloatingAssistant = () => {
  const { token } = useAuth();
  const [open, setOpen] = useState(false);
  const [minimized, setMinimized] = useState(false);
  const [messages, setMessages] = useState(initialMessages);
  const [input, setInput] = useState('');
  const [suggestions, setSuggestions] = useState(defaultSuggestions);
  const [pendingAction, setPendingAction] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [unread, setUnread] = useState(1);

  const sendMessage = async (text = input) => {
    const message = text.trim();
    if (!message) return;
    setMessages((current) => [...current, { role: 'user', text: message }]);
    setInput('');
    setLoading(true);
    setError('');
    try {
      const response = await api.post('/assistant/chat', { message }, { headers: getAuthHeaders(token) });
      setMessages((current) => [...current, {
        role: 'assistant',
        text: response.data.message,
        data: response.data.data,
        pendingAction: response.data.pending_action,
      }]);
      setPendingAction(response.data.pending_action);
      setSuggestions(response.data.suggested_questions?.length ? response.data.suggested_questions : defaultSuggestions);
      if (!open || minimized) {
        setUnread((current) => current + 1);
      }
    } catch (err) {
      console.error(err);
      setError('Unable to reach the assistant.');
    } finally {
      setLoading(false);
    }
  };

  const confirmAction = async (confirm) => {
    if (!pendingAction) return;
    setLoading(true);
    setError('');
    try {
      const response = await api.post('/assistant/confirm', {
        audit_id: pendingAction.audit_id,
        confirm,
      }, { headers: getAuthHeaders(token) });
      setMessages((current) => [...current, {
        role: 'assistant',
        text: response.data.message,
        data: response.data.result,
      }]);
      setPendingAction(null);
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || 'Unable to confirm assistant action.');
    } finally {
      setLoading(false);
    }
  };

  const openChat = () => {
    setOpen(true);
    setMinimized(false);
    setUnread(0);
  };

  const minimizeChat = () => {
    setMinimized(true);
  };

  const closeChat = () => {
    setOpen(false);
    setMinimized(false);
  };

  return (
    <div className="floating-assistant">
      {open && !minimized && (
        <section className="assistant-popup" aria-label="AI assistant chat">
          <header className="assistant-popup-header">
            <div>
              <span>FinSight AI</span>
              <strong>Finance Assistant</strong>
            </div>
            <div className="assistant-window-actions">
              <button type="button" onClick={minimizeChat} aria-label="Minimize chat">-</button>
              <button type="button" onClick={closeChat} aria-label="Close chat">x</button>
            </div>
          </header>

          {error && <div className="assistant-error">{error}</div>}

          <div className="assistant-suggestions">
            {suggestions.slice(0, 4).map((suggestion) => (
              <button key={suggestion} onClick={() => sendMessage(suggestion)} disabled={loading}>
                {suggestion}
              </button>
            ))}
          </div>

          <div className="assistant-thread">
            {messages.map((message, index) => (
              <article className={`assistant-message ${message.role}`} key={`${message.role}-${index}`}>
                <p>{message.text}</p>
                {message.pendingAction && (
                  <div className="assistant-action-preview">
                    <strong>{message.pendingAction.explanation}</strong>
                    <pre>{JSON.stringify(message.pendingAction.preview, null, 2)}</pre>
                  </div>
                )}
              </article>
            ))}
            {loading && <div className="assistant-loading">Thinking...</div>}
          </div>

          {pendingAction && (
            <div className="assistant-confirm-bar">
              <span>Confirm this action?</span>
              <button className="primary-button" onClick={() => confirmAction(true)} disabled={loading}>Confirm</button>
              <button className="secondary-button" onClick={() => confirmAction(false)} disabled={loading}>Cancel</button>
            </div>
          )}

          <form className="assistant-input" onSubmit={(event) => {
            event.preventDefault();
            sendMessage();
          }}>
            <input
              value={input}
              onChange={(event) => setInput(event.target.value)}
              placeholder="Ask me about your finances..."
            />
            <button className="primary-button" type="submit" disabled={loading}>Send</button>
          </form>
        </section>
      )}

      {open && minimized && (
        <button type="button" className="assistant-minimized" onClick={openChat}>
          Finance Assistant
          {unread > 0 && <span>{unread}</span>}
        </button>
      )}

      {!open && (
        <button type="button" className="assistant-fab" onClick={openChat} aria-label="Open AI assistant">
          +
          {unread > 0 && <span>{unread}</span>}
        </button>
      )}
    </div>
  );
};

export default FloatingAssistant;
