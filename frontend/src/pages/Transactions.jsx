import { useEffect, useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import CategoryBadge from '../components/CategoryBadge';
import Navigation from '../components/Navigation';
import Skeleton from '../components/Skeleton';
import { useUI } from '../hooks/useUI';
import api, { getAuthHeaders } from '../utils/api';
import '../styles/Transactions.css';

const INCOME_CATEGORY_NAMES = ['Refunds', 'Investments', 'Salary', 'Shopping', 'Other'];

const defaultFormState = {
  amount: '',
  category_id: '',
  description: '',
  merchant: '',
  transaction_type: 'expense',
  date: new Date().toISOString().slice(0, 16),
};

const Transactions = () => {
  const { token } = useAuth();
  const { confirm, showToast } = useUI();
  const [transactions, setTransactions] = useState([]);
  const [categories, setCategories] = useState([]);
  const [formData, setFormData] = useState(defaultFormState);
  const [editingId, setEditingId] = useState(null);
  const [search, setSearch] = useState('');
  const [filterType, setFilterType] = useState('');
  const [filterCategory, setFilterCategory] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(true);
  const [corrections, setCorrections] = useState({});

  const authHeaders = getAuthHeaders(token);

  const formatDateLocal = (isoString) => {
    if (!isoString) return '';
    const date = new Date(isoString);
    const offset = date.getTimezoneOffset();
    const localDate = new Date(date.getTime() - offset * 60000);
    return localDate.toISOString().slice(0, 16);
  };

  const loadTransactions = async () => {
    setLoading(true);
    setError('');

    try {
      const params = {};
      if (search) params.search = search;
      if (filterType) params.transaction_type = filterType;
      if (filterCategory) params.category_id = filterCategory;

      const response = await api.get('/transactions', {
        headers: authHeaders,
        params,
      });
      setTransactions(response.data);
    } catch (err) {
      console.error(err);
      setError('Unable to load transactions.');
    } finally {
      setLoading(false);
    }
  };

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
    const loadFilteredTransactions = async () => {
      setLoading(true);
      setError('');

      try {
        const params = {};
        if (search) params.search = search;
        if (filterType) params.transaction_type = filterType;
        if (filterCategory) params.category_id = filterCategory;

        const response = await api.get('/transactions', {
          headers: getAuthHeaders(token),
          params,
        });
        setTransactions(response.data);
      } catch (err) {
        console.error(err);
        setError('Unable to load transactions.');
      } finally {
        setLoading(false);
      }
    };

    loadFilteredTransactions();
  }, [search, filterType, filterCategory, token]);

  const resetForm = () => {
    setFormData(defaultFormState);
    setEditingId(null);
    setError('');
    setSuccess('');
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
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
      if (editingId) {
        await api.put(`/transactions/${editingId}`, payload, {
          headers: authHeaders,
        });
        setSuccess('Transaction updated.');
        showToast('Transaction updated.');
      } else {
        await api.post('/transactions', payload, {
          headers: authHeaders,
        });
        setSuccess('Transaction added.');
        showToast('Transaction added.');
      }
      resetForm();
      loadTransactions();
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || 'Failed to save transaction.');
    }
  };

  const handleEdit = (transaction) => {
    setEditingId(transaction.id);
    setFormData({
      amount: transaction.amount.toString(),
      category_id: transaction.category_id || '',
      description: transaction.description,
      merchant: transaction.merchant || '',
      transaction_type: transaction.transaction_type,
      date: formatDateLocal(transaction.date),
    });
    setSuccess('');
    setError('');
  };

  const handleDelete = async (id) => {
    const confirmed = await confirm({
      title: 'Delete transaction',
      message: 'This transaction will be removed from your account.',
      confirmLabel: 'Delete',
      danger: true,
    });
    if (!confirmed) return;

    try {
      await api.delete(`/transactions/${id}`, {
        headers: authHeaders,
      });
      setSuccess('Transaction deleted.');
      showToast('Transaction deleted.');
      loadTransactions();
    } catch (err) {
      console.error(err);
      setError('Unable to delete transaction.');
    }
  };

  const handleCorrectionChange = (transactionId, categoryId) => {
    setCorrections((prev) => ({
      ...prev,
      [transactionId]: categoryId,
    }));
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
      }, {
        headers: authHeaders,
      });
      setSuccess(response.data.message || 'Category updated. Learning rule saved.');
      showToast(response.data.message || 'Category updated. Learning rule saved.');
      setCorrections((prev) => {
        const next = { ...prev };
        delete next[transactionId];
        return next;
      });
      loadTransactions();
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || 'Unable to save category correction.');
    }
  };

  const getCategoriesForType = (transactionType) => (
    transactionType === 'income'
      ? categories.filter((category) => INCOME_CATEGORY_NAMES.includes(category.name))
      : categories.filter((category) => category.name !== 'Needs Review')
  );
  const mlLearnedCount = transactions.filter((transaction) => (
    transaction.categorization_method === 'ml_model'
    && (transaction.category_confidence ?? 0) >= 0.8
  )).length;

  return (
    <div>
      <Navigation />
      <div className="transactions-page">
        <div className="transactions-header">
          <div>
            <h1>Manual Transactions</h1>
            <p>Track income and expenses with categories, filters, and search.</p>
          </div>
        </div>

        <div className="transactions-main">
          <section className="transaction-form-panel">
            <h2>{editingId ? 'Edit Transaction' : 'Add Transaction'}</h2>
            {error && <div className="form-error">{error}</div>}
            {success && <div className="form-success">{success}</div>}
            {mlLearnedCount > 0 && (
              <div className="form-success">
                ML has successfully learned {mlLearnedCount} transaction pattern{mlLearnedCount === 1 ? '' : 's'}.
                Confident ML categories are locked here; use Categories with Include learned to change them later.
              </div>
            )}

            <form className="transaction-form" onSubmit={handleSubmit}>
              <label>
                Amount
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  name="amount"
                  value={formData.amount}
                  onChange={handleChange}
                  required
                />
              </label>

              <label>
                Date and Time
                <input
                  type="datetime-local"
                  name="date"
                  value={formData.date}
                  onChange={handleChange}
                  required
                />
              </label>

              <label>
                Description
                <input
                  type="text"
                  name="description"
                  value={formData.description}
                  onChange={handleChange}
                  required
                />
              </label>

              <label>
                Merchant
                <input
                  type="text"
                  name="merchant"
                  value={formData.merchant}
                  onChange={handleChange}
                />
              </label>

              <label>
                Transaction Type
                <select
                  name="transaction_type"
                  value={formData.transaction_type}
                  onChange={handleChange}
                  required
                >
                  <option value="expense">Expense</option>
                  <option value="income">Income</option>
                </select>
              </label>

              <label>
                Category
                <select
                  name="category_id"
                  value={formData.category_id}
                  onChange={handleChange}
                >
                  <option value="">None</option>
                  {getCategoriesForType(formData.transaction_type).map((category) => (
                    <option key={category.id} value={category.id}>
                      {category.name}
                    </option>
                  ))}
                </select>
              </label>

              <div className="form-actions">
                <button type="submit" className="primary-button">
                  {editingId ? 'Update Transaction' : 'Add Transaction'}
                </button>
                {editingId && (
                  <button type="button" className="secondary-button" onClick={resetForm}>
                    Cancel
                  </button>
                )}
              </div>
            </form>
          </section>

          <section className="transaction-list-panel">
            <div className="transaction-filters">
              <input
                type="text"
                placeholder="Search description or merchant"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
              <select value={filterType} onChange={(e) => setFilterType(e.target.value)}>
                <option value="">All types</option>
                <option value="expense">Expense</option>
                <option value="income">Income</option>
              </select>
              <select value={filterCategory} onChange={(e) => setFilterCategory(e.target.value)}>
                <option value="">All categories</option>
                {categories.map((category) => (
                  <option key={category.id} value={category.id}>
                    {category.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="transaction-table-wrapper">
              <table className="transaction-table">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Description</th>
                    <th>Category</th>
                    <th>Type</th>
                    <th>Amount</th>
                    <th>Merchant</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {loading && (
                    <tr>
                      <td colSpan="7"><Skeleton rows={4} /></td>
                    </tr>
                  )}
                  {!loading && transactions.length === 0 && (
                    <tr>
                      <td colSpan="7">No transactions found.</td>
                    </tr>
                  )}
                  {!loading && transactions.map((transaction) => {
                    const category = categories.find((c) => c.id === transaction.category_id);
                    const date = new Date(transaction.date).toLocaleString();
                    const needsReview = (transaction.category_confidence ?? 0) < 0.8
                      || category?.name === 'Needs Review';
                    return (
                      <tr key={transaction.id}>
                        <td>{date}</td>
                        <td>{transaction.description}</td>
                        <td>
                          <div className="category-correction">
                            <CategoryBadge category={category} name={category?.name || 'Uncategorized'} />
                            {needsReview && (
                              <>
                                <select
                                  value={corrections[transaction.id] || ''}
                                  onChange={(event) => handleCorrectionChange(transaction.id, event.target.value)}
                                >
                                  <option value="">Correct category</option>
                                  {getCategoriesForType(transaction.transaction_type)
                                    .map((item) => (
                                      <option key={item.id} value={item.id}>{item.name}</option>
                                    ))}
                                </select>
                                <button className="table-button" onClick={() => handleSaveCorrection(transaction.id)}>
                                  Save Correction
                                </button>
                              </>
                            )}
                          </div>
                        </td>
                        <td>{transaction.transaction_type}</td>
                        <td>{transaction.amount.toFixed(2)}</td>
                        <td>{transaction.extracted_merchant || transaction.merchant || '-'}</td>
                        <td>
                          <button className="table-button" onClick={() => handleEdit(transaction)}>
                            Edit
                          </button>
                          <button className="table-button danger" onClick={() => handleDelete(transaction.id)}>
                            Delete
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
};

export default Transactions;
