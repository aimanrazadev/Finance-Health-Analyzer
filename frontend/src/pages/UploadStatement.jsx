import { useEffect, useState } from 'react';
import Navigation from '../components/Navigation';
import { useAuth } from '../hooks/useAuth';
import api, { getAuthHeaders } from '../utils/api';
import '../styles/UploadStatement.css';

const INCOME_CATEGORY_NAMES = ['Refunds', 'Friends', 'Salary', 'Shopping', 'Other'];
const SAVINGS_CATEGORY_NAMES = ['Investments'];

const moneyFormatter = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  maximumFractionDigits: 2,
});

const formatMoney = (value) => (value ? moneyFormatter.format(Number(value)) : '-');
const formatDate = (value) => (value ? new Date(value).toLocaleDateString() : '-');

const UploadStatement = () => {
  const { token } = useAuth();
  const [selectedFile, setSelectedFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [history, setHistory] = useState([]);
  const [importProfiles, setImportProfiles] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [saving, setSaving] = useState(false);
  const [deletingUploadId, setDeletingUploadId] = useState(null);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const headers = getAuthHeaders(token);

  const loadHistory = async () => {
    try {
      const [historyResponse, profileResponse] = await Promise.all([
        api.get('/uploads/history', { headers }),
        api.get('/import-profiles', { headers }),
      ]);
      setHistory(historyResponse.data);
      setImportProfiles(profileResponse.data);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    let cancelled = false;

    const loadInitialHistory = async () => {
      try {
        const [response, profileResponse] = await Promise.all([
          api.get('/uploads/history', { headers: getAuthHeaders(token) }),
          api.get('/import-profiles', { headers: getAuthHeaders(token) }),
        ]);
        if (!cancelled) {
          setHistory(response.data);
          setImportProfiles(profileResponse.data);
        }
      } catch (err) {
        console.error(err);
      }
    };

    if (token) {
      loadInitialHistory();
    }

    return () => {
      cancelled = true;
    };
  }, [token]);

  useEffect(() => {
    const loadCategories = async () => {
      try {
        const response = await api.get('/categories');
        setCategories(response.data);
      } catch (err) {
        console.error(err);
      }
    };

    loadCategories();
  }, []);

  const handleFileChange = (event) => {
    setSelectedFile(event.target.files?.[0] || null);
    setPreview(null);
    setError('');
    setSuccess('');
  };

  const handlePreview = async (event) => {
    event.preventDefault();
    if (!selectedFile) {
      setError('Choose a CSV, Excel, or PDF statement first.');
      return;
    }

    const formData = new FormData();
    formData.append('file', selectedFile);
    setLoadingPreview(true);
    setError('');
    setSuccess('');

    try {
      const response = await api.post('/uploads/preview', formData, {
        headers: {
          ...headers,
          'Content-Type': 'multipart/form-data',
        },
      });
      setPreview(response.data);
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || 'Unable to preview this file.');
    } finally {
      setLoadingPreview(false);
    }
  };

  const handleConfirm = async () => {
    if (!preview || preview.valid_rows === 0) {
      setError('No valid rows available to save.');
      return;
    }

    setSaving(true);
    setError('');
    setSuccess('');

    try {
      const response = await api.post('/uploads/confirm', {
        file_name: preview.file_name,
        file_size: preview.file_size,
        file_type: preview.file_type,
        column_mapping: preview.column_mapping || {},
        total_rows: preview.total_rows,
        failed_rows: preview.failed_rows,
        rows: preview.rows,
      }, { headers });
      setSuccess(response.data.message);
      setSelectedFile(null);
      setPreview(null);
      await loadHistory();
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || 'Unable to save uploaded transactions.');
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    setSelectedFile(null);
    setPreview(null);
    setError('');
    setSuccess('');
  };

  const handleDeleteUpload = async (uploadedFile) => {
    const confirmed = window.confirm(
      `Delete ${uploadedFile.filename}? This will remove the uploaded statement and all transactions imported from it.`
    );
    if (!confirmed) return;

    setDeletingUploadId(uploadedFile.id);
    setError('');
    setSuccess('');

    try {
      await api.delete(`/uploads/${uploadedFile.id}`, { headers });
      setSuccess(`Deleted ${uploadedFile.filename} and its imported transactions.`);
      await loadHistory();
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || 'Unable to delete uploaded statement.');
    } finally {
      setDeletingUploadId(null);
    }
  };

  const handlePreviewCategoryChange = (rowNumber, categoryId) => {
    const selectedCategory = categories.find((category) => category.id === Number(categoryId));
    setPreview((current) => ({
      ...current,
      rows: current.rows.map((row) => (
        row.row_number === rowNumber
          ? {
              ...row,
              category_id: categoryId ? Number(categoryId) : null,
              category: selectedCategory?.name || 'Uncategorized',
              category_name: selectedCategory?.name || 'Uncategorized',
              transaction_type: selectedCategory?.name === 'Investments' ? 'savings' : row.transaction_type,
              category_confidence: categoryId ? 1 : row.category_confidence,
              categorization_method: categoryId ? 'manual' : row.categorization_method,
            }
          : row
      )),
    }));
  };

  const confidencePercent = (value) => `${Math.round((value ?? 0.3) * 100)}%`;
  const methodLabel = (method) => ({
    rule_based: 'Rule',
    learned: 'Learned',
    user_learned: 'Learned',
    ml_model: 'ML',
    ai_fallback: 'AI',
    manual: 'Manual',
    needs_review: 'Needs Review',
  }[method] || 'Needs Review');
  const getCategoriesForType = (transactionType) => (
    transactionType === 'savings'
      ? categories.filter((category) => SAVINGS_CATEGORY_NAMES.includes(category.name))
      : (
        transactionType === 'income'
          ? categories.filter((category) => INCOME_CATEGORY_NAMES.includes(category.name))
          : categories
      )
  );

  return (
    <div>
      <Navigation />
      <main className="upload-page">
        <div className="page-heading">
          <div>
            <p className="eyebrow">Statement import</p>
            <h1>Upload bank statement</h1>
            <p>Preview, clean, categorize, and confirm CSV, Excel, or PDF statement transactions before saving.</p>
          </div>
        </div>

        {error && <div className="surface-message error">{error}</div>}
        {success && <div className="surface-message success">{success}</div>}

        <section className="upload-layout">
          <div className="upload-panel">
            <h2>Select statement</h2>
            <form onSubmit={handlePreview} className="upload-form">
              <label className="statement-dropzone">
                <input type="file" accept=".csv,.xlsx,.xls,.pdf" onChange={handleFileChange} />
                <span className="dropzone-icon" aria-hidden="true">
                  <svg viewBox="0 0 24 24">
                    <path d="M12 3v12" />
                    <path d="m7 8 5-5 5 5" />
                    <path d="M5 15v4a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-4" />
                  </svg>
                </span>
                <span className="dropzone-title">Drag and drop your statement here</span>
                <span className="dropzone-or">or</span>
                <span className="dropzone-button">Choose file</span>
                <span className="dropzone-file-name">
                  {selectedFile ? selectedFile.name : 'No file selected'}
                </span>
              </label>
              <button type="submit" className="primary-button" disabled={loadingPreview}>
                {loadingPreview ? 'Reading file...' : 'Show upload preview'}
              </button>
            </form>
          </div>

          <div className="upload-panel">
            <h2>Upload history</h2>
            {history.length === 0 ? (
              <div className="empty-state">No statement uploads yet.</div>
            ) : (
              <div className="history-list">
                {history.map((item) => (
                  <div className="history-item" key={item.id}>
                    <div>
                      <strong>{item.filename}</strong>
                      <span>{item.file_type || 'statement'} · {new Date(item.upload_date).toLocaleString()}</span>
                    </div>
                    <div className="history-actions">
                      <b>{item.successful_rows || item.transaction_count} saved</b>
                      <button
                        type="button"
                        className="history-delete-button"
                        onClick={() => handleDeleteUpload(item)}
                        disabled={deletingUploadId === item.id}
                      >
                        {deletingUploadId === item.id ? 'Deleting...' : 'Delete'}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="upload-panel import-profile-panel">
            <h2>Import profiles</h2>
            {importProfiles.length === 0 ? (
              <div className="empty-state">Profiles are created after confirmed CSV or Excel uploads.</div>
            ) : (
              <div className="history-list">
                {importProfiles.slice(0, 4).map((profile) => (
                  <div className="history-item" key={profile.id}>
                    <div>
                      <strong>{profile.profile_name}</strong>
                      <span>{profile.bank_name || 'Bank format'} · {Math.round((profile.confidence_score || 0) * 100)}% confidence</span>
                    </div>
                    <b>{profile.usage_count} uses</b>
                  </div>
                ))}
              </div>
            )}
          </div>
        </section>

        {preview && (
          <section className="preview-panel">
            <div className="section-heading">
              <div>
                <h2>Upload preview</h2>
                <p>
                  {preview.file_name} · {preview.file_type?.toUpperCase()} import
                </p>
              </div>
              <div className="preview-actions">
                <button className="secondary-button" onClick={handleCancel} disabled={saving}>
                  Cancel
                </button>
                <button className="primary-button" onClick={handleConfirm} disabled={saving || preview.valid_rows === 0}>
                  {saving ? 'Saving...' : 'Confirm upload'}
                </button>
              </div>
            </div>

            <div className="upload-summary">
              <div>
                <span>Total rows</span>
                <strong>{preview.total_rows}</strong>
              </div>
              <div>
                <span>Successful rows</span>
                <strong>{preview.successful_rows || preview.valid_rows}</strong>
              </div>
              <div>
                <span>Failed rows</span>
                <strong>{preview.failed_rows}</strong>
              </div>
              <div>
                <span>Import confidence</span>
                <strong>{Math.round((preview.import_confidence || 0) * 100)}%</strong>
              </div>
            </div>

            <div className="preview-table-wrapper">
              <table className="preview-table">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Description</th>
                    <th>Reference No.</th>
                    <th>Withdrawal</th>
                    <th>Deposit</th>
                    <th>Balance</th>
                    <th>Type</th>
                    <th>Amount</th>
                    <th>Category</th>
                    <th>Confidence</th>
                    <th>Method</th>
                  </tr>
                </thead>
                <tbody>
                  {preview.rows.length === 0 ? (
                    <tr>
                      <td colSpan="11">No valid rows to preview.</td>
                    </tr>
                  ) : (
                    preview.rows.map((row) => (
                      <tr key={`${row.row_number}-${row.description}`}>
                        <td>{formatDate(row.transaction_date || row.date)}</td>
                        <td>{row.description}</td>
                        <td>{row.reference_no || '-'}</td>
                        <td>{formatMoney(row.withdrawal_amount)}</td>
                        <td>{formatMoney(row.deposit_amount)}</td>
                        <td>{formatMoney(row.balance)}</td>
                        <td>{row.transaction_type}</td>
                        <td>{formatMoney(row.amount)}</td>
                        <td>
                          <select
                            className="preview-category-select"
                            value={row.category_id || ''}
                            onChange={(event) => handlePreviewCategoryChange(row.row_number, event.target.value)}
                          >
                            <option value="">Needs Review</option>
                            {getCategoriesForType(row.transaction_type)
                              .map((category) => (
                                <option key={category.id} value={category.id}>
                                  {category.name}
                                </option>
                              ))}
                          </select>
                        </td>
                        <td>
                          {confidencePercent(row.category_confidence)}
                          {row.requires_confirmation && <span className="suggestion-note">Confirm</span>}
                        </td>
                        <td>
                          <span className={`method-badge method-${row.categorization_method || 'needs_review'}`}>
                            {methodLabel(row.categorization_method)}
                          </span>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            {preview.failed_items?.length > 0 && (
              <div className="failed-rows">
                <h3>Failed rows</h3>
                {preview.failed_items.map((item, index) => (
                  <div className="failed-row" key={`${item.row_number || index}-${item.error}`}>
                    <strong>Row {item.row_number || index + 1}</strong>
                    <span>{item.error}</span>
                    <code>{JSON.stringify(item.raw_data)}</code>
                  </div>
                ))}
              </div>
            )}
          </section>
        )}
      </main>
    </div>
  );
};

export default UploadStatement;
