import { useEffect, useState } from 'react';
import AppSelect from '../components/AppSelect';
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
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const formatMoney = (value) => moneyFormatter.format(Number(value || 0));
const formatPercent = (value) => (
  value === null || value === undefined ? 'N/A' : `${Number(value).toFixed(1)}%`
);

const AIInsights = () => {
  const { token } = useAuth();
  const [selectedMonth, setSelectedMonth] = useState(currentDate.getMonth() + 1);
  const [selectedYear, setSelectedYear] = useState(currentYear);
  const [score, setScore] = useState(null);
  const [summary, setSummary] = useState(null);
  const [snapshot, setSnapshot] = useState(null);
  const [generatedInsights, setGeneratedInsights] = useState([]);
  const [healthSignals, setHealthSignals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;

    const loadAIInsights = async () => {
      setLoading(true);
      setError('');
      try {
        const headers = getAuthHeaders(token);
        const params = {
          month: selectedMonth,
          year: selectedYear,
        };
        const [scoreResponse, summaryResponse, snapshotResponse, signalsResponse, insightsResponse] = await Promise.all([
          api.get('/financial-health/score', { headers, params }),
          api.get('/dashboard/summary', { headers, params }),
          api.get('/dashboard/snapshot', { headers, params }),
          api.get('/dashboard/insights', { headers, params }),
          api.get('/ai/insights', { headers, params }),
        ]);
        if (!cancelled) {
          setScore(scoreResponse.data);
          setSummary(summaryResponse.data);
          setSnapshot(snapshotResponse.data);
          setHealthSignals(signalsResponse.data?.insights || []);
          setGeneratedInsights(insightsResponse.data?.insights || []);
        }
      } catch (err) {
        console.error(err);
        if (!cancelled) {
          setError('Unable to load AI insights and financial health data.');
          setScore(null);
          setSummary(null);
          setSnapshot(null);
          setGeneratedInsights([]);
          setHealthSignals([]);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    if (token) {
      loadAIInsights();
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
            <p className="eyebrow">Financial intelligence</p>
            <h1>AI Insights</h1>
            <p>Your health score, financial snapshot, and generated spending insights in one view.</p>
          </div>
          <div className="health-actions">
            <label>
              Month
              <AppSelect
                value={selectedMonth}
                onChange={(nextValue) => setSelectedMonth(Number(nextValue))}
                ariaLabel="AI Insights month"
                options={monthOptions}
              />
            </label>
            <label>
              Year
              <AppSelect
                value={selectedYear}
                onChange={(nextValue) => setSelectedYear(Number(nextValue))}
                ariaLabel="AI Insights year"
                options={yearOptions.map((year) => ({ value: year, label: String(year) }))}
              />
            </label>
          </div>
        </div>

        {error && <div className="surface-message error">{error}</div>}

        {loading ? (
          <div className="empty-state">Preparing AI insights...</div>
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
                <h2>Monthly Financial Snapshot</h2>
                <p>Key figures for the selected month.</p>
              </div>

              <div className="health-snapshot-grid">
                <article>
                  <span>Income</span>
                  <strong>{formatMoney(summary?.total_income)}</strong>
                </article>
                <article>
                  <span>Opening Balance</span>
                  <strong>{formatMoney(summary?.opening_balance)}</strong>
                </article>
                <article>
                  <span>Available Funds</span>
                  <strong>{formatMoney(summary?.available_funds)}</strong>
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

              <div className="insight-section-heading">
                <div>
                  <h2>Generated AI Insights</h2>
                  <p>Personalized observations generated from your transaction data.</p>
                </div>
                <span>{generatedInsights.length} insights</span>
              </div>
              <div className="health-insights-list generated-insights-list">
                {generatedInsights.length === 0 ? (
                  <div className="empty-state">Add transactions to generate AI insights.</div>
                ) : generatedInsights.map((insight, index) => (
                  <article className="health-insight-card" key={insight.id || `${insight.insight_type}-${index}`}>
                    <span className="health-insight-index">{index + 1}</span>
                    <div>
                      <h3>{insight.insight_type?.replaceAll('_', ' ') || 'Insight'}</h3>
                      <p>{insight.insight_text}</p>
                    </div>
                  </article>
                ))}
              </div>

              <div className="insight-section-heading">
                <div>
                  <h2>Health Signals</h2>
                  <p>Score-linked signals calculated from your current financial patterns.</p>
                </div>
                <span>{healthSignals.length} signals</span>
              </div>
              <div className="health-insights-list">
                {healthSignals.length === 0 ? (
                  <div className="empty-state">Add transactions to calculate health signals.</div>
                ) : healthSignals.map((insight, index) => (
                  <article className="health-insight-card" key={`${insight.title}-${index}`}>
                    <span className="health-insight-index">{index + 1}</span>
                    <div>
                      <h3>{insight.title || 'Health signal'}</h3>
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

export default AIInsights;
