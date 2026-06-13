import { useEffect, useState } from 'react';
import CategoryBadge from '../components/CategoryBadge';
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
const todayIso = new Date().toISOString().slice(0, 10);

const defaultForm = {
  category_id: '',
  monthly_limit: '',
};

const defaultGoalForm = {
  name: '',
  target_amount: '',
  current_amount: '',
  monthly_contribution: '',
  target_date: todayIso,
  status: 'active',
};

const Budgets = () => {
  const { token } = useAuth();
  const [budgets, setBudgets] = useState([]);
  const [categories, setCategories] = useState([]);
  const [goals, setGoals] = useState([]);
  const [investmentSummary, setInvestmentSummary] = useState(null);
  const [selectedMonth, setSelectedMonth] = useState(currentDate.getMonth() + 1);
  const [selectedYear, setSelectedYear] = useState(currentYear);
  const [formData, setFormData] = useState(defaultForm);
  const [goalForm, setGoalForm] = useState(defaultGoalForm);
  const [editingId, setEditingId] = useState(null);
  const [editingGoalId, setEditingGoalId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [planningLoading, setPlanningLoading] = useState(true);
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

  useEffect(() => {
    let cancelled = false;

    const loadPlanningData = async () => {
      setPlanningLoading(true);
      try {
        const [goalsResponse, summaryResponse] = await Promise.all([
          api.get('/savings-goals', { headers }),
          api.get('/investments/summary', { headers }),
        ]);
        if (!cancelled) {
          setGoals(goalsResponse.data);
          setInvestmentSummary(summaryResponse.data);
        }
      } catch (err) {
        console.error(err);
      } finally {
        if (!cancelled) {
          setPlanningLoading(false);
        }
      }
    };

    if (token) {
      loadPlanningData();
    }

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const resetForm = () => {
    setFormData(defaultForm);
    setEditingId(null);
    setError('');
    setSuccess('');
  };

  const resetGoalForm = () => {
    setGoalForm(defaultGoalForm);
    setEditingGoalId(null);
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

  const handleGoalChange = (event) => {
    const { name, value } = event.target;
    setGoalForm((prev) => ({
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

  const loadPlanningAfterSave = async () => {
    const [goalsResponse, summaryResponse] = await Promise.all([
      api.get('/savings-goals', { headers }),
      api.get('/investments/summary', { headers }),
    ]);
    setGoals(goalsResponse.data);
    setInvestmentSummary(summaryResponse.data);
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

  const handleGoalSubmit = async (event) => {
    event.preventDefault();
    setSaving(true);
    setError('');
    setSuccess('');

    const payload = {
      name: goalForm.name.trim(),
      target_amount: Number(goalForm.target_amount),
      current_amount: Number(goalForm.current_amount || 0),
      monthly_contribution: Number(goalForm.monthly_contribution || 0),
      target_date: new Date(goalForm.target_date).toISOString(),
      status: goalForm.status,
    };

    try {
      if (editingGoalId) {
        await api.put(`/savings-goals/${editingGoalId}`, payload, { headers });
        setSuccess('Savings goal updated.');
      } else {
        await api.post('/savings-goals', payload, { headers });
        setSuccess('Savings goal created.');
      }
      resetGoalForm();
      await loadPlanningAfterSave();
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || 'Unable to save savings goal.');
    } finally {
      setSaving(false);
    }
  };

  const handleEdit = (budget) => {
    setEditingId(budget.id);
    setFormData({
      category_id: budget.category_id,
      monthly_limit: budget.monthly_limit,
    });
    setError('');
    setSuccess('');
  };

  const handleGoalEdit = (goal) => {
    setEditingGoalId(goal.id);
    setGoalForm({
      name: goal.name,
      target_amount: goal.target_amount,
      current_amount: goal.current_amount,
      monthly_contribution: goal.monthly_contribution,
      target_date: goal.target_date.slice(0, 10),
      status: goal.status,
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

  const handleGoalDelete = async (goalId) => {
    const confirmed = window.confirm('Delete this savings goal?');
    if (!confirmed) return;

    try {
      await api.delete(`/savings-goals/${goalId}`, { headers });
      setSuccess('Savings goal deleted.');
      await loadPlanningAfterSave();
    } catch (err) {
      console.error(err);
      setError('Unable to delete savings goal.');
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
            <p>Plan your cash balance, savings targets, and monthly category spending from one workspace.</p>
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

        <section className="budget-explainer">
          <div className="budget-explainer-icon">₹</div>
          <div>
            <strong>Budget = spending limit</strong>
            <p>Use budgets to cap how much you want to spend in a category this month. Example: Food budget INR 10,000 means the app warns you as spending approaches that limit.</p>
          </div>
        </section>

        {error && <div className="surface-message error">{error}</div>}
        {success && <div className="surface-message success">{success}</div>}

        <section className="budget-planning-section">
          <div className="section-heading">
            <div>
              <h2>Money Planning</h2>
              <p>Keep savings targets beside spending limits. Current balance is managed from the Dashboard.</p>
            </div>
          </div>
          <div className="planning-summary-grid">
            <article>
              <span>Savings saved</span>
              <strong>{moneyFormatter.format(investmentSummary?.savings_current_total || 0)}</strong>
            </article>
            <article>
              <span>Savings targets</span>
              <strong>{moneyFormatter.format(investmentSummary?.savings_goal_total || 0)}</strong>
            </article>
          </div>
          <div className="planning-layout">
            <section className="planning-card savings-form-card">
              <h3>{editingGoalId ? 'Edit Savings Goal' : 'Add Savings Goal'}</h3>
              <form className="budget-form" onSubmit={handleGoalSubmit}>
                <label>
                  Goal name
                  <input name="name" value={goalForm.name} onChange={handleGoalChange} placeholder="Emergency fund" required />
                </label>
                <label>
                  Target amount
                  <input name="target_amount" type="number" min="1" value={goalForm.target_amount} onChange={handleGoalChange} required />
                </label>
                <label>
                  Current saved amount
                  <input name="current_amount" type="number" min="0" value={goalForm.current_amount} onChange={handleGoalChange} />
                </label>
                <label>
                  Monthly contribution
                  <input name="monthly_contribution" type="number" min="0" value={goalForm.monthly_contribution} onChange={handleGoalChange} />
                </label>
                <label>
                  Target date
                  <input name="target_date" type="date" value={goalForm.target_date} onChange={handleGoalChange} required />
                </label>
                <div className="form-actions">
                  <button className="primary-button" type="submit" disabled={saving}>
                    {saving ? 'Saving...' : editingGoalId ? 'Update Savings Goal' : 'Add Savings Goal'}
                  </button>
                  {editingGoalId && (
                    <button className="secondary-button" type="button" onClick={resetGoalForm}>
                      Cancel
                    </button>
                  )}
                </div>
              </form>
            </section>

            <section className="planning-card planning-goals-card">
              <h3>Savings Goals</h3>
              {planningLoading ? (
                <div className="empty-state">Loading savings goals...</div>
              ) : goals.length === 0 ? (
                <div className="empty-state budget-empty-state">
                  <strong>No savings goals yet.</strong>
                  <span>Example: create an Emergency Fund goal of INR 50,000.</span>
                </div>
              ) : (
                <div className="planning-goals-list">
                  {goals.map((goal) => (
                    <article className="planning-goal-row" key={goal.id}>
                      <div>
                        <strong>{goal.name}</strong>
                        <span>{moneyFormatter.format(goal.current_amount)} saved of {moneyFormatter.format(goal.target_amount)}</span>
                      </div>
                      <div className="planning-goal-progress">
                        <div style={{ width: `${Math.min(goal.progress_percentage, 100)}%` }} />
                      </div>
                      <div className="budget-actions">
                        <button className="table-button" onClick={() => handleGoalEdit(goal)}>Edit</button>
                        <button className="table-button danger" onClick={() => handleGoalDelete(goal.id)}>Delete</button>
                      </div>
                    </article>
                  ))}
                </div>
              )}
            </section>
          </div>
        </section>

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
              <div className="budget-smart-note">
                Smart alerts are automatic at 50%, 75%, 90%, 95%, and 99% usage.
              </div>
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
              <div className="empty-state budget-empty-state">
                <strong>No spending limits set for this period.</strong>
                <span>Example: create a Food budget of INR 10,000 or a Shopping budget of INR 5,000 to control monthly expenses.</span>
              </div>
            ) : (
              <div className="budget-card-grid">
                {budgets.map((budget) => {
                  const progress = Math.min(budget.percentage_used, 100);
                  return (
                    <article className={`budget-card ${budget.status}`} key={budget.id}>
                      <div className="budget-card-header">
                        <div>
                          <CategoryBadge name={budget.category_name || 'Category'} />
                          <p>{budget.status.replace('_', ' ')}</p>
                        </div>
                        <span>{budget.percentage_used}%</span>
                      </div>
                      <div className="budget-milestones">
                        {(budget.smart_milestones || [50, 75, 90, 95, 99]).map((milestone) => (
                          <span
                            className={(budget.reached_milestones || []).includes(milestone) ? 'reached' : ''}
                            key={milestone}
                          >
                            {milestone}%
                          </span>
                        ))}
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
