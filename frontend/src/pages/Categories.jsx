import { useCallback, useEffect, useMemo, useState } from 'react';
import CategoryBadge from '../components/CategoryBadge';
import Navigation from '../components/Navigation';
import { useAuth } from '../hooks/useAuth';
import api, { getAuthHeaders } from '../utils/api';
import '../styles/NeedsReview.css';

const INCOME_CATEGORY_NAMES = ['Refunds', 'Friends', 'Salary', 'Shopping', 'Other'];
const SAVINGS_CATEGORY_NAMES = ['Investments'];
const confidencePercent = (value) => `${Math.round((value ?? 0.3) * 100)}%`;
const methodLabel = (method) => ({
  learned: 'Learned',
  user_learned: 'Learned',
  rule_based: 'Rule-Based',
  ml_model: 'ML',
  manual: 'Manual',
  needs_review: 'Needs Review',
}[method] || 'Needs Review');

const Categories = () => {
  const { token } = useAuth();
  const [transactions, setTransactions] = useState([]);
  const [categories, setCategories] = useState([]);
  const [selectedCategories, setSelectedCategories] = useState({});
  const [bulkCategoryId, setBulkCategoryId] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [includeLearned, setIncludeLearned] = useState(false);
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
    if (token) {
      queueMicrotask(() => {
        loadData();
      });
    }
  }, [loadData, token]);

  const saveCorrection = async (transactionId) => {
    const categoryId = selectedCategories[transactionId];
    if (!categoryId) {
      setError('Select a category before saving.');
      return;
    }

    try {
      const response = await api.post('/categories/correct', {
        transaction_id: transactionId,
        new_category_id: Number(categoryId),
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

  const normalizedSearch = searchTerm.trim().toLowerCase();
  const filteredTransactions = transactions.filter((transaction) => {
    if (!normalizedSearch) return true;
    return [
      transaction.description,
      transaction.merchant,
      transaction.transaction_type,
      transaction.amount?.toString(),
    ]
      .filter(Boolean)
      .some((value) => String(value).toLowerCase().includes(normalizedSearch));
  });

  const applyBulkCategory = () => {
    if (!bulkCategoryId) {
      setError('Select a bulk category first.');
      return;
    }
    const nextSelections = {};
    filteredTransactions.forEach((transaction) => {
      nextSelections[transaction.id] = bulkCategoryId;
    });
    setSelectedCategories(nextSelections);
    setError('');
  };

  const getCategoriesForType = (transactionType) => (
    transactionType === 'savings'
      ? categories.filter((category) => SAVINGS_CATEGORY_NAMES.includes(category.name))
      : (
        transactionType === 'income'
          ? categories.filter((category) => INCOME_CATEGORY_NAMES.includes(category.name))
          : categories
      )
  );

  const getCategoryById = (categoryId) => categories.find((category) => (
    String(category.id) === String(categoryId)
  ));

  const bulkCategoryOptions = filteredTransactions.length > 0
    && filteredTransactions.every((transaction) => transaction.transaction_type === 'savings')
    ? categories.filter((category) => SAVINGS_CATEGORY_NAMES.includes(category.name))
    : (
      filteredTransactions.length > 0
      && filteredTransactions.every((transaction) => transaction.transaction_type === 'income')
        ? categories.filter((category) => INCOME_CATEGORY_NAMES.includes(category.name))
        : categories
    );

  const saveBulkCorrections = async () => {
    const entries = Object.entries(selectedCategories).filter(([, categoryId]) => categoryId);
    if (entries.length === 0) {
      setError('Select at least one category correction before bulk saving.');
      return;
    }

    try {
      const response = await api.post('/categories/bulk-correct', {
        corrections: entries.map(([transactionId, categoryId]) => ({
          transaction_id: Number(transactionId),
          new_category_id: Number(categoryId),
        })),
      }, { headers });
      setMessage(response.data.message || `${entries.length} category corrections saved. Learning rules updated for future transactions.`);
      setSelectedCategories({});
      setBulkCategoryId('');
      await loadData();
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || 'Unable to save bulk category corrections.');
    }
  };

  return (
    <div>
      <Navigation />
      <main className="review-page">
        <div className="page-heading">
          <div>
            <p className="eyebrow">Smart categorization</p>
            <h1>Categories</h1>
            <p>Review low-confidence transactions and teach the system better category rules.</p>
          </div>
        </div>

        {message && <div className="surface-message success">{message}</div>}
        {error && <div className="surface-message error">{error}</div>}

        <section className="review-panel">
          {loading ? (
            <div className="empty-state">Loading category queue...</div>
          ) : transactions.length === 0 ? (
            <div className="empty-state">All transactions are categorized confidently.</div>
          ) : (
            <>
              <div className="bulk-review-actions">
                <div className="review-search-control">
                  <input
                    type="search"
                    value={searchTerm}
                    onChange={(event) => setSearchTerm(event.target.value)}
                    placeholder="Search transactions"
                  />
                  <label className="review-toggle">
                    <input
                      type="checkbox"
                      checked={includeLearned}
                      onChange={(event) => setIncludeLearned(event.target.checked)}
                    />
                    Include learned
                  </label>
                </div>
                <div className="review-bulk-control">
                  <select value={bulkCategoryId} onChange={(event) => setBulkCategoryId(event.target.value)}>
                    <option value="">Bulk category</option>
                    {bulkCategoryOptions.map((category) => (
                      <option key={category.id} value={category.id}>{category.name}</option>
                    ))}
                  </select>
                  <button className="secondary-button" onClick={applyBulkCategory}>
                    Assign
                  </button>
                  <button className="primary-button" onClick={saveBulkCorrections}>
                    Save All
                  </button>
                </div>
              </div>
              <p className="review-count">
                Showing {filteredTransactions.length} of {transactions.length} low-confidence transactions
              </p>
              <div className="review-list">
                {filteredTransactions.length === 0 ? (
                  <div className="empty-state">No matching transactions found.</div>
                ) : filteredTransactions.map((transaction) => (
                  <div className="review-row" key={transaction.id}>
                    <div>
                      <strong>{transaction.description}</strong>
                      <span>
                        {new Date(transaction.date).toLocaleDateString()} · {transaction.transaction_type} · INR {transaction.amount.toFixed(2)}
                      </span>
                      <span>
                        Merchant: {transaction.extracted_merchant || transaction.merchant || 'Unknown'} · Confidence: {confidencePercent(transaction.category_confidence)} · {methodLabel(transaction.categorization_method)}
                      </span>
                      {selectedCategories[transaction.id] && (
                        <CategoryBadge category={getCategoryById(selectedCategories[transaction.id])} />
                      )}
                    </div>
                    <select
                      value={selectedCategories[transaction.id] || ''}
                      onChange={(event) => setSelectedCategories((current) => ({
                        ...current,
                        [transaction.id]: event.target.value,
                      }))}
                    >
                      <option value="">Select category</option>
                      {getCategoriesForType(transaction.transaction_type).map((category) => (
                        <option key={category.id} value={category.id}>{category.name}</option>
                      ))}
                    </select>
                    <button className="primary-button" onClick={() => saveCorrection(transaction.id)}>
                      Save
                    </button>
                  </div>
                ))}
              </div>
            </>
          )}
        </section>
      </main>
    </div>
  );
};

export default Categories;
