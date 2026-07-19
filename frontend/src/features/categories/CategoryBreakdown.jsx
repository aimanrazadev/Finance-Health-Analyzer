import { useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import {
  Bar,
  BarChart,
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
import useAuth from '../auth/useAuth';
import api, { getAuthHeaders } from '../../shared/services/apiClient';
import { getCategoryChartColor } from '../../utils/categoryDisplay';
import { getPeriodSelection, savePeriodSelection } from '../../utils/periodSession';
import './CategoryBreakdown.css';

const now = new Date();

const monthNames = [
  'All',
  'January',
  'February',
  'March',
  'April',
  'May',
  'June',
  'July',
  'August',
  'September',
  'October',
  'November',
  'December',
];

const moneyFormatter = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const formatMoney = (value) => moneyFormatter.format(Number(value || 0));

const compactMoneyFormatter = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  notation: 'compact',
  maximumFractionDigits: 1,
});

const formatCompactMoney = (value) => compactMoneyFormatter.format(Number(value || 0));

const parsePeriod = (searchParams) => {
  const monthParam = searchParams.get('month');
  const yearParam = searchParams.get('year');
  const savedPeriod = getPeriodSelection();
  const month = monthParam === null ? savedPeriod.month : Number(monthParam);
  const year = yearParam === null ? savedPeriod.year : Number(yearParam);
  if (month >= 1 && month <= 12 && Number.isFinite(year)) savePeriodSelection(month, year);
  return {
    month: Number.isFinite(month) ? month : now.getMonth() + 1,
    year: Number.isFinite(year) ? year : now.getFullYear(),
  };
};

const CategoryBreakdown = () => {
  const { token } = useAuth();
  const [searchParams] = useSearchParams();
  const [{ month, year }] = useState(() => parsePeriod(searchParams));
  const [breakdown, setBreakdown] = useState({ total_expenses: 0, categories: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const periodLabel = useMemo(() => {
    if (month === -1) return 'all transaction data';
    if (month === 0) return `all of ${year}`;
    return `${monthNames[month] || 'This month'} ${year}`;
  }, [month, year]);

  useEffect(() => {
    let cancelled = false;

    const loadBreakdown = async () => {
      setLoading(true);
      setError('');
      try {
        const params = month === -1 ? { month: -1 } : { month, year };
        const response = await api.get('/dashboard/category-merchants', {
          headers: getAuthHeaders(token),
          params,
        });
        if (!cancelled) setBreakdown(response.data);
      } catch (err) {
        console.error(err);
        if (!cancelled) {
          setBreakdown({ total_expenses: 0, categories: [] });
          setError('Unable to load category merchant breakdown.');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    if (token) loadBreakdown();

    return () => {
      cancelled = true;
    };
  }, [token, month, year]);

  const categories = breakdown.categories || [];
  const totalExpenses = Number(breakdown.total_expenses || 0);
  const categoryChartData = categories.map((category, index) => ({
    name: category.category_name,
    value: Number(category.total || 0),
    color: category.color || getCategoryChartColor(category.category_name, index),
  }));

  return (
    <>
      <Navigation />
      <main className="category-breakdown-page">
        <header className="category-breakdown-header">
          <div>
            <p className="eyebrow">Category merchant analysis</p>
            <h1>Spending by Category</h1>
          </div>
          <Link className="category-breakdown-back" to="/dashboard" aria-label="Back to dashboard" title="Back to dashboard">
            <ArrowLeft aria-hidden="true" />
          </Link>
        </header>

        {error && <div className="surface-message error">{error}</div>}

        <section className="category-breakdown-summary category-summary-card">
          <div className="category-summary-copy">
            <span>Total Expenses</span>
            <strong>{formatMoney(totalExpenses)}</strong>
            <em>{categories.length} categories in {periodLabel}</em>
          </div>
          {categories.length > 0 && (
            <div className="category-summary-chart">
              <div className="summary-donut">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={categoryChartData}
                      dataKey="value"
                      nameKey="name"
                      innerRadius="66%"
                      outerRadius="88%"
                      paddingAngle={0}
                      stroke="none"
                      strokeWidth={0}
                      isAnimationActive={false}
                    >
                      {categoryChartData.map((entry) => (
                        <Cell key={entry.name} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip
                      formatter={(value) => formatMoney(value)}
                      contentStyle={{
                        border: '1px solid rgba(255,255,255,0.08)',
                        borderRadius: 14,
                        background: 'oklch(.14 0 0)',
                        color: 'oklch(.96 0 0)',
                      }}
                    />
                  </PieChart>
                </ResponsiveContainer>
                <div className="summary-donut-center">
                  <strong>{formatCompactMoney(totalExpenses)}</strong>
                  <span>Total</span>
                </div>
              </div>
              <div className="summary-category-list">
                {categoryChartData.map((category) => (
                  <div className="summary-category-row" key={category.name}>
                    <span className="category-breakdown-dot" style={{ background: category.color }} />
                    <span>{category.name}</span>
                    <strong>{formatCompactMoney(category.value)}</strong>
                  </div>
                ))}
              </div>
            </div>
          )}
        </section>

        <section className="category-breakdown-list">
          {loading ? (
            <div className="chart-empty-state">Loading category merchant breakdown...</div>
          ) : categories.length === 0 ? (
            <div className="chart-empty-state">No category spending found for this period.</div>
          ) : categories.map((category, index) => {
            const categoryColor = category.color || getCategoryChartColor(category.category_name, index);
            return (
              <article className="category-breakdown-card" key={`${category.category_id || 'uncategorized'}-${category.category_name}`}>
                <div className="category-breakdown-card-header">
                  <div>
                    <span className="category-breakdown-dot" style={{ background: categoryColor }} />
                    <div>
                      <h2>{category.category_name}</h2>
                      <p>{category.transaction_count} transactions · {category.percentage.toFixed(1)}% of spending</p>
                    </div>
                  </div>
                  <strong>{formatMoney(category.total)}</strong>
                </div>

                <div className="merchant-chart-module">
                  {category.merchants.length === 0 ? (
                    <div className="chart-empty-state small">No merchants found in this category.</div>
                  ) : (
                    <div className="merchant-chart-frame" style={{ '--category-glow': categoryColor }}>
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart
                            data={category.merchants.map((merchant) => ({
                              merchant: merchant.merchant_name,
                              shortMerchant: merchant.merchant_name.length > 14
                                ? `${merchant.merchant_name.slice(0, 13)}...`
                                : merchant.merchant_name,
                              total: Number(merchant.total_spent || 0),
                              transactions: Number(merchant.transaction_count || 0),
                              percentage: Number(merchant.percentage || 0),
                            }))}
                            margin={{ top: 18, right: 14, left: 4, bottom: 10 }}
                          >
                            <defs>
                              <linearGradient id={`barGradient-${category.category_id || index}`} x1="0" x2="0" y1="0" y2="1">
                                <stop offset="0%" stopColor={categoryColor} stopOpacity={1} />
                                <stop offset="12%" stopColor={categoryColor} stopOpacity={0.92} />
                                <stop offset="100%" stopColor={categoryColor} stopOpacity={0.55} />
                              </linearGradient>
                            </defs>
                            <CartesianGrid stroke="rgba(255,255,255,0.08)" vertical={false} />
                            <XAxis
                              dataKey="shortMerchant"
                              tick={false}
                              axisLine={false}
                              tickLine={false}
                            />
                            <YAxis
                              tick={{ fill: 'oklch(.76 0 0)', fontSize: 11 }}
                              axisLine={{ stroke: 'rgba(255,255,255,0.18)' }}
                              tickLine={false}
                              width={66}
                              tickFormatter={(value) => formatCompactMoney(value)}
                            />
                            <Tooltip
                              formatter={(value, name, props) => [
                                formatMoney(value),
                                `${props.payload.transactions} txn${props.payload.transactions === 1 ? '' : 's'} · ${props.payload.percentage.toFixed(1)}%`,
                              ]}
                              labelFormatter={(_label, payload) => payload?.[0]?.payload?.merchant || ''}
                              contentStyle={{
                                border: '1px solid rgba(255,255,255,0.08)',
                                borderRadius: 14,
                                background: 'oklch(.14 0 0)',
                                color: 'oklch(.96 0 0)',
                              }}
                              cursor={{ fill: 'rgba(255,255,255,0.035)' }}
                            />
                            <Bar dataKey="total" radius={[12, 12, 4, 4]} fill={`url(#barGradient-${category.category_id || index})`} isAnimationActive={false}>
                              {category.merchants.map((merchant) => (
                                <Cell key={merchant.merchant_name} fill={`url(#barGradient-${category.category_id || index})`} />
                              ))}
                            </Bar>
                          </BarChart>
                        </ResponsiveContainer>
                    </div>
                  )}
                </div>
              </article>
            );
          })}
        </section>
      </main>
    </>
  );
};

export default CategoryBreakdown;
