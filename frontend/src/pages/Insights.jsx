import { useState } from 'react';
import Navigation from '../components/Navigation';
import { useAuth } from '../hooks/useAuth';
import api, { getAuthHeaders } from '../utils/api';
import '../styles/Insights.css';

const currentDate = new Date();
const currentYear = currentDate.getFullYear();
const monthOptions = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
].map((label, index) => ({ label, value: index + 1 }));
const yearOptions = Array.from({ length: 7 }, (_, index) => currentYear - 5 + index);

const suggestedQuestions = [
  'How can I save more this month?',
  'Where am I overspending?',
  'Review my subscriptions',
  'How can I improve my health score?',
  'Generate a monthly report',
  'Search transactions above INR 500',
];

const parseAssistantContent = (content) => {
  try {
    return JSON.parse(content);
  } catch {
    return {
      summary: content,
      main_problem: '',
      recommendations: [],
      subscriptions: [],
      risk_note: 'This is budgeting guidance, not investment, tax, or legal advice.',
    };
  }
};

const Insights = () => {
  const { token } = useAuth();
  const [selectedMonth, setSelectedMonth] = useState(currentDate.getMonth() + 1);
  const [selectedYear, setSelectedYear] = useState(currentYear);
  const [question, setQuestion] = useState('');
  const [activeChatId, setActiveChatId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const headers = getAuthHeaders(token);

  const askAdvisor = async (event) => {
    event.preventDefault();
    if (!question.trim()) return;
    setLoading(true);
    setError('');

    try {
      const response = await api.post('/advisor/ask', {
        question: question.trim(),
        chat_id: activeChatId,
        month: selectedMonth,
        year: selectedYear,
      }, { headers });
      setActiveChatId(response.data.chat.id);
      setQuestion('');
      await openChat(response.data.chat.id);
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || 'Unable to generate advisor response.');
    } finally {
      setLoading(false);
    }
  };

  const openChat = async (chatId) => {
    setError('');
    try {
      const response = await api.get(`/advisor/chats/${chatId}`, { headers });
      setActiveChatId(chatId);
      setMessages(response.data.messages);
    } catch (err) {
      console.error(err);
      setError('Unable to open advisor chat.');
    }
  };

  const startNewChat = async () => {
    setActiveChatId(null);
    setMessages([]);
    setQuestion('');
  };

  const handleQuestionKeyDown = (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      event.currentTarget.form?.requestSubmit();
    }
  };

  return (
    <div>
      <Navigation />
      <main className="advisor-page">
        <section className="simple-advisor-shell">
          <header className="simple-advisor-header">
            <div>
              <span>AI Advisor</span>
              <h1>Finance chat</h1>
            </div>
            <div className="simple-advisor-actions">
              <button type="button" onClick={startNewChat}>New chat</button>
              <select value={selectedMonth} onChange={(event) => setSelectedMonth(Number(event.target.value))}>
                {monthOptions.map((month) => <option key={month.value} value={month.value}>{month.label}</option>)}
              </select>
              <select value={selectedYear} onChange={(event) => setSelectedYear(Number(event.target.value))}>
                {yearOptions.map((year) => <option key={year} value={year}>{year}</option>)}
              </select>
            </div>
          </header>

          {error && <div className="surface-message error">{error}</div>}

          <div className="simple-chat-window">
            <article className="simple-chat-message assistant">
              <div className="simple-avatar">AI</div>
              <div>
                <strong>AI Advisor</strong>
                <p>Ask me about your spending, savings, subscriptions, or health score. I use your uploaded transaction data before answering.</p>
                {messages.length === 0 && (
                  <div className="simple-suggestion-grid">
                    {suggestedQuestions.map((item) => (
                      <button type="button" key={item} onClick={() => setQuestion(item)}>
                        {item}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </article>

            {messages.map((message) => {
              const parsed = message.role === 'assistant' ? parseAssistantContent(message.content) : null;
              return (
                <article className={`simple-chat-message ${message.role}`} key={message.id}>
                  <div className="simple-avatar">{message.role === 'assistant' ? 'AI' : 'You'}</div>
                  <div>
                    <strong>{message.role === 'assistant' ? 'AI Advisor' : 'You'}</strong>
                    <p>{message.role === 'assistant' ? parsed.summary : message.content}</p>
                    {message.role === 'assistant' && parsed.main_problem && (
                      <div className="simple-advice-card">
                        <span>Main issue</span>
                        <p>{parsed.main_problem}</p>
                      </div>
                    )}
                    {message.role === 'assistant' && parsed.recommendations?.length > 0 && (
                      <div className="simple-advice-list">
                        {parsed.recommendations.slice(0, 3).map((item, index) => (
                          <div key={`${item.title}-${index}`}>
                            <span>{item.title}</span>
                            <p>{item.impact || item.reason}</p>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </article>
              );
            })}

            {loading && (
              <article className="simple-chat-message assistant simple-thinking">
                <div className="simple-avatar">AI</div>
                <div>
                  <strong>AI Advisor</strong>
                  <p>Reading your finance data...</p>
                </div>
              </article>
            )}
          </div>

          <form className="simple-chat-composer" onSubmit={askAdvisor}>
            <textarea
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              onKeyDown={handleQuestionKeyDown}
              placeholder="Message AI Advisor..."
              rows={1}
            />
            <button type="submit" disabled={loading || !question.trim()}>
              {loading ? '...' : 'Send'}
            </button>
          </form>
        </section>
      </main>
    </div>
  );
};

export default Insights;
