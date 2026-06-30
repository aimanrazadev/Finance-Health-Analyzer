import { useCallback, useEffect, useMemo, useState } from 'react';
import { CalendarDays, ChevronRight, Copy, EyeOff, Search } from 'lucide-react';
import Navigation from '../components/Navigation';
import { useAuth } from '../hooks/useAuth';
import api, { getAuthHeaders } from '../utils/api';
import '../styles/Friends.css';

const moneyFormatter = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const formatMoney = (value) => moneyFormatter.format(Number(value || 0));
const formatDate = (value) => (value ? new Date(value).toLocaleDateString('en-GB') : '-');
const formatMemberSince = (value) => (value
  ? new Date(value).toLocaleDateString('en-US', { month: 'short', year: 'numeric' })
  : 'Unknown');
const formatTransactionAmount = (transaction) => {
  const amount = formatMoney(transaction.amount);
  return transaction.transaction_type === 'expense' ? `-${amount}` : amount;
};

const Friends = () => {
  const { token } = useAuth();
  const headers = useMemo(() => getAuthHeaders(token), [token]);
  const [dashboard, setDashboard] = useState({ active_friends: 0, linked_transactions: 0, friends: [] });
  const [selectedFriend, setSelectedFriend] = useState(null);
  const [detail, setDetail] = useState(null);
  const [friendName, setFriendName] = useState('');
  const [search, setSearch] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [copiedFriendId, setCopiedFriendId] = useState(null);

  const chooseSelectedFriend = useCallback((friends, preferredFriendId) => {
    setSelectedFriend((current) => {
      if (preferredFriendId) {
        return friends.find((friend) => friend.id === preferredFriendId) || current || friends[0] || null;
      }
      if (current) {
        return friends.find((friend) => friend.id === current.id) || friends[0] || null;
      }
      return friends[0] || null;
    });
  }, []);

  const loadFriends = useCallback(async (preferredFriendId = null) => {
    setLoading(true);
    setError('');
    try {
      const response = await api.get('/friends/dashboard', { headers });
      setDashboard(response.data);
      const friends = response.data.friends || [];
      chooseSelectedFriend(friends, preferredFriendId);
    } catch (err) {
      console.error(err);
      try {
        const fallback = await api.get('/friends', { headers });
        const friends = fallback.data || [];
        setDashboard({
          active_friends: friends.length,
          linked_transactions: friends.reduce((sum, friend) => sum + Number(friend.transaction_count || 0), 0),
          friends,
        });
        chooseSelectedFriend(friends, preferredFriendId);
      } catch (fallbackErr) {
        console.error(fallbackErr);
        const status = fallbackErr.response?.status;
        const detail = fallbackErr.response?.data?.detail;
        setError(detail || (status ? `Unable to load friends. Backend returned ${status}.` : 'Unable to load friends. Check that the backend is running on port 8000.'));
      }
    } finally {
      setLoading(false);
    }
  }, [chooseSelectedFriend, headers]);

  const loadFriendDetail = useCallback(async (friendId) => {
    if (!friendId) {
      setDetail(null);
      return;
    }
    try {
      const response = await api.get(`/friends/${friendId}`, { headers });
      setDetail(response.data);
    } catch (err) {
      console.error(err);
      setError('Unable to load friend transactions.');
    }
  }, [headers]);

  useEffect(() => {
    if (token) {
      void Promise.resolve().then(() => loadFriends());
    }
  }, [loadFriends, token]);

  useEffect(() => {
    void Promise.resolve().then(() => loadFriendDetail(selectedFriend?.id));
  }, [loadFriendDetail, selectedFriend]);

  const filteredFriends = (dashboard.friends || []).filter((friend) => {
    if (!search.trim()) return true;
    const term = search.trim().toLowerCase();
    return [friend.name, friend.normalized_name]
      .filter(Boolean)
      .some((value) => String(value).toLowerCase().includes(term));
  });

  const addFriend = async (event) => {
    event.preventDefault();
    if (!friendName.trim()) {
      setError('Enter a friend name first.');
      return;
    }
    setSaving(true);
    setError('');
    setMessage('');
    try {
      const response = await api.post('/friends', { name: friendName }, { headers });
      setMessage(response.data.message);
      setFriendName('');
      setSelectedFriend(response.data.friend);
      await loadFriends(response.data.friend.id);
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || 'Unable to save friend.');
    } finally {
      setSaving(false);
    }
  };

  const hideFriend = async (friendId) => {
    try {
      await api.delete(`/friends/${friendId}`, { headers });
      setSelectedFriend(null);
      setDetail(null);
      await loadFriends();
    } catch (err) {
      console.error(err);
      setError('Unable to hide friend.');
    }
  };

  const getFriendUpiId = (friend) => {
    const normalizedName = friend?.normalized_name || friend?.name || 'friend';
    return `${normalizedName.trim().toLowerCase().replace(/\s+/g, '.')}@upi`;
  };

  const copyFriendId = async (friend) => {
    try {
      await navigator.clipboard.writeText(getFriendUpiId(friend));
      setCopiedFriendId(friend.id);
      window.setTimeout(() => setCopiedFriendId(null), 1600);
    } catch (err) {
      console.error(err);
      setError('Unable to copy the friend ID.');
    }
  };

  return (
    <div>
      <Navigation />
      <main className="friends-page">
        <div className="friends-heading">
          <h1>Friends</h1>
        </div>

        {message && <div className="surface-message success">{message}</div>}
        {error && <div className="surface-message error">{error}</div>}

        <section className="friends-stats">
          <article>
            <span>Active friends</span>
            <strong>{dashboard.active_friends || 0}</strong>
          </article>
          <article>
            <span>Linked transactions</span>
            <strong>{dashboard.linked_transactions || 0}</strong>
          </article>
        </section>

        <section className="friends-workspace">
          <section className="friends-directory" aria-label="Friend directory">
            <form className="friend-form" onSubmit={addFriend}>
              <div className="friends-section-title">
                <h2>Friend Directory</h2>
                <div>
                  <span>{filteredFriends.length} shown</span>
                  <button className="friend-add-button plain-button" disabled={saving}>
                    {saving ? 'Saving...' : 'Add Friend'}
                  </button>
                </div>
              </div>
              <input
                value={friendName}
                onChange={(event) => setFriendName(event.target.value)}
                placeholder="Friend name"
                aria-label="Friend name"
              />
            </form>
            <label className="friend-search-control">
              <Search aria-hidden="true" />
              <input
                className="friend-search"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Search friends"
                aria-label="Search friends"
              />
            </label>

            <div className="friends-list">
              {loading ? (
                <div className="friends-empty">Loading friends...</div>
              ) : filteredFriends.length === 0 ? (
                <div className="friends-empty">No friends found yet.</div>
              ) : filteredFriends.map((friend) => (
                <button
                  type="button"
                  className={`friend-row plain-button ${selectedFriend?.id === friend.id ? 'active' : ''}`}
                  key={friend.id}
                  onClick={() => setSelectedFriend(friend)}
                >
                  <span>
                    <strong>{friend.name}</strong>
                    <small>
                      {friend.transaction_count || 0} txns - Last {formatDate(friend.last_transaction_at)}
                    </small>
                  </span>
                  <em>{formatMoney(friend.total_amount)}</em>
                  <ChevronRight className="friend-row-chevron" aria-hidden="true" />
                </button>
              ))}
            </div>
          </section>

          <section className="friend-detail" aria-label="Friend transaction detail">
            {!detail ? (
              <div className="friends-empty detail-empty">Select a friend to see linked transactions.</div>
            ) : (
              <>
                <div className="friend-detail-header">
                  <div className="friend-identity">
                    <h2>{detail.friend.name}</h2>
                    <div className="friend-id-row">
                      <span>UPI ID: {getFriendUpiId(detail.friend)}</span>
                      <button
                        type="button"
                        className="copy-friend-id plain-button"
                        onClick={() => copyFriendId(detail.friend)}
                        title={copiedFriendId === detail.friend.id ? 'Copied' : 'Copy UPI ID'}
                        aria-label={copiedFriendId === detail.friend.id ? 'UPI ID copied' : 'Copy UPI ID'}
                      >
                        <Copy aria-hidden="true" />
                      </button>
                    </div>
                    <p className="friend-member-since">
                      <CalendarDays aria-hidden="true" />
                      Member since {formatMemberSince(detail.friend.created_at)}
                    </p>
                  </div>
                  <div className="friend-detail-total">
                    <strong>{formatMoney(detail.friend.total_amount)}</strong>
                    <span>Total Balance</span>
                    <button className="hide-details-button plain-button" onClick={() => hideFriend(detail.friend.id)}>
                      <EyeOff aria-hidden="true" />
                      Hide Details
                    </button>
                  </div>
                </div>

                <div className="friend-transactions-heading">
                  <h3>All Transactions</h3>
                  <span>{detail.friend.transaction_count || 0} linked</span>
                </div>
                <div className="friend-transaction-list friend-transaction-table-wrapper">
                  {(detail.transactions || []).length === 0 ? (
                    <div className="friends-empty">No linked transactions yet.</div>
                  ) : (
                    <table className="friend-transaction-table">
                      <thead>
                        <tr>
                          <th>Date</th>
                          <th>Description</th>
                          <th>Type</th>
                          <th>Amount</th>
                        </tr>
                      </thead>
                      <tbody>
                        {detail.transactions.map((transaction) => (
                          <tr key={transaction.id}>
                            <td>{formatDate(transaction.date)}</td>
                            <td>
                              <strong>{transaction.extracted_merchant || transaction.merchant || detail.friend.name}</strong>
                              <span>{transaction.description}</span>
                            </td>
                            <td className={`transaction-type ${transaction.transaction_type}`}>{transaction.transaction_type}</td>
                            <td className={transaction.transaction_type}>{formatTransactionAmount(transaction)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              </>
            )}
          </section>
        </section>
      </main>
    </div>
  );
};

export default Friends;
