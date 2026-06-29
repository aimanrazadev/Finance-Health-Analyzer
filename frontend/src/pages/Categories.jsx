import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  CalendarDays,
  ChartNoAxesCombined,
  ChevronLeft,
  ChevronRight,
  CircleHelp,
  FileText,
  MoreVertical,
  Search,
} from 'lucide-react';
import { Line, LineChart, ResponsiveContainer } from 'recharts';
import { useSearchParams } from 'react-router-dom';
import AppSelect from '../components/AppSelect';
import Navigation from '../components/Navigation';
import { useAuth } from '../hooks/useAuth';
import api, { getAuthHeaders } from '../utils/api';
import '../styles/NeedsReview.css';

const PAGE_SIZE = 10;

const confidenceValue = (value) => Math.max(0, Math.min(1, Number(value ?? 0.3)));
const confidencePercent = (value) => `${Math.round(confidenceValue(value) * 100)}%`;

const formatMoney = (value) => new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
}).format(Number(value || 0));

const formatDate = (value) => {
  if (!value) return '-';
  const date = new Date(`${String(value).slice(0, 10)}T00:00:00`);
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleDateString('en-GB');
};

const merchantName = (transaction) => (
  transaction.extracted_merchant || transaction.merchant || 'Unknown merchant'
);

const categoryName = (transaction) => {
  const name = transaction.suggested_category_name || transaction.category_name || 'Others';
  return name === 'Uncategorized' ? 'Others' : name;
};

const Categories = () => {
  const [searchParams] = useSearchParams();
  const { token } = useAuth();
  const [transactions, setTransactions] = useState([]);
  const [categories, setCategories] = useState([]);
  const [selectedCategories, setSelectedCategories] = useState({});
  const [bulkCategoryId, setBulkCategoryId] = useState('');
  const [searchTerm, setSearchTerm] = useState(() => searchParams.get('search') || '');
  const [includeLearned, setIncludeLearned] = useState(false);
  const [sortBy, setSortBy] = useState('newest');
  const [page, setPage] = useState(1);
  const [openMenuId, setOpenMenuId] = useState(null);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  const headers = useMemo(() => getAuthHeaders(token), [token]);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [categoryQueueResponse, categoriesResponse] = await Promise.all([
        api.get('/categories/needs-review', {
          headers,
          params: { include_learned: includeLearned },
        }),
        api.get('/categories'),
      ]);
      setTransactions(categoryQueueResponse.data);
      setCategories(categoriesResponse.data);
    } catch (err) {
      console.error(err);
      setError('Unable to load category queue.');
    } finally {
      setLoading(false);
    }
  }, [headers, includeLearned]);

  useEffect(() => {
    if (token) queueMicrotask(loadData);
  }, [loadData, token]);

  const normalizedSearch = searchTerm.trim().toLowerCase();
  const filteredTransactions = useMemo(() => transactions.filter((transaction) => {
    if (!normalizedSearch) return true;
    return [
      transaction.description,
      merchantName(transaction),
      transaction.transaction_type,
      transaction.amount,
      categoryName(transaction),
    ]
      .filter(Boolean)
      .some((value) => String(value).toLowerCase().includes(normalizedSearch));
  }), [normalizedSearch, transactions]);

  const sortedTransactions = useMemo(() => [...filteredTransactions].sort((left, right) => {
    if (sortBy === 'oldest') return new Date(left.date) - new Date(right.date);
    if (sortBy === 'confidence-low') return confidenceValue(left.category_confidence) - confidenceValue(right.category_confidence);
    if (sortBy === 'confidence-high') return confidenceValue(right.category_confidence) - confidenceValue(left.category_confidence);
    if (sortBy === 'amount-high') return Number(right.amount || 0) - Number(left.amount || 0);
    return new Date(right.date) - new Date(left.date);
  }), [filteredTransactions, sortBy]);

  const pageCount = Math.max(1, Math.ceil(sortedTransactions.length / PAGE_SIZE));
  const currentPage = Math.min(page, pageCount);
  const pageStart = (currentPage - 1) * PAGE_SIZE;
  const visibleTransactions = sortedTransactions.slice(pageStart, pageStart + PAGE_SIZE);

  const averageConfidence = useMemo(() => {
    if (!transactions.length) return 0;
    const total = transactions.reduce((sum, transaction) => sum + confidenceValue(transaction.category_confidence), 0);
    return Math.round((total / transactions.length) * 100);
  }, [transactions]);

  const confidenceTrend = useMemo(() => {
    const points = [...transactions]
      .sort((left, right) => new Date(left.date) - new Date(right.date))
      .slice(-12)
      .map((transaction, index) => ({ index, confidence: Math.round(confidenceValue(transaction.category_confidence) * 100) }));
    return points.length > 1 ? points : [{ index: 0, confidence: averageConfidence }, { index: 1, confidence: averageConfidence }];
  }, [averageConfidence, transactions]);

  const selectedCount = Object.values(selectedCategories).filter(Boolean).length;

  const selectCategory = (transactionId, categoryId) => {
    setSelectedCategories((current) => ({ ...current, [transactionId]: categoryId }));
    setError('');
  };

  const saveCorrection = async (transactionId) => {
    const selectedCategoryId = selectedCategories[transactionId];
    if (!selectedCategoryId) {
      setError('Select a category before saving.');
      return;
    }

    try {
      const response = await api.post('/categories/correct', {
        transaction_id: transactionId,
        new_category_id: Number(selectedCategoryId),
      }, { headers });
      setMessage(response.data.message);
      setSelectedCategories((current) => {
        const next = { ...current };
        delete next[transactionId];
        return next;
      });
      await loadData();
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || 'Unable to save category correction.');
    }
  };

  const applyBulkCategory = () => {
    if (!bulkCategoryId) {
      setError('Select a bulk category first.');
      return;
    }
    setSelectedCategories((current) => {
      const next = { ...current };
      filteredTransactions.forEach((transaction) => {
        next[transaction.id] = bulkCategoryId;
      });
      return next;
    });
    setError('');
  };

  const saveBulkCorrections = async () => {
    const entries = Object.entries(selectedCategories).filter(([, selectedCategoryId]) => selectedCategoryId);
    if (!entries.length) {
      setError('Select at least one category correction before saving.');
      return;
    }

    try {
      const response = await api.post('/categories/bulk-correct', {
        corrections: entries.map(([transactionId, selectedCategoryId]) => ({
          transaction_id: Number(transactionId),
          new_category_id: Number(selectedCategoryId),
        })),
      }, { headers });
      setMessage(response.data.message || `${entries.length} category corrections saved.`);
      setSelectedCategories({});
      setBulkCategoryId('');
      await loadData();
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || 'Unable to save category corrections.');
    }
  };

  return (
    <div>
      <Navigation />
      <main className="categories-review-page">
        <header className="categories-review-heading">
          <h1>Review Categories</h1>
          <p>Review low-confidence transactions and teach the system better category rules.</p>
        </header>

        <section className="categories-review-summary" aria-label="Category review summary">
          <article className="categories-dashboard-card categories-stat-card">
            <span className="categories-icon-box"><FileText /></span>
            <div>
              <p>Low-confidence transactions</p>
              <strong>{transactions.length}</strong>
              <span>Out of {transactions.length} total</span>
            </div>
          </article>

          <article className="categories-dashboard-card categories-stat-card categories-confidence-card">
            <span className="categories-icon-box"><ChartNoAxesCombined /></span>
            <div>
              <p>Avg. confidence</p>
              <strong>{averageConfidence}%</strong>
              <span>Across all transactions</span>
            </div>
            <div className="categories-confidence-chart" aria-hidden="true">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={confidenceTrend}>
                  <Line type="monotone" dataKey="confidence" stroke="var(--categories-accent)" strokeWidth={2.5} dot={false} isAnimationActive />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </article>
        </section>

        {message && <div className="categories-surface-message success">{message}</div>}
        {error && <div className="categories-surface-message error">{error}</div>}

        <section className="categories-dashboard-card categories-review-toolbar" aria-label="Category review controls">
          <label className="categories-search-control">
            <Search aria-hidden="true" />
            <input
              type="search"
              value={searchTerm}
              onChange={(event) => { setSearchTerm(event.target.value); setPage(1); }}
              placeholder="Search by description or merchant..."
              aria-label="Search transactions"
            />
          </label>

          <label className="categories-learned-toggle">
            <input
              type="checkbox"
              checked={includeLearned}
              onChange={(event) => { setIncludeLearned(event.target.checked); setPage(1); }}
            />
            <span>Include learned transactions</span>
            <CircleHelp aria-hidden="true" title="Show transactions that already have learned category rules" />
          </label>

          <AppSelect
            className="categories-bulk-select"
            value={bulkCategoryId}
            onChange={setBulkCategoryId}
            ariaLabel="Bulk category"
            options={[
              { value: '', label: 'Bulk category' },
              ...categories.map((category) => ({ value: category.id, label: category.name })),
            ]}
          />
          <button className="categories-secondary-action plain-button" onClick={applyBulkCategory}>Assign</button>
          <button className="categories-primary-action" onClick={saveBulkCorrections}>Save All{selectedCount ? ` (${selectedCount})` : ''}</button>
        </section>

        <section className={`categories-dashboard-card categories-review-table-card ${openMenuId ? 'menu-open' : ''}`}>
          <header className="categories-table-toolbar">
            <p>
              {sortedTransactions.length
                ? `Showing ${pageStart + 1} to ${Math.min(pageStart + PAGE_SIZE, sortedTransactions.length)} of ${sortedTransactions.length} transactions`
                : 'No transactions to show'}
            </p>
            <label>
              <span>Sort by:</span>
              <AppSelect
                value={sortBy}
                onChange={(nextValue) => { setSortBy(nextValue); setPage(1); }}
                ariaLabel="Sort category review transactions"
                options={[
                  { value: 'newest', label: 'Newest' },
                  { value: 'oldest', label: 'Oldest' },
                  { value: 'confidence-low', label: 'Lowest confidence' },
                  { value: 'confidence-high', label: 'Highest confidence' },
                  { value: 'amount-high', label: 'Highest amount' },
                ]}
              />
            </label>
          </header>

          <div className="categories-table-scroll">
            <table className="categories-review-table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Amount</th>
                  <th>Description &amp; Merchant</th>
                  <th>Confidence</th>
                  <th>Category</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {loading && (
                  <tr><td colSpan="6" className="categories-table-state">Loading category queue...</td></tr>
                )}
                {!loading && !visibleTransactions.length && (
                  <tr><td colSpan="6" className="categories-table-state">{transactions.length ? 'No matching transactions found.' : 'No transactions need category review.'}</td></tr>
                )}
                {!loading && visibleTransactions.map((transaction) => {
                  const confidence = confidencePercent(transaction.category_confidence);
                  const transactionType = String(transaction.transaction_type || 'expense').toLowerCase();
                  return (
                    <tr key={transaction.id}>
                      <td>
                        <div className="categories-date-cell">
                          <span className="categories-calendar-icon"><CalendarDays /></span>
                          <div>
                            <strong>{formatDate(transaction.date)}</strong>
                            <em className={transactionType}>{transactionType}</em>
                          </div>
                        </div>
                      </td>
                      <td className="categories-amount-cell">{formatMoney(transaction.amount)}</td>
                      <td>
                        <div className="categories-description-cell">
                          <strong>{transaction.description || 'Bank transaction'}</strong>
                          <span>
                            Merchant: {merchantName(transaction)}
                            <i>•</i>
                            <b>Needs Review</b>
                          </span>
                        </div>
                      </td>
                      <td><span className="categories-confidence-pill">{confidence}</span></td>
                      <td>
                        <AppSelect
                          value={selectedCategories[transaction.id] || ''}
                          onChange={(nextValue) => selectCategory(transaction.id, nextValue)}
                          ariaLabel={`Category for ${transaction.description || 'transaction'}`}
                          options={[
                            { value: '', label: 'Select category' },
                            ...categories.map((category) => ({ value: category.id, label: category.name })),
                          ]}
                        />
                      </td>
                      <td>
                        <div className="categories-row-actions">
                          <button className="categories-primary-action categories-row-save" onClick={() => saveCorrection(transaction.id)}>Save</button>
                          <button
                            className="categories-menu-button plain-button"
                            onClick={() => setOpenMenuId((current) => current === transaction.id ? null : transaction.id)}
                            aria-label={`More actions for ${transaction.description || 'transaction'}`}
                            aria-expanded={openMenuId === transaction.id}
                          >
                            <MoreVertical aria-hidden="true" />
                          </button>
                          {openMenuId === transaction.id && (
                            <div className="categories-row-menu">
                              {transaction.suggested_category_id && (
                                <button className="plain-button" onClick={() => { selectCategory(transaction.id, String(transaction.suggested_category_id)); setOpenMenuId(null); }}>
                                  Use suggested category
                                </button>
                              )}
                              <button className="plain-button" onClick={() => { selectCategory(transaction.id, ''); setOpenMenuId(null); }}>Clear selection</button>
                            </div>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {pageCount > 1 && (
            <footer className="categories-pagination">
              <button className="plain-button" onClick={() => setPage((current) => Math.max(1, current - 1))} disabled={currentPage === 1} aria-label="Previous page"><ChevronLeft /></button>
              <span>Page {currentPage} of {pageCount}</span>
              <button className="plain-button" onClick={() => setPage((current) => Math.min(pageCount, current + 1))} disabled={currentPage === pageCount} aria-label="Next page"><ChevronRight /></button>
            </footer>
          )}
        </section>
      </main>
    </div>
  );
};

export default Categories;
