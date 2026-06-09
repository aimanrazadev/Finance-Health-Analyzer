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
import api, { getAuthHeaders } from '../utils/api';

const moneyFormatter = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  maximumFractionDigits: 0,
});

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

const chartColors = ['#0073ea', '#00a36c', '#f59f00', '#d92d20', '#7c3aed', '#0891b2'];

const ChartEmptyState = ({ children = 'No chart data for this period.' }) => (
  <div className="chart-empty-state">{children}</div>
);

const currencyTooltip = (value) => moneyFormatter.format(value);

const monthOptions = [
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
  const [selectedMonth, setSelectedMonth] = useState(emptySummary.month);
  const [selectedYear, setSelectedYear] = useState(emptySummary.year);
  const [loading, setLoading] = useState(true);
  const [chartsLoading, setChartsLoading] = useState(true);
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

  const maxCategoryTotal = useMemo(
    () => Math.max(...summary.category_breakdown.map((item) => item.total), 0),
    [summary.category_breakdown]
  );

  const selectedMonthLabel = monthOptions.find((month) => month.value === Number(summary.month))?.label;
  const hasNoTransactions = !loading && summary.transaction_count === 0;
  const incomeExpenseData = [
    { name: 'Income', value: charts.income_vs_expense.income },
    { name: 'Expenses', value: charts.income_vs_expense.expenses },
  ];
  const hasIncomeExpenseData = incomeExpenseData.some((item) => item.value > 0);
  const hasMonthlySpendingData = charts.monthly_spending.some((item) => item.expenses > 0);

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
        
        <div className="dashboard-cards">
          <div className="metric-card">
            <span>Total income</span>
            <strong>{loading ? 'Loading...' : moneyFormatter.format(summary.total_income)}</strong>
            <small>{loading ? 'Fetching period data' : `${summary.transaction_count} transactions recorded`}</small>
          </div>
          <div className="metric-card">
            <span>Total expenses</span>
            <strong>{loading ? 'Loading...' : moneyFormatter.format(summary.total_expenses)}</strong>
            <small>{summary.top_category ? `Top category: ${summary.top_category}` : 'No expense category yet'}</small>
          </div>
          <div className="metric-card">
            <span>Net savings</span>
            <strong>{loading ? 'Loading...' : moneyFormatter.format(summary.total_savings)}</strong>
            <small>{summary.savings_rate}% savings rate</small>
          </div>
          <div className="metric-card">
            <span>Financial health</span>
            <strong>{loading ? 'Loading...' : summary.savings_rate >= 25 ? 'Strong' : summary.savings_rate > 0 ? 'Building' : 'Needs data'}</strong>
            <small>Based on current MVP transaction data</small>
          </div>
        </div>

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
            {loading && <div className="empty-state">Loading category analytics...</div>}

            {!loading && summary.category_breakdown.length === 0 && (
              <div className="empty-state">Add expense transactions to see category analytics.</div>
            )}

            {!loading && summary.category_breakdown.map((item) => {
              const width = maxCategoryTotal ? `${(item.total / maxCategoryTotal) * 100}%` : '0%';
              return (
                <div className="breakdown-row" key={`${item.category_id}-${item.category_name}`}>
                  <div className="breakdown-label">
                    <span>{item.category_name}</span>
                    <strong>{moneyFormatter.format(item.total)}</strong>
                  </div>
                  <div className="breakdown-track">
                    <div className="breakdown-bar" style={{ width }} />
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        <section className="charts-grid">
          <div className="chart-panel">
            <div className="section-heading">
              <div>
                <h2>Category Pie Chart</h2>
                <p>Expense share by category.</p>
              </div>
            </div>
            <div className="chart-frame">
              {chartsLoading ? (
                <ChartEmptyState>Loading chart...</ChartEmptyState>
              ) : charts.category_breakdown.length === 0 ? (
                <ChartEmptyState>Add expenses to see category share.</ChartEmptyState>
              ) : (
                <ResponsiveContainer width="100%" height={280}>
                  <PieChart>
                    <Pie data={charts.category_breakdown} dataKey="value" nameKey="name" innerRadius={64} outerRadius={96}>
                      {charts.category_breakdown.map((entry, index) => (
                        <Cell key={entry.name} fill={chartColors[index % chartColors.length]} />
                      ))}
                    </Pie>
                    <Tooltip formatter={currencyTooltip} />
                  </PieChart>
                </ResponsiveContainer>
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
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={charts.category_breakdown}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                    <YAxis tickFormatter={(value) => `${value}`} tick={{ fontSize: 12 }} />
                    <Tooltip formatter={currencyTooltip} />
                    <Bar dataKey="value" fill="#0073ea" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </div>
          </div>

          <div className="chart-panel">
            <div className="section-heading">
              <div>
                <h2>Income vs Expense</h2>
                <p>Cash flow comparison for the selected month.</p>
              </div>
            </div>
            <div className="chart-frame">
              {chartsLoading ? (
                <ChartEmptyState>Loading chart...</ChartEmptyState>
              ) : !hasIncomeExpenseData ? (
                <ChartEmptyState>Add income or expenses to compare cash flow.</ChartEmptyState>
              ) : (
                <ResponsiveContainer width="100%" height={260}>
                  <BarChart data={incomeExpenseData}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                    <YAxis tick={{ fontSize: 12 }} />
                    <Tooltip formatter={currencyTooltip} />
                    <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                      {incomeExpenseData.map((entry, index) => (
                        <Cell key={entry.name} fill={index === 0 ? '#00a36c' : '#d92d20'} />
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
                <h2>Monthly Spending Line Chart</h2>
                <p>Expense trend across {selectedYear}.</p>
              </div>
            </div>
            <div className="chart-frame">
              {chartsLoading ? (
                <ChartEmptyState>Loading chart...</ChartEmptyState>
              ) : !hasMonthlySpendingData ? (
                <ChartEmptyState>Add expenses across months to see a trend.</ChartEmptyState>
              ) : (
                <ResponsiveContainer width="100%" height={260}>
                  <LineChart data={charts.monthly_spending}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="month" tick={{ fontSize: 12 }} />
                    <YAxis tick={{ fontSize: 12 }} />
                    <Tooltip formatter={currencyTooltip} />
                    <Line type="monotone" dataKey="expenses" stroke="#0073ea" strokeWidth={3} dot={{ r: 3 }} />
                  </LineChart>
                </ResponsiveContainer>
              )}
            </div>
          </div>

          <div className="chart-panel chart-panel-wide">
            <div className="section-heading">
              <div>
                <h2>Top Merchants Chart</h2>
                <p>Highest expense merchants in {selectedMonthLabel} {summary.year}.</p>
              </div>
            </div>
            <div className="chart-frame">
              {chartsLoading ? (
                <ChartEmptyState>Loading chart...</ChartEmptyState>
              ) : charts.top_merchants.length === 0 ? (
                <ChartEmptyState>Add merchant names to see top spending destinations.</ChartEmptyState>
              ) : (
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={charts.top_merchants} layout="vertical" margin={{ left: 24 }}>
                    <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                    <XAxis type="number" tick={{ fontSize: 12 }} />
                    <YAxis dataKey="name" type="category" tick={{ fontSize: 12 }} width={130} />
                    <Tooltip formatter={currencyTooltip} />
                    <Bar dataKey="value" fill="#00a36c" radius={[0, 6, 6, 0]} />
                  </BarChart>
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
