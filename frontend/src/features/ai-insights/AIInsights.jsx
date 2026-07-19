import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { PolarAngleAxis, RadialBar, RadialBarChart, ResponsiveContainer } from 'recharts';
import {
  Activity, CreditCard,
  RefreshCw, ShieldCheck, ShoppingBag, Sparkles, Store,
} from 'lucide-react';
import { useAuth } from '../auth/authContext';
import Navigation from '../../components/layout/Navigation';
import AppSelect from '../../components/ui/AppSelect';
import api, { getAuthHeaders } from '../../shared/services/apiClient';
import { getPeriodSelection, savePeriodSelection } from '../../utils/periodSession';
import './AIInsights.css';

const monthNames = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
const monthOptions = monthNames.map((label, index) => ({ value: index + 1, label }));
const currentDate = new Date();
const insightGroups = [
  { key: 'spending_insights', label: 'Spending', Icon: ShoppingBag, tone: 'blue' },
  { key: 'merchant_insights', label: 'Merchants', Icon: Store, tone: 'amber' },
  { key: 'subscription_insights', label: 'Subscriptions', Icon: CreditCard, tone: 'purple' },
  { key: 'health_insights', label: 'Financial health', Icon: ShieldCheck, tone: 'teal' },
];
function InsightCard({ group, items }) {
  const { Icon } = group;
  return <article className={`insight-feed-card tone-${group.tone}`}>
    <header><span className="insight-icon"><Icon /></span><h3>{group.label}</h3></header>
    {items.length ? <ul>{items.slice(0, 4).map((item, index) => <li key={`${group.key}-${index}`}>{item}</li>)}</ul> : <p className="insight-empty">No {group.label.toLowerCase()} insight was found for this period.</p>}
  </article>;
}

export default function AIInsights() {
  const { token } = useAuth();
  const initialPeriod = getPeriodSelection();
  const [month, setMonth] = useState(initialPeriod.month);
  const [year, setYear] = useState(initialPeriod.year);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const activeRequest = useRef({ id: 0, controller: null });
  const yearOptions = useMemo(() => Array.from({ length: 8 }, (_, index) => currentDate.getFullYear() - 5 + index).map(value => ({ value, label: String(value) })), []);

  const load = useCallback(async () => {
    if (!token) return;
    activeRequest.current.controller?.abort();
    const controller = new AbortController();
    const requestId = activeRequest.current.id + 1;
    activeRequest.current = { id: requestId, controller };
    setLoading(true);
    setError('');
    try {
      const response = await api.get('/ai/insights', {
        headers: { ...getAuthHeaders(token), 'Cache-Control': 'no-cache' },
        params: { month, year },
        signal: controller.signal,
      });
      if (activeRequest.current.id !== requestId) return;
      const responseData = response.data;
      if (Number(responseData?.month) !== month || Number(responseData?.year) !== year) {
        throw new Error(`Insights period mismatch: requested ${month}/${year}, received ${responseData?.month}/${responseData?.year}`);
      }
      setData(responseData);
    } catch (requestError) {
      if (controller.signal.aborted || requestError?.code === 'ERR_CANCELED') return;
      console.error(requestError);
      if (activeRequest.current.id === requestId) {
        setData(null);
        setError('We could not verify insights for the selected period. Please refresh.');
      }
    } finally {
      if (activeRequest.current.id === requestId) setLoading(false);
    }
  }, [token, month, year]);

  useEffect(() => {
    // Loading is the external synchronization performed by this effect.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
    return () => activeRequest.current.controller?.abort();
  }, [load]);

  const context = data?.context;
  const components = context?.health_score?.components;
  const score = Number(data?.health_score || 0);
  const scoreChart = [{ value: score, fill: '#9bf000' }];

  return <><Navigation /><main className="insights-page-v3">
    <header className="insights-header">
      <div className="insights-title"><span><Sparkles /> AI Insights Engine</span><h1>Your money, explained clearly.</h1></div>
      <div className="insights-controls" aria-label="AI Insights period filters">
        <label><span>Month</span><AppSelect ariaLabel="Select AI Insights month" value={month} onChange={value => { const nextMonth = Number(value); setMonth(nextMonth); savePeriodSelection(nextMonth, year); }} options={monthOptions} /></label>
        <label><span>Year</span><AppSelect ariaLabel="Select AI Insights year" value={year} onChange={value => { const nextYear = Number(value); setYear(nextYear); savePeriodSelection(month, nextYear); }} options={yearOptions} /></label>
        <button type="button" onClick={load} disabled={loading}><RefreshCw className={loading ? 'spin' : ''} /> Refresh</button>
      </div>
    </header>

    {loading ? <div className="insights-loading" aria-label="Preparing AI insights"><span /><span /><span /></div> : error ? <section className="insights-state is-error"><Activity /><h2>Insights are unavailable</h2><p>{error}</p><button type="button" onClick={load}>Try again</button></section> : !data ? <section className="insights-state"><Sparkles /><h2>No insights yet</h2><p>Upload a statement to start your financial analysis.</p></section> : <div className="insights-layout">
      <section className="insights-hero">
        <div className="score-column" tabIndex="0" aria-label="Financial health score. Hover or focus to view score details.">
          <small>Financial health</small>
          <div className="score-ring"><ResponsiveContainer width="100%" height="100%"><RadialBarChart innerRadius="78%" outerRadius="100%" data={scoreChart} startAngle={90} endAngle={-270}><PolarAngleAxis type="number" domain={[0, 100]} tick={false} /><RadialBar dataKey="value" background={{ fill: 'rgba(255,255,255,.10)' }} cornerRadius={10} /></RadialBarChart></ResponsiveContainer><div><strong>{score}</strong><span>/100</span></div></div>
          <em>{data.status}</em>
          <div className="score-hover-detail" aria-hidden="true">
            <header><span>Score detail</span><strong>What shaped your score</strong></header>
            {[['Savings', components?.savings_score], ['Subscriptions', components?.subscription_score], ['Stability', components?.spending_stability_score], ['Balance', components?.financial_balance_score]].map(([label, value]) => <div className="score-hover-row" key={label}><span><small>{label}</small><strong>{value ?? 0}/100</strong></span><div><i style={{ width: `${Math.max(0, Math.min(100, value || 0))}%` }} /></div></div>)}
          </div>
        </div>
        <div className="summary-column">
          <small>AI summary · {monthNames[month - 1]} {year}</small>
          <h2>{data.summary}</h2>
        </div>
      </section>

      <section className="insights-section insight-feed-section">
        <div className="section-heading"><div><h2>Your insight feed</h2></div><p>Five focused views of the selected period.</p></div>
        <div className="insight-feed-grid">{insightGroups.map(group => <InsightCard key={group.key} group={group} items={data[group.key] || []} />)}</div>
      </section>

    </div>}
  </main></>;
}
