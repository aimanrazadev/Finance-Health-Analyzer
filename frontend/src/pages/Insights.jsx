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

const moneyFormatter = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  maximumFractionDigits: 0,
});

const priorityLabels = {
  High: 'High priority',
  Medium: 'Medium priority',
  Low: 'Low priority',
};

const Insights = () => {
  const { token } = useAuth();
  const [selectedMonth, setSelectedMonth] = useState(currentDate.getMonth() + 1);
  const [selectedYear, setSelectedYear] = useState(currentYear);
  const [insights, setInsights] = useState([]);
  const [recommendationSummary, setRecommendationSummary] = useState({
    total_income: 0,
    total_expenses: 0,
    savings_rate: 0,
    recommendations: [],
  });
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
      const [insightsResponse, recommendationsResponse] = await Promise.all([
        api.get('/ai/insights', {
          headers: getAuthHeaders(token),
          params: {
            month: selectedMonth,
            year: selectedYear,
            regenerate,
          },
        }),
        api.get('/budget-recommendations', {
          headers: getAuthHeaders(token),
          params: {
            month: selectedMonth,
            year: selectedYear,
          },
        }),
      ]);
      setInsights(insightsResponse.data.insights);
      setRecommendationSummary(recommendationsResponse.data);
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
        const [insightsResponse, recommendationsResponse] = await Promise.all([
          api.get('/ai/insights', {
            headers: getAuthHeaders(token),
            params: {
              month: selectedMonth,
              year: selectedYear,
            },
          }),
          api.get('/budget-recommendations', {
            headers: getAuthHeaders(token),
            params: {
              month: selectedMonth,
              year: selectedYear,
            },
          }),
        ]);
        if (!cancelled) {
          setInsights(insightsResponse.data.insights);
          setRecommendationSummary(recommendationsResponse.data);
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
            <p className="eyebrow">AI insights</p>
            <h1>AI Insights</h1>
            <p>Review spending insights, unusual activity, budget recommendations, priority levels, and potential savings.</p>
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

        <section className="insight-summary">
          <div>
            <span>Income</span>
            <strong>{moneyFormatter.format(recommendationSummary.total_income)}</strong>
          </div>
          <div>
            <span>Expenses</span>
            <strong>{moneyFormatter.format(recommendationSummary.total_expenses)}</strong>
          </div>
          <div>
            <span>Savings rate</span>
            <strong>{recommendationSummary.savings_rate.toFixed(1)}%</strong>
          </div>
          <div>
            <span>Potential savings</span>
            <strong>
              {moneyFormatter.format(
                recommendationSummary.recommendations.reduce((total, item) => total + Number(item.potential_savings || 0), 0)
              )}
            </strong>
          </div>
        </section>

        <section className="insights-section">
          <div className="section-heading">
            <div>
              <h2>Spending Insights</h2>
              <p>AI-generated signals for spending changes, unusual transactions, subscriptions, and category movement.</p>
            </div>
          </div>
          {loading ? (
            <div className="empty-state">Loading insights...</div>
          ) : insights.length === 0 ? (
            <div className="empty-state">Add transactions to generate AI spending insights.</div>
          ) : (
            <div className="insight-grid">
              {insights.map((insight) => (
                <article className="insight-card" key={insight.id}>
                  <span>{insightLabels[insight.insight_type] || 'Insight'}</span>
                  <p>{insight.insight_text}</p>
                  <small>{new Date(insight.created_at).toLocaleString()}</small>
                </article>
              ))}
            </div>
          )}
        </section>

        <section className="insights-section">
          <div className="section-heading">
            <div>
              <h2>Budget Recommendations</h2>
              <p>Ranked actions based on budget overages, high-spend categories, savings rate, and potential savings.</p>
            </div>
          </div>
          {loading ? (
            <div className="empty-state">Loading recommendations...</div>
          ) : recommendationSummary.recommendations.length === 0 ? (
            <div className="empty-state">Add income, expenses, and budgets to generate recommendations.</div>
          ) : (
            <div className="recommendation-grid">
              {recommendationSummary.recommendations.map((recommendation, index) => (
                <article className={`recommendation-card ${recommendation.priority.toLowerCase()}`} key={recommendation.id}>
                  <div className="recommendation-card-top">
                    <span>Recommendation {index + 1}</span>
                    <strong>{priorityLabels[recommendation.priority] || recommendation.priority}</strong>
                  </div>
                  <h2>{recommendation.title}</h2>
                  <p>{recommendation.recommendation_text}</p>
                  <div className="recommendation-meta">
                    <div>
                      <span>Potential savings</span>
                      <strong>{moneyFormatter.format(recommendation.potential_savings)}/month</strong>
                    </div>
                    <div>
                      <span>Reason</span>
                      <strong>{recommendation.reason.replaceAll('_', ' ')}</strong>
                    </div>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  );
};

export default Insights;
