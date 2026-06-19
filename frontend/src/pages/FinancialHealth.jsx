import { useEffect, useState } from 'react';
import Navigation from '../components/Navigation';
import { useAuth } from '../hooks/useAuth';
import api, { getAuthHeaders } from '../utils/api';
import '../styles/FinancialHealth.css';

const monthOptions = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
].map((label, index) => ({ label, value: index + 1 }));

const currentDate = new Date();
const currentYear = currentDate.getFullYear();
const yearOptions = Array.from({ length: 7 }, (_, index) => currentYear - 5 + index);

const statusClass = (label = '') => label.toLowerCase().replaceAll(' ', '-');
const moneyFormatter = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  maximumFractionDigits: 0,
});

const formatMoney = (value) => moneyFormatter.format(Number(value || 0));
const formatPercent = (value) => `${Number(value || 0).toFixed(1)}%`;

const FinancialHealth = () => {
  const { token } = useAuth();
  const [selectedMonth, setSelectedMonth] = useState(currentDate.getMonth() + 1);
  const [selectedYear, setSelectedYear] = useState(currentYear);
  const [score, setScore] = useState(null);
  const [summary, setSummary] = useState(null);
  const [snapshot, setSnapshot] = useState(null);
  const [insights, setInsights] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;

    const loadHealthIntelligence = async () => {
      setLoading(true);
      setError('');
      try {
        const headers = getAuthHeaders(token);
        const params = {
          month: selectedMonth,
          year: selectedYear,
        };
        const [scoreResponse, summaryResponse, snapshotResponse, insightsResponse] = await Promise.all([
          api.get('/financial-health/score', { headers, params }),
          api.get('/dashboard/summary', { headers, params }),
          api.get('/dashboard/snapshot', { headers, params }),
          api.get('/dashboard/insights', { headers, params }),
        ]);
        if (!cancelled) {
          setScore(scoreResponse.data);
          setSummary(summaryResponse.data);
          setSnapshot(snapshotResponse.data);
          setInsights(insightsResponse.data?.insights || []);
        }
      } catch (err) {
        console.error(err);
        if (!cancelled) {
          setError('Unable to calculate financial health and insights.');
          setScore(null);
          setSummary(null);
          setSnapshot(null);
          setInsights([]);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    if (token) {
      loadHealthIntelligence();
    }

    return () => {
      cancelled = true;
    };
  }, [token, selectedMonth, selectedYear]);

  return (
    <div>
      <Navigation />
      <main className="health-page">
        <div className="page-heading">
          <div>
            <p className="eyebrow">Financial health score</p>
            <h1>Financial Health</h1>
            <p>Understand savings strength, expense control, spending stability, and recurring payment load.</p>
          </div>
          <div className="health-actions">
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
          </div>
        </div>

        {error && <div className="surface-message error">{error}</div>}

        {loading ? (
          <div className="empty-state">Calculating financial health...</div>
        ) : !score ? (
          <div className="empty-state">Add income and expense transactions to calculate your financial health score.</div>
        ) : (
          <div className="health-layout">
            <section className={`health-score-card ${statusClass(score.status_label)}`}>
              <span>Overall score</span>
              <strong>{score.overall_score}</strong>
              <p>{score.status_label}</p>
              <small>Calculated {new Date(score.calculated_at).toLocaleString()}</small>
            </section>

            <section className="health-breakdown-panel">
              <div className="section-heading">
                <h2>Score Breakdown</h2>
                <p>Each component is scored out of 100 and combined into the final score.</p>
              </div>
              <div className="health-breakdown-list">
                {score.breakdown.map((item) => (
                  <article className="health-breakdown-row" key={item.label}>
                    <div>
                      <strong>{item.label}</strong>
                      <span>{item.description}</span>
                    </div>
                    <div className="health-bar-wrap">
                      <div className="health-bar">
                        <div style={{ width: `${item.score}%` }} />
                      </div>
                      <span className={`health-status ${statusClass(item.status)}`}>{item.status}</span>
                      <strong>{item.score}</strong>
                    </div>
                  </article>
                ))}
              </div>
            </section>

            <section className="health-tips-panel">
              <h2>Improvement Tips</h2>
              <div className="health-tips-list">
                {score.improvement_tips.map((tip) => (
                  <div className="health-tip" key={tip}>{tip}</div>
                ))}
              </div>
            </section>

            <section className="health-insights-panel">
              <div className="section-heading">
                <h2>AI Insights</h2>
                <p>Financial snapshot and readable signals for the selected month.</p>
              </div>

              <div className="health-snapshot-grid">
                <article>
                  <span>Income</span>
                  <strong>{formatMoney(summary?.total_income)}</strong>
                </article>
                <article>
                  <span>Expenses</span>
                  <strong>{formatMoney(summary?.total_expenses)}</strong>
                </article>
                <article>
                  <span>Savings Rate</span>
                  <strong>{formatPercent(summary?.savings_rate)}</strong>
                </article>
                <article>
                  <span>Projected Spending</span>
                  <strong>{formatMoney(snapshot?.projected_month_end_spending)}</strong>
                </article>
                <article>
                  <span>Projected Savings</span>
                  <strong>{formatMoney(snapshot?.projected_month_end_savings)}</strong>
                </article>
                <article>
                  <span>Top Signal</span>
                  <strong>{snapshot?.top_signal || summary?.top_category || 'No signal'}</strong>
                </article>
              </div>

              <div className="health-insights-list">
                {insights.length === 0 ? (
                  <div className="empty-state">Upload or add transactions to generate AI insights.</div>
                ) : insights.map((insight, index) => (
                  <article className="health-insight-card" key={`${insight.title}-${index}`}>
                    <span className="health-insight-index">{index + 1}</span>
                    <div>
                      <h3>{insight.title || 'Insight'}</h3>
                      <p>{insight.message}</p>
                    </div>
                  </article>
                ))}
              </div>
            </section>
          </div>
        )}
      </main>
    </div>
  );
};

export default FinancialHealth;
