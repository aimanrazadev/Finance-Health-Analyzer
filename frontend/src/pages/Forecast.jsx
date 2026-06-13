import { useEffect, useMemo, useState } from 'react';
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import Navigation from '../components/Navigation';
import { useAuth } from '../hooks/useAuth';
import api, { getAuthHeaders } from '../utils/api';
import '../styles/Forecast.css';

const moneyFormatter = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  maximumFractionDigits: 0,
});

const currencyTooltip = (value) => (value === null || value === undefined ? '-' : moneyFormatter.format(value));

const Forecast = () => {
  const { token } = useAuth();
  const [forecast, setForecast] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;

    const loadForecast = async () => {
      setLoading(true);
      setError('');
      try {
        const response = await api.get('/forecast/expenses', {
          headers: getAuthHeaders(token),
        });
        if (!cancelled) {
          setForecast(response.data);
        }
      } catch (err) {
        console.error(err);
        if (!cancelled) {
          setError('Unable to generate expense forecast.');
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    if (token) {
      loadForecast();
    }

    return () => {
      cancelled = true;
    };
  }, [token]);

  const chartData = useMemo(() => (
    forecast?.history?.map((item) => ({
      month: item.month,
      actual: item.actual_expenses,
      forecast: item.predicted_expenses,
    })) || []
  ), [forecast]);

  const previousSpending = Number(forecast?.feature_summary?.previous_month_spending || 0);
  const predictedAmount = Number(forecast?.predicted_amount || 0);
  const forecastDelta = predictedAmount - previousSpending;
  const forecastTrendClass = previousSpending === 0
    ? 'prediction-neutral'
    : forecastDelta > 0
      ? 'prediction-up'
      : forecastDelta < 0
        ? 'prediction-down'
        : 'prediction-neutral';
  const forecastTrendText = previousSpending === 0
    ? 'Waiting for previous month comparison'
    : forecastDelta > 0
      ? `${moneyFormatter.format(Math.abs(forecastDelta))} above previous month`
      : forecastDelta < 0
        ? `${moneyFormatter.format(Math.abs(forecastDelta))} below previous month`
        : 'Same as previous month';

  return (
    <div>
      <Navigation />
      <main className="forecast-page">
        <div className="page-heading">
          <div>
            <p className="eyebrow">Expense forecasting ML</p>
            <h1>Expense Forecast</h1>
            <p>Predict next month spending using monthly history, income, transaction count, and category trends.</p>
          </div>
        </div>

        {error && <div className="surface-message error">{error}</div>}

        {loading ? (
          <div className="empty-state">Training forecast model...</div>
        ) : !forecast ? (
          <div className="empty-state">Add transactions to generate an expense forecast.</div>
        ) : (
          <>
            <section className="forecast-summary-grid">
              <article className={`forecast-main-card prediction-card ${forecastTrendClass}`}>
                <span>Next month forecast</span>
                <strong>{moneyFormatter.format(forecast.predicted_amount)}</strong>
                <p>{forecast.forecast_month}</p>
                <small>
                  Range: {moneyFormatter.format(forecast.confidence_lower)} - {moneyFormatter.format(forecast.confidence_upper)}
                </small>
                <em>{forecastTrendText}</em>
              </article>
              <article className="forecast-metric-card">
                <span>Model used</span>
                <strong>{forecast.model_used.replaceAll('_', ' ')}</strong>
                <small>{forecast.accuracy ? `${forecast.accuracy}% fit accuracy` : 'Limited history fallback'}</small>
              </article>
              <article className={`forecast-metric-card prediction-card ${forecastTrendClass}`}>
                <span>3-month average</span>
                <strong>{moneyFormatter.format(forecast.feature_summary.three_month_average)}</strong>
                <small>Previous month: {moneyFormatter.format(forecast.feature_summary.previous_month_spending)}</small>
              </article>
            </section>

            <section className="forecast-panel">
              <div className="section-heading">
                <h2>Forecast Line Chart</h2>
                <p>Actual monthly expenses with next month prediction.</p>
              </div>
              <div className="forecast-chart-frame">
                <ResponsiveContainer width="100%" height={320}>
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="month" tick={{ fontSize: 12 }} />
                    <YAxis tick={{ fontSize: 12 }} />
                    <Tooltip formatter={currencyTooltip} />
                    <Legend />
                    <Line type="monotone" dataKey="actual" stroke="#0073ea" strokeWidth={3} dot={{ r: 3 }} connectNulls />
                    <Line type="monotone" dataKey="forecast" stroke="#d92d20" strokeWidth={3} dot={{ r: 4 }} connectNulls />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </section>

            <section className="forecast-layout">
              <div className="forecast-panel">
                <div className="section-heading">
                  <h2>Category Forecasts</h2>
                  <p>Predicted next-month spending for top categories.</p>
                </div>
                <div className="category-forecast-list">
                  {forecast.category_forecasts.length === 0 ? (
                    <div className="empty-state">Add categorized expenses to see category forecasts.</div>
                  ) : forecast.category_forecasts.map((item) => (
                    <div className="category-forecast-row" key={`${item.category_id}-${item.category_name}`}>
                      <span>{item.category_name}</span>
                      <strong>{moneyFormatter.format(item.predicted_amount)}</strong>
                    </div>
                  ))}
                </div>
              </div>

              <div className="forecast-panel">
                <div className="section-heading">
                  <h2>Feature Summary</h2>
                  <p>Signals used for the prediction.</p>
                </div>
                <div className="forecast-feature-grid">
                  <div><span>Months used</span><strong>{forecast.feature_summary.months_used}</strong></div>
                  <div><span>Average income</span><strong>{moneyFormatter.format(forecast.feature_summary.average_income)}</strong></div>
                  <div><span>Transaction count</span><strong>{forecast.feature_summary.average_transaction_count}</strong></div>
                  <div><span>Previous spending</span><strong>{moneyFormatter.format(forecast.feature_summary.previous_month_spending)}</strong></div>
                </div>
              </div>
            </section>
          </>
        )}
      </main>
    </div>
  );
};

export default Forecast;
