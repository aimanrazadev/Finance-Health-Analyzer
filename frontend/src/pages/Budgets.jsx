import { useEffect, useState } from 'react';
import Navigation from '../components/Navigation';
import { useAuth } from '../hooks/useAuth';
import api, { getAuthHeaders } from '../utils/api';
import '../styles/Budgets.css';

const moneyFormatter = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  maximumFractionDigits: 2,
});

const monthOptions = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
].map((label, index) => ({ label, value: index + 1 }));

const currentDate = new Date();
const currentYear = currentDate.getFullYear();
const yearOptions = Array.from({ length: 7 }, (_, index) => currentYear - 5 + index);

const defaultForm = {
  category_id: '',
  monthly_limit: '',
  alert_threshold: 80,
};

const Budgets = () => {
  const { token } = useAuth();
  const [budgets, setBudgets] = useState([]);
  const [categories, setCategories] = useState([]);
  const [selectedMonth, setSelectedMonth] = useState(currentDate.getMonth() + 1);
  const [selectedYear, setSelectedYear] = useState(currentYear);
  const [formData, setFormData] = useState(defaultForm);
  const [editingId, setEditingId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const headers = getAuthHeaders(token);

  useEffect(() => {
    let cancelled = false;

    const loadCategories = async () => {
      try {
        const response = await api.get('/categories');
        if (!cancelled) {
          setCategories(response.data.filter((category) => category.name !== 'Salary' && category.name !== 'Investments'));
        }
      } catch (err) {
        console.error(err);
      }
    };

    loadCategories();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;

    const loadBudgets = async () => {
      setLoading(true);
      try {
        const response = await api.get('/budgets', {
          headers: getAuthHeaders(token),
          params: {
            month: selectedMonth,
            year: selectedYear,
          },
        });
        if (!cancelled) {
          setBudgets(response.data);
          setError('');
        }
      } catch (err) {
        console.error(err);
        if (!cancelled) {
          setError('Unable to load budgets.');
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    if (token) {
      loadBudgets();
    }

    return () => {
      cancelled = true;
    };
  }, [token, selectedMonth, selectedYear]);

  const resetForm = () => {
    setFormData(defaultForm);
    setEditingId(null);
    setError('');
    setSuccess('');
  };

  const handleChange = (event) => {
    const { name, value } = event.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const loadBudgetsAfterSave = async () => {
    const response = await api.get('/budgets', {
      headers,
      params: {
        month: selectedMonth,
        year: selectedYear,
      },
    });
    setBudgets(response.data);
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setSaving(true);
    setError('');
    setSuccess('');

    const payload = {
      category_id: Number(formData.category_id),
      monthly_limit: Number(formData.monthly_limit),
      month: selectedMonth,
      year: selectedYear,
      alert_threshold: Number(formData.alert_threshold),
      is_active: true,
    };

    try {
      if (editingId) {
        await api.put(`/budgets/${editingId}`, payload, { headers });
        setSuccess('Budget updated.');
      } else {
        await api.post('/budgets', payload, { headers });
        setSuccess('Budget created.');
      }
      resetForm();
      await loadBudgetsAfterSave();
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || 'Unable to save budget.');
    } finally {
      setSaving(false);
    }
  };

  const handleEdit = (budget) => {
    setEditingId(budget.id);
    setFormData({
      category_id: budget.category_id,
      monthly_limit: budget.monthly_limit,
      alert_threshold: budget.alert_threshold,
    });
    setError('');
    setSuccess('');
  };

  const handleDelete = async (budgetId) => {
    const confirmed = window.confirm('Delete this budget?');
    if (!confirmed) return;

    try {
      await api.delete(`/budgets/${budgetId}`, { headers });
      setSuccess('Budget deleted.');
      await loadBudgetsAfterSave();
    } catch (err) {
      console.error(err);
      setError('Unable to delete budget.');
    }
  };

  return (
    <div>
      <Navigation />
      <main className="budgets-page">
        <div className="page-heading">
          <div>
            <p className="eyebrow">Budget planner</p>
            <h1>Monthly Budgets</h1>
            <p>Set category limits, compare real spending, and catch alerts before overspending.</p>
          </div>
          <div className="budget-filters">
            <label>
              Month
              <select value={selectedMonth} onChange={(event) => setSelectedMonth(Number(event.target.value))}>
                {monthOptions.map((month) => (
                  <option key={month.value} value={month.value}>{month.label}</option>
                ))}
              </select>
            </label>
            <label>
              Year
              <select value={selectedYear} onChange={(event) => setSelectedYear(Number(event.target.value))}>
                {yearOptions.map((year) => (
                  <option key={year} value={year}>{year}</option>
                ))}
              </select>
            </label>
          </div>
        </div>

        {error && <div className="surface-message error">{error}</div>}
        {success && <div className="surface-message success">{success}</div>}

        <div className="budgets-layout">
          <section className="budget-form-panel">
            <h2>{editingId ? 'Edit Budget' : 'Create Budget'}</h2>
            <form className="budget-form" onSubmit={handleSubmit}>
              <label>
                Category
                <select name="category_id" value={formData.category_id} onChange={handleChange} required>
                  <option value="">Select category</option>
                  {categories.map((category) => (
                    <option key={category.id} value={category.id}>{category.name}</option>
                  ))}
                </select>
              </label>
              <label>
                Monthly limit
                <input
                  type="number"
                  name="monthly_limit"
                  min="1"
                  step="0.01"
                  value={formData.monthly_limit}
                  onChange={handleChange}
                  required
                />
              </label>
              <label>
                Alert threshold %
                <input
                  type="number"
                  name="alert_threshold"
                  min="0"
                  max="100"
                  step="1"
                  value={formData.alert_threshold}
                  onChange={handleChange}
                  required
                />
              </label>
              <div className="form-actions">
                <button className="primary-button" type="submit" disabled={saving}>
                  {saving ? 'Saving...' : editingId ? 'Update Budget' : 'Create Budget'}
                </button>
                {editingId && (
                  <button className="secondary-button" type="button" onClick={resetForm}>
                    Cancel
                  </button>
                )}
              </div>
            </form>
          </section>

          <section className="budget-list-panel">
            <div className="section-heading">
              <div>
                <h2>Budget Status</h2>
                <p>Actual spending is calculated from expense transactions in the selected month.</p>
              </div>
            </div>

            {loading ? (
              <div className="empty-state">Loading budgets...</div>
            ) : budgets.length === 0 ? (
              <div className="empty-state">No budgets yet for this period.</div>
            ) : (
              <div className="budget-card-grid">
                {budgets.map((budget) => {
                  const progress = Math.min(budget.percentage_used, 100);
                  return (
                    <article className={`budget-card ${budget.status}`} key={budget.id}>
                      <div className="budget-card-header">
                        <div>
                          <h3>{budget.category_name || 'Category'}</h3>
                          <p>{budget.status.replace('_', ' ')}</p>
                        </div>
                        <span>{budget.percentage_used}%</span>
                      </div>
                      <div className="budget-progress">
                        <div style={{ width: `${progress}%` }} />
                      </div>
                      <div className="budget-values">
                        <span>Spent: {moneyFormatter.format(budget.actual_spent)}</span>
                        <span>Limit: {moneyFormatter.format(budget.monthly_limit)}</span>
                        <span>Remaining: {moneyFormatter.format(budget.remaining_amount)}</span>
                      </div>
                      {budget.alert_message && <div className="budget-alert">{budget.alert_message}</div>}
                      <div className="budget-actions">
                        <button className="table-button" onClick={() => handleEdit(budget)}>Edit</button>
                        <button className="table-button danger" onClick={() => handleDelete(budget.id)}>Delete</button>
                      </div>
                    </article>
                  );
                })}
              </div>
            )}
          </section>
        </div>
      </main>
    </div>
  );
};

export default Budgets;
