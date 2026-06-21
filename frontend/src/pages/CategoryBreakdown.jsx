import { useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import Navigation from '../components/Navigation';
import { useAuth } from '../hooks/useAuth';
import api, { getAuthHeaders } from '../utils/api';
import { getCategoryChartColor } from '../utils/categoryDisplay';

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
  maximumFractionDigits: 0,
});

const formatMoney = (value) => moneyFormatter.format(Number(value || 0));

const parsePeriod = (searchParams) => {
  const monthParam = searchParams.get('month');
  const yearParam = searchParams.get('year');
  const month = monthParam === null ? now.getMonth() + 1 : Number(monthParam);
  const year = yearParam === null ? now.getFullYear() : Number(yearParam);
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
    if (month === -1) return 'all uploaded data';
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

  return (
    <div>
      <Navigation />
      <main className="category-breakdown-page">
        <header className="category-breakdown-header">
          <div>
            <p className="eyebrow">Category merchant analysis</p>
            <h1>Spending by Category</h1>
            <p>Top vendors and merchants inside each category for {periodLabel}.</p>
          </div>
          <Link className="category-breakdown-back" to="/dashboard">Dashboard</Link>
        </header>

        {error && <div className="surface-message error">{error}</div>}

        <section className="category-breakdown-summary">
          <span>Total Expenses</span>
          <strong>{formatMoney(breakdown.total_expenses)}</strong>
          <em>{categories.length} categories</em>
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

                <div className="merchant-bar-list">
                  {category.merchants.length === 0 ? (
                    <div className="chart-empty-state small">No merchants found in this category.</div>
                  ) : category.merchants.map((merchant) => (
                    <div className="merchant-bar-row" key={`${category.category_name}-${merchant.merchant_name}`}>
                      <div className="merchant-bar-meta">
                        <span>{merchant.merchant_name}</span>
                        <em>{merchant.transaction_count} txn{merchant.transaction_count === 1 ? '' : 's'}</em>
                      </div>
                      <div className="merchant-bar-track" aria-hidden="true">
                        <span style={{ width: `${Math.max(merchant.percentage, 2)}%`, background: categoryColor }} />
                      </div>
                      <strong>{formatMoney(merchant.total_spent)}</strong>
                      <em>{merchant.percentage.toFixed(1)}%</em>
                    </div>
                  ))}
                </div>
              </article>
            );
          })}
        </section>
      </main>
    </div>
  );
};

export default CategoryBreakdown;
