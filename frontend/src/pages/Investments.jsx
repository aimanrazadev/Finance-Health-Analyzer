import { useEffect, useMemo, useState } from 'react';
import Navigation from '../components/Navigation';
import { useAuth } from '../hooks/useAuth';
import api, { getAuthHeaders } from '../utils/api';
import '../styles/Investments.css';

const initialHoldingForm = {
  asset_name: '',
  symbol: '',
  exchange: 'NSE',
  quantity: '',
  average_buy_price: '',
  current_price: '',
};

const moneyFormatter = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  maximumFractionDigits: 0,
});

const Investments = () => {
  const { token } = useAuth();
  const [summary, setSummary] = useState(null);
  const [holdingForm, setHoldingForm] = useState(initialHoldingForm);
  const [editingHoldingId, setEditingHoldingId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [refreshingId, setRefreshingId] = useState(null);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  const headers = getAuthHeaders(token);

  const loadPageData = async () => {
    setLoading(true);
    setError('');
    try {
      const [goalsResponse, summaryResponse] = await Promise.all([
        api.get('/savings-goals', { headers }),
        api.get('/investments/summary', { headers }),
      ]);
      void goalsResponse;
      setSummary(summaryResponse.data);
    } catch (err) {
      console.error(err);
      setError('Unable to load investments and savings data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (token) {
      queueMicrotask(() => {
        loadPageData();
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const holdings = useMemo(() => summary?.holdings || [], [summary?.holdings]);
  const topMover = useMemo(() => (
    holdings.length
      ? [...holdings].sort((a, b) => Math.abs(b.pnl_amount) - Math.abs(a.pnl_amount))[0]
      : null
  ), [holdings]);

  const resetHoldingForm = () => {
    setEditingHoldingId(null);
    setHoldingForm(initialHoldingForm);
  };

  const handleHoldingChange = (event) => {
    const { name, value } = event.target;
    setHoldingForm((current) => ({ ...current, [name]: value }));
  };

  const saveHolding = async (event) => {
    event.preventDefault();
    setSaving(true);
    setError('');
    setMessage('');

    const payload = {
      asset_name: holdingForm.asset_name.trim(),
      symbol: holdingForm.symbol.trim(),
      exchange: holdingForm.exchange,
      quantity: Number(holdingForm.quantity),
      average_buy_price: Number(holdingForm.average_buy_price),
      current_price: holdingForm.current_price ? Number(holdingForm.current_price) : null,
    };

    try {
      if (editingHoldingId) {
        await api.put(`/investments/holdings/${editingHoldingId}`, payload, { headers });
        setMessage('Investment holding updated.');
      } else {
        await api.post('/investments/holdings', payload, { headers });
        setMessage('Investment holding added.');
      }
      resetHoldingForm();
      await loadPageData();
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || 'Unable to save investment holding.');
    } finally {
      setSaving(false);
    }
  };

  const editHolding = (holding) => {
    setEditingHoldingId(holding.id);
    setHoldingForm({
      asset_name: holding.asset_name,
      symbol: holding.symbol,
      exchange: holding.exchange,
      quantity: holding.quantity,
      average_buy_price: holding.average_buy_price,
      current_price: holding.current_price || '',
    });
  };

  const deleteHolding = async (holdingId) => {
    if (!window.confirm('Delete this investment holding?')) return;
    try {
      await api.delete(`/investments/holdings/${holdingId}`, { headers });
      setMessage('Investment holding deleted.');
      await loadPageData();
    } catch (err) {
      console.error(err);
      setError('Unable to delete investment holding.');
    }
  };

  const refreshPrice = async (holdingId) => {
    setRefreshingId(holdingId);
    setError('');
    setMessage('');
    try {
      await api.post(`/investments/holdings/${holdingId}/refresh-price`, {}, { headers });
      setMessage('Public market price refreshed.');
      await loadPageData();
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || 'Public price is unavailable. Enter current price manually.');
    } finally {
      setRefreshingId(null);
    }
  };

  return (
    <div>
      <Navigation />
      <main className="investments-page">
        <div className="page-heading investment-heading">
          <div>
            <p className="eyebrow">Manual portfolio tracking</p>
            <h1>Investments</h1>
            <p>Track savings, current balance, and investments without connecting bank or brokerage accounts.</p>
          </div>
        </div>

        <section className="investment-explainer">
          <div className="investment-explainer-icon">I</div>
          <div>
            <strong>Safe mode: no bank login, no broker login, no trading access.</strong>
            <p>Enter your current balance and holdings manually. Public market quotes are used only to estimate portfolio value and profit/loss.</p>
          </div>
        </section>

        {message && <div className="surface-message success">{message}</div>}
        {error && <div className="surface-message error">{error}</div>}

        <section className="investment-summary-grid">
          <article>
            <span>Current balance</span>
            <strong>{moneyFormatter.format(summary?.account_balance?.balance_amount || 0)}</strong>
          </article>
          <article>
            <span>Portfolio value</span>
            <strong>{moneyFormatter.format(summary?.current_portfolio_value || 0)}</strong>
          </article>
          <article>
            <span>Total P/L</span>
            <strong className={(summary?.total_pnl_amount || 0) >= 0 ? 'positive-value' : 'negative-value'}>
              {moneyFormatter.format(summary?.total_pnl_amount || 0)}
            </strong>
          </article>
          <article>
            <span>Net worth estimate</span>
            <strong>{moneyFormatter.format(summary?.net_worth || 0)}</strong>
          </article>
        </section>

        <section className="investment-summary-grid investment-secondary-grid">
          <article>
            <span>Manual invested</span>
            <strong>{moneyFormatter.format(summary?.manual_invested_amount || 0)}</strong>
          </article>
          <article>
            <span>PDF-detected investments</span>
            <strong>{moneyFormatter.format(summary?.auto_detected_invested_amount || 0)}</strong>
          </article>
          <article>
            <span>Savings goals saved</span>
            <strong>{moneyFormatter.format(summary?.savings_current_total || 0)}</strong>
          </article>
          <article>
            <span>Top movement</span>
            <strong>{topMover ? topMover.symbol : 'None'}</strong>
          </article>
        </section>

        <div className="investment-layout investment-insights-layout">
          <section className="investment-list-panel">
            <div className="section-heading">
              <h2>Portfolio Insights</h2>
              <p>Past vs present is calculated from invested amount, current value, and uploaded transactions marked as Investments.</p>
            </div>
            <div className="insight-list">
              {(summary?.insights || []).map((insight) => (
                <article className={`investment-insight ${insight.severity}`} key={insight.title}>
                  <strong>{insight.title}</strong>
                  <p>{insight.message}</p>
                </article>
              ))}
            </div>
          </section>
        </div>

        <div className="investment-layout">
          <section className="investment-form-panel">
            <h2>{editingHoldingId ? 'Edit Investment' : 'Add Investment'}</h2>
            <form className="investment-form" onSubmit={saveHolding}>
              <label>
                Stock / fund name
                <input name="asset_name" value={holdingForm.asset_name} onChange={handleHoldingChange} placeholder="Reliance Industries" required />
              </label>
              <label>
                Symbol
                <input name="symbol" value={holdingForm.symbol} onChange={handleHoldingChange} placeholder="RELIANCE" required />
              </label>
              <label>
                Exchange
                <select name="exchange" value={holdingForm.exchange} onChange={handleHoldingChange}>
                  <option value="NSE">NSE</option>
                  <option value="BSE">BSE</option>
                </select>
              </label>
              <label>
                Quantity
                <input name="quantity" type="number" min="0.0001" step="0.0001" value={holdingForm.quantity} onChange={handleHoldingChange} required />
              </label>
              <label>
                Average buy price
                <input name="average_buy_price" type="number" min="0.01" step="0.01" value={holdingForm.average_buy_price} onChange={handleHoldingChange} required />
              </label>
              <label>
                Current price optional
                <input name="current_price" type="number" min="0.01" step="0.01" value={holdingForm.current_price} onChange={handleHoldingChange} placeholder="Leave blank to fetch public quote" />
              </label>
              <div className="investment-form-actions">
                <button className="primary-button" type="submit" disabled={saving}>
                  {saving ? 'Saving...' : editingHoldingId ? 'Update Investment' : 'Add Investment'}
                </button>
                {editingHoldingId && (
                  <button className="secondary-button" type="button" onClick={resetHoldingForm}>
                    Cancel
                  </button>
                )}
              </div>
            </form>
          </section>

          <section className="investment-list-panel">
            <div className="section-heading">
              <h2>Investment Holdings</h2>
              <p>Manual holdings are valued using public market quotes or your entered current price.</p>
            </div>
            {loading ? (
              <div className="empty-state">Loading holdings...</div>
            ) : holdings.length === 0 ? (
              <div className="empty-state investment-empty-state">
                <strong>No investments added yet.</strong>
                <span>Example: add RELIANCE, quantity 2, average buy price INR 2,800.</span>
              </div>
            ) : (
              <div className="holdings-table-wrap">
                <table className="holdings-table">
                  <thead>
                    <tr>
                      <th>Investment</th>
                      <th>Qty</th>
                      <th>Invested</th>
                      <th>Current Value</th>
                      <th>P/L</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {holdings.map((holding) => (
                      <tr key={holding.id}>
                        <td>
                          <strong>{holding.asset_name}</strong>
                          <span>{holding.symbol} · {holding.exchange} · LTP {holding.current_price ? moneyFormatter.format(holding.current_price) : 'Manual needed'}</span>
                        </td>
                        <td>{holding.quantity}</td>
                        <td>{moneyFormatter.format(holding.invested_amount)}</td>
                        <td>{moneyFormatter.format(holding.current_value)}</td>
                        <td className={holding.pnl_amount >= 0 ? 'positive-value' : 'negative-value'}>
                          {moneyFormatter.format(holding.pnl_amount)} ({holding.pnl_percent}%)
                        </td>
                        <td>
                          <div className="holding-actions">
                            <button className="table-button" onClick={() => refreshPrice(holding.id)} disabled={refreshingId === holding.id}>
                              {refreshingId === holding.id ? 'Refreshing...' : 'Refresh'}
                            </button>
                            <button className="table-button" onClick={() => editHolding(holding)}>Edit</button>
                            <button className="table-button danger" onClick={() => deleteHolding(holding.id)}>Delete</button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </div>

      </main>
    </div>
  );
};

export default Investments;
