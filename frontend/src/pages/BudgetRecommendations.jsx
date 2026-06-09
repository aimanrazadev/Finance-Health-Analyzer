import { useEffect, useState } from 'react';
import Navigation from '../components/Navigation';
import { useAuth } from '../hooks/useAuth';
import api, { getAuthHeaders } from '../utils/api';
import '../styles/BudgetRecommendations.css';

const monthOptions = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
].map((label, index) => ({ label, value: index + 1 }));

const currentDate = new Date();
const currentYear = currentDate.getFullYear();
const yearOptions = Array.from({ length: 7 }, (_, index) => currentYear - 5 + index);

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

const BudgetRecommendations = () => {
  const { token } = useAuth();
  const [selectedMonth, setSelectedMonth] = useState(currentDate.getMonth() + 1);
  const [selectedYear, setSelectedYear] = useState(currentYear);
  const [summary, setSummary] = useState({
    total_income: 0,
    total_expenses: 0,
    savings_rate: 0,
    recommendations: [],
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;

    const loadRecommendations = async () => {
      setLoading(true);
      setError('');
      try {
        const response = await api.get('/budget-recommendations', {
          headers: getAuthHeaders(token),
          params: {
            month: selectedMonth,
            year: selectedYear,
          },
        });
        if (!cancelled) {
          setSummary(response.data);
        }
      } catch (err) {
        console.error(err);
        if (!cancelled) {
          setError('Unable to load budget recommendations.');
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    if (token) {
      loadRecommendations();
    }

    return () => {
      cancelled = true;
    };
  }, [token, selectedMonth, selectedYear]);

  return (
    <div>
      <Navigation />
      <main className="recommendations-page">
        <div className="page-heading">
          <div>
            <p className="eyebrow">AI budget recommendations</p>
            <h1>Budget Recommendations</h1>
            <p>Review ranked actions based on budget overages, savings rate, income share, and high-spend categories.</p>
          </div>
          <div className="recommendation-actions">
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

        <section className="recommendation-summary">
          <div>
            <span>Income</span>
            <strong>{moneyFormatter.format(summary.total_income)}</strong>
          </div>
          <div>
            <span>Expenses</span>
            <strong>{moneyFormatter.format(summary.total_expenses)}</strong>
          </div>
          <div>
            <span>Savings rate</span>
            <strong>{summary.savings_rate.toFixed(1)}%</strong>
          </div>
        </section>

        {loading ? (
          <div className="empty-state">Loading recommendations...</div>
        ) : summary.recommendations.length === 0 ? (
          <div className="empty-state">Add income, expenses, and budgets to generate recommendations.</div>
        ) : (
          <section className="recommendation-grid">
            {summary.recommendations.map((recommendation, index) => (
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
          </section>
        )}
      </main>
    </div>
  );
};

export default BudgetRecommendations;
