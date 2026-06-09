import { useEffect, useState } from 'react';
import Navigation from '../components/Navigation';
import { useAuth } from '../hooks/useAuth';
import api, { getAuthHeaders } from '../utils/api';
import '../styles/Insights.css';

const monthOptions = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
].map((label, index) => ({ label, value: index + 1 }));

const currentDate = new Date();
const currentYear = currentDate.getFullYear();
const yearOptions = Array.from({ length: 7 }, (_, index) => currentYear - 5 + index);

const insightLabels = {
  spending: 'Spending',
  comparison: 'Monthly Comparison',
  category_increase: 'Category Increase',
  anomaly: 'Unusual Spending',
  subscription: 'Subscriptions',
  ai: 'AI Insight',
};

const Insights = () => {
  const { token } = useAuth();
  const [selectedMonth, setSelectedMonth] = useState(currentDate.getMonth() + 1);
  const [selectedYear, setSelectedYear] = useState(currentYear);
  const [insights, setInsights] = useState([]);
  const [loading, setLoading] = useState(true);
  const [regenerating, setRegenerating] = useState(false);
  const [error, setError] = useState('');

  const loadInsights = async (regenerate = false) => {
    if (regenerate) {
      setRegenerating(true);
    } else {
      setLoading(true);
    }
    setError('');

    try {
      const response = await api.get('/ai/insights', {
        headers: getAuthHeaders(token),
        params: {
          month: selectedMonth,
          year: selectedYear,
          regenerate,
        },
      });
      setInsights(response.data.insights);
    } catch (err) {
      console.error(err);
      setError('Unable to load AI spending insights.');
    } finally {
      setLoading(false);
      setRegenerating(false);
    }
  };

  useEffect(() => {
    let cancelled = false;

    const loadInitialInsights = async () => {
      setLoading(true);
      setError('');
      try {
        const response = await api.get('/ai/insights', {
          headers: getAuthHeaders(token),
          params: {
            month: selectedMonth,
            year: selectedYear,
          },
        });
        if (!cancelled) {
          setInsights(response.data.insights);
        }
      } catch (err) {
        console.error(err);
        if (!cancelled) {
          setError('Unable to load AI spending insights.');
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    if (token) {
      loadInitialInsights();
    }

    return () => {
      cancelled = true;
    };
  }, [token, selectedMonth, selectedYear]);

  return (
    <div>
      <Navigation />
      <main className="insights-page">
        <div className="page-heading">
          <div>
            <p className="eyebrow">AI spending insights</p>
            <h1>Financial Insights</h1>
            <p>Review month-over-month patterns, subscription signals, spending spikes, and category changes.</p>
          </div>
          <div className="insights-actions">
            <label>
              Month
              <select value={selectedMonth} onChange={(event) => setSelectedMonth(Number(event.target.value))}>
                {monthOptions.map((month) => (
                  <option key={month.value} value={month.value}>{month.label}</option>
                ))}
              </select>
            </label>
            <label>
              Year
              <select value={selectedYear} onChange={(event) => setSelectedYear(Number(event.target.value))}>
                {yearOptions.map((year) => (
                  <option key={year} value={year}>{year}</option>
                ))}
              </select>
            </label>
            <button className="primary-button" onClick={() => loadInsights(true)} disabled={regenerating}>
              {regenerating ? 'Regenerating...' : 'Regenerate'}
            </button>
          </div>
        </div>

        {error && <div className="surface-message error">{error}</div>}

        {loading ? (
          <div className="empty-state">Loading insights...</div>
        ) : insights.length === 0 ? (
          <div className="empty-state">Add transactions to generate AI spending insights.</div>
        ) : (
          <section className="insight-grid">
            {insights.map((insight) => (
              <article className="insight-card" key={insight.id}>
                <span>{insightLabels[insight.insight_type] || 'Insight'}</span>
                <p>{insight.insight_text}</p>
                <small>{new Date(insight.created_at).toLocaleString()}</small>
              </article>
            ))}
          </section>
        )}
      </main>
    </div>
  );
};

export default Insights;
