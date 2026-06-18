import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import Navigation from '../components/Navigation';
import { useAuth } from '../hooks/useAuth';
import api, { getAuthHeaders } from '../utils/api';

const now = new Date();
const monthOptions = [
  { value: 1, label: 'January' },
  { value: 2, label: 'February' },
  { value: 3, label: 'March' },
  { value: 4, label: 'April' },
  { value: 5, label: 'May' },
  { value: 6, label: 'June' },
  { value: 7, label: 'July' },
  { value: 8, label: 'August' },
  { value: 9, label: 'September' },
  { value: 10, label: 'October' },
  { value: 11, label: 'November' },
  { value: 12, label: 'December' },
];
const currentYear = now.getFullYear();
const yearOptions = Array.from({ length: 7 }, (_, index) => currentYear - 5 + index);

const moneyFormatter = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  maximumFractionDigits: 0,
});

const formatMoney = (value) => moneyFormatter.format(Number(value || 0));

const AIInsights = () => {
  const { token } = useAuth();
  const [selectedMonth, setSelectedMonth] = useState(now.getMonth() + 1);
  const [selectedYear, setSelectedYear] = useState(currentYear);
  const [summary, setSummary] = useState(null);
  const [snapshot, setSnapshot] = useState(null);
  const [insights, setInsights] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;

    const loadInsights = async () => {
      setLoading(true);
      setError('');
      const headers = getAuthHeaders(token);
      const params = { month: selectedMonth, year: selectedYear };

      try {
        const [summaryResponse, snapshotResponse, insightsResponse] = await Promise.all([
          api.get('/dashboard/summary', { headers, params }),
          api.get('/dashboard/snapshot', { headers, params }),
          api.get('/dashboard/insights', { headers, params }),
        ]);
        if (cancelled) return;
        setSummary(summaryResponse.data);
        setSnapshot(snapshotResponse.data);
        setInsights(insightsResponse.data.insights || []);
      } catch (err) {
        console.error(err);
        if (!cancelled) setError('Unable to load AI insights.');
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    if (token) loadInsights();

    return () => {
      cancelled = true;
    };
  }, [token, selectedMonth, selectedYear]);

  return (
    <div>
      <Navigation />
      <main className="dashboard-container premium-dashboard ai-insights-page">
        <header className="premium-dashboard-header">
          <div>
            <p className="eyebrow">AI Insights</p>
            <h1>Financial signals from your data</h1>
            <p>Insights are generated from uploaded and categorized transactions. No chatbot here.</p>
          </div>
          <div className="premium-header-actions">
            <label className="premium-date-control">
              <span className="control-glyph" aria-hidden="true">□</span>
              <select value={selectedMonth} onChange={(event) => setSelectedMonth(Number(event.target.value))}>
                {monthOptions.map((month) => (
                  <option key={month.value} value={month.value}>{month.label} {selectedYear}</option>
                ))}
              </select>
            </label>
            <label className="premium-year-control">
              <select value={selectedYear} onChange={(event) => setSelectedYear(Number(event.target.value))}>
                {yearOptions.map((year) => <option key={year} value={year}>{year}</option>)}
              </select>
            </label>
          </div>
        </header>

        {error && <div className="surface-message error">{error}</div>}

        <section className="ai-insights-shell">
          <article className="dashboard-card ai-insights-snapshot">
            <div className="premium-panel-header">
              <div>
                <h2>Financial Snapshot</h2>
                <p>Current period summary and projected month-end pace.</p>
              </div>
              <Link to="/dashboard">Back to dashboard</Link>
            </div>
            <div className="ai-insights-metric-grid">
              <div>
                <span>Income</span>
                <strong>{loading ? 'Loading...' : formatMoney(summary?.total_income)}</strong>
              </div>
              <div>
                <span>Expenses</span>
                <strong>{loading ? 'Loading...' : formatMoney(summary?.total_expenses)}</strong>
              </div>
              <div>
                <span>Savings rate</span>
                <strong>{loading ? 'Loading...' : `${Number(summary?.savings_rate || 0).toFixed(1)}%`}</strong>
              </div>
              <div>
                <span>Health score</span>
                <strong>{loading ? 'Loading...' : `${summary?.financial_health_score || 0}/100`}</strong>
              </div>
              <div>
                <span>Projected spending</span>
                <strong>{loading ? 'Loading...' : formatMoney(snapshot?.projected_month_end_spending)}</strong>
              </div>
              <div>
                <span>Projected savings</span>
                <strong>{loading ? 'Loading...' : formatMoney(snapshot?.projected_month_end_savings)}</strong>
              </div>
            </div>
          </article>

          <section className="ai-insights-list-section">
            <div className="premium-panel-header">
              <div>
                <h2>Insight Cards</h2>
                <p>Readable observations from spending, savings, merchant, and subscription analytics.</p>
              </div>
            </div>
            {loading ? (
              <div className="chart-empty-state">Loading insights...</div>
            ) : insights.length === 0 ? (
              <div className="chart-empty-state">Upload transactions to generate insights.</div>
            ) : (
              <div className="ai-insights-card-grid">
                {insights.map((insight, index) => (
                  <article className="premium-insight-card" key={`${insight.title}-${index}`}>
                    <span className="metric-icon small" aria-hidden="true">{index + 1}</span>
                    <div>
                      <strong>{insight.title || 'Insight'}</strong>
                      <p>{insight.message}</p>
                      <small>{index === 0 ? 'Just now' : `${index + 1} min ago`}</small>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </section>
        </section>
      </main>
    </div>
  );
};

export default AIInsights;
