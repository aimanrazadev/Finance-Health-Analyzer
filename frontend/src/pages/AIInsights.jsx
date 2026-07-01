import { useCallback, useEffect, useMemo, useState } from 'react';
import { PolarAngleAxis, RadialBar, RadialBarChart, ResponsiveContainer } from 'recharts';
import {
  Activity, ArrowRight, CalendarDays, CreditCard, Lightbulb,
  PiggyBank, ReceiptText, RefreshCw, ShieldCheck, ShoppingBag, Sparkles,
  Store, Target, TrendingUp,
} from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import Navigation from '../components/Navigation';
import AppSelect from '../components/AppSelect';
import api, { getAuthHeaders } from '../utils/api';
import './AIInsights.css';

const monthNames = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
const monthOptions = monthNames.map((label, index) => ({ value: index + 1, label }));
const currentDate = new Date();
const money = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', minimumFractionDigits: 2, maximumFractionDigits: 2 });
const formatMoney = (value) => money.format(Number(value || 0));

const insightGroups = [
  { key: 'spending_insights', label: 'Spending', eyebrow: 'Where your money went', Icon: ShoppingBag, tone: 'blue' },
  { key: 'savings_insights', label: 'Savings', eyebrow: 'What you kept aside', Icon: PiggyBank, tone: 'green' },
  { key: 'merchant_insights', label: 'Merchants', eyebrow: 'Who you paid most', Icon: Store, tone: 'amber' },
  { key: 'subscription_insights', label: 'Subscriptions', eyebrow: 'Your recurring costs', Icon: CreditCard, tone: 'purple' },
  { key: 'health_insights', label: 'Financial health', eyebrow: 'What shaped your score', Icon: ShieldCheck, tone: 'teal' },
];
const actionIcons = [PiggyBank, CreditCard, ReceiptText, TrendingUp];

function InsightCard({ group, items }) {
  const { Icon } = group;
  return <article className={`insight-feed-card tone-${group.tone}`}>
    <header><span className="insight-icon"><Icon /></span><div><small>{group.eyebrow}</small><h3>{group.label}</h3></div></header>
    {items.length ? <ul>{items.slice(0, 4).map((item, index) => <li key={`${group.key}-${index}`}>{item}</li>)}</ul> : <p className="insight-empty">No {group.label.toLowerCase()} insight was found for this period.</p>}
  </article>;
}

export default function AIInsights() {
  const { token } = useAuth();
  const [month, setMonth] = useState(currentDate.getMonth() + 1);
  const [year, setYear] = useState(currentDate.getFullYear());
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const yearOptions = useMemo(() => Array.from({ length: 8 }, (_, index) => currentDate.getFullYear() - 5 + index).map(value => ({ value, label: String(value) })), []);

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError('');
    try {
      const response = await api.get('/ai/insights', { headers: getAuthHeaders(token), params: { month, year } });
      setData(response.data);
    } catch (requestError) {
      console.error(requestError);
      setError('We could not prepare insights for this period.');
    } finally {
      setLoading(false);
    }
  }, [token, month, year]);

  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { load(); }, [load]);

  const context = data?.context;
  const metrics = context?.core_metrics;
  const components = context?.health_score?.components;
  const score = Number(data?.health_score || 0);
  const scoreChart = [{ value: score, fill: '#9bf000' }];
  const recommendations = data?.recommendations || [];

  return <><Navigation /><main className="insights-page-v3">
    <header className="insights-header">
      <div className="insights-title"><span><Sparkles /> AI Insights Engine</span><h1>Your money, explained clearly.</h1></div>
      <div className="insights-controls" aria-label="AI Insights period filters">
        <label><span>Month</span><AppSelect ariaLabel="Select AI Insights month" value={month} onChange={value => setMonth(Number(value))} options={monthOptions} /></label>
        <label><span>Year</span><AppSelect ariaLabel="Select AI Insights year" value={year} onChange={value => setYear(Number(value))} options={yearOptions} /></label>
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
          <h2>Your financial health for {monthNames[month - 1]} {year} is {data.status}.</h2>
          <div className="priority-card"><span><Target /></span><div><small>Top priority</small><strong>{data.top_priority}</strong></div><ArrowRight /></div>
        </div>
      </section>

      <section className="insights-section insight-feed-section">
        <div className="section-heading"><div><h2>Your insight feed</h2></div><p>Five focused views of the selected period.</p></div>
        <div className="insight-feed-grid">{insightGroups.map(group => <InsightCard key={group.key} group={group} items={data[group.key] || []} />)}</div>
      </section>

      <section className="insights-section action-section">
        <div className="section-heading"><div><h2>Recommended priorities</h2></div><p>Ranked by what can help most right now.</p></div>
        {recommendations.length ? <div className="recommendation-grid">{recommendations.slice(0, 4).map((item, index) => { const Icon = actionIcons[index] || Target; return <article key={`${item.priority}-${item.title}`}><header><span className="rank">0{index + 1}</span><span className="action-icon"><Icon /></span><span className="focus">{item.focus}</span></header><h3>{item.title}</h3><p>{item.reason}</p><footer><span>{item.action}</span><ArrowRight /></footer></article>; })}</div> : <div className="recommendation-empty"><Lightbulb /><span>No action is needed for this period.</span></div>}
      </section>

      <section className="insights-bottom-grid">
        <article className="period-snapshot"><header><div><span>Monthly overview</span><h2>{context?.period_label}</h2></div><CalendarDays /></header><dl><div><dt>Available funds</dt><dd>{formatMoney(metrics?.available_funds)}</dd></div><div><dt>Saved or invested</dt><dd>{formatMoney(metrics?.total_savings)}</dd></div><div><dt>Recurring costs</dt><dd>{formatMoney(context?.subscriptions?.monthly_total)}</dd></div><div><dt>Transactions</dt><dd>{context?.transaction_count || 0}</dd></div></dl></article>
      </section>

    </div>}
  </main></>;
}
