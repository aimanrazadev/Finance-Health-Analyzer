import { useCallback, useEffect, useMemo, useState } from 'react';
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import Navigation from '../components/Navigation';
import { useAuth } from '../hooks/useAuth';
import api, { getAuthHeaders } from '../utils/api';
import '../styles/Subscriptions.css';

const moneyFormatter = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  maximumFractionDigits: 2,
});

const Subscriptions = () => {
  const { token } = useAuth();
  const headers = useMemo(() => getAuthHeaders(token), [token]);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadSubscriptions = useCallback(async (refresh = false) => {
    setLoading(true);
    setError('');
    try {
      const response = refresh
        ? await api.post('/subscriptions/refresh', {}, { headers })
        : await api.get('/subscriptions', { headers });
      setData(response.data);
    } catch (err) {
      console.error(err);
      setError('Unable to load recurring payments.');
    } finally {
      setLoading(false);
    }
  }, [headers]);

  useEffect(() => {
    if (token) {
      queueMicrotask(() => loadSubscriptions());
    }
  }, [loadSubscriptions, token]);

  const subscriptions = data?.active_subscriptions || [];
  const chartData = data?.chart_data || [];

  return (
    <div>
      <Navigation />
      <main className="subscriptions-page">
        <div className="page-heading">
          <div>
            <p className="eyebrow">Recurring payments</p>
            <h1>Subscriptions</h1>
            <p>Detect repeated merchants, monthly charges, and subscription services from your transaction history.</p>
          </div>
          <button className="primary-button" onClick={() => loadSubscriptions(true)} disabled={loading}>
            Refresh Detection
          </button>
        </div>

        {error && <div className="surface-message error">{error}</div>}

        <section className="subscription-summary">
          <div>
            <span>Active subscriptions</span>
            <strong>{data?.subscription_count || 0}</strong>
          </div>
          <div>
            <span>Monthly total</span>
            <strong>{moneyFormatter.format(data?.monthly_total || 0)}</strong>
          </div>
          <div>
            <span>Transactions marked recurring</span>
            <strong>{data?.marked_transaction_ids?.length || 0}</strong>
          </div>
        </section>

        <section className="subscription-chart-panel">
          <h2>Monthly Subscription Spend</h2>
          {chartData.length === 0 ? (
            <div className="empty-state">No recurring subscription pattern detected yet.</div>
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="name" tickLine={false} axisLine={false} />
                <YAxis tickLine={false} axisLine={false} tickFormatter={(value) => `₹${value}`} />
                <Tooltip formatter={(value) => moneyFormatter.format(value)} />
                <Bar dataKey="value" fill="#0073ea" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </section>

        <section className="subscription-list">
          <h2>Active Subscriptions</h2>
          {loading ? (
            <div className="empty-state">Detecting recurring payments...</div>
          ) : subscriptions.length === 0 ? (
            <div className="empty-state">No active subscriptions found from your current transactions.</div>
          ) : subscriptions.map((subscription) => (
            <article className="subscription-card" key={`${subscription.merchant_name}-${subscription.monthly_amount}`}>
              <div className="subscription-card-main">
                <div>
                  <h3>{subscription.merchant_name}</h3>
                  <p>
                    {subscription.transaction_count} repeated transaction{subscription.transaction_count === 1 ? '' : 's'}
                    {' '}from {new Date(subscription.first_seen).toLocaleDateString()} to {new Date(subscription.last_seen).toLocaleDateString()}
                  </p>
                </div>
                <div className="subscription-amount">
                  <strong>{moneyFormatter.format(subscription.monthly_amount)}</strong>
                  <span>per month</span>
                </div>
              </div>

              <div className="subscription-meta">
                <span>{Math.round(subscription.confidence * 100)}% confidence</span>
                <span>Next expected {new Date(subscription.next_expected_date).toLocaleDateString()}</span>
                {subscription.review_suggestion && <b>{subscription.review_suggestion}</b>}
              </div>

              <div className="subscription-transactions">
                {subscription.transactions.map((transaction) => (
                  <div key={transaction.id}>
                    <span>{new Date(transaction.date).toLocaleDateString()}</span>
                    <span>{transaction.description}</span>
                    <strong>{moneyFormatter.format(transaction.amount)}</strong>
                  </div>
                ))}
              </div>
            </article>
          ))}
        </section>
      </main>
    </div>
  );
};

export default Subscriptions;
