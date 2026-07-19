import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Area,
  AreaChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import Navigation from '../../components/layout/Navigation';
import AppSelect from '../../components/ui/AppSelect';
import useAuth from '../auth/useAuth';
import api, { getAuthHeaders } from '../../shared/services/apiClient';
import { getCategoryChartColor } from '../../utils/categoryDisplay';
import { getPeriodSelection, savePeriodSelection } from '../../utils/periodSession';
import './Dashboard.css';

const now = new Date();

const emptySummary = {
  month: now.getMonth() + 1,
  year: now.getFullYear(),
  total_income: 0,
  total_expenses: 0,
  lifestyle_expenses: 0,
  total_savings: 0,
  savings_rate: null,
  savings_status: 'Poor',
  transaction_count: 0,
  top_category: null,
  top_merchant: null,
  recurring_subscription_count: 0,
  current_balance: 0,
  closing_balance: 0,
  opening_balance: 0,
  available_funds: 0,
  expected_closing_balance: 0,
  pdf_closing_balance: null,
  balance_mismatch: false,
  calculated_closing_balance: 0,
  balance_difference: 0,
};

const emptyCharts = { category_breakdown: [], top_merchants: [] };
const emptyTrendSummary = {
  trends: [],
  income_change_percentage: null,
  expense_change_percentage: null,
  savings_change_percentage: null,
  current_balance_change_percentage: null,
  savings_rate_change_points: null,
};
const emptyMerchants = { top_merchants: [], most_frequent_merchants: [], highest_spending_merchants: [] };
const emptySubscriptions = { subscription_count: 0, total_monthly_cost: 0, total_annual_cost: 0, subscriptions: [] };
const emptyHealth = { overall_score: 0, status_label: 'Needs Improvement', breakdown: [], improvement_tips: [] };

const asObject = (value) => (
  value && typeof value === 'object' && !Array.isArray(value) ? value : {}
);
const asArray = (value) => (Array.isArray(value) ? value : []);
const asRecordArray = (value) => asArray(value).filter(
  (item) => item && typeof item === 'object' && !Array.isArray(item),
);
const asNumber = (value) => {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : 0;
};

const monthOptions = [
  { value: 0, label: 'All' },
  { value: 1, label: 'January' },
  { value: 2, label: 'February' },
  { value: 3, label: 'March' },
  { value: 4, label: 'April' },
  { value: 5, label: 'May' },
  { value: 6, label: 'June' },
  { value: 7, label: 'July' },
  { value: 8, label: 'August' },
  { value: 9, label: 'September' },
  { value: 10, label: 'October' },
  { value: 11, label: 'November' },
  { value: 12, label: 'December' },
];

const currentYear = now.getFullYear();
const yearOptions = Array.from({ length: currentYear - 1999 + 2 }, (_, index) => currentYear + 1 - index);
const ALL_YEARS = 'all';

const moneyFormatter = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const compactMoneyFormatter = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  notation: 'compact',
  maximumFractionDigits: 1,
});

const percentFormatter = new Intl.NumberFormat('en-IN', {
  maximumFractionDigits: 1,
});

const formatMoney = (value) => moneyFormatter.format(Number(value || 0));
const formatCompactMoney = (value) => compactMoneyFormatter.format(Number(value || 0));

const formatDelta = (value, previousLabel, fallback = 'This period') => {
  if (value === null || value === undefined) return fallback;
  const numeric = Number(value || 0);
  return `${numeric >= 0 ? '+' : '-'}${Math.abs(numeric).toFixed(1)}% vs ${previousLabel}`;
};

const getMonthLabel = (month) => (
  Number(month) === 0 ? 'All' : monthOptions.find((item) => item.value === Number(month))?.label || 'This month'
);

const MetricIcon = ({ name }) => {
  const common = {
    viewBox: '0 0 24 24',
    fill: 'none',
    stroke: 'currentColor',
    strokeWidth: 1.8,
    strokeLinecap: 'round',
    strokeLinejoin: 'round',
    'aria-hidden': 'true',
  };

  const icons = {
    income: <svg {...common}><path d="M4 17 10 11l4 4 6-8" /><path d="M14 7h6v6" /></svg>,
    expenses: <svg {...common}><path d="M4 7 10 13l4-4 6 8" /><path d="M14 17h6v-6" /></svg>,
    savings: <svg {...common}><path d="M12 21s7-4.4 7-11V5l-7-3-7 3v5c0 6.6 7 11 7 11Z" /><path d="M9 12h6" /></svg>,
    balance: <svg {...common}><path d="M19 7V6a2 2 0 0 0-2-2H5a3 3 0 0 0 0 6h14a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2H5a3 3 0 0 1-3-3V7" /><path d="M16 14h.01" /></svg>,
    category: <svg {...common}><path d="M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM14 14h6v6h-6z" /></svg>,
  };

  return icons[name] || icons.balance;
};

const DashboardMetric = ({ icon, label, numericValue, helper, delta, deltaLabel, deltaDirection = 'higher-is-better', deltaUnit = 'percent', tone, loading, format = 'currency' }) => (
  <article className={`dashboard-card metric-card metric-format-${format} dashboard-card-selected tone-${tone}`}>
    <div className="metric-card-top">
      <span className="metric-icon"><MetricIcon name={icon} /></span>
      <span className="metric-label">{label}</span>
    </div>
    <strong className="metric-value">
      {loading ? (
        'Loading...'
      ) : numericValue === null || numericValue === undefined ? (
        format === 'percent' ? 'N/A' : '-'
      ) : format === 'text' ? (
        numericValue
      ) : format === 'percent' ? (
        `${percentFormatter.format(Number(numericValue))}%`
      ) : (
        formatMoney(numericValue)
      )}
    </strong>
    {delta !== null && delta !== undefined ? (
      <small className={`metric-delta ${(
        deltaDirection === 'lower-is-better' ? Number(delta) <= 0 : Number(delta) >= 0
      ) ? 'is-favorable' : 'is-unfavorable'}`}>
        <span className="metric-delta-value" aria-hidden="true">
          {Number(delta) >= 0 ? '↑' : '↓'} {Math.abs(Number(delta)).toFixed(1)}{deltaUnit === 'points' ? ' pp' : '%'}
        </span>
        <span className="metric-delta-context">vs {deltaLabel}</span>
      </small>
    ) : helper ? <small>{helper}</small> : null}
  </article>
);

const DashboardTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;

  return (
    <div className="dashboard-tooltip">
      <strong>{label}</strong>
      {payload.map((item) => (
        <span key={item.dataKey} style={{ '--tooltip-color': item.color }}>
          {item.name}: {formatMoney(item.value)}
        </span>
      ))}
    </div>
  );
};

const DonutTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null;
  const item = payload[0];

  return (
    <div className="dashboard-tooltip">
      <strong>{item.name}</strong>
      <span style={{ '--tooltip-color': item.payload?.fill || item.color }}>
        {formatMoney(item.value)}
      </span>
    </div>
  );
};

const Dashboard = () => {
  const { token, user } = useAuth();
  const [summary, setSummary] = useState(emptySummary);
  const [charts, setCharts] = useState(emptyCharts);
  const [trendSummary, setTrendSummary] = useState(emptyTrendSummary);
  const [merchantAnalytics, setMerchantAnalytics] = useState(emptyMerchants);
  const [subscriptionAnalytics, setSubscriptionAnalytics] = useState(emptySubscriptions);
  const [health, setHealth] = useState(emptyHealth);
  const [recentTransactions, setRecentTransactions] = useState([]);
  const initialPeriod = getPeriodSelection();
  const [selectedMonth, setSelectedMonth] = useState(initialPeriod.month);
  const [selectedYear, setSelectedYear] = useState(initialPeriod.year);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;

    const loadDashboard = async () => {
      setLoading(true);
      setError('');
      const headers = getAuthHeaders(token);
      const isAllTime = selectedYear === ALL_YEARS;
      const numericYear = isAllTime ? now.getFullYear() : Number(selectedYear);
      const params = isAllTime ? { month: -1 } : { month: selectedMonth, year: numericYear };
      try {
        const response = await api.get('/dashboard', { headers, params });

        if (cancelled) return;
        const data = asObject(response.data);
        const summaryData = asObject(data.summary);
        const chartsData = asObject(data.charts);
        const trendData = asObject(data.trends);
        const merchantData = asObject(data.merchants);
        const subscriptionData = asObject(data.subscriptions);
        const healthData = asObject(data.health);

        setSummary({ ...emptySummary, ...summaryData });
        setCharts({
          ...emptyCharts,
          ...chartsData,
          category_breakdown: asRecordArray(chartsData.category_breakdown),
          monthly_trends: asRecordArray(chartsData.monthly_trends),
          top_merchants: asRecordArray(chartsData.top_merchants),
        });
        setTrendSummary({
          ...emptyTrendSummary,
          ...trendData,
          trends: asRecordArray(trendData.trends),
        });
        setMerchantAnalytics({
          ...emptyMerchants,
          ...merchantData,
          top_merchants: asRecordArray(merchantData.top_merchants),
          most_frequent_merchants: asRecordArray(merchantData.most_frequent_merchants),
          highest_spending_merchants: asRecordArray(merchantData.highest_spending_merchants),
        });
        setSubscriptionAnalytics({
          ...emptySubscriptions,
          ...subscriptionData,
          subscriptions: asRecordArray(subscriptionData.subscriptions),
        });
        setHealth({
          ...emptyHealth,
          ...healthData,
          breakdown: asRecordArray(healthData.breakdown),
          improvement_tips: asArray(healthData.improvement_tips),
        });
        setRecentTransactions(asRecordArray(data.recent_transactions));
      } catch (err) {
        console.error(err);
        if (!cancelled) {
          setSummary(emptySummary);
          setCharts(emptyCharts);
          setTrendSummary(emptyTrendSummary);
          setHealth(emptyHealth);
          setRecentTransactions([]);
          setError('Unable to load dashboard data.');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    if (token) loadDashboard();

    return () => {
      cancelled = true;
    };
  }, [token, selectedMonth, selectedYear]);

  const categoryBreakdown = asRecordArray(charts.category_breakdown).map((item) => ({
    ...item,
    name: String(item.name || ''),
    value: asNumber(item.value),
  }));
  const normalizeTrendData = (value) => asRecordArray(value).map((item) => ({
    ...item,
    month: String(item.month || ''),
    income: asNumber(item.income),
    expenses: asNumber(item.expenses),
  }));
  const monthlyTrends = normalizeTrendData(charts.monthly_trends);
  const fallbackTrends = normalizeTrendData(trendSummary.trends);
  const trendData = monthlyTrends.length ? monthlyTrends : fallbackTrends;
  const totalCategorySpend = categoryBreakdown.reduce((sum, item) => sum + Number(item.value || 0), 0);
  const hasCategoryData = categoryBreakdown.length > 0 && totalCategorySpend > 0;
  const hasTrendData = trendData.some((item) => Number(item.income || 0) || Number(item.expenses || 0));
  const healthScore = Number(health.overall_score || 0);
  const boundedHealthScore = Math.min(Math.max(healthScore, 0), 100);
  const healthToneColor = boundedHealthScore < 40 ? '#ff5252' : boundedHealthScore < 70 ? '#ffa43b' : '#a3ff12';
  const healthRotation = boundedHealthScore * 3.6;
  const isAllTime = selectedYear === ALL_YEARS;
  const numericSelectedYear = isAllTime ? now.getFullYear() : Number(selectedYear);
  const monthLabel = getMonthLabel(selectedMonth);
  const periodLabel = isAllTime
    ? 'all transaction data'
    : selectedMonth === 0
      ? `all of ${numericSelectedYear}`
      : `${monthLabel} ${numericSelectedYear}`;
  const previousMonthLabel = isAllTime
    ? 'earlier data'
    : selectedMonth === 0
      ? 'last year'
      : 'last month';
  const categoryBreakdownPath = `/dashboard/category-analytics?${new URLSearchParams(
    isAllTime ? { month: '-1' } : { month: String(selectedMonth), year: String(numericSelectedYear) },
  ).toString()}`;
  const isCurrentMonthSelected = !isAllTime
    && numericSelectedYear === now.getFullYear()
    && selectedMonth === now.getMonth() + 1;
  const metrics = [
    {
      icon: 'balance',
      label: 'Opening Balance',
      numericValue: summary.opening_balance,
      helper: null,
      tone: Number(summary.opening_balance || 0) >= 0 ? 'positive' : 'negative',
    },
    {
      icon: 'income',
      label: 'Total Income',
      numericValue: summary.total_income,
      helper: 'No previous-period income comparison',
      delta: trendSummary.income_change_percentage,
      deltaLabel: previousMonthLabel,
      tone: 'positive',
    },
    {
      icon: 'expenses',
      label: 'Total Expenses',
      numericValue: summary.total_expenses,
      helper: 'No previous-period expense comparison',
      delta: trendSummary.expense_change_percentage,
      deltaLabel: previousMonthLabel,
      deltaDirection: 'lower-is-better',
      tone: 'negative',
    },
    {
      icon: 'balance',
      label: 'Closing Balance',
      numericValue: summary.closing_balance,
      helper: null,
      tone: Number(summary.closing_balance || 0) >= 0 ? 'positive' : 'negative',
    },
    {
      icon: 'savings',
      label: 'Total Savings',
      numericValue: summary.total_savings,
      helper: 'No previous-period savings comparison',
      delta: trendSummary.savings_change_percentage,
      deltaLabel: previousMonthLabel,
      tone: 'positive',
    },
    {
      icon: 'savings',
      label: 'Savings Rate',
      numericValue: summary.savings_rate,
      helper: 'Intentional savings as a share of available funds',
      delta: trendSummary.savings_rate_change_points,
      deltaLabel: previousMonthLabel,
      deltaUnit: 'percent',
      tone: summary.savings_rate === null || summary.savings_rate === undefined
        ? 'neutral'
        : Number(summary.savings_rate) >= 10 ? 'positive' : 'negative',
      format: 'percent',
    },
    {
      icon: 'balance',
      label: 'Current Balance',
      numericValue: isCurrentMonthSelected ? summary.current_balance : null,
      helper: null,
      delta: isCurrentMonthSelected ? trendSummary.current_balance_change_percentage : null,
      deltaLabel: previousMonthLabel,
      tone: isCurrentMonthSelected
        ? Number(summary.current_balance || 0) >= 0 ? 'positive' : 'negative'
        : 'neutral',
    },
    {
      icon: 'category',
      label: 'Highest Spending Category',
      numericValue: summary.top_category || 'No spending yet',
      helper: null,
      tone: 'neutral',
      format: 'text',
    },
  ];

  return (
    <div>
      <Navigation />
      <main className="dashboard-page">
        <header className="dashboard-header">
          <div>
            <p className="dashboard-kicker">Financial dashboard</p>
            <h1>Good evening, {user?.name || 'Aiman Raza'}</h1>
            <p>Financial summary for selected month</p>
          </div>
          <div className="dashboard-filters" aria-label="Dashboard filters">
            <label>
              <span>Month</span>
              <AppSelect
                ariaLabel="Select dashboard month"
                value={isAllTime ? 0 : selectedMonth}
                disabled={isAllTime}
                onChange={(nextValue) => {
                  const nextMonth = Number(nextValue);
                  setSelectedMonth(nextMonth);
                  savePeriodSelection(nextMonth, selectedYear);
                }}
                options={monthOptions}
              />
            </label>
            <label>
              <span>Year</span>
              <AppSelect
                ariaLabel="Select dashboard year"
                value={selectedYear}
                onChange={(nextValue) => {
                  const nextYear = nextValue === ALL_YEARS ? ALL_YEARS : Number(nextValue);
                  setSelectedYear(nextYear);
                  if (nextYear !== ALL_YEARS) savePeriodSelection(selectedMonth, nextYear);
                }}
                options={[
                  { value: ALL_YEARS, label: 'All' },
                  ...yearOptions.map((year) => ({ value: year, label: String(year) })),
                ]}
              />
            </label>
          </div>
        </header>

        {error && <div className="dashboard-card dashboard-error">{error}</div>}

        <section className="dashboard-grid metric-grid" aria-label={`Summary cards for ${periodLabel}`}>
          {metrics.map((metric) => (
            <DashboardMetric key={metric.label} {...metric} loading={loading} />
          ))}
        </section>

        <section className="dashboard-grid chart-grid">
          <article className="dashboard-card chart-card income-expense-card">
            <div className="dashboard-card-header">
              <div>
                <h2>Income vs Expenses</h2>
                <p>{formatDelta(trendSummary.expense_change_percentage, previousMonthLabel, 'Monthly trend')}</p>
              </div>
              <div className="chart-legend" aria-hidden="true">
                <span className="positive">Income</span>
                <span className="negative">Expenses</span>
              </div>
            </div>
            {loading ? (
              <div className="chart-empty-state">Loading monthly trends...</div>
            ) : !hasTrendData ? (
              <div className="chart-empty-state">No monthly trend data yet.</div>
            ) : (
              <div className="line-chart-frame">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={trendData} margin={{ top: 14, right: 12, left: 4, bottom: 4 }}>
                    <defs>
                      <linearGradient id="incomeFill" x1="0" x2="0" y1="0" y2="1">
                        <stop offset="0%" stopColor="#a3ff12" stopOpacity={0.28} />
                        <stop offset="100%" stopColor="#a3ff12" stopOpacity={0.02} />
                      </linearGradient>
                      <linearGradient id="expenseFill" x1="0" x2="0" y1="0" y2="1">
                        <stop offset="0%" stopColor="#ff5252" stopOpacity={0.24} />
                        <stop offset="100%" stopColor="#ff5252" stopOpacity={0.02} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid stroke="rgba(255,255,255,0.08)" vertical={false} />
                    <XAxis dataKey="month" tick={{ fontSize: 12, fill: 'oklch(.76 0 0)' }} axisLine={false} tickLine={false} />
                    <YAxis
                      tick={{ fontSize: 12, fill: 'oklch(.76 0 0)' }}
                      axisLine={false}
                      tickLine={false}
                      width={64}
                      tickFormatter={(value) => formatCompactMoney(value)}
                    />
                    <Tooltip content={<DashboardTooltip />} cursor={{ stroke: 'rgba(255,255,255,0.12)' }} />
                    <Area type="monotone" dataKey="income" name="Income" stroke="#a3ff12" fill="url(#incomeFill)" strokeWidth={3} dot={false} activeDot={{ r: 5 }} isAnimationActive={false} />
                    <Area type="monotone" dataKey="expenses" name="Expenses" stroke="#ff5252" fill="url(#expenseFill)" strokeWidth={3} dot={false} activeDot={{ r: 5 }} isAnimationActive={false} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            )}
          </article>

          <article className="dashboard-card chart-card category-chart-card has-route">
            <div className="dashboard-card-header">
              <div>
                <h2>Spending by Category</h2>
                <p>{formatMoney(totalCategorySpend)} total expenses</p>
              </div>
              <Link to={categoryBreakdownPath}>View</Link>
            </div>
            {loading ? (
              <div className="chart-empty-state">Loading expense categories...</div>
            ) : !hasCategoryData ? (
              <div className="chart-empty-state">No expense categories found for this period.</div>
            ) : (
              <div className="donut-layout">
                <div className="donut-chart">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={categoryBreakdown}
                        dataKey="value"
                        nameKey="name"
                        innerRadius="66%"
                        outerRadius="88%"
                        paddingAngle={0}
                        stroke="none"
                        strokeWidth={0}
                        isAnimationActive={false}
                      >
                        {categoryBreakdown.map((entry, index) => (
                          <Cell key={entry.name} fill={getCategoryChartColor(entry, index)} />
                        ))}
                      </Pie>
                      <Tooltip content={<DonutTooltip />} />
                    </PieChart>
                  </ResponsiveContainer>
                  <div className="donut-center">
                    <strong>{formatCompactMoney(totalCategorySpend)}</strong>
                    <span>Total</span>
                  </div>
                </div>
                <div className="category-list">
                  {categoryBreakdown.slice(0, 6).map((entry, index) => {
                    const color = getCategoryChartColor(entry, index);
                    const percentage = totalCategorySpend ? ((Number(entry.value || 0) / totalCategorySpend) * 100).toFixed(1) : '0.0';

                    return (
                      <div className="category-row" key={entry.name}>
                        <span className="dashboard-category-name" style={{ '--category-color': color }}>{entry.name}</span>
                        <strong>{formatCompactMoney(entry.value)}</strong>
                        <em>{percentage}%</em>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </article>
        </section>

        <section className="dashboard-grid dashboard-health-grid">
          <article
            className="dashboard-card dashboard-health-card has-route"
            style={{ '--health-tone': healthToneColor, '--health-deg': `${healthRotation}deg` }}
          >
            <div className="dashboard-card-header">
              <div>
                <h2>Financial Health Score</h2>
                <p>Open AI Insights for the full score breakdown and financial signals</p>
              </div>
              <Link to="/ai-insights" className="dashboard-health-insights-link">
                View Insights
              </Link>
            </div>
            <div className="dashboard-health-content">
              <div className="dashboard-health-score-cluster">
                <div className="dashboard-health-ring" aria-label={`Financial health score ${Math.round(healthScore)} out of 100`}>
                  <div className="dashboard-health-ring-label" aria-hidden="true">
                    <strong>{Math.round(healthScore)}</strong>
                    <span>/100</span>
                  </div>
                </div>
                <div className="dashboard-health-copy">
                  <strong>{health.status_label || 'Needs Improvement'}</strong>
                  <p>{health.breakdown?.[0]?.description || 'Your score improves as income, savings, subscriptions, and balance become healthier.'}</p>
                  <div className="dashboard-health-scale" style={{ '--health-score': `${boundedHealthScore}%` }}>
                    <span />
                  </div>
                </div>
              </div>
            </div>
          </article>
        </section>

        <section className="dashboard-grid table-grid">
          <article className="dashboard-card table-card">
            <div className="dashboard-card-header">
              <div>
                <h2>Top Merchants</h2>
                <p>Highest spend in {periodLabel}</p>
              </div>
            </div>
            <div className="dashboard-table-wrap">
              <table className="dashboard-table">
                <thead>
                  <tr>
                    <th>Merchant</th>
                    <th>Transactions</th>
                    <th>Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {(merchantAnalytics.top_merchants || []).length === 0 ? (
                    <tr><td colSpan="3">No merchant spending yet.</td></tr>
                  ) : merchantAnalytics.top_merchants.slice(0, 6).map((merchant, index) => (
                    <tr key={merchant.merchant_name}>
                      <td>
                        <span className="merchant-dot" style={{ background: getCategoryChartColor({ name: merchant.merchant_name }, index) }} />
                        {merchant.merchant_name}
                      </td>
                      <td>{merchant.frequency} txn{merchant.frequency === 1 ? '' : 's'}</td>
                      <td className="money negative">{formatMoney(merchant.total_spent)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </article>

          <article className="dashboard-card table-card">
            <div className="dashboard-card-header">
              <div>
                <h2>Top Subscriptions</h2>
                <p>{formatMoney(subscriptionAnalytics.total_monthly_cost)} monthly cost</p>
              </div>
            </div>
            <div className="dashboard-table-wrap">
              <table className="dashboard-table">
                <thead>
                  <tr>
                    <th>Subscription</th>
                    <th>Confidence</th>
                    <th>Monthly</th>
                  </tr>
                </thead>
                <tbody>
                  {(subscriptionAnalytics.subscriptions || []).length === 0 ? (
                    <tr><td colSpan="3">No subscription payments found.</td></tr>
                  ) : subscriptionAnalytics.subscriptions.slice(0, 6).map((subscription, index) => (
                    <tr key={subscription.merchant_name}>
                      <td>
                        <span className="merchant-dot" style={{ background: getCategoryChartColor('Subscriptions', index) }} />
                        {subscription.merchant_name}
                      </td>
                      <td>{Math.round((subscription.confidence || 0) * 100)}%</td>
                      <td className="money warning">{formatMoney(subscription.monthly_cost)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </article>

          <article className="dashboard-card table-card recent-transactions-card has-route">
            <div className="dashboard-card-header">
              <div>
                <h2>Recent Transactions</h2>
                <p>Latest activity in {periodLabel}</p>
              </div>
              <Link to="/transactions">View all</Link>
            </div>
            <div className="dashboard-table-wrap">
              <table className="dashboard-table recent-transactions-table">
                <thead>
                  <tr>
                    <th>Transaction</th>
                    <th>Category</th>
                    <th>Date</th>
                    <th>Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {recentTransactions.length === 0 ? (
                    <tr><td colSpan="4">No transactions found for this period.</td></tr>
                  ) : recentTransactions.map((transaction) => (
                    <tr key={transaction.id}>
                      <td>{transaction.merchant || transaction.description}</td>
                      <td>{transaction.category_name}</td>
                      <td>{new Date(transaction.date).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })}</td>
                      <td className={`money ${transaction.transaction_type === 'income' ? 'positive' : 'negative'}`}>
                        {transaction.transaction_type === 'income' ? '+' : '-'}{formatMoney(transaction.amount)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </article>
        </section>
      </main>
    </div>
  );
};

export default Dashboard;
