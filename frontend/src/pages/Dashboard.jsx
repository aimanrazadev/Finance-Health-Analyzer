import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import Navigation from '../components/Navigation';
import { useAuth } from '../hooks/useAuth';
import api, { getAuthHeaders } from '../utils/api';
import { getCategoryChartColor } from '../utils/categoryDisplay';

const now = new Date();

const emptySummary = {
  month: now.getMonth() + 1,
  year: now.getFullYear(),
  total_income: 0,
  total_expenses: 0,
  total_savings: 0,
  savings_rate: 0,
  savings_status: 'Poor',
  transaction_count: 0,
  top_category: null,
  top_merchant: null,
  recurring_subscription_count: 0,
  account_balance: 0,
  financial_health_score: 0,
  financial_health_status: 'Needs Improvement',
  financial_health_reason: '',
};

const emptyCharts = { category_breakdown: [], top_merchants: [] };
const emptyTrendSummary = { trends: [], income_change_percentage: null, expense_change_percentage: null, savings_change_percentage: null };
const emptyMerchants = { top_merchants: [], most_frequent_merchants: [], highest_spending_merchants: [] };
const emptySubscriptions = { subscription_count: 0, total_monthly_cost: 0, subscriptions: [] };

const monthOptions = [
  { value: 0, label: 'All year' },
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

const moneyFormatter = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  maximumFractionDigits: 0,
});

const compactMoneyFormatter = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  notation: 'compact',
  maximumFractionDigits: 1,
});

const formatMoney = (value) => moneyFormatter.format(Number(value || 0));
const formatCompactMoney = (value) => compactMoneyFormatter.format(Number(value || 0));

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
    rate: <svg {...common}><path d="m7 17 10-10" /><circle cx="7.5" cy="7.5" r="1.8" /><circle cx="16.5" cy="16.5" r="1.8" /></svg>,
    transactions: <svg {...common}><path d="M8 3h8l3 3v15H5V3h3Z" /><path d="M16 3v4h4" /><path d="M8 11h8" /><path d="M8 15h6" /></svg>,
    category: <svg {...common}><path d="M4 5h6v6H4z" /><path d="M14 5h6v6h-6z" /><path d="M4 15h6v6H4z" /><path d="M14 15h6v6h-6z" /></svg>,
    merchant: <svg {...common}><path d="M4 10h16" /><path d="m5 10 1-5h12l1 5" /><path d="M6 10v9h12v-9" /><path d="M9 19v-5h6v5" /></svg>,
    health: <svg {...common}><path d="M12 21s7-4.4 7-11V5l-7-3-7 3v5c0 6.6 7 11 7 11Z" /><path d="M12 8v5" /><path d="M12 17h.01" /></svg>,
    balance: <svg {...common}><path d="M19 7V6a2 2 0 0 0-2-2H5a3 3 0 0 0 0 6h14a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2H5a3 3 0 0 1-3-3V7" /><path d="M16 14h.01" /></svg>,
  };

  return icons[name] || icons.transactions;
};

const getMonthLabel = (month) => (
  Number(month) === 0 ? 'All year' : monthOptions.find((item) => item.value === Number(month))?.label || 'This month'
);

const getDateRangeLabel = (month, year) => {
  if (Number(month) === 0) return `Jan 1 - Dec 31, ${year}`;
  const firstDay = new Date(year, month - 1, 1);
  const lastDay = new Date(year, month, 0);
  const monthName = firstDay.toLocaleString('en-US', { month: 'short' });
  return `${monthName} 1 - ${monthName} ${lastDay.getDate()}, ${year}`;
};

const getPreviousMonthLabel = (month, year) => {
  if (Number(month) === 0) return String(Number(year) - 1);
  return new Date(year, Number(month) - 2, 1).toLocaleString('en-US', { month: 'short' });
};

const formatDelta = (value, previousLabel, fallback = 'This period') => {
  if (value === null || value === undefined) return fallback;
  const numeric = Number(value || 0);
  return `${numeric >= 0 ? '+' : '-'} ${Math.abs(numeric).toFixed(1)}% vs ${previousLabel}`;
};

const deltaClass = (value, reverse = false) => {
  if (value === null || value === undefined) return 'neutral';
  const positive = reverse ? Number(value) <= 0 : Number(value) >= 0;
  return positive ? 'positive' : 'negative';
};

const MiniSparkline = ({ tone = 'positive' }) => {
  const path = tone === 'negative'
    ? 'M3 25 C14 22 20 23 28 16 S42 9 50 10 S62 30 77 20'
    : 'M3 24 C15 23 18 16 31 17 S44 20 54 13 S66 6 78 11';

  return (
    <svg className={`metric-sparkline ${tone}`} viewBox="0 0 82 34" aria-hidden="true">
      <path d={path} />
    </svg>
  );
};

const DashboardMetric = ({ icon, label, value, helper, delta, tone = 'neutral', spark = true, loading = false }) => (
  <article className={`premium-metric-card tone-${tone}`}>
    <div className="metric-card-copy">
      <div className="metric-icon" aria-hidden="true"><MetricIcon name={icon} /></div>
      <div>
        <span>{label}</span>
        <strong>{loading ? 'Loading...' : value}</strong>
        {helper && <small>{helper}</small>}
      </div>
    </div>
    {(delta || spark) && (
      <div className="metric-trend-row">
        {delta && <em className={`metric-delta ${tone}`}>{delta}</em>}
        {spark && <MiniSparkline tone={tone === 'negative' ? 'negative' : 'positive'} />}
      </div>
    )}
  </article>
);

const Dashboard = () => {
  const { token, user } = useAuth();
  const [summary, setSummary] = useState(emptySummary);
  const [charts, setCharts] = useState(emptyCharts);
  const [trendSummary, setTrendSummary] = useState(emptyTrendSummary);
  const [merchantAnalytics, setMerchantAnalytics] = useState(emptyMerchants);
  const [subscriptionAnalytics, setSubscriptionAnalytics] = useState(emptySubscriptions);
  const [periodMode, setPeriodMode] = useState('month');
  const [selectedMonth, setSelectedMonth] = useState(emptySummary.month);
  const [selectedYear, setSelectedYear] = useState(emptySummary.year);
  const [selectedDate, setSelectedDate] = useState(now.toISOString().slice(0, 10));
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;

    const loadDashboard = async () => {
      setLoading(true);
      setError('');
      const headers = getAuthHeaders(token);
      const selectedDayDate = new Date(`${selectedDate}T00:00:00`);
      const params = periodMode === 'lifetime'
        ? { month: -1, year: selectedYear }
        : periodMode === 'day'
          ? {
            month: selectedDayDate.getMonth() + 1,
            year: selectedDayDate.getFullYear(),
            day: selectedDayDate.getDate(),
          }
          : periodMode === 'year'
            ? { month: 0, year: selectedYear }
            : { month: selectedMonth, year: selectedYear };
      const trendYear = periodMode === 'day' ? selectedDayDate.getFullYear() : selectedYear;

      try {
        const results = await Promise.allSettled([
          api.get('/dashboard/summary', { headers, params }),
          api.get('/dashboard/charts', { headers, params }),
          api.get('/dashboard/charts/monthly-trends', { headers, params: { year: trendYear } }),
          api.get('/dashboard/merchants', { headers, params }),
          api.get('/dashboard/subscriptions', { headers, params }),
        ]);

        if (cancelled) return;

        const [
          summaryResult,
          chartsResult,
          trendsResult,
          merchantsResult,
          subscriptionsResult,
        ] = results;
        setSummary(summaryResult.status === 'fulfilled' ? summaryResult.value.data : emptySummary);
        setCharts(chartsResult.status === 'fulfilled' ? chartsResult.value.data : emptyCharts);
        setTrendSummary(trendsResult.status === 'fulfilled' ? trendsResult.value.data : emptyTrendSummary);
        setMerchantAnalytics(merchantsResult.status === 'fulfilled' ? merchantsResult.value.data : emptyMerchants);
        setSubscriptionAnalytics(subscriptionsResult.status === 'fulfilled' ? subscriptionsResult.value.data : emptySubscriptions);

        if (summaryResult.status === 'rejected') {
          setError('Unable to load dashboard summary.');
        }
      } catch (err) {
        console.error(err);
        if (!cancelled) {
          setSummary(emptySummary);
          setCharts(emptyCharts);
          setTrendSummary(emptyTrendSummary);
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
  }, [token, periodMode, selectedDate, selectedMonth, selectedYear]);

  const categoryBreakdown = charts.category_breakdown || [];
  const trendData = charts.monthly_trends?.length ? charts.monthly_trends : (trendSummary.trends || []);
  const totalCategorySpend = categoryBreakdown.reduce((sum, item) => sum + Number(item.value || 0), 0);
  const hasCategoryData = categoryBreakdown.length > 0 && totalCategorySpend > 0;
  const hasTrendData = trendData.some((item) => Number(item.income || 0) || Number(item.expenses || 0));
  const healthScore = Number(summary.financial_health_score || 0);
  const healthRotation = Math.min(Math.max(healthScore, 0), 100) * 3.6;
  const selectedDayDate = new Date(`${selectedDate}T00:00:00`);
  const monthLabel = getMonthLabel(selectedMonth);
  const periodLabel = periodMode === 'lifetime'
    ? 'all time'
    : periodMode === 'day'
      ? selectedDayDate.toLocaleDateString('en-US', { day: 'numeric', month: 'long', year: 'numeric' })
      : periodMode === 'year'
        ? `all ${selectedYear}`
        : `${monthLabel} ${selectedYear}`;
  const comparisonMonth = periodMode === 'day' ? selectedDayDate.getMonth() + 1 : selectedMonth;
  const comparisonYear = periodMode === 'day' ? selectedDayDate.getFullYear() : selectedYear;
  const previousMonthLabel = periodMode === 'lifetime'
    ? 'earlier data'
    : periodMode === 'year'
      ? `${selectedYear - 1}`
      : getPreviousMonthLabel(comparisonMonth, comparisonYear);

  const metrics = [
    {
      icon: 'income',
      label: 'Total Income',
      value: formatMoney(summary.total_income),
      delta: formatDelta(trendSummary.income_change_percentage, previousMonthLabel, 'This month'),
      tone: deltaClass(trendSummary.income_change_percentage),
    },
    {
      icon: 'expenses',
      label: 'Total Expenses',
      value: formatMoney(summary.total_expenses),
      delta: formatDelta(trendSummary.expense_change_percentage, previousMonthLabel, 'This month'),
      tone: deltaClass(trendSummary.expense_change_percentage, true),
    },
    {
      icon: 'savings',
      label: 'Total Savings',
      value: formatMoney(summary.total_savings),
      delta: formatDelta(trendSummary.savings_change_percentage, previousMonthLabel, `${Number(summary.savings_rate || 0).toFixed(1)}% rate`),
      tone: Number(summary.total_savings || 0) >= 0 ? 'positive' : 'negative',
    },
    {
      icon: 'rate',
      label: 'Savings Rate',
      value: `${Number(summary.savings_rate || 0).toFixed(1)}%`,
      helper: summary.savings_status || 'Calculated from cash flow',
      tone: Number(summary.savings_rate || 0) >= 20 ? 'positive' : Number(summary.savings_rate || 0) < 0 ? 'negative' : 'neutral',
    },
    {
      icon: 'transactions',
      label: 'Transactions',
      value: String(summary.transaction_count || 0),
      helper: 'This period',
      tone: 'neutral',
      spark: false,
    },
    {
      icon: 'category',
      label: 'Top Category',
      value: summary.top_category || 'No category',
      helper: 'Highest spending group',
      tone: 'neutral',
      spark: false,
    },
    {
      icon: 'merchant',
      label: 'Top Merchant',
      value: summary.top_merchant || 'No merchant',
      helper: summary.top_merchant ? 'Highest spending merchant' : '',
      tone: 'warning',
      spark: false,
    },
    {
      icon: 'balance',
      label: 'Balance',
      value: formatMoney(summary.account_balance || 0),
      helper: 'Latest statement balance',
      tone: Number(summary.account_balance || 0) >= 0 ? 'positive' : 'negative',
      spark: false,
    },
  ];

  return (
    <div>
      <Navigation />
      <main className="dashboard-container premium-dashboard">
        <header className="premium-dashboard-header">
          <div>
            <p className="eyebrow">Financial health intelligence</p>
            <h1>Good evening, {user?.name || 'Aiman Raza'}</h1>
            <p>Here&apos;s your financial overview for {periodLabel}</p>
          </div>
          <div className="premium-header-actions">
            <label className="premium-date-control period-mode-control">
              <span className="control-glyph" aria-hidden="true">□</span>
              <select aria-label="Select dashboard period type" value={periodMode} onChange={(event) => setPeriodMode(event.target.value)}>
                <option value="month">Month</option>
                <option value="year">Year</option>
                <option value="day">Day</option>
                <option value="lifetime">All</option>
              </select>
            </label>
            {periodMode === 'month' && (
              <label className="premium-date-control month-period-control">
                <select aria-label="Select dashboard month" value={selectedMonth} onChange={(event) => setSelectedMonth(Number(event.target.value))}>
                  {monthOptions.filter((month) => month.value > 0).map((month) => (
                    <option key={month.value} value={month.value}>
                      {month.label} {selectedYear}
                    </option>
                  ))}
                </select>
              </label>
            )}
            {(periodMode === 'month' || periodMode === 'year') && (
              <label className="premium-year-control">
                <select aria-label="Select dashboard year" value={selectedYear} onChange={(event) => setSelectedYear(Number(event.target.value))}>
                  {yearOptions.map((year) => (
                    <option key={year} value={year}>{year}</option>
                  ))}
                </select>
              </label>
            )}
            {periodMode === 'day' && (
              <label className="premium-date-control dashboard-day-control">
                <input
                  aria-label="Select dashboard day"
                  type="date"
                  value={selectedDate}
                  onChange={(event) => setSelectedDate(event.target.value)}
                />
              </label>
            )}
            {periodMode === 'year' && (
              <span className="premium-period-pill">Full year</span>
            )}
            {periodMode === 'lifetime' && (
              <span className="premium-period-pill">All time</span>
            )}
          </div>
        </header>

        {error && <div className="surface-message error">{error}</div>}

        <div className="premium-dashboard-grid">
          <section className="premium-dashboard-main">
            <div className="premium-metrics-grid">
              {metrics.map((metric) => (
                <DashboardMetric key={metric.label} {...metric} loading={loading} />
              ))}
            </div>

            <Link className="health-link-card dashboard-health-wide" to="/financial-health">
              <section className="dashboard-card health-panel">
                <div className="premium-panel-header">
                  <div>
                    <h2>Financial Health Score</h2>
                    <p>{summary.financial_health_status || 'Needs Improvement'}</p>
                  </div>
                  <span>Details</span>
                </div>
                <div className="health-ring" style={{ '--health-deg': `${healthRotation}deg` }}>
                  <strong>{healthScore}</strong>
                  <span>/100</span>
                </div>
                <strong className="health-label">{summary.financial_health_status || 'Needs Improvement'}</strong>
                <p>{summary.financial_health_reason || 'Your score improves as income, savings, and spending patterns become healthier.'}</p>
                <div className="health-scale" style={{ '--health-score': `${Math.min(Math.max(healthScore, 0), 100)}%` }}>
                  <span />
                  <span />
                  <span />
                  <span />
                </div>
              </section>
            </Link>

            <section className="premium-chart-grid">
              <article className="dashboard-card spending-panel">
                <div className="premium-panel-header">
                  <div>
                    <h2>Spending by Category</h2>
                    <p>{formatMoney(totalCategorySpend)} total expenses</p>
                  </div>
                  <Link to="/categories">View breakdown</Link>
                </div>
                {!hasCategoryData ? (
                  <div className="chart-empty-state">No expense categories found for this period.</div>
                ) : (
                  <div className="premium-donut-layout">
                    <div className="premium-donut">
                      <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                          <Pie
                            data={categoryBreakdown}
                            dataKey="value"
                            nameKey="name"
                            innerRadius="62%"
                            outerRadius="88%"
                            paddingAngle={1.5}
                            stroke="none"
                            strokeWidth={0}
                            isAnimationActive={false}
                          >
                            {categoryBreakdown.map((entry, index) => (
                              <Cell key={entry.name} fill={getCategoryChartColor(entry, index)} stroke="none" strokeWidth={0} />
                            ))}
                          </Pie>
                          <Tooltip formatter={(value) => formatMoney(value)} />
                        </PieChart>
                      </ResponsiveContainer>
                      <div className="donut-center">
                        <strong>{formatMoney(totalCategorySpend)}</strong>
                        <span>Total Expenses</span>
                      </div>
                    </div>
                    <div className="premium-category-list">
                      {categoryBreakdown.slice(0, 8).map((entry, index) => {
                        const percentage = totalCategorySpend ? ((Number(entry.value || 0) / totalCategorySpend) * 100).toFixed(1) : '0.0';
                        return (
                          <div className="premium-category-row" key={entry.name}>
                            <span className="legend-dot" style={{ background: getCategoryChartColor(entry, index) }} />
                            <span>{entry.name}</span>
                            <strong>{formatCompactMoney(entry.value)}</strong>
                            <em>{percentage}%</em>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </article>

              <article className="dashboard-card trend-panel">
                <div className="premium-panel-header">
                  <div>
                    <h2>Income vs Expenses</h2>
                    <p>{formatDelta(trendSummary.expense_change_percentage, previousMonthLabel, 'Monthly trend')}</p>
                  </div>
                </div>
                {!hasTrendData ? (
                  <div className="chart-empty-state">No monthly trend data yet.</div>
                ) : (
                  <ResponsiveContainer width="100%" height={235}>
                    <LineChart data={trendData} margin={{ top: 10, right: 8, left: -18, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,0.08)" />
                      <XAxis dataKey="month" tick={{ fontSize: 11, fill: '#8d969f' }} axisLine={false} tickLine={false} />
                      <YAxis tick={{ fontSize: 11, fill: '#7D8781' }} axisLine={false} tickLine={false} tickFormatter={(value) => `INR ${Math.round(Number(value || 0) / 1000)}K`} />
                      <Tooltip formatter={(value) => formatMoney(value)} />
                      <Line type="monotone" dataKey="income" stroke="#a3e635" strokeWidth={2.5} dot={false} isAnimationActive={false} />
                      <Line type="monotone" dataKey="expenses" stroke="#ff4d4d" strokeWidth={2.2} dot={false} isAnimationActive={false} />
                    </LineChart>
                  </ResponsiveContainer>
                )}
              </article>
            </section>

          </section>

          <aside className="premium-right-rail">
            <section className="rail-section">
              <div className="premium-panel-header">
                <div>
                  <h2>Top Merchants</h2>
                  <p>Highest spending merchants this period.</p>
                </div>
              </div>
              <div className="premium-category-list compact">
                {(merchantAnalytics.top_merchants || []).length === 0 ? (
                  <div className="chart-empty-state small">No merchant spending yet.</div>
                ) : merchantAnalytics.top_merchants.slice(0, 5).map((merchant, index) => (
                  <div className="premium-category-row" key={merchant.merchant_name}>
                    <span className="legend-dot" style={{ background: index === 0 ? '#a3e635' : '#8d969f' }} />
                    <span>{merchant.merchant_name}</span>
                    <strong>{formatCompactMoney(merchant.total_spent)}</strong>
                    <em>{merchant.frequency}x</em>
                  </div>
                ))}
              </div>
            </section>

            <section className="rail-section">
              <div className="premium-panel-header">
                <div>
                  <h2>Subscription Analysis</h2>
                  <p>
                    {subscriptionAnalytics.subscription_count || 0} active -
                    {' '}{formatMoney(subscriptionAnalytics.total_monthly_cost || 0)} / month
                  </p>
                </div>
              </div>
              <div className="premium-category-list compact">
                {(subscriptionAnalytics.subscriptions || []).length === 0 ? (
                  <div className="chart-empty-state small">No Subscriptions category payments found.</div>
                ) : subscriptionAnalytics.subscriptions.slice(0, 4).map((subscription) => (
                  <div className="premium-category-row" key={subscription.merchant_name}>
                    <span className="legend-dot" style={{ background: '#5eead4' }} />
                    <span>{subscription.merchant_name}</span>
                    <strong>{formatCompactMoney(subscription.monthly_cost)}</strong>
                    <em>{Math.round((subscription.confidence || 0) * 100)}%</em>
                  </div>
                ))}
              </div>
            </section>
          </aside>
        </div>
      </main>
    </div>
  );
};

export default Dashboard;
