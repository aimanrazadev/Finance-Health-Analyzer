import { useEffect, useState } from 'react';
import { ChevronRight, Eye, Plus, Upload } from 'lucide-react';
import AppSelect from '../../components/ui/AppSelect';
import Navigation from '../../components/layout/Navigation';
import { useAuth } from '../../hooks/useAuth';
import api, { getAuthHeaders } from '../../services/api';
import './UploadStatement.css';

const MAX_PDF_SIZE = 10 * 1024 * 1024;

const moneyFormatter = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  minimumFractionDigits: 2,
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
  const [historyFilter, setHistoryFilter] = useState('all');
  const [visibleHistoryCount, setVisibleHistoryCount] = useState(4);

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
    const file = event.target.files?.[0] || null;
    setPreview(null);
    setError('');
    setSuccess('');

    if (file && !file.name.toLowerCase().endsWith('.pdf')) {
      setSelectedFile(null);
      event.target.value = '';
      setError('Choose a PDF bank statement. Other file formats are not supported.');
      return;
    }
    if (file && file.size > MAX_PDF_SIZE) {
      setSelectedFile(null);
      event.target.value = '';
      setError('PDF statements must be 10 MB or less.');
      return;
    }
    setSelectedFile(file);
  };

  const handlePreview = async (event) => {
    event.preventDefault();
    if (!selectedFile) {
      setError('Choose a PDF bank statement first.');
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
        file_type: 'pdf',
        bank_name: preview.bank_name,
        opening_balance: preview.opening_balance,
        closing_balance: preview.closing_balance,
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
  const getCategoriesForType = () => categories;
  const newestUploadTime = history.reduce((latest, item) => Math.max(latest, new Date(item.upload_date).getTime()), 0);
  const filteredHistory = historyFilter === 'recent'
    ? history.filter((item) => newestUploadTime - new Date(item.upload_date).getTime() <= 30 * 24 * 60 * 60 * 1000)
    : history;
  const visibleHistory = filteredHistory.slice(0, visibleHistoryCount);

  return (
    <div>
      <Navigation />
      <main className="upload-page">
        <div className="page-heading">
          <div>
            <h1>Upload PDF statement</h1>
            <p>Upload, view and manage your PDF statements</p>
          </div>
        </div>

        {error && <div className="surface-message error">{error}</div>}
        {success && <div className="surface-message success">{success}</div>}

        <section className="upload-layout">
          <div className="upload-left-column">
            <div className="upload-panel">
            <div className="upload-panel-heading">
              <div>
                <h2>Upload new statement</h2>
                <span>PDF only, up to 10 MB</span>
              </div>
              <span className="pdf-format-badge">PDF</span>
            </div>
            <form onSubmit={handlePreview} className="upload-form">
              <label className="statement-dropzone">
                <input type="file" accept="application/pdf,.pdf" onChange={handleFileChange} />
                <span className="dropzone-icon" aria-hidden="true"><Upload /></span>
                <span className="dropzone-title">Drag &amp; drop your PDF here</span>
                <span className="dropzone-or">or</span>
                <span className="dropzone-button">Choose file</span>
                <span className="dropzone-file-name">
                  {selectedFile ? `${selectedFile.name} / ${(selectedFile.size / 1024 / 1024).toFixed(2)} MB` : 'No file selected'}
                </span>
              </label>
              <button type="submit" className="primary-button preview-transactions-button" disabled={loadingPreview || !selectedFile}>
                <Eye aria-hidden="true" />
                {loadingPreview ? 'Reading PDF...' : 'Preview transactions'}
              </button>
            </form>
            </div>

            <div className="upload-panel import-profile-panel">
              <div className="profile-panel-heading">
                <div><h2>Import profiles</h2><p>Access and manage your saved import profiles</p></div>
                <button type="button" onClick={() => setSuccess('Import profiles are created automatically after a confirmed statement upload.')}><Plus /> Create new profile</button>
              </div>
              {importProfiles.length === 0 ? (
                <div className="empty-state">PDF bank profiles appear after a confirmed upload.</div>
              ) : (
                <div className="history-list">
                  {importProfiles.slice(0, 4).map((profile) => (
                    <div className="history-item" key={profile.id}>
                      <div className="profile-copy">
                        <strong>{profile.profile_name}</strong>
                        <span>{profile.bank_name || 'Bank format'}</span>
                        <i><span style={{ width: `${Math.round((profile.confidence_score || 0) * 100)}%` }} /></i>
                        <em>{Math.round((profile.confidence_score || 0) * 100)}% confidence</em>
                      </div>
                      <div className="profile-usage"><b>{profile.usage_count}</b><span>uses</span></div>
                      <ChevronRight className="profile-chevron" aria-hidden="true" />
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          <div className="upload-panel upload-history-panel">
            <div className="history-panel-heading">
              <div><h2>Upload history</h2><p>View and manage your previously uploaded statements</p></div>
              <AppSelect
                ariaLabel="Filter uploaded statements"
                value={historyFilter}
                onChange={setHistoryFilter}
                options={[{ value: 'all', label: 'All statements' }, { value: 'recent', label: 'Last 30 days' }]}
              />
            </div>
            {filteredHistory.length === 0 ? (
              <div className="empty-state">No statement uploads yet.</div>
            ) : (
              <div className="history-list">
                {visibleHistory.map((item) => (
                  <div className="history-item" key={item.id}>
                    <div>
                      <strong>{item.filename}</strong>
                      <span>{new Date(item.upload_date).toLocaleString()} {item.file_size ? ` · ${(item.file_size / 1024 / 1024).toFixed(1)} MB` : ''}</span>
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
                {visibleHistoryCount < filteredHistory.length && (
                  <button type="button" className="load-more-history" onClick={() => setVisibleHistoryCount((count) => count + 4)}>Load more statements</button>
                )}
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
                  {preview.file_name} / PDF import
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
              <div>
                <span>Opening balance</span>
                <strong>{preview.opening_balance === null || preview.opening_balance === undefined ? 'Not detected' : formatMoney(preview.opening_balance)}</strong>
              </div>
              <div>
                <span>Closing balance</span>
                <strong>{preview.closing_balance === null || preview.closing_balance === undefined ? 'Not detected' : formatMoney(preview.closing_balance)}</strong>
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
                          <AppSelect
                            className="preview-category-select"
                            value={row.category_id || ''}
                            onChange={(nextValue) => handlePreviewCategoryChange(row.row_number, nextValue)}
                            ariaLabel={`Category for ${row.description}`}
                            options={[
                              { value: '', label: 'Needs Review' },
                              ...getCategoriesForType(row.transaction_type)
                                .map((category) => ({ value: category.id, label: category.name })),
                            ]}
                          />
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
