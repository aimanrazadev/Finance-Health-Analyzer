import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  CalendarDays,
  ChevronLeft,
  ChevronRight,
  IndianRupee,
  MoreVertical,
  Pencil,
  ReceiptIndianRupee,
  Search,
  Sparkles,
  Tag,
  UserRound,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/authContext';
import AppSelect from '../../components/ui/AppSelect';
import CategoryBadge from '../../components/ui/CategoryBadge';
import Navigation from '../../components/layout/Navigation';
import Skeleton from '../../components/ui/Skeleton';
import { useUI } from '../../shared/context/UIContext';
import api, { getAuthHeaders } from '../../shared/services/apiClient';
import './Transactions.css';

const createDefaultFormState = () => ({
  amount: '',
  category_id: '',
  description: '',
  merchant: '',
  transaction_type: 'expense',
  date: new Date().toISOString().slice(0, 16),
});

const formatDateLocal = (isoString) => {
  if (!isoString) return '';
  const date = new Date(isoString);
  const offset = date.getTimezoneOffset();
  return new Date(date.getTime() - offset * 60000).toISOString().slice(0, 16);
};

const formatTransactionDate = (value) => {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value || '-');
  return date.toLocaleDateString('en-GB');
};

const formatAmount = (value) => new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
}).format(Number(value || 0));

const Transactions = () => {
  const navigate = useNavigate();
  const { token } = useAuth();
  const { confirm, showToast } = useUI();
  const [transactions, setTransactions] = useState([]);
  const [categories, setCategories] = useState([]);
  const [formData, setFormData] = useState(createDefaultFormState);
  const [editingId, setEditingId] = useState(null);
  const [search, setSearch] = useState('');
  const [filterType, setFilterType] = useState('');
  const [filterCategory, setFilterCategory] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(true);
  const [corrections, setCorrections] = useState({});
  const [openMenuId, setOpenMenuId] = useState(null);
  const [page, setPage] = useState(1);
  const [rowsPerPage, setRowsPerPage] = useState(10);

  const authHeaders = useMemo(() => getAuthHeaders(token), [token]);

  const loadTransactions = useCallback(async () => {
    setLoading(true);
    setError('');

    try {
      const params = {};
      if (search) params.search = search;
      if (filterType) params.transaction_type = filterType;
      if (filterCategory) params.category_id = filterCategory;

      const response = await api.get('/transactions', { headers: authHeaders, params });
      setTransactions(response.data);
    } catch (err) {
      console.error(err);
      setError('Unable to load transactions.');
    } finally {
      setLoading(false);
    }
  }, [authHeaders, filterCategory, filterType, search]);

  useEffect(() => {
    const loadInitialCategories = async () => {
      try {
        const response = await api.get('/categories');
        setCategories(response.data);
      } catch (err) {
        console.error(err);
      }
    };

    loadInitialCategories();
  }, []);

  useEffect(() => {
    if (token) queueMicrotask(loadTransactions);
  }, [loadTransactions, token]);

  const resetForm = () => {
    setFormData(createDefaultFormState());
    setEditingId(null);
    setError('');
  };

  const handleChange = (event) => {
    const { name, value } = event.target;
    setFormData((current) => ({ ...current, [name]: value }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    setSuccess('');

    const payload = {
      amount: parseFloat(formData.amount),
      category_id: formData.category_id ? Number(formData.category_id) : null,
      description: formData.description,
      merchant: formData.merchant || null,
      transaction_type: formData.transaction_type,
      date: new Date(formData.date).toISOString(),
    };

    try {
      const feedback = editingId ? 'Transaction updated.' : 'Transaction added.';
      if (editingId) {
        await api.put(`/transactions/${editingId}`, payload, { headers: authHeaders });
      } else {
        await api.post('/transactions', payload, { headers: authHeaders });
      }
      resetForm();
      setSuccess(feedback);
      showToast(feedback);
      await loadTransactions();
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || 'Failed to save transaction.');
    }
  };

  const handleEdit = (transaction) => {
    const category = getTransactionCategory(transaction);
    const isUncategorized = !transaction.category_id
      || String(category?.name || '').trim().toLowerCase() === 'uncategorized';

    if (isUncategorized) {
      resetForm();
      setOpenMenuId(null);
      navigate(`/categories?search=${encodeURIComponent(transaction.description || '')}`);
      return;
    }

    setEditingId(transaction.id);
    setFormData({
      amount: transaction.amount.toString(),
      category_id: transaction.category_id || '',
      description: transaction.description,
      merchant: transaction.merchant || '',
      transaction_type: transaction.transaction_type || 'expense',
      date: formatDateLocal(transaction.date),
    });
    setOpenMenuId(null);
    setSuccess('');
    setError('');
  };

  const handleDelete = async (id) => {
    setOpenMenuId(null);
    const confirmed = await confirm({
      title: 'Delete transaction',
      message: 'This transaction will be removed from your account.',
      confirmLabel: 'Delete',
      danger: true,
    });
    if (!confirmed) return;

    try {
      await api.delete(`/transactions/${id}`, { headers: authHeaders });
      setSuccess('Transaction deleted.');
      showToast('Transaction deleted.');
      await loadTransactions();
    } catch (err) {
      console.error(err);
      setError('Unable to delete transaction.');
    }
  };

  const handleCorrectionChange = (transactionId, categoryId) => {
    setCorrections((current) => ({ ...current, [transactionId]: categoryId }));
  };

  const handleSaveCorrection = async (transactionId) => {
    const newCategoryId = corrections[transactionId];
    if (!newCategoryId) {
      setError('Select a category before saving the correction.');
      return;
    }

    try {
      const response = await api.post('/categories/correct', {
        transaction_id: transactionId,
        new_category_id: Number(newCategoryId),
      }, { headers: authHeaders });
      const feedback = response.data.message || 'Category updated. Learning rule saved.';
      setSuccess(feedback);
      showToast(feedback);
      setCorrections((current) => {
        const next = { ...current };
        delete next[transactionId];
        return next;
      });
      setOpenMenuId(null);
      await loadTransactions();
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || 'Unable to save category correction.');
    }
  };

  const getTransactionCategory = (transaction) => (
    categories.find((category) => Number(category.id) === Number(transaction.category_id))
  );

  const mlLearnedCount = transactions.filter((transaction) => (
    transaction.categorization_method === 'ml_model'
    && (transaction.category_confidence ?? 0) >= 0.8
  )).length;

  const pageCount = Math.max(1, Math.ceil(transactions.length / rowsPerPage));
  const currentPage = Math.min(page, pageCount);
  const pageStart = (currentPage - 1) * rowsPerPage;
  const visibleTransactions = transactions.slice(pageStart, pageStart + rowsPerPage);

  const paginationItems = useMemo(() => {
    if (pageCount <= 5) return Array.from({ length: pageCount }, (_, index) => index + 1);
    if (currentPage <= 3) return [1, 2, 3, 'ellipsis-end', pageCount];
    if (currentPage >= pageCount - 2) return [1, 'ellipsis-start', pageCount - 2, pageCount - 1, pageCount];
    return [1, 'ellipsis-start', currentPage - 1, currentPage, currentPage + 1, 'ellipsis-end', pageCount];
  }, [currentPage, pageCount]);

  return (
    <div>
      <Navigation />
      <main className="transactions-page">
        <div className="transactions-layout">
          <aside className="transaction-form-card">
            <header>
              <h2>{editingId ? 'Edit Manual Transaction' : 'Add Manual Transaction'}</h2>
              <p>{editingId ? 'Update this transaction in your account.' : 'Add a new transaction to your account.'}</p>
            </header>

            {error && <div className="transaction-message error">{error}</div>}
            {success && <div className="transaction-message success">{success}</div>}

            <form className="transaction-form" onSubmit={handleSubmit}>
              <label>
                <span>Amount</span>
                <div className="transaction-input-shell">
                  <IndianRupee aria-hidden="true" />
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    name="amount"
                    value={formData.amount}
                    onChange={handleChange}
                    placeholder="0.00"
                    required
                  />
                </div>
              </label>

              <label>
                <span>Date and Time</span>
                <div className="transaction-input-shell">
                  <CalendarDays aria-hidden="true" />
                  <input type="datetime-local" name="date" value={formData.date} onChange={handleChange} required />
                </div>
              </label>

              <label>
                <span>Description</span>
                <div className="transaction-input-shell">
                  <Pencil aria-hidden="true" />
                  <input
                    type="text"
                    name="description"
                    value={formData.description}
                    onChange={handleChange}
                    placeholder="Enter description"
                    required
                  />
                </div>
              </label>

              <label>
                <span>Merchant</span>
                <div className="transaction-input-shell">
                  <UserRound aria-hidden="true" />
                  <input
                    type="text"
                    name="merchant"
                    value={formData.merchant}
                    onChange={handleChange}
                    placeholder="Enter merchant name"
                  />
                </div>
              </label>

              <label>
                <span>Transaction Type</span>
                <div className="transaction-input-shell">
                  <ReceiptIndianRupee aria-hidden="true" />
                  <AppSelect
                    className="app-select--embedded"
                    name="transaction_type"
                    value={formData.transaction_type}
                    onChange={(nextValue) => setFormData((current) => ({ ...current, transaction_type: nextValue }))}
                    ariaLabel="Transaction type"
                    options={[{ value: 'expense', label: 'Expense' }, { value: 'income', label: 'Income' }]}
                  />
                </div>
              </label>

              <label>
                <span>Category</span>
                <div className="transaction-input-shell">
                  <Tag aria-hidden="true" />
                  <AppSelect
                    className="app-select--embedded"
                    name="category_id"
                    value={formData.category_id}
                    onChange={(nextValue) => setFormData((current) => ({ ...current, category_id: nextValue }))}
                    ariaLabel="Transaction category"
                    options={[
                      { value: '', label: 'Select category' },
                      ...categories.map((category) => ({ value: category.id, label: category.name })),
                    ]}
                  />
                </div>
              </label>

              <div className="transaction-form-actions">
                <button type="submit" className="transaction-submit-button">
                  {editingId ? 'Update Transaction' : 'Add Transaction'}
                </button>
                {editingId && (
                  <button type="button" className="transaction-cancel-button plain-button" onClick={resetForm}>Cancel</button>
                )}
              </div>
            </form>
          </aside>

          <section className="transactions-content">
            <header className="transactions-header">
              <h1>Transactions</h1>
              <p>View, search and manage all your transactions.</p>
            </header>

            {mlLearnedCount > 0 && (
              <div className="transactions-learning-banner">
                <Sparkles aria-hidden="true" />
                <p>
                  ML has successfully learned {mlLearnedCount} transaction pattern{mlLearnedCount === 1 ? '' : 's'}.
                  Confident ML categories are locked here; use Categories with Include learned to change them later.
                </p>
              </div>
            )}

            <section className="transaction-filters" aria-label="Transaction filters">
              <label className="transaction-search-control">
                <Search aria-hidden="true" />
                <input
                  type="search"
                  placeholder="Search description or merchant"
                  value={search}
                  onChange={(event) => { setSearch(event.target.value); setPage(1); }}
                  aria-label="Search transactions"
                />
              </label>
              <AppSelect
                value={filterType}
                onChange={(nextValue) => { setFilterType(nextValue); setPage(1); }}
                ariaLabel="Transaction type filter"
                options={[
                  { value: '', label: 'All types' },
                  { value: 'expense', label: 'Expense' },
                  { value: 'income', label: 'Income' },
                ]}
              />
              <AppSelect
                value={filterCategory}
                onChange={(nextValue) => { setFilterCategory(nextValue); setPage(1); }}
                ariaLabel="Category filter"
                options={[
                  { value: '', label: 'All categories' },
                  ...categories.map((category) => ({ value: category.id, label: category.name })),
                ]}
              />
            </section>

            <section className={`transaction-ledger-card ${openMenuId ? 'menu-open' : ''}`}>
              <div className="transaction-table-wrapper">
                <table className="transaction-table">
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Description</th>
                      <th>Type</th>
                      <th>Category</th>
                      <th>Amount</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {loading && (
                      <tr><td colSpan="6" className="transaction-table-state"><Skeleton rows={4} /></td></tr>
                    )}
                    {!loading && transactions.length === 0 && (
                      <tr><td colSpan="6" className="transaction-table-state">No transactions found.</td></tr>
                    )}
                    {!loading && visibleTransactions.map((transaction) => {
                      const category = getTransactionCategory(transaction);
                      const displayType = transaction.transaction_type || 'expense';
                      const formattedDate = formatTransactionDate(transaction.date);
                      const needsReview = (transaction.category_confidence ?? 0) < 0.8
                        || transaction.review_status === 'needs_review'
                        || transaction.is_needs_review;
                      return (
                        <tr key={transaction.id}>
                          <td>
                            <div className="transaction-date-cell">
                              <span><CalendarDays aria-hidden="true" /></span>
                              <strong>{formattedDate}</strong>
                            </div>
                          </td>
                          <td className="transaction-description-cell" title={transaction.description}>{transaction.description}</td>
                          <td className="transaction-type-cell">{displayType}</td>
                          <td><CategoryBadge category={category} name={category?.name || 'Uncategorized'} /></td>
                          <td className={`transaction-amount-cell ${displayType}`}>
                            {displayType === 'income' ? '+' : '-'}{formatAmount(transaction.amount)}
                          </td>
                          <td>
                            <div className="transaction-action-cell">
                              <button
                                type="button"
                                className="transaction-menu-trigger plain-button"
                                onClick={() => setOpenMenuId((current) => current === transaction.id ? null : transaction.id)}
                                aria-label={`Actions for ${transaction.description}`}
                                aria-expanded={openMenuId === transaction.id}
                              >
                                <MoreVertical aria-hidden="true" />
                              </button>
                              {openMenuId === transaction.id && (
                                <div className="transaction-row-menu">
                                  <button type="button" className="plain-button" onClick={() => handleEdit(transaction)}>Edit</button>
                                  {needsReview && (
                                    <div className="transaction-menu-correction">
                                      <AppSelect
                                        value={corrections[transaction.id] || ''}
                                        onChange={(nextValue) => handleCorrectionChange(transaction.id, nextValue)}
                                        ariaLabel={`Correct category for ${transaction.description}`}
                                        options={[
                                          { value: '', label: 'Correct category' },
                                          ...categories.map((item) => ({ value: item.id, label: item.name })),
                                        ]}
                                      />
                                      <button type="button" className="plain-button" onClick={() => handleSaveCorrection(transaction.id)}>Save category</button>
                                    </div>
                                  )}
                                  <button type="button" className="plain-button danger" onClick={() => handleDelete(transaction.id)}>Delete</button>
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

              {!loading && transactions.length > 0 && (
                <footer className="transaction-pagination">
                  <p>Showing {pageStart + 1} to {Math.min(pageStart + rowsPerPage, transactions.length)} of {transactions.length.toLocaleString('en-IN')} transactions</p>
                  <nav aria-label="Transaction pages">
                    <button type="button" className="plain-button" onClick={() => setPage((current) => Math.max(1, current - 1))} disabled={currentPage === 1} aria-label="Previous page">
                      <ChevronLeft aria-hidden="true" />
                    </button>
                    {paginationItems.map((item) => (
                      typeof item === 'number' ? (
                        <button
                          type="button"
                          className={`plain-button ${item === currentPage ? 'active' : ''}`}
                          key={item}
                          onClick={() => setPage(item)}
                          aria-current={item === currentPage ? 'page' : undefined}
                        >
                          {item}
                        </button>
                      ) : <span key={item}>...</span>
                    ))}
                    <button type="button" className="plain-button" onClick={() => setPage((current) => Math.min(pageCount, current + 1))} disabled={currentPage === pageCount} aria-label="Next page">
                      <ChevronRight aria-hidden="true" />
                    </button>
                  </nav>
                  <label>
                    <span>Rows per page:</span>
                    <AppSelect
                      value={rowsPerPage}
                      onChange={(nextValue) => { setRowsPerPage(Number(nextValue)); setPage(1); }}
                      ariaLabel="Rows per page"
                      options={[10, 25, 50].map((count) => ({ value: count, label: String(count) }))}
                    />
                  </label>
                </footer>
              )}
            </section>
          </section>
        </div>
      </main>
    </div>
  );
};

export default Transactions;
