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

const FinancialHealth = () => {
  const { token } = useAuth();
  const [selectedMonth, setSelectedMonth] = useState(currentDate.getMonth() + 1);
  const [selectedYear, setSelectedYear] = useState(currentYear);
  const [score, setScore] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;

    const loadScore = async () => {
      setLoading(true);
      setError('');
      try {
        const response = await api.get('/financial-health/score', {
          headers: getAuthHeaders(token),
          params: {
            month: selectedMonth,
            year: selectedYear,
          },
        });
        if (!cancelled) {
          setScore(response.data);
        }
      } catch (err) {
        console.error(err);
        if (!cancelled) {
          setError('Unable to calculate financial health score.');
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    if (token) {
      loadScore();
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
          </div>
        )}
      </main>
    </div>
  );
};

export default FinancialHealth;
