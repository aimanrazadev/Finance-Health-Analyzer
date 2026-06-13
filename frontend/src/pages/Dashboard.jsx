import { useEffect, useMemo, useState } from 'react';
import {
  Bar,
  BarChart,
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
import { useAuth } from '../hooks/useAuth';
import Navigation from '../components/Navigation';
import Skeleton from '../components/Skeleton';
import { AnimateNumber } from '../components/ui/AnimatedBlurNumber';
import api, { getAuthHeaders } from '../utils/api';
import { getCategoryChartColor } from '../utils/categoryDisplay';

const moneyFormatter = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  maximumFractionDigits: 0,
});

const animatedCurrencyFormat = {
  style: 'currency',
  currency: 'INR',
  maximumFractionDigits: 0,
};

const animatedPercentFormat = {
  maximumFractionDigits: 0,
};

const emptySummary = {
  month: new Date().getMonth() + 1,
  year: new Date().getFullYear(),
  total_income: 0,
  total_expenses: 0,
  total_savings: 0,
  savings_rate: 0,
  transaction_count: 0,
  top_category: null,
  category_breakdown: [],
};

const emptyCharts = {
  category_breakdown: [],
  income_vs_expense: {
    income: 0,
    expenses: 0,
  },
  monthly_spending: [],
  top_merchants: [],
};

const emptyForecast = {
  predicted_amount: 0,
  forecast_month: '',
  confidence_lower: 0,
  confidence_upper: 0,
  history: [],
  category_forecasts: [],
  feature_summary: {},
};

const emptyInvestments = {
  account_balance: null,
  current_portfolio_value: 0,
  manual_invested_amount: 0,
  auto_detected_invested_amount: 0,
  total_pnl_amount: 0,
  total_pnl_percent: 0,
  net_worth: 0,
};

const incomeExpenseColors = ['#86efac', '#fca5a5'];
const lineChartColor = '#93c5fd';

const ChartEmptyState = ({ children = 'No chart data for this period.' }) => (
  <div className="chart-empty-state">{children}</div>
);

const currencyTooltip = (value) => moneyFormatter.format(value);

const AnimatedCurrency = ({ value, className = '' }) => (
  <AnimateNumber
    value={Number(value || 0)}
    locale="en-IN"
    format={animatedCurrencyFormat}
    className={className}
  />
);

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

const currentYear = new Date().getFullYear();
const yearOptions = Array.from({ length: 7 }, (_, index) => currentYear - 5 + index);

const Dashboard = () => {
  const { token, user } = useAuth();
  const [summary, setSummary] = useState(emptySummary);
  const [charts, setCharts] = useState(emptyCharts);
  const [forecast, setForecast] = useState(emptyForecast);
  const [investments, setInvestments] = useState(emptyInvestments);
  const [budgets, setBudgets] = useState([]);
  const [selectedMonth, setSelectedMonth] = useState(emptySummary.month);
  const [selectedYear, setSelectedYear] = useState(emptySummary.year);
  const [balanceDraft, setBalanceDraft] = useState({ account_name: 'Kotak 811', balance_amount: '' });
  const [editingBalance, setEditingBalance] = useState(false);
  const [loading, setLoading] = useState(true);
  const [chartsLoading, setChartsLoading] = useState(true);
  const [forecastLoading, setForecastLoading] = useState(true);
  const [investmentsLoading, setInvestmentsLoading] = useState(true);
  const [balanceSaving, setBalanceSaving] = useState(false);
  const [budgetsLoading, setBudgetsLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const loadSummary = async () => {
      setLoading(true);
      try {
        const response = await api.get('/dashboard/summary', {
          headers: getAuthHeaders(token),
          params: {
            month: selectedMonth,
            year: selectedYear,
          },
        });
        setSummary(response.data);
        setError('');
      } catch (err) {
        console.error(err);
        setError('Unable to load dashboard summary.');
      } finally {
        setLoading(false);
      }
    };

    if (token) {
      loadSummary();
    }
  }, [token, selectedMonth, selectedYear]);

  useEffect(() => {
    const loadCharts = async () => {
      setChartsLoading(true);
      try {
        const response = await api.get('/dashboard/charts', {
          headers: getAuthHeaders(token),
          params: {
            month: selectedMonth,
            year: selectedYear,
          },
        });
        setCharts(response.data);
      } catch (err) {
        console.error(err);
        setCharts(emptyCharts);
      } finally {
        setChartsLoading(false);
      }
    };

    if (token) {
      loadCharts();
    }
  }, [token, selectedMonth, selectedYear]);

  useEffect(() => {
    const loadForecast = async () => {
      setForecastLoading(true);
      try {
        const response = await api.get('/forecast/expenses', {
          headers: getAuthHeaders(token),
        });
        setForecast(response.data);
      } catch (err) {
        console.error(err);
        setForecast(emptyForecast);
      } finally {
        setForecastLoading(false);
      }
    };

    if (token) {
      loadForecast();
    }
  }, [token]);

  useEffect(() => {
    const loadInvestments = async () => {
      setInvestmentsLoading(true);
      try {
        const response = await api.get('/investments/summary', {
          headers: getAuthHeaders(token),
        });
        setInvestments(response.data);
        if (response.data.account_balance) {
          setBalanceDraft({
            account_name: response.data.account_balance.account_name,
            balance_amount: response.data.account_balance.balance_amount,
          });
        }
      } catch (err) {
        console.error(err);
        setInvestments(emptyInvestments);
      } finally {
        setInvestmentsLoading(false);
      }
    };

    if (token) {
      loadInvestments();
    }
  }, [token]);

  useEffect(() => {
    const loadBudgets = async () => {
      setBudgetsLoading(true);
      try {
        const params = selectedMonth === 0
          ? { year: selectedYear }
          : { month: selectedMonth, year: selectedYear };
        const response = await api.get('/budgets', {
          headers: getAuthHeaders(token),
          params,
        });
        setBudgets(response.data);
      } catch (err) {
        console.error(err);
        setBudgets([]);
      } finally {
        setBudgetsLoading(false);
      }
    };

    if (token) {
      loadBudgets();
    }
  }, [token, selectedMonth, selectedYear]);

  const maxCategoryTotal = useMemo(
    () => Math.max(...summary.category_breakdown.map((item) => item.total), 0),
    [summary.category_breakdown]
  );

  const selectedMonthLabel = selectedMonth === 0
    ? 'All year'
    : monthOptions.find((month) => month.value === Number(summary.month))?.label;
  const hasNoTransactions = !loading && summary.transaction_count === 0;
  const incomeExpenseData = [
    { name: 'Income', value: charts.income_vs_expense.income },
    { name: 'Expenses', value: charts.income_vs_expense.expenses },
  ];
  const hasIncomeExpenseData = incomeExpenseData.some((item) => item.value > 0);
  const hasMonthlySpendingData = charts.monthly_spending.length > 0;
  const totalBudgetLimit = budgets.reduce((sum, budget) => sum + Number(budget.monthly_limit || 0), 0);
  const totalBudgetSpent = budgets.reduce((sum, budget) => sum + Number(budget.actual_spent || 0), 0);
  const budgetUsagePercent = totalBudgetLimit ? Math.round((totalBudgetSpent / totalBudgetLimit) * 100) : 0;
  const reachedBudgetMilestone = [99, 95, 90, 75, 50].find((milestone) => budgetUsagePercent >= milestone);
  const nextBudgetMilestone = [50, 75, 90, 95, 99].find((milestone) => budgetUsagePercent < milestone);
  const forecastExceedsBudget = selectedMonth !== 0 && totalBudgetLimit > 0 && forecast.predicted_amount > totalBudgetLimit;
  const forecastPreviousSpending = Number(forecast.feature_summary?.previous_month_spending || 0);
  const forecastPredictedAmount = Number(forecast.predicted_amount || 0);
  const forecastDelta = forecastPredictedAmount - forecastPreviousSpending;
  const forecastTrendClass = forecastPreviousSpending === 0
    ? 'prediction-neutral'
    : forecastDelta > 0
      ? 'prediction-up'
      : forecastDelta < 0
        ? 'prediction-down'
        : 'prediction-neutral';
  const forecastTrendText = forecastPreviousSpending === 0
    ? 'Waiting for previous month comparison'
    : forecastDelta > 0
      ? `${moneyFormatter.format(Math.abs(forecastDelta))} above previous month`
      : forecastDelta < 0
        ? `${moneyFormatter.format(Math.abs(forecastDelta))} below previous month`
        : 'Same as previous month';
  const saveBalance = async (event) => {
    event.preventDefault();
    setBalanceSaving(true);
    try {
      await api.post('/investments/balance', {
        account_name: balanceDraft.account_name.trim() || 'Current balance',
        balance_amount: Number(balanceDraft.balance_amount || 0),
      }, {
        headers: getAuthHeaders(token),
      });
      const response = await api.get('/investments/summary', {
        headers: getAuthHeaders(token),
      });
      setInvestments(response.data);
      if (response.data.account_balance) {
        setBalanceDraft({
          account_name: response.data.account_balance.account_name,
          balance_amount: response.data.account_balance.balance_amount,
        });
      }
      setEditingBalance(false);
    } catch (err) {
      console.error(err);
      setError('Unable to update current balance.');
    } finally {
      setBalanceSaving(false);
    }
  };

  return (
    <div>
      <Navigation />
      <div className="dashboard-container">
        <div className="page-heading">
          <div>
            <p className="eyebrow">Personal finance workspace</p>
            <h1>Welcome back, {user?.name}</h1>
            <p>Track your cash flow, spending mix, and savings position from your latest transactions.</p>
          </div>
          <div className="dashboard-filters">
            <label>
              Month
              <select value={selectedMonth} onChange={(event) => setSelectedMonth(Number(event.target.value))}>
                {monthOptions.map((month) => (
                  <option key={month.value} value={month.value}>
                    {month.label}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Year
              <select value={selectedYear} onChange={(event) => setSelectedYear(Number(event.target.value))}>
                {yearOptions.map((year) => (
                  <option key={year} value={year}>
                    {year}
                  </option>
                ))}
              </select>
            </label>
          </div>
        </div>

        {error && <div className="surface-message error">{error}</div>}

        <section className="dashboard-balance-hero">
          <div
            className="balance-hero-card"
            onDoubleClick={() => setEditingBalance(true)}
            role="button"
            tabIndex={0}
            onKeyDown={(event) => {
              if (event.key === 'Enter') {
                setEditingBalance(true);
              }
            }}
          >
            <div className="balance-hero-copy">
              <span>Current balance</span>
              <strong>
                {investmentsLoading ? 'Loading...' : (
                  <AnimatedCurrency value={investments.account_balance?.balance_amount || 0} />
                )}
              </strong>
              <small>{investments.account_balance?.account_name || 'Double-click the card to enter balance'}</small>
            </div>
            {editingBalance ? (
              <form className="balance-inline-form" onSubmit={saveBalance} onClick={(event) => event.stopPropagation()}>
                <input
                  value={balanceDraft.account_name}
                  onChange={(event) => setBalanceDraft((current) => ({ ...current, account_name: event.target.value }))}
                  placeholder="Account label"
                  autoFocus
                />
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={balanceDraft.balance_amount}
                  onChange={(event) => setBalanceDraft((current) => ({ ...current, balance_amount: event.target.value }))}
                  placeholder="Current balance"
                />
                <div className="balance-inline-actions">
                  <button className="primary-button" type="submit" disabled={balanceSaving}>
                    {balanceSaving ? 'Saving...' : 'Save'}
                  </button>
                  <button className="secondary-button" type="button" onClick={() => setEditingBalance(false)}>
                    Cancel
                  </button>
                </div>
              </form>
            ) : (
              <button className="secondary-button" type="button" onClick={() => setEditingBalance(true)}>
                Edit balance
              </button>
            )}
          </div>
        </section>
        
        <div className="dashboard-cards">
          <div
            className="metric-card balance-stat-card"
            onDoubleClick={() => setEditingBalance(true)}
            role="button"
            tabIndex={0}
            onKeyDown={(event) => {
              if (event.key === 'Enter') {
                setEditingBalance(true);
              }
            }}
          >
            <span>Account balance</span>
            {investmentsLoading ? <Skeleton rows={1} /> : (
              <strong><AnimatedCurrency value={investments.account_balance?.balance_amount || 0} /></strong>
            )}
            {editingBalance ? (
              <form className="balance-card-form" onSubmit={saveBalance} onClick={(event) => event.stopPropagation()}>
                <input
                  value={balanceDraft.account_name}
                  onChange={(event) => setBalanceDraft((current) => ({ ...current, account_name: event.target.value }))}
                  placeholder="Account label"
                  autoFocus
                />
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={balanceDraft.balance_amount}
                  onChange={(event) => setBalanceDraft((current) => ({ ...current, balance_amount: event.target.value }))}
                  placeholder="Current balance"
                />
                <div className="balance-card-actions">
                  <button className="primary-button" type="submit" disabled={balanceSaving}>
                    {balanceSaving ? 'Saving...' : 'Save'}
                  </button>
                  <button className="secondary-button" type="button" onClick={() => setEditingBalance(false)}>
                    Cancel
                  </button>
                </div>
              </form>
            ) : (
              <small>{investments.account_balance?.account_name || 'Double-click to enter balance'}</small>
            )}
          </div>
          <div className={`metric-card ${Number(summary.total_income || 0) > 0 ? 'metric-positive' : 'metric-neutral'}`}>
            <span>Total income</span>
            {loading ? <Skeleton rows={1} /> : (
              <strong><AnimatedCurrency value={summary.total_income} /></strong>
            )}
            <small>{loading ? 'Fetching period data' : `${summary.transaction_count} transactions recorded`}</small>
          </div>
          <div className={`metric-card ${Number(summary.total_expenses || 0) > 0 ? 'metric-negative' : 'metric-neutral'}`}>
            <span>Total expenses</span>
            {loading ? <Skeleton rows={1} /> : (
              <strong><AnimatedCurrency value={summary.total_expenses} /></strong>
            )}
            <small>{summary.top_category ? `Top category: ${summary.top_category}` : 'No expense category yet'}</small>
          </div>
          <div className={`metric-card ${Number(summary.total_savings || 0) > 0 ? 'metric-positive' : Number(summary.total_savings || 0) < 0 ? 'metric-negative' : 'metric-neutral'}`}>
            <span>Net savings</span>
            {loading ? <Skeleton rows={1} /> : (
              <strong><AnimatedCurrency value={summary.total_savings} /></strong>
            )}
            <small>{summary.savings_rate}% savings rate</small>
          </div>
          <div className={`metric-card ${totalBudgetLimit ? budgetUsagePercent >= 90 ? 'metric-negative' : budgetUsagePercent >= 50 ? 'metric-positive' : 'metric-neutral' : 'metric-neutral'}`}>
            <span>Budget usage</span>
            {budgetsLoading ? <Skeleton rows={1} /> : (
              <strong>
                {totalBudgetLimit ? (
                  <AnimateNumber
                    value={budgetUsagePercent}
                    suffix="%"
                    locale="en-IN"
                    format={animatedPercentFormat}
                  />
                ) : 'No budget'}
              </strong>
            )}
            <small>
              {totalBudgetLimit
                ? `${moneyFormatter.format(totalBudgetSpent)} of ${moneyFormatter.format(totalBudgetLimit)} used. ${
                  reachedBudgetMilestone ? `${reachedBudgetMilestone}% milestone reached.` : `Next milestone: ${nextBudgetMilestone}%.`
                }`
                : 'Create budgets to track progress'}
            </small>
          </div>
          <div className={`metric-card prediction-card ${forecastTrendClass} ${forecastExceedsBudget ? 'metric-card-warning' : ''}`}>
            <span>Next month forecast</span>
            {forecastLoading ? <Skeleton rows={1} /> : (
              <strong><AnimatedCurrency value={forecast.predicted_amount || 0} /></strong>
            )}
            <small>
              {forecast.forecast_month ? `${forecast.forecast_month} predicted expense` : 'Add more data for prediction'}
              {forecast.forecast_month && <em>{forecastTrendText}</em>}
            </small>
          </div>
          <div className={`metric-card ${Number(investments.total_pnl_amount || 0) > 0 ? 'metric-positive' : Number(investments.total_pnl_amount || 0) < 0 ? 'metric-negative' : 'metric-neutral'}`}>
            <span>Investments</span>
            {investmentsLoading ? <Skeleton rows={1} /> : (
              <strong><AnimatedCurrency value={investments.current_portfolio_value || 0} /></strong>
            )}
            <small>
              P/L <AnimatedCurrency value={investments.total_pnl_amount || 0} className="inline-animate-number" /> ({investments.total_pnl_percent || 0}%)
            </small>
          </div>
          <div className={`metric-card ${Number(investments.net_worth || 0) > 0 ? 'metric-positive' : Number(investments.net_worth || 0) < 0 ? 'metric-negative' : 'metric-neutral'}`}>
            <span>Net worth estimate</span>
            {investmentsLoading ? <Skeleton rows={1} /> : (
              <strong><AnimatedCurrency value={investments.net_worth || 0} /></strong>
            )}
            <small>Balance + tracked portfolio value</small>
          </div>
        </div>

        {forecastExceedsBudget && (
          <div className="surface-message error dashboard-empty">
            Forecast warning: next month predicted expense is above your selected monthly budget total of {moneyFormatter.format(totalBudgetLimit)}.
          </div>
        )}

        {hasNoTransactions && (
          <div className="empty-state dashboard-empty">
            No transactions found for {selectedMonthLabel} {summary.year}. Add income or expense records to populate this summary.
          </div>
        )}

        <section className="analytics-section">
          <div className="section-heading">
            <div>
              <h2>Expense Breakdown</h2>
              <p>Category totals for {selectedMonthLabel} {summary.year}.</p>
            </div>
          </div>

          <div className="breakdown-list">
            {loading && <Skeleton rows={4} />}

            {!loading && summary.category_breakdown.length === 0 && (
              <div className="empty-state">Add expense transactions to see category analytics.</div>
            )}

              {!loading && summary.category_breakdown.map((item, index) => {
                const width = maxCategoryTotal ? `${(item.total / maxCategoryTotal) * 100}%` : '0%';
                const categoryColor = getCategoryChartColor(item.category_name, index);
                return (
                  <div className="breakdown-row" key={`${item.category_id}-${item.category_name}`}>
                  <div className="breakdown-label">
                    <span>{item.category_name}</span>
                    <strong>{moneyFormatter.format(item.total)}</strong>
                  </div>
                  <div className="breakdown-track">
                    <div
                      className="breakdown-bar"
                      style={{
                        width,
                        background: categoryColor,
                      }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        <section className="charts-grid">
          <div className="chart-panel category-donut-panel">
            <div className="section-heading">
              <div>
                <h2>Total Expenses</h2>
                <p>Expense share by category.</p>
              </div>
            </div>
            <div className="chart-frame">
              {chartsLoading ? (
                <ChartEmptyState>Loading chart...</ChartEmptyState>
              ) : charts.category_breakdown.length === 0 ? (
                <ChartEmptyState>Add expenses to see category share.</ChartEmptyState>
              ) : (
                <div className="category-donut-layout">
                  <div className="category-donut-chart">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={charts.category_breakdown}
                          dataKey="value"
                          nameKey="name"
                          innerRadius="54%"
                          outerRadius="78%"
                          paddingAngle={1.5}
                        >
                          {charts.category_breakdown.map((entry, index) => (
                            <Cell key={entry.name} fill={getCategoryChartColor(entry.name, index)} />
                          ))}
                        </Pie>
                        <Tooltip formatter={currencyTooltip} />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                  <div className="category-donut-legend">
                    {charts.category_breakdown.map((entry, index) => {
                      const total = charts.category_breakdown.reduce((sum, item) => sum + Number(item.value || 0), 0);
                      const percentage = total ? ((Number(entry.value || 0) / total) * 100).toFixed(1) : '0.0';
                      return (
                        <div className="category-legend-row" key={entry.name}>
                          <span className="legend-dot" style={{ background: getCategoryChartColor(entry.name, index) }} />
                          <span>{entry.name}</span>
                          <strong>{moneyFormatter.format(entry.value)}</strong>
                          <em>{percentage}%</em>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          </div>

          <div className="chart-panel">
            <div className="section-heading">
              <div>
                <h2>Category Bar Graph</h2>
                <p>Expense totals by category.</p>
              </div>
            </div>
            <div className="chart-frame">
              {chartsLoading ? (
                <ChartEmptyState>Loading chart...</ChartEmptyState>
              ) : charts.category_breakdown.length === 0 ? (
                <ChartEmptyState>Add expenses to compare categories.</ChartEmptyState>
              ) : (
                <ResponsiveContainer width="100%" height={360}>
                  <BarChart data={charts.category_breakdown}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                    <YAxis tickFormatter={(value) => `${value}`} tick={{ fontSize: 12 }} />
                    <Tooltip formatter={currencyTooltip} />
                    <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                      {charts.category_breakdown.map((entry, index) => (
                        <Cell key={entry.name} fill={getCategoryChartColor(entry.name, index)} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              )}
            </div>
          </div>

          <div className="chart-panel">
            <div className="section-heading">
              <div>
                <h2>Income vs Expense</h2>
                <p>Cash flow comparison for the selected period.</p>
              </div>
            </div>
            <div className="chart-frame">
              {chartsLoading ? (
                <ChartEmptyState>Loading chart...</ChartEmptyState>
              ) : !hasIncomeExpenseData ? (
                <ChartEmptyState>Add income or expenses to compare cash flow.</ChartEmptyState>
              ) : (
                <ResponsiveContainer width="100%" height={340}>
                  <BarChart data={incomeExpenseData}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                    <YAxis tick={{ fontSize: 12 }} />
                    <Tooltip formatter={currencyTooltip} />
                    <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                      {incomeExpenseData.map((entry, index) => (
                        <Cell key={entry.name} fill={incomeExpenseColors[index % incomeExpenseColors.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              )}
            </div>
          </div>

          <div className="chart-panel chart-panel-wide">
            <div className="section-heading">
              <div>
                <h2>Monthly Spending Line Chart</h2>
                <p>Expense trend across {selectedYear}.</p>
              </div>
            </div>
            <div className="chart-frame">
              {chartsLoading ? (
                <ChartEmptyState>Loading chart...</ChartEmptyState>
              ) : !hasMonthlySpendingData ? (
                <ChartEmptyState>Monthly spending data is not available yet.</ChartEmptyState>
              ) : (
                <ResponsiveContainer width="100%" height={340}>
                  <LineChart data={charts.monthly_spending}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="month" tick={{ fontSize: 12 }} />
                    <YAxis tick={{ fontSize: 12 }} />
                    <Tooltip formatter={currencyTooltip} />
                    <Line type="monotone" dataKey="expenses" stroke={lineChartColor} strokeWidth={3} dot={{ r: 3, fill: lineChartColor }} />
                  </LineChart>
                </ResponsiveContainer>
              )}
            </div>
          </div>
        </section>
      </div>
    </div>
  );
};

export default Dashboard;
