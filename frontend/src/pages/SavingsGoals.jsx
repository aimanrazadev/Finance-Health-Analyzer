import { useEffect, useState } from 'react';
import Navigation from '../components/Navigation';
import { useAuth } from '../hooks/useAuth';
import api, { getAuthHeaders } from '../utils/api';
import '../styles/SavingsGoals.css';

const todayIso = new Date().toISOString().slice(0, 10);

const initialForm = {
  name: '',
  target_amount: '',
  current_amount: '',
  monthly_contribution: '',
  target_date: todayIso,
  status: 'active',
};

const moneyFormatter = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  maximumFractionDigits: 0,
});

const SavingsGoals = () => {
  const { token } = useAuth();
  const [goals, setGoals] = useState([]);
  const [formData, setFormData] = useState(initialForm);
  const [editingId, setEditingId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  const headers = getAuthHeaders(token);

  const loadGoals = async () => {
    setLoading(true);
    setError('');
    try {
      const response = await api.get('/savings-goals', { headers });
      setGoals(response.data);
    } catch (err) {
      console.error(err);
      setError('Unable to load savings goals.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (token) {
      queueMicrotask(() => {
        loadGoals();
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const resetForm = () => {
    setEditingId(null);
    setFormData(initialForm);
  };

  const handleChange = (event) => {
    const { name, value } = event.target;
    setFormData((current) => ({ ...current, [name]: value }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setSaving(true);
    setError('');
    setMessage('');

    const payload = {
      name: formData.name.trim(),
      target_amount: Number(formData.target_amount),
      current_amount: Number(formData.current_amount || 0),
      monthly_contribution: Number(formData.monthly_contribution || 0),
      target_date: new Date(formData.target_date).toISOString(),
      status: formData.status,
    };

    try {
      if (editingId) {
        await api.put(`/savings-goals/${editingId}`, payload, { headers });
        setMessage('Savings goal updated.');
      } else {
        await api.post('/savings-goals', payload, { headers });
        setMessage('Savings goal created.');
      }
      resetForm();
      await loadGoals();
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || 'Unable to save savings goal.');
    } finally {
      setSaving(false);
    }
  };

  const handleEdit = (goal) => {
    setEditingId(goal.id);
    setFormData({
      name: goal.name,
      target_amount: goal.target_amount,
      current_amount: goal.current_amount,
      monthly_contribution: goal.monthly_contribution,
      target_date: goal.target_date.slice(0, 10),
      status: goal.status,
    });
  };

  const handleDelete = async (goalId) => {
    const confirmed = window.confirm('Delete this savings goal?');
    if (!confirmed) return;
    try {
      await api.delete(`/savings-goals/${goalId}`, { headers });
      setMessage('Savings goal deleted.');
      await loadGoals();
    } catch (err) {
      console.error(err);
      setError('Unable to delete savings goal.');
    }
  };

  return (
    <div>
      <Navigation />
      <main className="savings-page">
        <div className="page-heading">
          <div>
            <p className="eyebrow">Savings goals</p>
            <h1>Goal Planner</h1>
            <p>Plan targets, track saved amounts, and see how monthly contributions affect your completion date.</p>
          </div>
        </div>

        {message && <div className="surface-message success">{message}</div>}
        {error && <div className="surface-message error">{error}</div>}

        <div className="savings-layout">
          <section className="savings-form-panel">
            <h2>{editingId ? 'Edit Goal' : 'Add Goal'}</h2>
            <form className="savings-form" onSubmit={handleSubmit}>
              <label>
                Goal name
                <input name="name" value={formData.name} onChange={handleChange} placeholder="Emergency fund" required />
              </label>
              <label>
                Target amount
                <input name="target_amount" type="number" min="1" value={formData.target_amount} onChange={handleChange} required />
              </label>
              <label>
                Current saved amount
                <input name="current_amount" type="number" min="0" value={formData.current_amount} onChange={handleChange} />
              </label>
              <label>
                Monthly contribution
                <input name="monthly_contribution" type="number" min="0" value={formData.monthly_contribution} onChange={handleChange} />
              </label>
              <label>
                Target date
                <input name="target_date" type="date" value={formData.target_date} onChange={handleChange} required />
              </label>
              <div className="savings-form-actions">
                <button className="primary-button" type="submit" disabled={saving}>
                  {saving ? 'Saving...' : editingId ? 'Update Goal' : 'Create Goal'}
                </button>
                {editingId && (
                  <button className="secondary-button" type="button" onClick={resetForm}>
                    Cancel
                  </button>
                )}
              </div>
            </form>
          </section>

          <section className="savings-list-panel">
            <div className="section-heading">
              <h2>Your Goals</h2>
              <p>Progress and timeline are recalculated whenever you update saved amount or contribution.</p>
            </div>

            {loading ? (
              <div className="empty-state">Loading savings goals...</div>
            ) : goals.length === 0 ? (
              <div className="empty-state">No savings goals yet.</div>
            ) : (
              <div className="savings-card-grid">
                {goals.map((goal) => (
                  <article className="savings-card" key={goal.id}>
                    <div className="savings-card-header">
                      <div>
                        <h3>{goal.name}</h3>
                        <p>{goal.status.replace('_', ' ')}</p>
                      </div>
                      <span>{goal.progress_percentage}%</span>
                    </div>
                    <div className="goal-progress">
                      <div style={{ width: `${Math.min(goal.progress_percentage, 100)}%` }} />
                    </div>
                    <div className="goal-values">
                      <span>Saved: {moneyFormatter.format(goal.current_amount)}</span>
                      <span>Target: {moneyFormatter.format(goal.target_amount)}</span>
                      <span>Remaining: {moneyFormatter.format(goal.remaining_amount)}</span>
                      <span>Monthly: {moneyFormatter.format(goal.monthly_contribution)}</span>
                    </div>
                    <div className="goal-timeline">
                      <div>
                        <span>Months required</span>
                        <strong>{goal.months_required ?? 'Set contribution'}</strong>
                      </div>
                      <div>
                        <span>Estimated completion</span>
                        <strong>
                          {goal.estimated_completion_date
                            ? new Date(goal.estimated_completion_date).toLocaleDateString()
                            : 'Not available'}
                        </strong>
                      </div>
                    </div>
                    <div className="goal-suggestion">{goal.ai_suggestion}</div>
                    <div className="goal-actions">
                      <button className="table-button" onClick={() => handleEdit(goal)}>Edit</button>
                      <button className="table-button danger" onClick={() => handleDelete(goal.id)}>Delete</button>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </section>
        </div>
      </main>
    </div>
  );
};

export default SavingsGoals;
